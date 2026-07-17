import sqlite3
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.agents import profiler
from app.api import datasets
from app.core.models import (
    ColumnMapping,
    DatasetProfile,
    DormancyRule,
    HoldoutAssertion,
    ServiceTaxonomyEntry,
)
from app.main import app


def example_profile() -> DatasetProfile:
    return DatasetProfile(
        summary="A visit-level clinic export with messy Botox variants.",
        column_mapping=ColumnMapping(
            client_identifier=["email"],
            customer_name=["client_name"],
            email="email",
            service="service",
            appointment_date="appt_date",
            amount_paid="amount_paid",
        ),
        service_taxonomy=[
            ServiceTaxonomyEntry(
                canonical_service="Botox",
                observed_variants=["Botox", "BOTOX 50u"],
                cadence_days=90,
                rationale="The treatment is a neurotoxin service.",
            )
        ],
        dormancy_rules=[
            DormancyRule(
                canonical_service="Botox",
                dormant_after_days=135,
                rationale="This allows a conservative buffer after the 90-day cadence.",
            )
        ],
        holdout_assertions=[
            HoldoutAssertion(
                assertion="Every segmented row must have a parseable appointment date.",
                rationale="Dates drive the dormancy calculation.",
            )
        ],
    )


def test_profiler_persists_profile_and_run(monkeypatch, tmp_path) -> None:
    dataset_id = "a" * 32
    monkeypatch.setattr(datasets, "UPLOADS_DIRECTORY", tmp_path)
    (tmp_path / f"{dataset_id}.csv").write_text(
        "client_name,email,service,appt_date,amount_paid\nMaya,maya@example.com,Botox,2026-01-01,300\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr(profiler, "get_openai_api_key", lambda: "test-key")

    response = SimpleNamespace(
        output_parsed=example_profile(),
        usage=SimpleNamespace(input_tokens=12, output_tokens=34),
    )
    monkeypatch.setattr(
        profiler,
        "OpenAI",
        lambda api_key: SimpleNamespace(responses=SimpleNamespace(parse=lambda **_: response)),
    )

    result = profiler.profile_dataset(dataset_id)

    assert result.column_mapping.service == "service"
    assert (tmp_path / "test.sqlite3").is_file()
    with sqlite3.connect(tmp_path / "test.sqlite3") as connection:
        run = connection.execute(
            "SELECT status, input_tokens, output_tokens FROM runs"
        ).fetchone()
    assert run == ("completed", 12, 34)


def test_profile_endpoint_uses_profiler_result(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(datasets, "UPLOADS_DIRECTORY", tmp_path)
    monkeypatch.setattr(profiler, "profile_dataset", lambda _: example_profile())
    client = TestClient(app)
    upload = client.post(
        "/api/datasets",
        files={"file": ("clinic.csv", b"name,service\nMaya,Botox\n", "text/csv")},
    )

    response = client.post(f"/api/datasets/{upload.json()['id']}/profile")

    assert response.status_code == 200
    assert response.json()["service_taxonomy"][0]["cadence_days"] == 90


def test_profile_endpoint_returns_safe_actionable_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(datasets, "UPLOADS_DIRECTORY", tmp_path)
    monkeypatch.setattr(
        profiler,
        "profile_dataset",
        lambda _: (_ for _ in ()).throw(
            profiler.ProfilingError("provider details", "OpenAI API billing quota is exhausted.")
        ),
    )
    client = TestClient(app)
    upload = client.post(
        "/api/datasets",
        files={"file": ("clinic.csv", b"name,service\nMaya,Botox\n", "text/csv")},
    )

    response = client.post(f"/api/datasets/{upload.json()['id']}/profile")

    assert response.status_code == 502
    assert response.json()["detail"] == "OpenAI API billing quota is exhausted."
