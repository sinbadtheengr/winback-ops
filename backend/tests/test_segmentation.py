from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import datasets
from app.core.database import list_runs
from app.main import app
from app.services import segmentation


REPOSITORY_DIRECTORY = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "fixture_name",
    ["clinic_a.csv", "clinic_b.csv", "clinic_c.csv", "clinic_adversarial.csv"],
)
def test_demo_pipeline_handles_all_seeded_clinics(monkeypatch, tmp_path, fixture_name: str) -> None:
    """Each published fixture must clear profile and verified segmentation."""
    monkeypatch.setattr(datasets, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("DEMO_MODE", "true")
    client = TestClient(app)
    contents = (REPOSITORY_DIRECTORY / "sample_data" / fixture_name).read_bytes()

    upload = client.post("/api/datasets", files={"file": (fixture_name, contents, "text/csv")})
    assert upload.status_code == 201
    dataset_id = upload.json()["id"]

    assert client.post(f"/api/datasets/{dataset_id}/profile").status_code == 200
    segmentation_response = client.post(f"/api/datasets/{dataset_id}/segment")

    assert segmentation_response.status_code == 200
    result = segmentation_response.json()
    clients = [client for segment in result["segments"] for client in segment["clients"]]
    assert result["totals"]["dormant_clients"] == len(clients)
    assert result["totals"]["recoverable_revenue"] == round(
        sum(segment["recoverable_revenue"] for segment in result["segments"]), 2
    )


def test_failed_sandbox_attempt_is_repaired_and_logged(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(datasets, "UPLOADS_DIRECTORY", tmp_path / "uploads")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("DEMO_MODE", "true")
    client = TestClient(app)
    contents = (REPOSITORY_DIRECTORY / "sample_data" / "clinic_a.csv").read_bytes()
    upload = client.post("/api/datasets", files={"file": ("clinic_a.csv", contents, "text/csv")})
    dataset_id = upload.json()["id"]
    assert client.post(f"/api/datasets/{dataset_id}/profile").status_code == 200

    safe_generator = segmentation.generate_demo_segmenter
    monkeypatch.setattr(segmentation, "generate_demo_segmenter", lambda _: "import os")
    monkeypatch.setattr(
        segmentation,
        "repair_demo_segmenter",
        lambda profile, error, attempt: safe_generator(profile),
    )

    result = segmentation.segment_dataset(dataset_id)

    assert result.totals["dormant_clients"] > 0
    runs = list_runs(dataset_id)
    assert [run["agent_name"] for run in runs] == [
        "profiler",
        "codegen",
        "sandbox",
        "codegen_repair",
        "sandbox",
    ]
    assert runs[2]["status"] == "failed"
    assert runs[-1]["status"] == "completed"
