"""Winback Ops API — see docs/PLAN.md for architecture."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Winback Ops")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# TODO (Day 1): POST /api/datasets — CSV upload + storage
# TODO (Day 2): POST /api/datasets/{id}/profile — profiler agent
# TODO (Day 3): POST /api/datasets/{id}/segment — codegen + sandbox loop
#               GET  /api/runs/{id}/stream — SSE agent activity
# TODO (Day 4): POST /api/datasets/{id}/campaigns — campaign agent
# TODO (Day 5): POST /api/campaigns/{id}/approve — HITL gate + (mock) send
