# CLAUDE.md — Winback Ops

## What this is

Hackathon project for OpenAI Build Week (deadline Jul 21, 2026, 5PM PT).
Track: Work and productivity. Read `docs/PLAN.md` first — it is the source of
truth for scope, schedule, and judging criteria. Do not expand scope beyond it.

An agentic revenue-recovery operator for med spas: upload a messy booking CSV,
GPT-5.6 profiles it, **Codex/GPT-5.6 writes and executes custom segmentation
code for that dataset**, dashboard shows recoverable revenue in dollars, human
approves win-back email sequences.

IMPORTANT: This is an OpenAI hackathon — the PRODUCT must use OpenAI's GPT-5.6
via the OpenAI API for all agent steps. Claude Code is the build tool only.
Never wire Anthropic API calls into the product.

## Stack

- `backend/` — FastAPI (Python 3.11+), SQLite via sqlite3/SQLModel, OpenAI SDK
- `frontend/` — Next.js App Router, TypeScript, Tailwind
- No Postgres, no Redis, no Docker required for dev. Zero-infra bias.

## Architecture (agent pipeline)

1. **Profiler agent** (`backend/app/agents/profiler.py`) — GPT-5.6 structured
   output → `DatasetProfile`: column mapping, service taxonomy, per-service
   cadence (days), dormancy rules, data quirks, and holdout assertions.
2. **Codegen agent** (`backend/app/agents/codegen.py`) — receives profile +
   `backend/app/agents/reference/segment_reference.py`, writes a
   dataset-specific segmentation script.
3. **Sandbox executor** (`backend/app/sandbox/executor.py`) — runs generated
   code in a restricted subprocess: 30s timeout, no network, import whitelist
   (pandas, numpy, datetime, json, re only), output schema validation,
   holdout assertion checks. On failure: feed traceback back to codegen agent,
   max 3 repair attempts. Log every attempt to DB — the UI streams these.
4. **Campaign agent** (`backend/app/agents/campaign.py`) — per-segment
   win-back sequences + recoverable-revenue projection.
5. **HITL gate** — nothing sends without an explicit approve action. Send is
   mocked by default (`MOCK_SEND=true`).

## Conventions

- Python: ruff + type hints; Pydantic models in `backend/app/core/models.py`
- All agent prompts live in `backend/app/agents/prompts/` as .md files, not
  inline strings
- Every agent call logged to `runs` table: input hash, model, tokens, latency,
  output. The UI's "agent activity" stream reads from this.
- SSE endpoint `/api/runs/{id}/stream` for live pipeline status
- Frontend: no component library beyond Tailwind + lucide-react; keep it fast
- Secrets in `.env` (see `.env.example`); never commit `.env`

## Commands

- Backend dev: `cd backend && uvicorn app.main:app --reload --port 8000`
- Frontend dev: `cd frontend && npm run dev`
- Generate sample data: `python scripts/generate_sample_data.py`
- Tests: `cd backend && pytest`

## Working style

- Ship vertical slices: each day's work must be demoable end-to-end
- The codegen→sandbox→verify→repair loop is the centerpiece. When in doubt,
  invest effort there and in the UI that makes it visible.
- Ask before adding any dependency not already in requirements.txt/package.json
