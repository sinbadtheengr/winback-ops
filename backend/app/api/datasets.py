"""Day 1 dataset upload endpoint and lightweight CSV inspection."""
from __future__ import annotations

import csv
import io
from pathlib import Path
import re
from uuid import uuid4

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.core.database import delete_dataset_records, get_profile, list_runs
from app.core.models import Campaign, DatasetProfile, DatasetUploadResponse, RunActivity, SegmentationResult

router = APIRouter(tags=["datasets"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
UPLOADS_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "uploads"


def get_dataset_path(dataset_id: str) -> Path:
    """Return the stored upload path while preventing path traversal."""
    if not re.fullmatch(r"[a-f0-9]{32}", dataset_id):
        raise FileNotFoundError(dataset_id)
    path = UPLOADS_DIRECTORY / f"{dataset_id}.csv"
    if not path.is_file():
        raise FileNotFoundError(dataset_id)
    return path


def _read_csv_metadata(contents: bytes) -> tuple[list[str], int]:
    """Return header names and data-row count for a UTF-8 CSV payload."""
    try:
        decoded = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSV files must be UTF-8 encoded.",
        ) from exc

    # Detect from the header first: later quoted free-text fields can make the
    # full sample ambiguous even when the delimiter is clear in row one.
    header_line = decoded.splitlines()[0] if decoded.splitlines() else ""
    try:
        dialect = csv.Sniffer().sniff(header_line, delimiters=",;\t")
    except csv.Error:
        try:
            dialect = csv.Sniffer().sniff(decoded[:4096], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel

    rows = csv.reader(io.StringIO(decoded), dialect)
    try:
        columns = next(rows)
    except StopIteration as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The CSV is empty.",
        ) from exc

    normalized_columns = [column.strip() for column in columns]
    if not any(normalized_columns):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The CSV must include a header row.",
        )

    return normalized_columns, sum(1 for row in rows if any(cell.strip() for cell in row))


@router.post("/datasets", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile) -> DatasetUploadResponse:
    """Store a raw clinic CSV and return basic, non-agent metadata."""
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only .csv files are supported.",
        )

    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded file is empty.",
        )
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="CSV uploads must be 10 MB or smaller.",
        )

    columns, row_count = _read_csv_metadata(contents)
    dataset_id = uuid4().hex
    UPLOADS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    stored_path = UPLOADS_DIRECTORY / f"{dataset_id}.csv"
    stored_path.write_bytes(contents)

    return DatasetUploadResponse(
        id=dataset_id,
        filename=filename,
        byte_size=len(contents),
        row_count=row_count,
        columns=columns,
    )


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> dict[str, str]:
    """Delete a local upload and all derived demo data."""
    try:
        path = get_dataset_path(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.") from exc
    path.unlink()
    delete_dataset_records(dataset_id)
    return {"status": "deleted"}


@router.post("/datasets/{dataset_id}/profile", response_model=DatasetProfile)
async def profile_dataset_upload(dataset_id: str) -> DatasetProfile:
    """Create a GPT-5.6 schema/cadence profile for an already-stored CSV."""
    from app.agents.profiler import DatasetNotFoundError, ProfilingError, profile_dataset

    try:
        return await run_in_threadpool(profile_dataset, dataset_id)
    except DatasetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.") from exc
    except ProfilingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.public_message,
        ) from exc


@router.get("/datasets/{dataset_id}/profile", response_model=DatasetProfile)
def get_dataset_profile(dataset_id: str) -> DatasetProfile:
    """Return the latest persisted profile without calling the model again."""
    profile = get_profile(dataset_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return profile


@router.post("/datasets/{dataset_id}/segment", response_model=SegmentationResult)
async def segment_dataset_upload(dataset_id: str) -> SegmentationResult:
    from app.services.segmentation import SegmentationError, segment_dataset

    try:
        return await run_in_threadpool(segment_dataset, dataset_id)
    except SegmentationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/datasets/{dataset_id}/campaigns", response_model=list[Campaign])
async def create_dataset_campaigns(dataset_id: str) -> list[Campaign]:
    from app.services.campaigns import CampaignError, create_campaigns
    try:
        return await run_in_threadpool(create_campaigns, dataset_id)
    except CampaignError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/datasets/{dataset_id}/campaigns", response_model=list[Campaign])
def list_dataset_campaigns(dataset_id: str) -> list[Campaign]:
    from app.services.campaigns import list_campaigns
    return list_campaigns(dataset_id)


@router.post("/campaigns/{campaign_id}/approve", response_model=Campaign)
async def approve_campaign_send(campaign_id: str) -> Campaign:
    from app.services.campaigns import CampaignError, approve_and_mock_send
    try:
        return await run_in_threadpool(approve_and_mock_send, campaign_id)
    except CampaignError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/datasets/{dataset_id}/runs", response_model=list[RunActivity])
def get_dataset_runs(dataset_id: str) -> list[RunActivity]:
    return [RunActivity.model_validate(run) for run in list_runs(dataset_id)]


@router.get("/datasets/{dataset_id}/runs/stream")
async def stream_dataset_runs(dataset_id: str, request: Request) -> StreamingResponse:
    """Stream run-log snapshots for the Day 5 agent activity panel."""
    async def events():
        previous = ""
        while not await request.is_disconnected():
            payload = json.dumps(list_runs(dataset_id))
            if payload != previous:
                yield f"event: runs\ndata: {payload}\n\n"
                previous = payload
            else:
                yield ": keepalive\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(events(), media_type="text/event-stream")
