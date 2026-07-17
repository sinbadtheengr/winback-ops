"""Winback Ops API — see docs/PLAN.md for architecture."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.datasets import router as datasets_router

app = FastAPI(title="Winback Ops")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets_router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# TODO (Day 2): POST /api/datasets/{id}/profile — profiler agent
# TODO (Day 3): POST /api/datasets/{id}/segment — codegen + sandbox loop
#               GET  /api/runs/{id}/stream — SSE agent activity
# TODO (Day 4): POST /api/datasets/{id}/campaigns — campaign agent
# TODO (Day 5): POST /api/campaigns/{id}/approve — HITL gate + (mock) send
