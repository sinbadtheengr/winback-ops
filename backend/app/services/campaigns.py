"""Day 4 deterministic campaign drafts and human approval gate."""
from __future__ import annotations

import hashlib
from uuid import uuid4

from app.core.config import get_setting, is_demo_mode
from app.core.database import approve_campaign, complete_run, create_run, get_campaigns, get_segmentation, save_campaigns
from app.core.models import Campaign, SegmentationResult


class CampaignError(RuntimeError):
    pass


def _draft_for_segment(dataset_id: str, name: str, client_count: int, revenue: float) -> Campaign:
    service = name.split("_")[0].replace("-", " ").title()
    return Campaign(
        id=uuid4().hex,
        dataset_id=dataset_id,
        segment_name=name,
        recipient_count=client_count,
        projected_revenue=revenue,
        subject=f"A {service} visit, when you're ready",
        body=(f"Hi there,\n\nIt's been a little while since your last {service} visit. "
              "If you're ready to refresh your routine, reply to this email and we'll help find a time that works.\n\n"
              "Warmly,\nYour clinic team"),
        status="draft",
    )


def create_campaigns(dataset_id: str) -> list[Campaign]:
    if not is_demo_mode():
        raise CampaignError("Live campaign generation requires GPT-5.6 API billing. Set DEMO_MODE=true for local fixtures.")
    payload = get_segmentation(dataset_id)
    if payload is None:
        raise CampaignError("Run verified segmentation before creating campaigns.")
    segmentation = SegmentationResult.model_validate_json(payload)
    run = create_run(dataset_id=dataset_id, input_hash=hashlib.sha256(payload.encode()).hexdigest(), model="demo-campaign", agent_name="campaign")
    campaigns = [_draft_for_segment(dataset_id, segment.name, len(segment.clients), segment.recoverable_revenue) for segment in segmentation.segments]
    save_campaigns([campaign.model_dump() for campaign in campaigns])
    complete_run(run, status="completed", latency_ms=0, output=json_dumps(campaigns))
    return campaigns


def json_dumps(campaigns: list[Campaign]) -> str:
    return "[" + ",".join(campaign.model_dump_json() for campaign in campaigns) + "]"


def list_campaigns(dataset_id: str) -> list[Campaign]:
    return [Campaign.model_validate(item) for item in get_campaigns(dataset_id)]


def approve_and_mock_send(campaign_id: str) -> Campaign:
    mock_send = (get_setting("MOCK_SEND", "true") or "true").lower() in {"1", "true", "yes"}
    if not mock_send:
        raise CampaignError("A real email provider is not configured. Keep MOCK_SEND=true for this build.")
    status = "mock_sent"
    campaign = approve_campaign(campaign_id, status)
    if campaign is None:
        raise CampaignError("Campaign not found.")
    return Campaign.model_validate(campaign)
