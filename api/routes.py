from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.errors import DependencyUnavailableError
from core.orchestrator import WatchThisOrchestrator
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
