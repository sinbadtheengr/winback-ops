"""Shared API models for the upload and profiling slices."""
from pydantic import BaseModel, ConfigDict, Field


class StructuredModel(BaseModel):
    """Base model used for strict OpenAI structured-output parsing."""

    model_config = ConfigDict(extra="forbid")


class DatasetUploadResponse(StructuredModel):
    """Metadata returned immediately after a raw CSV is safely stored."""

    id: str = Field(description="Server-generated identifier for the stored raw upload.")
    filename: str
    byte_size: int = Field(ge=1)
    row_count: int = Field(ge=0)
    columns: list[str]


class ColumnMapping(StructuredModel):
    """The profiler's mapping from raw CSV headers to booking concepts."""

    client_identifier: list[str] = Field(
        description="One or more raw columns that can identify a returning client."
    )
    customer_name: list[str] = Field(default_factory=list)
    email: str | None = None
    phone: str | None = None
    service: str
    appointment_date: str
    amount_paid: str | None = None
    notes: str | None = None


class ServiceTaxonomyEntry(StructuredModel):
    canonical_service: str
    observed_variants: list[str]
    cadence_days: int = Field(ge=7, le=730)
    rationale: str


class DormancyRule(StructuredModel):
    canonical_service: str
    dormant_after_days: int = Field(ge=7, le=1460)
    rationale: str


class DataQuirk(StructuredModel):
    category: str
    detail: str


class HoldoutAssertion(StructuredModel):
    assertion: str
    rationale: str


class DatasetProfile(StructuredModel):
    """Validated outcome of the Day 2 profiler agent."""

    summary: str
    column_mapping: ColumnMapping
    service_taxonomy: list[ServiceTaxonomyEntry] = Field(min_length=1)
    dormancy_rules: list[DormancyRule] = Field(min_length=1)
    data_quirks: list[DataQuirk] = Field(default_factory=list)
    holdout_assertions: list[HoldoutAssertion] = Field(default_factory=list)


class SegmentClient(StructuredModel):
    client_key: str
    last_visit: str
    primary_service: str
    days_overdue: int = Field(ge=0)
    lifetime_value: float = Field(ge=0)
    avg_ticket: float = Field(ge=0)


class Segment(StructuredModel):
    name: str
    clients: list[SegmentClient]
    recoverable_revenue: float = Field(ge=0)


class SegmentationResult(StructuredModel):
    segments: list[Segment]
    totals: dict[str, float | int]


class Campaign(StructuredModel):
    id: str
    dataset_id: str
    segment_name: str
    recipient_count: int = Field(ge=0)
    projected_revenue: float = Field(ge=0)
    subject: str
    body: str
    status: str
    approved_at: str | None = None


class RunActivity(StructuredModel):
    id: str
    agent_name: str
    model: str
    status: str
    latency_ms: int | None = None
    created_at: str
