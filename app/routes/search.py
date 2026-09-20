from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from src.domain.athena_api import AthenaAPI
from src.retrieval.hybrid_search import HybridRetrievalService
from src.retrieval.retrieval_diagnostics import build_retrieval_diagnostics
from src.retrieval.temporal_result_context import TemporalResultContext

from app.services.hybrid_retrieval import get_hybrid_retrieval_service

router = APIRouter()


class TemporalSignalDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relevant: bool
    score: float
    date_source: str
    query_start: datetime | None
    query_end: datetime | None


class EvidenceSignalDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_present: bool
    evidence_count: int
    observed_count: int
    inferred_count: int
    confidence: float | None
    evidence_quality: float


class HybridResultDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temporal_query_relevant: bool = False
    temporal_query_score: float = 0.0
    temporal_query_context: TemporalResultContext | None = None
    temporal_signal: TemporalSignalDTO | None = None
    evidence_signal: EvidenceSignalDTO | None = None

    entry_id: int
    source_profile: str
    origin_memory_id: str
    fused_score: float
    fused_rank: int
    reranker_score: float | None
    reranker_rank: int | None
    rank_change: int | None
    keyword_rank: int | None
    keyword_contribution: float
    semantic_rank: int | None
    semantic_contribution: float
    graph_rank: int | None
    graph_contribution: float
    temporal_rank: int | None
    temporal_contribution: float
    entity_rank: int | None
    entity_contribution: float
    provenance: Any


class HybridSearchDiagnosticsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    result_count: int
    requested_top_k: int
    candidate_limit: int
    result_entry_ids: tuple[int, ...]
    reranking_enabled: bool
    reranker_diagnostics: Any | None
    result_diagnostics: tuple[Any, ...]
    evaluation: Any | None


class HybridSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    profile: str | None
    temporal_mode: str | None
    rerank_requested: bool
    reranker_available: bool
    diagnostics: HybridSearchDiagnosticsDTO
    results: list[HybridResultDTO]


def _date_window(start: date | None, end: date | None):
    if start is None and end is None:
        return None, None
    if start is None or end is None:
        raise HTTPException(
            status_code=400,
            detail="date_from and date_to must be supplied together",
        )
    if end < start:
        raise HTTPException(
            status_code=400,
            detail="date_to must be on or after date_from",
        )
    return datetime.combine(start, time.min), datetime.combine(end, time.max)


def hybrid_service_dep() -> HybridRetrievalService:
    return get_hybrid_retrieval_service()


@router.get("/api/search/hybrid", response_model=HybridSearchResponse)
def search_hybrid(
    q: str = Query(..., min_length=1, description="Natural-language memory query"),
    top_k: int = Query(10, ge=1, le=50),
    candidate_limit: int = Query(20, ge=1, le=100),
    profile: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    rerank: bool = Query(True),
    service: HybridRetrievalService = Depends(hybrid_service_dep),
) -> HybridSearchResponse:
    profile = profile.strip() if profile and profile.strip() else None
    start, end = _date_window(date_from, date_to)
    temporal_mode = "event_date" if start is not None else None

    try:
        api = AthenaAPI(hybrid_service=service)
        results = api.search_hybrid(
            q,
            top_k=top_k,
            candidate_limit=candidate_limit,
            profile=profile,
            temporal_mode=temporal_mode,
            temporal_start=start,
            temporal_end=end,
            rerank=rerank,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Hybrid retrieval model is unavailable: {exc}",
        ) from exc
    except (ImportError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    diagnostics = build_retrieval_diagnostics(
        query=q,
        results=results,
        requested_top_k=top_k,
        candidate_limit=candidate_limit,
        reranking_enabled=rerank,
    )

    return HybridSearchResponse(
        query=q,
        profile=profile,
        temporal_mode=temporal_mode,
        rerank_requested=rerank,
        reranker_available=service.reranker is not None,
        diagnostics=HybridSearchDiagnosticsDTO(
            query=diagnostics.query,
            result_count=diagnostics.result_count,
            requested_top_k=diagnostics.requested_top_k,
            candidate_limit=diagnostics.candidate_limit,
            result_entry_ids=diagnostics.result_entry_ids,
            reranking_enabled=diagnostics.reranking_enabled,
            reranker_diagnostics=diagnostics.reranker_diagnostics,
            result_diagnostics=diagnostics.result_diagnostics,
            evaluation=diagnostics.evaluation,
        ),
        results=[HybridResultDTO(**result.__dict__) for result in results],
    )
