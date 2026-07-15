# Winback Ops — OpenAI Build Week Plan

**Hackathon:** OpenAI Build Week (Jul 13–21, 2026) · Deadline **Jul 21, 5:00 PM PT**
**Track:** Work and productivity (back-office operations / sales automation)
**Prize pool:** $100,000 · Solo entry

## One-liner

An agentic revenue-recovery operator for local service businesses. Upload a messy
booking export → GPT-5.6 profiles it and infers per-service treatment cadences →
**Codex writes and executes custom segmentation code for that specific business** →
dashboard shows recoverable revenue in dollars → human approves → win-back
sequences ship.

## Why this wins (criteria mapping)

| Criterion | How we hit it |
|---|---|
| **Technological Implementation** | Codex generating, sandbox-executing, and self-verifying bespoke data pipelines per client. A real agentic loop (plan → codegen → execute → verify against holdout → repair), not a chat wrapper. |
| **Design** | Complete product: upload → analyze → approve → send. Polished dashboard, empty states, error handling. Demo ends on a working end-to-end flow. |
| **Potential Impact** | Specific audience (med spas / aesthetic clinics), specific problem (dormant clients = silent churn), specific number ("this clinic has $47K recoverable"). Built by someone running an actual business in this niche. |
| **Quality of Idea** | Non-obvious inversion: the agent doesn't write marketing copy first — it writes *the engineering* (schema inference + segmentation code) that makes the copy targeted. Every clinic's data is messy in a different way; templates fail, codegen doesn't. |

## Architecture

```
┌────────────┐   CSV upload    ┌──────────────────────────────┐
│  Next.js    │ ───────────────▶│  FastAPI backend             │
│  dashboard  │◀─── SSE status ─│                              │
└────────────┘                 │  ┌────────────────────────┐  │
                               │  │ 1. Profiler agent      │  │  GPT-5.6
                               │  │    schema + cadence    │  │  (Responses API)
                               │  │    inference           │  │
                               │  ├────────────────────────┤  │
                               │  │ 2. Codegen agent       │  │  GPT-5.6 / Codex
                               │  │    writes segment.py   │  │
                               │  │    for THIS dataset    │  │
                               │  ├────────────────────────┤  │
                               │  │ 3. Sandbox executor    │  │  subprocess,
                               │  │    runs code, verifies │  │  resource-limited
                               │  │    vs holdout, repairs │  │
                               │  ├────────────────────────┤  │
                               │  │ 4. Campaign agent      │  │  GPT-5.6
                               │  │    per-segment copy +  │  │
                               │  │    revenue projection  │  │
                               │  ├────────────────────────┤  │
                               │  │ 5. HITL approval gate  │  │  human clicks
                               │  │    then send (mock/    │  │  approve
                               │  │    Resend)             │  │
                               │  └────────────────────────┘  │
                               │  SQLite (state) · runs log    │
                               └──────────────────────────────┘
```

**Stack:** Next.js (App Router) + FastAPI + SQLite + OpenAI Responses API.
No Postgres/Redis — keep infra at zero so all effort goes into the agent loop
and the demo. (Familiar territory: this mirrors the Jarvis stack minus the
heavy parts.)

**The core innovation — the codegen loop (step 2–3):**
1. Profiler emits a structured `DatasetProfile` (columns, types, service
   taxonomy, inferred cadence per service, data quirks found).
2. Codegen agent receives the profile + a reference implementation
   (`reference/segment_reference.py`, adapted from RelayOps `segment.py`) and
   writes a dataset-specific script.
3. Executor runs it in a restricted subprocess against 80% of rows; validates
   output schema + spot-checks against a 20% holdout with assertions the
   profiler pre-wrote.
4. On failure, the error + traceback goes back to the codegen agent for repair
   (max 3 attempts). Every attempt is logged and **shown in the UI** — the
   repair loop is demo gold, don't hide it.

## 7-day schedule

**Day 1 (Jul 14 — today): Skeleton + data.**
Repo, FastAPI + Next.js scaffolds running, `scripts/generate_sample_data.py`
producing 3 realistic messy clinic exports (different schemas, dirty dates,
inconsistent service names). Upload endpoint + file storage.

**Day 2: Profiler agent.**
GPT-5.6 structured-output profiling: schema mapping, service taxonomy,
cadence inference (botox ~90d, laser ~45d, facials ~30d), dormancy definition
per service. Output rendered in UI as a "what the agent understood" panel.

**Day 3: Codegen + sandbox loop.** ← the hard part, budget the full day
Codegen prompt with reference implementation, restricted subprocess executor
(timeouts, no network, whitelisted imports), holdout verification, repair loop.
Get all 3 sample datasets passing.

**Day 4: Revenue math + campaign agent.**
Recoverable-revenue calc (dormant clients × avg ticket × expected return
rate by segment), per-segment win-back sequences (reuse RelayOps campaign
templates as few-shot examples), projection attached to each sequence.

**Day 5: Dashboard.**
The four-panel flow: Upload → Analysis (profile + live codegen/repair stream)
→ Revenue board (segments, $ figures) → Approve & send. SSE for live agent
status. This is what judges see — make it feel like a product, not a demo rig.

**Day 6: Polish + hardening.**
Empty states, error states, a 4th adversarial dataset to prove robustness,
README with architecture diagram, seed data one-command setup.

**Day 7 (Jul 20–21): Demo video + submission.**
3-minute video script (below), Devpost writeup, submit **at least 6 hours
before deadline**.

## Demo video script (~3 min)

1. (0:00) The problem in one line: "Med spas sit on tens of thousands of
   dollars of dormant clients. The data to find them is a mess."
2. (0:20) Upload real-shaped messy export. Show the mess.
3. (0:40) Profiler panel: agent explains the schema and cadences it inferred.
4. (1:10) **Codegen live**: watch GPT-5.6 write the segmentation script, fail
   verification once, read its own traceback, repair, pass. (Narrate: "it's
   doing the data engineering, not just the writing.")
5. (2:00) Revenue board: "$47,300 recoverable across 3 segments."
6. (2:20) Per-segment sequences with projections. One click to approve.
7. (2:45) Close: real business, real niche, agent as operator not copywriter.

## Scope guardrails (do NOT expand)

- One vertical: med spa / aesthetic clinic
- One data source: CSV upload (no integrations)
- One channel: email (mock send is fine; Resend if time allows)
- No auth, no multi-tenant, no billing

## Risk register

| Risk | Mitigation |
|---|---|
| Codegen loop unreliable | Reference implementation as anchor + pre-written assertions; fall back to "agent patches the reference script" instead of full generation |
| GPT-5.6 API surprises | Day 1: smoke-test the Responses API + structured outputs before building on it |
| Day 3 overruns | Day 4 revenue math can compress; campaign copy has RelayOps templates ready |
| Demo flakiness | Record video against seeded data with cached agent runs as backup |
