from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import asyncio

from clients.anthropic_client import AnthropicClient
from clients.gemini_client import GeminiClient
from clients.omdb_client import OMDbClient
from clients.tmdb_client import TMDBClient
from clients.watchmode_client import WatchmodeClient
from config import Settings, get_settings
from core.candidate_curation import CandidateCurator
from core.candidate_retrieval import CandidateRetriever
from core.mood_interpreter import MoodInterpreter
from core.ranker import Ranker
from core.signal_enrichment import SignalEnricher
from core.streaming_lookup import StreamingLookup
from data.database import get_recent_selected_ids, init_db, insert_request_log, managed_connection, update_request_error
from data.models import RecommendationRequest, RecommendationResponse


logger = logging.getLogger("watchthis")


class WatchThisOrchestrator:
    def __init__(
        self,
        mood_interpreter: MoodInterpreter,
        candidate_retriever: CandidateRetriever,
        signal_enricher: SignalEnricher,
        candidate_curator: CandidateCurator,
        ranker: Ranker,
        streaming_lookup: StreamingLookup,
        gemini_client: GeminiClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.mood_interpreter = mood_interpreter
        self.candidate_retriever = candidate_retriever
        self.signal_enricher = signal_enricher
        self.candidate_curator = candidate_curator
        self.ranker = ranker
        self.streaming_lookup = streaming_lookup
        self.gemini_client = gemini_client

        logging.basicConfig(level=self.settings.log_level)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        init_db(self.settings)

    @classmethod
    def build_default(cls, settings: Settings | None = None) -> "WatchThisOrchestrator":
        cfg = settings or get_settings()
        anthropic_client = AnthropicClient(cfg)
        tmdb_client = TMDBClient(cfg)
        omdb_client = OMDbClient(cfg)
        watchmode_client = WatchmodeClient(cfg)
        gemini_client = GeminiClient(cfg) if cfg.gemini_api_key else None

        return cls(
            mood_interpreter=MoodInterpreter(anthropic_client, gemini_client),
            candidate_retriever=CandidateRetriever(tmdb_client, cfg),
            signal_enricher=SignalEnricher(omdb_client, cfg),
            candidate_curator=CandidateCurator(cfg),
            ranker=Ranker(anthropic_client),
            streaming_lookup=StreamingLookup(watchmode_client),
            gemini_client=gemini_client,
            settings=cfg,
        )

    async def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        request_id = str(uuid.uuid4())
        started = time.perf_counter()

        latency_mood = 0
        latency_tmdb = 0
        latency_enrich = 0
        latency_rank = 0
        latency_streaming = 0

        interpretation = None
        selected = None
        ranked = None
        candidates_count = 0

        try:
            resolved_session_id = request.session_id or request.reroll_of

            stage = time.perf_counter()
            interpretation = await self.mood_interpreter.interpret(request.mood_input, is_roulette=request.is_roulette)
            latency_mood = int((time.perf_counter() - stage) * 1000)

            excluded = set(request.excluded_tmdb_ids)
            if request.is_reroll:
                with managed_connection(self.settings.db_path_obj) as conn:
                    excluded.update(get_recent_selected_ids(conn, resolved_session_id, request.mood_input, limit=5))

            stage = time.perf_counter()
            candidates = await self.candidate_retriever.retrieve(
                interpretation,
                request.filters,
                is_roulette=request.is_roulette,
                excluded_tmdb_ids=sorted(excluded),
            )
            latency_tmdb = int((time.perf_counter() - stage) * 1000)
            candidates_count = len(candidates)

            if not candidates:
                raise ValueError("No candidates found for the given mood and filters")

            # Parallel enrichment: OMDb/Reddit (existing) + Gemini Pro search (new)
            stage = time.perf_counter()

            enrich_task = self.signal_enricher.enrich(candidates, interpretation.mood_tags)

            gemini_search_task = None
            if self.gemini_client and not request.is_roulette:
                gemini_search_task = self.gemini_client.search_recommendations(
                    mood_text=request.mood_input,
                    mood_tags=interpretation.mood_tags,
                    format_filter=request.filters.format,
                )

            if gemini_search_task:
                enriched, gemini_recs = await asyncio.gather(
                    enrich_task, gemini_search_task, return_exceptions=True
                )
                if isinstance(enriched, Exception):
                    raise enriched
                if isinstance(gemini_recs, Exception):
                    logger.warning("Gemini search failed: %s", gemini_recs)
                    gemini_recs = []

                # Boost candidates that Gemini's community search also recommends
                if gemini_recs and isinstance(gemini_recs, list):
                    gemini_titles = {
                        r.get("title", "").lower().strip()
                        for r in gemini_recs
                        if isinstance(r, dict)
                    }
                    for candidate in enriched:
                        if candidate.title.lower().strip() in gemini_titles:
                            candidate.reddit_boost = max(candidate.reddit_boost, 1.5)
                            if "gemini-recommended" not in candidate.reddit_mood_match:
                                candidate.reddit_mood_match.append("gemini-recommended")
            else:
                enriched = await enrich_task

            latency_enrich = int((time.perf_counter() - stage) * 1000)

            shortlisted = self.candidate_curator.curate(
                candidates=enriched,
                user_mood=request.mood_input,
                mood_tags=interpretation.mood_tags,
                session_id=resolved_session_id,
            )
            if shortlisted:
                enriched = shortlisted

            stage = time.perf_counter()
            selected, ranked = await self.ranker.rank(
                user_mood=request.mood_input,
                filters=request.filters,
                candidates=enriched,
                is_roulette=request.is_roulette,
            )
            latency_rank = int((time.perf_counter() - stage) * 1000)

            stage = time.perf_counter()
            streaming_sources = await self.streaming_lookup.get_sources(
                selected.tmdb_id,
                selected.media_type,
                selected.title,
                selected.year,
            )
            latency_streaming = int((time.perf_counter() - stage) * 1000)

            total_latency = int((time.perf_counter() - started) * 1000)
            self._log_request(
                request_id=request_id,
                request=request,
                session_id=resolved_session_id,
                interpretation=interpretation.model_dump(),
                candidates_count=candidates_count,
                selected_tmdb_id=selected.tmdb_id,
                selected_title=selected.title,
                pitch=ranked.pitch,
                confidence=ranked.confidence,
                reasoning=ranked.reasoning,
                latency_ms=total_latency,
                latency_mood_ms=latency_mood,
                latency_tmdb_ms=latency_tmdb,
                latency_enrichment_ms=latency_enrich,
                latency_ranking_ms=latency_rank,
                latency_streaming_ms=latency_streaming,
                error=None,
            )

            logger.info(
                "recommendation_served",
                extra={
                    "request_id": request_id,
                    "selected_tmdb_id": selected.tmdb_id,
                    "latency_ms": total_latency,
                    "candidates_count": candidates_count,
                },
            )

            return RecommendationResponse(
                request_id=request_id,
                recommendation=selected,
                pitch=ranked.pitch,
                confidence=ranked.confidence,
                reasoning=ranked.reasoning,
                streaming_sources=streaming_sources,
            )

        except Exception as exc:
            total_latency = int((time.perf_counter() - started) * 1000)
            self._log_request(
                request_id=request_id,
                request=request,
                session_id=resolved_session_id,
                interpretation=interpretation.model_dump() if interpretation else None,
                candidates_count=candidates_count,
                selected_tmdb_id=selected.tmdb_id if selected else None,
                selected_title=selected.title if selected else None,
                pitch=ranked.pitch if ranked else None,
                confidence=ranked.confidence if ranked else None,
                reasoning=ranked.reasoning if ranked else None,
                latency_ms=total_latency,
                latency_mood_ms=latency_mood,
                latency_tmdb_ms=latency_tmdb,
                latency_enrichment_ms=latency_enrich,
                latency_ranking_ms=latency_rank,
                latency_streaming_ms=latency_streaming,
                error=str(exc),
            )
            raise

    def _log_request(
        self,
        request_id: str,
        request: RecommendationRequest,
        session_id: str | None,
        interpretation: dict[str, Any] | None,
        candidates_count: int,
        selected_tmdb_id: int | None,
        selected_title: str | None,
        pitch: str | None,
        confidence: float | None,
        reasoning: str | None,
        latency_ms: int,
        latency_mood_ms: int,
        latency_tmdb_ms: int,
        latency_enrichment_ms: int,
        latency_ranking_ms: int,
        latency_streaming_ms: int,
        error: str | None,
    ) -> None:
        row = {
            "id": request_id,
            "session_id": session_id,
            "mood_input": request.mood_input,
            "format_filter": request.filters.format,
            "length_filter": request.filters.length,
            "mood_interpretation": interpretation,
            "candidates_count": candidates_count,
            "selected_tmdb_id": selected_tmdb_id,
            "selected_title": selected_title,
            "pitch": pitch,
            "confidence": confidence,
            "reasoning": reasoning,
            "latency_ms": latency_ms,
            "latency_mood_ms": latency_mood_ms,
            "latency_tmdb_ms": latency_tmdb_ms,
            "latency_enrichment_ms": latency_enrichment_ms,
            "latency_ranking_ms": latency_ranking_ms,
            "latency_streaming_ms": latency_streaming_ms,
            "is_roulette": request.is_roulette,
            "is_reroll": request.is_reroll,
            "reroll_of": request.reroll_of,
            "error": error,
        }

        with managed_connection(self.settings.db_path_obj) as conn:
            insert_request_log(conn, row)
            if error:
                update_request_error(conn, request_id, error)
