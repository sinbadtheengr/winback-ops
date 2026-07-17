"""Deterministic codegen and repair fallback used only when DEMO_MODE is enabled."""
from __future__ import annotations

import json

from app.core.config import get_segmentation_as_of_date
from app.core.models import DatasetProfile


def generate_demo_segmenter(profile: DatasetProfile) -> str:
    """Build a self-contained segmenter tailored to the profiled CSV columns."""
    mapping = profile.column_mapping.model_dump()
    cadences = {item.canonical_service.lower(): item.cadence_days for item in profile.service_taxonomy}
    aliases = {
        variant.strip().lower(): item.canonical_service.lower()
        for item in profile.service_taxonomy
        for variant in item.observed_variants
    }
    identity_columns = list(dict.fromkeys([
        *mapping["client_identifier"], *mapping["customer_name"],
        *([mapping["phone"]] if mapping["phone"] else []),
    ]))
    config = json.dumps({"mapping": mapping, "cadences": cadences, "aliases": aliases,
                         "identity_columns": identity_columns,
                         "as_of_date": get_segmentation_as_of_date().isoformat()})
    return f'''import json
import re
from datetime import date
import pandas as pd

CONFIG = json.loads({config!r})
TODAY = date.fromisoformat(CONFIG["as_of_date"])
RATES = {{"1x_overdue": 0.35, "2x_overdue": 0.20, "3x_plus": 0.10}}

def normalized(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())

def canonical_service(value):
    value = normalized(value)
    for alias, canonical in CONFIG["aliases"].items():
        if normalized(alias) in value:
            return canonical
    return "other"

def client_key(row):
    for column in CONFIG["identity_columns"]:
        value = str(row[column]).strip()
        if value and value.lower() not in {{"nan", "none"}}:
            return f"{{column}}:{{normalized(value)}}"
    return ""

def main(path):
    df = pd.read_csv(path, sep=None, engine="python").drop_duplicates()
    m = CONFIG["mapping"]
    df["client_key"] = df.apply(client_key, axis=1)
    df["service"] = df[m["service"]].map(canonical_service)
    df["visit_date"] = pd.to_datetime(df[m["appointment_date"]], errors="coerce")
    amount = m.get("amount_paid")
    df["amount"] = pd.to_numeric(df[amount].astype(str).str.replace(r"[^0-9.-]", "", regex=True), errors="coerce").fillna(0) if amount else 0
    df = df.dropna(subset=["visit_date"])
    df = df[(df["client_key"] != "") & (df["service"] != "other")]
    groups = {{}}
    for (key, service), group in df.groupby(["client_key", "service"]):
        last = group["visit_date"].max().date()
        cadence = CONFIG["cadences"].get(service, 60)
        days = (TODAY - last).days
        if days <= cadence: continue
        bucket = "1x_overdue" if days < cadence*2 else "2x_overdue" if days < cadence*3 else "3x_plus"
        groups.setdefault(f"{{service}}_{{bucket}}", []).append({{"client_key": str(key), "last_visit": last.isoformat(), "primary_service": service, "days_overdue": max(0, days-cadence), "lifetime_value": round(float(group["amount"].sum()), 2), "avg_ticket": round(float(group["amount"].mean()), 2), "bucket": bucket}})
    segments = []
    for name, clients in sorted(groups.items()):
        revenue = round(sum(c["avg_ticket"] * RATES[c.pop("bucket")] for c in clients), 2)
        segments.append({{"name": name, "clients": clients, "recoverable_revenue": revenue}})
    print(json.dumps({{"segments": segments, "totals": {{"dormant_clients": sum(len(s["clients"]) for s in segments), "recoverable_revenue": round(sum(s["recoverable_revenue"] for s in segments), 2)}}}}))

main("__CSV_PATH__")
'''


def repair_demo_segmenter(profile: DatasetProfile, error: str, attempt: int) -> str:
    """Return the known-safe regenerated script after a failed sandbox attempt.

    Demo mode intentionally stays offline, so this is a deterministic repair
    fallback rather than an LLM call. The orchestration and run log mirror the
    live GPT-5.6 repair loop and make each repair visible to the dashboard.
    """
    del error, attempt
    return generate_demo_segmenter(profile)
