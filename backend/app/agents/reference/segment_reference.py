"""REFERENCE segmentation implementation.

This is the anchor script shown to the codegen agent. It assumes a clean,
canonical schema. The agent's job is to produce a variant of this that
handles the *actual* uploaded dataset's schema and quirks (per the
DatasetProfile), while preserving the output contract below.

Adapt this from RelayOps' segment.py — replace the body with your real
segmentation logic on Day 3.

OUTPUT CONTRACT (the sandbox validates this):
    result = {
        "segments": [
            {
                "name": str,              # e.g. "high_value_botox_lapsed"
                "clients": [
                    {
                        "client_key": str,     # email or name+phone
                        "last_visit": "YYYY-MM-DD",
                        "primary_service": str,   # canonical service key
                        "days_overdue": int,
                        "lifetime_value": float,
                        "avg_ticket": float,
                    }
                ],
                "recoverable_revenue": float,
            }
        ],
        "totals": {"dormant_clients": int, "recoverable_revenue": float},
    }
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

TODAY = date(2026, 7, 14)

# Canonical cadences (days). The profiler may override per dataset.
CADENCE = {"botox": 90, "laser": 45, "facial": 30, "filler": 180, "microneedling": 42}
EXPECTED_RETURN_RATE = {"1x_overdue": 0.35, "2x_overdue": 0.20, "3x_plus": 0.10}


def segment(df: pd.DataFrame) -> dict:
    """df columns (canonical): client_key, service, visit_date, amount."""
    df = df.copy()
    df["visit_date"] = pd.to_datetime(df["visit_date"]).dt.date

    out_segments: dict[str, list[dict]] = {}
    for key, g in df.groupby("client_key"):
        last_visit = g["visit_date"].max()
        primary = g["service"].mode().iat[0]
        cadence = CADENCE.get(primary, 60)
        days_since = (TODAY - last_visit).days
        if days_since <= cadence:
            continue  # active client
        overdue_ratio = days_since / cadence
        bucket = ("1x_overdue" if overdue_ratio < 2
                  else "2x_overdue" if overdue_ratio < 3 else "3x_plus")
        seg_name = f"{primary}_{bucket}"
        out_segments.setdefault(seg_name, []).append({
            "client_key": key,
            "last_visit": last_visit.isoformat(),
            "primary_service": primary,
            "days_overdue": days_since - cadence,
            "lifetime_value": round(float(g["amount"].sum()), 2),
            "avg_ticket": round(float(g["amount"].mean()), 2),
            "_bucket": bucket,
        })

    segments = []
    total_rev = 0.0
    total_clients = 0
    for name, clients in sorted(out_segments.items()):
        rev = round(sum(c["avg_ticket"] * EXPECTED_RETURN_RATE[c.pop("_bucket")]
                        for c in clients), 2)
        segments.append({"name": name, "clients": clients,
                         "recoverable_revenue": rev})
        total_rev += rev
        total_clients += len(clients)

    return {"segments": segments,
            "totals": {"dormant_clients": total_clients,
                       "recoverable_revenue": round(total_rev, 2)}}


if __name__ == "__main__":
    import sys
    df = pd.read_csv(sys.argv[1])
    print(json.dumps(segment(df), indent=2))
