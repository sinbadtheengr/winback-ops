"""SQLite persistence for Day 2 profiles and the required agent run log."""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import get_database_path
from app.core.models import DatasetProfile


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _connect() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    _initialize(connection)
    return connection


def _initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            latency_ms INTEGER,
            output TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS dataset_profiles (
            dataset_id TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS segmentations (
            dataset_id TEXT PRIMARY KEY, result_json TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, campaign_json TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """
    )


def create_run(*, dataset_id: str, input_hash: str, model: str, agent_name: str = "profiler") -> str:
    run_id = uuid4().hex
    with _connect() as connection:
        connection.execute(
            """INSERT INTO runs (id, dataset_id, agent_name, input_hash, model, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'running', ?)""",
            (run_id, dataset_id, agent_name, input_hash, model, _utc_now()),
        )
    return run_id


def complete_run(
    run_id: str,
    *,
    status: str,
    latency_ms: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    output: str | None = None,
    error: str | None = None,
) -> None:
    with _connect() as connection:
        connection.execute(
            """UPDATE runs
            SET status = ?, input_tokens = ?, output_tokens = ?, latency_ms = ?, output = ?, error = ?, completed_at = ?
            WHERE id = ?""",
            (status, input_tokens, output_tokens, latency_ms, output, error, _utc_now(), run_id),
        )


def save_profile(dataset_id: str, profile: DatasetProfile) -> None:
    now = _utc_now()
    payload = profile.model_dump_json()
    with _connect() as connection:
        connection.execute("DELETE FROM segmentations WHERE dataset_id = ?", (dataset_id,))
        connection.execute("DELETE FROM campaigns WHERE dataset_id = ?", (dataset_id,))
        connection.execute(
            """INSERT INTO dataset_profiles (dataset_id, profile_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(dataset_id) DO UPDATE SET profile_json = excluded.profile_json, updated_at = excluded.updated_at""",
            (dataset_id, payload, now, now),
        )


def get_profile(dataset_id: str) -> DatasetProfile | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT profile_json FROM dataset_profiles WHERE dataset_id = ?", (dataset_id,)
        ).fetchone()
    return DatasetProfile.model_validate_json(row["profile_json"]) if row else None


def save_segmentation(dataset_id: str, result_json: str) -> None:
    with _connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS segmentations (
                dataset_id TEXT PRIMARY KEY, result_json TEXT NOT NULL, updated_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """INSERT INTO segmentations (dataset_id, result_json, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(dataset_id) DO UPDATE SET result_json = excluded.result_json, updated_at = excluded.updated_at""",
            (dataset_id, result_json, _utc_now()),
        )


def get_segmentation(dataset_id: str) -> str | None:
    with _connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS segmentations (
                dataset_id TEXT PRIMARY KEY, result_json TEXT NOT NULL, updated_at TEXT NOT NULL
            )"""
        )
        row = connection.execute("SELECT result_json FROM segmentations WHERE dataset_id = ?", (dataset_id,)).fetchone()
    return str(row["result_json"]) if row else None


def save_campaigns(campaigns: list[dict[str, object]]) -> None:
    with _connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, campaign_json TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL
            )"""
        )
        if campaigns:
            connection.execute("DELETE FROM campaigns WHERE dataset_id = ?", (campaigns[0]["dataset_id"],))
        for campaign in campaigns:
            connection.execute(
                "INSERT OR REPLACE INTO campaigns (id, dataset_id, campaign_json, status, updated_at) VALUES (?, ?, ?, ?, ?)",
                (campaign["id"], campaign["dataset_id"], json.dumps(campaign), campaign["status"], _utc_now()),
            )


def get_campaigns(dataset_id: str) -> list[dict[str, object]]:
    with _connect() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, campaign_json TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL)")
        rows = connection.execute("SELECT campaign_json FROM campaigns WHERE dataset_id = ? ORDER BY updated_at", (dataset_id,)).fetchall()
    return [json.loads(str(row["campaign_json"])) for row in rows]


def approve_campaign(campaign_id: str, status: str) -> dict[str, object] | None:
    with _connect() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, campaign_json TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL)")
        row = connection.execute("SELECT campaign_json FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if row is None:
            return None
        campaign = json.loads(str(row["campaign_json"]))
        if campaign.get("status") != "draft":
            return None
        campaign["status"] = status
        campaign["approved_at"] = _utc_now()
        connection.execute("UPDATE campaigns SET campaign_json = ?, status = ?, updated_at = ? WHERE id = ?", (json.dumps(campaign), status, _utc_now(), campaign_id))
    return campaign


def delete_dataset_records(dataset_id: str) -> None:
    """Permanently remove locally stored derived data for an uploaded dataset."""
    with _connect() as connection:
        for table in ("dataset_profiles", "segmentations", "campaigns", "runs"):
            connection.execute(f"DELETE FROM {table} WHERE dataset_id = ?", (dataset_id,))


def list_runs(dataset_id: str) -> list[dict[str, object]]:
    with _connect() as connection:
        rows = connection.execute(
            """SELECT id, agent_name, model, status, latency_ms, created_at
            FROM runs WHERE dataset_id = ? ORDER BY created_at""",
            (dataset_id,),
        ).fetchall()
    return [dict(row) for row in rows]
