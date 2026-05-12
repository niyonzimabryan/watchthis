from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.errors import DependencyUnavailableError
from core.orchestrator import WatchThisOrchestrator
from data.database import (
    get_vote_stats,
    managed_connection,
    record_vote,
    request_log_exists,
)
from data.models import FormatFilter, LengthFilter, RecommendationRequest, UserFilters


router = APIRouter()


class RecommendInput(BaseModel):
    mood_input: str = Field(min_length=1, max_length=500)
    session_id: str | None = Field(default=None, min_length=3, max_length=120)
    format: FormatFilter = FormatFilter.ANY
    length: LengthFilter = LengthFilter.ANY
    reroll_of: str | None = None
    excluded_tmdb_ids: list[int] = Field(default_factory=list)


class RouletteInput(BaseModel):
    session_id: str | None = Field(default=None, min_length=3, max_length=120)
    format: FormatFilter = FormatFilter.ANY
    length: LengthFilter = LengthFilter.ANY
    reroll_of: str | None = None
    excluded_tmdb_ids: list[int] = Field(default_factory=list)


class VoteInput(BaseModel):
    request_id: str = Field(min_length=1, max_length=120)
    vote: int = Field(description="+1 for upvote, -1 for downvote")
    session_id: str = Field(min_length=3, max_length=120)
    reason: str | None = Field(default=None, max_length=500)


@lru_cache(maxsize=1)
def get_orchestrator() -> WatchThisOrchestrator:
    return WatchThisOrchestrator.build_default()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/recommend")
async def recommend(payload: RecommendInput, orchestrator: WatchThisOrchestrator = Depends(get_orchestrator)):
    request = RecommendationRequest(
        mood_input=payload.mood_input,
        session_id=payload.session_id,
        filters=UserFilters(format=payload.format, length=payload.length),
        is_roulette=False,
        is_reroll=bool(payload.reroll_of),
        reroll_of=payload.reroll_of,
        excluded_tmdb_ids=payload.excluded_tmdb_ids,
    )
    try:
        response = await orchestrator.recommend(request)
        return response.model_dump()
    except DependencyUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/roulette")
async def roulette(payload: RouletteInput, orchestrator: WatchThisOrchestrator = Depends(get_orchestrator)):
    request = RecommendationRequest(
        mood_input=None,
        session_id=payload.session_id,
        filters=UserFilters(format=payload.format, length=payload.length),
        is_roulette=True,
        is_reroll=bool(payload.reroll_of),
        reroll_of=payload.reroll_of,
        excluded_tmdb_ids=payload.excluded_tmdb_ids,
    )
    try:
        response = await orchestrator.recommend(request)
        return response.model_dump()
    except DependencyUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/vote")
async def vote(payload: VoteInput) -> dict[str, Any]:
    if payload.vote not in (-1, 1):
        raise HTTPException(
            status_code=422,
            detail="vote must be +1 (upvote) or -1 (downvote)",
        )

    reason = payload.reason.strip() if payload.reason else None
    if reason == "":
        reason = None

    with managed_connection() as conn:
        if not request_log_exists(conn, payload.request_id):
            raise HTTPException(
                status_code=404,
                detail=(
                    "We couldn't find that recommendation to attach your vote to. "
                    "It may have expired or never reached the server — try a fresh "
                    "recommendation and vote again."
                ),
            )
        record_vote(
            conn,
            request_id=payload.request_id,
            session_id=payload.session_id,
            vote=payload.vote,
            reason=reason,
        )

    return {"ok": True}


@router.get("/vote-stats")
async def vote_stats() -> dict[str, Any]:
    with managed_connection() as conn:
        return get_vote_stats(conn)
