"""GPT-5.6 structured-output profiling for a stored clinic CSV."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any

from openai import AuthenticationError, NotFoundError, OpenAI, PermissionDeniedError, RateLimitError

from app.api.datasets import get_dataset_path
from app.core.config import get_openai_api_key, get_openai_model, is_demo_mode
from app.core.database import complete_run, create_run, save_profile
from app.core.models import (
    ColumnMapping,
    DataQuirk,
    DatasetProfile,
    DormancyRule,
    ServiceTaxonomyEntry,
)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "profiler.md"
MAX_SAMPLE_ROWS = 100
SENSITIVE_HEADER_TERMS = (
    "name",
    "email",
    "phone",
    "contact",
    "customer",
    "client",
    "first",
    "last",
)


class DatasetNotFoundError(FileNotFoundError):
    """Raised when a requested upload is not available for profiling."""


class ProfilingError(RuntimeError):
    """Raised when the profiler cannot create a validated profile."""

    def __init__(self, message: str, public_message: str | None = None) -> None:
        super().__init__(message)
        self.public_message = public_message or "The profiler could not create a dataset profile."


def _csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    contents = path.read_text(encoding="utf-8-sig")
    header_line = contents.splitlines()[0] if contents.splitlines() else ""
    try:
        dialect = csv.Sniffer().sniff(header_line, delimiters=",;\t")
    except csv.Error:
        try:
            dialect = csv.Sniffer().sniff(contents[:4096], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
    reader = csv.DictReader(io.StringIO(contents), dialect=dialect)
    headers = reader.fieldnames or []
    return headers, [dict(row) for row in reader]


def _sample_rows(headers: list[str], rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(rows) <= MAX_SAMPLE_ROWS:
        sample = rows
    else:
        step = len(rows) / MAX_SAMPLE_ROWS
        sample = [rows[int(index * step)] for index in range(MAX_SAMPLE_ROWS)]

    redacted_headers = {
        header for header in headers if any(term in header.lower() for term in SENSITIVE_HEADER_TERMS)
    }
    return [
        {
            header: "<redacted>" if header in redacted_headers else (row.get(header) or "")[:300]
            for header in headers
        }
        for row in sample
    ]


def _dataset_context(path: Path) -> str:
    headers, rows = _csv_rows(path)
    payload = {
        "headers": headers,
        "row_count": len(rows),
        "sample_rows": _sample_rows(headers, rows),
    }
    return json.dumps(payload, ensure_ascii=False)


def _usage_tokens(response: Any, name: str) -> int | None:
    usage = getattr(response, "usage", None)
    value = getattr(usage, name, None)
    return value if isinstance(value, int) else None


def _public_error_message(error: Exception) -> str:
    """Translate known provider failures into an actionable, secret-safe UI message."""
    if isinstance(error, AuthenticationError):
        return "OpenAI rejected the API key. Replace OPENAI_API_KEY with the full active key and retry."
    if isinstance(error, (NotFoundError, PermissionDeniedError)):
        return "The configured OpenAI model is not available to this API project. Check OPENAI_MODEL access."
    if isinstance(error, RateLimitError):
        if getattr(error, "code", None) == "insufficient_quota" or "insufficient_quota" in str(error):
            return "OpenAI API billing quota is exhausted. Add API billing credit or raise the project budget, then retry."
        return "OpenAI API rate limit reached. Wait briefly, then retry."
    return "OpenAI could not complete profiling. Check the backend run log and retry."


def _validate_column_mapping(profile: DatasetProfile, headers: list[str]) -> None:
    """Reject a syntactically valid profile that invents CSV headers."""
    mapping = profile.column_mapping
    referenced_columns = [
        *mapping.client_identifier,
        *mapping.customer_name,
        mapping.email,
        mapping.phone,
        mapping.service,
        mapping.appointment_date,
        mapping.amount_paid,
        mapping.notes,
    ]
    unknown_columns = sorted(
        {column for column in referenced_columns if column is not None and column not in headers}
    )
    if unknown_columns:
        raise ProfilingError(
            f"The model mapped fields to columns not present in the CSV: {', '.join(unknown_columns)}."
        )


def _first_header(headers: list[str], choices: tuple[str, ...]) -> str | None:
    return next((header for header in headers if any(choice in header.lower() for choice in choices)), None)


def _demo_profile(headers: list[str]) -> DatasetProfile:
    """Offline profile for the supplied intentionally messy clinic fixtures."""
    service = _first_header(headers, ("service", "treatment", "procedure", "svc"))
    appointment_date = _first_header(headers, ("date", "visit", "completed"))
    amount = _first_header(headers, ("amount", "price", "total", "paid"))
    email = _first_header(headers, ("email",))
    phone = _first_header(headers, ("phone",))
    names = [header for header in headers if any(word in header.lower() for word in ("name", "first", "last", "customer"))]
    if not service or not appointment_date:
        raise ProfilingError("Demo mode could not identify service and date columns.")
    identifier = [email] if email else [phone] if phone else names
    taxonomy = [
        ("botox", ["botox", "neurotoxin", "tox"], 90),
        ("laser", ["laser", "lhr", "ipl", "laser hair removal"], 45),
        ("facial", ["facial", "hydrafacial", "hydra facial"], 30),
        ("filler", ["filler"], 180),
        ("microneedling", ["microneedling", "skinpen"], 42),
    ]
    return DatasetProfile(
        summary="Demo profile generated locally from the uploaded clinic export.",
        column_mapping=ColumnMapping(client_identifier=identifier, customer_name=names, email=email, phone=phone, service=service, appointment_date=appointment_date, amount_paid=amount, notes=_first_header(headers, ("note",))),
        service_taxonomy=[ServiceTaxonomyEntry(canonical_service=name, observed_variants=variants, cadence_days=cadence, rationale="Demo fixture cadence.") for name, variants, cadence in taxonomy],
        dormancy_rules=[DormancyRule(canonical_service=name, dormant_after_days=round(cadence * 1.5), rationale="Conservative 1.5x cadence threshold.") for name, _, cadence in taxonomy],
        data_quirks=[DataQuirk(category="demo_mode", detail="Local deterministic profile; no OpenAI API call was made.")],
    )


def profile_dataset(dataset_id: str) -> DatasetProfile:
    """Call GPT-5.6, validate its structured response, and persist the result."""
    try:
        dataset_path = get_dataset_path(dataset_id)
    except FileNotFoundError as exc:
        raise DatasetNotFoundError(dataset_id) from exc

    headers, _ = _csv_rows(dataset_path)
    dataset_context = _dataset_context(dataset_path)
    input_hash = hashlib.sha256(dataset_context.encode("utf-8")).hexdigest()
    model = "demo-profiler" if is_demo_mode() else get_openai_model()
    run_id = create_run(dataset_id=dataset_id, input_hash=input_hash, model=model)
    started_at = time.perf_counter()

    if is_demo_mode():
        profile = _demo_profile(headers)
        save_profile(dataset_id, profile)
        complete_run(run_id, status="completed", latency_ms=0, output=profile.model_dump_json())
        return profile

    try:
        response = OpenAI(api_key=get_openai_api_key()).responses.parse(
            model=model,
            instructions=PROMPT_PATH.read_text(encoding="utf-8"),
            input=dataset_context,
            text_format=DatasetProfile,
        )
        if response.output_parsed is None:
            raise ProfilingError("The model returned no structured profile.")
        profile = DatasetProfile.model_validate(response.output_parsed)
        _validate_column_mapping(profile, headers)
        save_profile(dataset_id, profile)
        complete_run(
            run_id,
            status="completed",
            latency_ms=round((time.perf_counter() - started_at) * 1000),
            input_tokens=_usage_tokens(response, "input_tokens"),
            output_tokens=_usage_tokens(response, "output_tokens"),
            output=profile.model_dump_json(),
        )
        return profile
    except Exception as exc:
        complete_run(
            run_id,
            status="failed",
            latency_ms=round((time.perf_counter() - started_at) * 1000),
            error=str(exc),
        )
        if isinstance(exc, ProfilingError):
            raise
        raise ProfilingError(
            "The profiler could not create a dataset profile.", _public_error_message(exc)
        ) from exc
