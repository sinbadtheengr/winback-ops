"""Generate realistic, *messy* med-spa booking exports.

Three clinics, three different schemas, three different flavors of dirty data.
The codegen agent must handle all of them — that's the whole point.

Usage: python scripts/generate_sample_data.py
Output: sample_data/clinic_{a,b,c}.csv
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).resolve().parent.parent / "sample_data"
OUT.mkdir(exist_ok=True)

FIRST = ["Maya", "Jess", "Priya", "Hannah", "Dana", "Sofia", "Grace", "Amara",
         "Nicole", "Leah", "Tara", "Ivy", "Rosa", "Elena", "Kim", "Farah"]
LAST = ["Nguyen", "Smith", "Patel", "Garcia", "Chen", "Ali", "Brown", "Kaur",
        "Rossi", "Lee", "Silva", "Khan", "Dubois", "Ortiz", "Novak", "Reyes"]

# service name variants (inconsistent on purpose), price range, cadence days
SERVICES = {
    "botox": (["Botox", "BOTOX 50u", "botox touch-up", "Neurotoxin"], (250, 600), 90),
    "laser": (["Laser Hair Removal", "LHR - legs", "laser hair", "IPL"], (150, 400), 45),
    "facial": (["HydraFacial", "hydrafacial deluxe", "Signature Facial"], (120, 300), 30),
    "filler": (["Lip Filler", "Dermal Filler 1ml", "filler - cheeks"], (400, 900), 180),
    "microneedling": (["Microneedling", "SkinPen", "micro-needling + PRP"], (200, 500), 42),
}

DATE_STYLES = [
    lambda d: d.isoformat(),                      # 2026-03-14
    lambda d: d.strftime("%m/%d/%Y"),             # 03/14/2026
    lambda d: d.strftime("%d-%b-%y"),             # 14-Mar-26
]


def make_clients(n: int) -> list[dict]:
    clients = []
    for i in range(n):
        fav = random.choice(list(SERVICES))
        clients.append({
            "id": i + 1,
            "name": f"{random.choice(FIRST)} {random.choice(LAST)}",
            "email": f"client{i+1}@example.com",
            "phone": f"416-555-{random.randint(1000, 9999)}",
            "fav": fav,
            # ~40% dormant: last visit pushed well past their cadence
            "dormant": random.random() < 0.4,
        })
    return clients


def visits_for(client: dict, today: date) -> list[tuple[date, str, float]]:
    fav = client["fav"]
    names, (lo, hi), cadence = SERVICES[fav]
    rows = []
    n_visits = random.randint(2, 7)
    if client["dormant"]:
        last = today - timedelta(days=int(cadence * random.uniform(2.0, 5.0)))
    else:
        last = today - timedelta(days=int(cadence * random.uniform(0.2, 0.9)))
    d = last
    for _ in range(n_visits):
        rows.append((d, random.choice(names), round(random.uniform(lo, hi), 2)))
        d = d - timedelta(days=int(cadence * random.uniform(0.8, 1.4)))
    return rows


def dirty(value: str, p: float = 0.08) -> str:
    """Randomly add whitespace/casing noise."""
    if random.random() < p:
        value = f"  {value} " if random.random() < 0.5 else value.upper()
    return value


def write_clinic_a(clients: list[dict], today: date) -> None:
    """Clinic A: one row per visit, ISO-ish dates, occasional blank emails."""
    path = OUT / "clinic_a.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["client_name", "email", "service", "appt_date", "amount_paid"])
        for c in clients:
            for d, svc, amt in visits_for(c, today):
                email = "" if random.random() < 0.05 else c["email"]
                w.writerow([dirty(c["name"]), email, dirty(svc),
                            DATE_STYLES[0](d), f"{amt:.2f}"])
    print(f"wrote {path}")


def write_clinic_b(clients: list[dict], today: date) -> None:
    """Clinic B: US dates, price with $ sign, split name columns, phone key."""
    path = OUT / "clinic_b.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["First", "Last", "Phone", "Treatment", "Date of Service", "Price"])
        for c in clients:
            first, last = c["name"].split(" ", 1)
            for d, svc, amt in visits_for(c, today):
                w.writerow([first, dirty(last), c["phone"], dirty(svc),
                            DATE_STYLES[1](d), f"${amt:,.2f}"])
    print(f"wrote {path}")


def write_clinic_c(clients: list[dict], today: date) -> None:
    """Clinic C: dd-Mon-yy dates, duplicate rows, a 'notes' column of chaos."""
    path = OUT / "clinic_c.csv"
    notes = ["", "rebook?", "VIP", "no-show last time", "referred by friend", "n/a"]
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["customer", "contact_email", "svc", "visit_dt", "total", "notes"])
        for c in clients:
            for d, svc, amt in visits_for(c, today):
                row = [c["name"], c["email"], svc.lower(),
                       DATE_STYLES[2](d), f"{amt:.2f}", random.choice(notes)]
                w.writerow(row)
                if random.random() < 0.04:  # duplicate rows
                    w.writerow(row)
    print(f"wrote {path}")


if __name__ == "__main__":
    today = date(2026, 7, 14)
    write_clinic_a(make_clients(120), today)
    write_clinic_b(make_clients(90), today)
    write_clinic_c(make_clients(150), today)
