from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_upload_csv_returns_metadata_and_stores_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.api.datasets.UPLOADS_DIRECTORY", tmp_path)

    response = client.post(
        "/api/datasets",
        files={"file": ("clinic.csv", b"name,service\nMaya,Botox\n", "text/csv")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "clinic.csv"
    assert data["row_count"] == 1
    assert data["columns"] == ["name", "service"]
    assert (tmp_path / f"{data['id']}.csv").read_bytes().startswith(b"name,service")


def test_upload_rejects_non_csv_file() -> None:
    response = client.post(
        "/api/datasets",
        files={"file": ("clinic.xlsx", b"not a csv", "application/octet-stream")},
    )

    assert response.status_code == 415
