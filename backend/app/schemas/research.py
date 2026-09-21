"""Public schemas for the read-only research anomaly boundary."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.financial import TransactionStatus


class ResearchModelMetadata(BaseModel):
    """Version metadata required to interpret one research score."""

    model_config = ConfigDict(extra="forbid")

    dataset_version: str
    generator_version: str
    feature_version: str
    model_name: str
    model_version: str
    score_semantics: str
    higher_score_means_more_anomalous: Literal[True] = True
    threshold_source: str
    threshold_version: str
    thresholds_are_decisions: Literal[False] = False


class ResearchTransactionSummary(BaseModel):
    """Owner-safe current transaction fields used by the research view."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    amount: Decimal
    currency: str
    status: TransactionStatus
    created_at: datetime


class ResearchExplanation(BaseModel):
    """Deterministic signal summary, never a fraud or payment decision."""

    model_config = ConfigDict(extra="forbid")

    explanation_text: str
    signal_strengths: dict[str, Literal["none", "weak", "moderate", "strong"]]
    signal_feature_names: list[str]
    missing_history_warning: bool
    explainability_version: str
    deterministic: Literal[True] = True


class ResearchAnomalyScoreResponse(BaseModel):
    """One owner-scoped score or explicit unavailable result."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    research_only: Literal[True] = True
    status: Literal["scored", "unavailable"]
    transaction: ResearchTransactionSummary
    anomaly_score: float | None = Field(default=None, ge=0.0, le=1.0)
    score_semantics: str | None = None
    higher_score_means_more_anomalous: Literal[True] = True
    model_metadata: ResearchModelMetadata | None = None
    unavailable_reason: str | None = None
    request_id: str


class ResearchAnomalyScoreItem(BaseModel):
    """One bounded list item with per-row availability."""

    model_config = ConfigDict(extra="forbid")

    transaction: ResearchTransactionSummary
    status: Literal["scored", "unavailable"]
    anomaly_score: float | None = Field(default=None, ge=0.0, le=1.0)
    model_metadata: ResearchModelMetadata | None = None
    unavailable_reason: str | None = None


class ResearchAnomalyScoreListResponse(BaseModel):
    """Bounded owner-scoped research score listing."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    research_only: Literal[True] = True
    items: list[ResearchAnomalyScoreItem]
    next_cursor: str | None
    request_id: str


class ResearchAnomalyExplanationResponse(BaseModel):
    """One score plus its deterministic, label-free explanation."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    research_only: Literal[True] = True
    transaction: ResearchTransactionSummary
    anomaly_score: float = Field(ge=0.0, le=1.0)
    score_semantics: str
    higher_score_means_more_anomalous: Literal[True] = True
    model_metadata: ResearchModelMetadata
    explanation: ResearchExplanation
    request_id: str


__all__ = [
    "ResearchAnomalyExplanationResponse",
    "ResearchAnomalyScoreItem",
    "ResearchAnomalyScoreListResponse",
    "ResearchAnomalyScoreResponse",
    "ResearchExplanation",
    "ResearchModelMetadata",
    "ResearchTransactionSummary",
]
