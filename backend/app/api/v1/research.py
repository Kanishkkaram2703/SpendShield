"""Authenticated, owner-scoped research anomaly read APIs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.dependencies import get_current_user, get_research_anomaly_service
from app.repositories.users import UserRecord
from app.schemas.research import (
    ResearchAnomalyExplanationResponse,
    ResearchAnomalyScoreListResponse,
    ResearchAnomalyScoreResponse,
)
from app.services.research_anomaly_service import ResearchAnomalyService

router = APIRouter(prefix="/research", tags=["research"])


@router.get(
    "/anomaly-score/{transaction_id}",
    response_model=ResearchAnomalyScoreResponse,
)
def get_research_anomaly_score(
    transaction_id: UUID,
    request: Request,
    user: UserRecord = Depends(get_current_user),
    service: ResearchAnomalyService = Depends(get_research_anomaly_service),
) -> ResearchAnomalyScoreResponse:
    """Return one read-only research score for the authenticated owner."""

    scored = service.score_for_owner(str(transaction_id), user.user_id)
    return ResearchAnomalyScoreResponse(
        status="scored",
        transaction=service.summary(scored.execution),
        anomaly_score=scored.score,
        score_semantics=scored.artifact.metadata.score_semantics,
        model_metadata=scored.artifact.metadata,
        request_id=request.state.request_id,
    )


@router.get(
    "/anomaly-scores",
    response_model=ResearchAnomalyScoreListResponse,
)
def list_research_anomaly_scores(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: UUID | None = Query(default=None),
    user: UserRecord = Depends(get_current_user),
    service: ResearchAnomalyService = Depends(get_research_anomaly_service),
) -> ResearchAnomalyScoreListResponse:
    """Return bounded owner-scoped scores or explicit unavailable items."""

    items, next_cursor = service.list_for_owner(
        user.user_id,
        limit=limit,
        cursor=str(cursor) if cursor is not None else None,
    )
    return ResearchAnomalyScoreListResponse(
        items=items,
        next_cursor=next_cursor,
        request_id=request.state.request_id,
    )


@router.get(
    "/anomaly-score/{transaction_id}/explanation",
    response_model=ResearchAnomalyExplanationResponse,
)
def explain_research_anomaly_score(
    transaction_id: UUID,
    request: Request,
    user: UserRecord = Depends(get_current_user),
    service: ResearchAnomalyService = Depends(get_research_anomaly_service),
) -> ResearchAnomalyExplanationResponse:
    """Return a deterministic label-free explanation for one score."""

    scored, explanation = service.explanation_for_owner(
        str(transaction_id), user.user_id
    )
    return ResearchAnomalyExplanationResponse(
        transaction=service.summary(scored.execution),
        anomaly_score=scored.score,
        score_semantics=scored.artifact.metadata.score_semantics,
        model_metadata=scored.artifact.metadata,
        explanation=explanation,
        request_id=request.state.request_id,
    )


__all__ = ["router"]
