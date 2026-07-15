# Winback Ops

**An agentic revenue-recovery operator for local service businesses.**
OpenAI Build Week 2026 · Track: Work and productivity

Med spas and clinics sit on tens of thousands of dollars of dormant clients —
and the booking data needed to find them is a mess, different in every business.
Winback Ops doesn't just write marketing copy. It does the engineering:

1. **Upload** a raw booking export (CSV, any schema)
2. **Profile** — GPT-5.6 infers the schema, service taxonomy, and per-service
   treatment cadence (botox ≈ 90 days, laser ≈ 45, facials ≈ 30)
3. **Codegen** — the agent writes a segmentation script *custom to this
   dataset*, executes it in a sandbox, verifies it against a holdout, and
   repairs its own failures
4. **Revenue board** — dormant clients segmented by recoverable dollars
5. **Approve & send** — per-segment win-back sequences with revenue
   projections, gated behind human approval

## Quickstart

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # add your OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install && npm run dev

# sample data
python scripts/generate_sample_data.py
```

## Docs

- [`docs/PLAN.md`](docs/PLAN.md) — hackathon plan, architecture, schedule
- [`CLAUDE.md`](CLAUDE.md) — agent/contributor context
