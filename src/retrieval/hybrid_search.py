"""Unified hybrid retrieval orchestration for Mnemosyne."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

import numpy as np

from src.domain.embedding_generator import SentenceTransformerEncoder
from src.domain.temporal_evidence import TemporalEvidenceDAO
from src.retrieval.explainability import (
    RetrievalExplanation,
    explain_fused,
    explain_reranked,
)
from src.retrieval.graph_search import GraphSearcher
from src.retrieval.keyword_search import KeywordSearcher
from src.retrieval.rank_fusion import RankFusion
from src.retrieval.reranker import Reranker
from src.retrieval.semantic_search import SemanticSearcher
from src.retrieval.temporal_search import TemporalSearcher
from src.retrieval.temporal_query import TemporalQueryIntent
from src.retrieval.temporal_query_scoring import score_temporal_result
from src.retrieval.temporal_result_context import (
    TemporalResultContext,
    build_temporal_result_context,
)
from src.retrieval.query_classification import classify_query
from src.retrieval.query_routing import (
    QueryRouter,
    RetrievalRoute,
)
from src.retrieval.candidate_generation import CandidateGenerator
from src.retrieval.evidence_signal import EvidenceSignal, build_evidence_signal
from src.retrieval.temporal_signal import TemporalSignal, build_temporal_signal


@dataclass(frozen=True)
class HybridResult:
    """Final unified retrieval result."""

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

    provenance: object

    temporal_query_relevant: bool = False
    temporal_query_score: float = 0.0
    temporal_query_context: TemporalResultContext | None = None
    temporal_signal: TemporalSignal | None = None
    evidence_signal: EvidenceSignal | None = None



class HybridRetrievalService:
    """Orchestrate keyword, semantic, graph, temporal and reranking."""

    def __init__(
        self,
        keyword_searcher: KeywordSearcher,
        semantic_searcher: SemanticSearcher,
        graph_searcher: GraphSearcher,
        temporal_searcher: TemporalSearcher,
        fusion: RankFusion,
        encoder: SentenceTransformerEncoder,
        entity_searcher=None,
        reranker: Reranker | None = None,
        evidence_dao: TemporalEvidenceDAO | None = None,
    ) -> None:
        self.keyword_searcher = keyword_searcher
        self.semantic_searcher = semantic_searcher
        self.graph_searcher = graph_searcher
        self.temporal_searcher = temporal_searcher
        self.fusion = fusion
        self.encoder = encoder
        self.entity_searcher = entity_searcher
        self.reranker = reranker
        self.evidence_dao = evidence_dao
        self.candidate_generator = CandidateGenerator()

    @staticmethod
    def _decode_embedding(blob: bytes) -> np.ndarray:
        vector = np.frombuffer(blob, dtype=np.float32)

        if vector.ndim != 1:
            raise ValueError("encoder returned an invalid embedding")

        return vector

    @staticmethod
    def _validate_limit(name: str, value: int) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ValueError(f"{name} must be a positive integer")

    @staticmethod
    def _unique_seed_ids(
        keyword_results: Sequence,
        semantic_results: Sequence,
        *,
        limit: int,
    ) -> list[int]:
        seeds: list[int] = []
        seen: set[int] = set()

        for result in (*keyword_results, *semantic_results):
            entry_id = int(result.entry_id)

            if entry_id in seen:
                continue

            seen.add(entry_id)
            seeds.append(entry_id)

            if len(seeds) >= limit:
                break

        return seeds

    @staticmethod
    def _filter_to_candidate_ids(
        results: Sequence,
        candidate_ids: set[int],
    ) -> list:
        """Keep channel results inside the bounded candidate universe."""

        return [
            result
            for result in results
            if int(result.entry_id) in candidate_ids
        ]

    @staticmethod
    def _to_hybrid_results(
        explanations: Sequence[RetrievalExplanation],
        temporal_contexts: dict[int, TemporalResultContext] | None = None,
        evidence_signals: dict[int, EvidenceSignal] | None = None,
    ) -> list[HybridResult]:
        temporal_contexts = temporal_contexts or {}
        evidence_signals = evidence_signals or {}

        results: list[HybridResult] = []

        for explanation in explanations:
            temporal_context = temporal_contexts.get(
                explanation.entry_id
            )

            results.append(
                HybridResult(
                    entry_id=explanation.entry_id,
                    source_profile=explanation.source_profile,
                    origin_memory_id=explanation.origin_memory_id,
                    fused_score=explanation.fused_score,
                    fused_rank=explanation.fused_rank,
                    reranker_score=explanation.reranker_score,
                    reranker_rank=explanation.reranker_rank,
                    rank_change=explanation.rank_change,
                    keyword_rank=explanation.keyword_rank,
                    keyword_contribution=explanation.keyword_contribution,
                    semantic_rank=explanation.semantic_rank,
                    semantic_contribution=explanation.semantic_contribution,
                    graph_rank=explanation.graph_rank,
                    graph_contribution=explanation.graph_contribution,
                    temporal_rank=explanation.temporal_rank,
                    temporal_contribution=explanation.temporal_contribution,
                    temporal_query_relevant=(
                        temporal_context is not None
                        and temporal_context.temporal_relevant
                    ),
                    temporal_query_score=(
                        temporal_context.temporal_score
                        if temporal_context is not None
                        else 0.0
                    ),
                    temporal_query_context=temporal_context,
                    temporal_signal=build_temporal_signal(temporal_context),
                    evidence_signal=evidence_signals.get(
                        explanation.entry_id
                    ),
                    entity_rank=explanation.entity_rank,
                    entity_contribution=explanation.entity_contribution,
                    provenance=explanation.provenance,
                )
            )

        return results

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        candidate_limit: int = 20,
        keyword_limit: int = 20,
        semantic_limit: int = 20,
        graph_seed_limit: int = 5,
        graph_limit_per_seed: int = 4,
        profile: str | None = None,
        temporal_mode: str | None = None,
        temporal_start: datetime | None = None,
        temporal_end: datetime | None = None,
        reference_time: datetime | None = None,
        rerank: bool = True,
    ) -> list[HybridResult]:
        """Return deterministic hybrid retrieval results.

        Query classification and routing are explicit Phase 15 metadata.
        The route does not replace the existing governed retrieval pipeline;
        all existing retrieval channels and governance checks remain
        authoritative.
        """

        if not isinstance(query, str):
            raise TypeError("query must be a string")

        if not query.strip():
            return []

        retrieval_route = QueryRouter.route_query(query)

        self._validate_limit("top_k", top_k)
        self._validate_limit("candidate_limit", candidate_limit)
        self._validate_limit("keyword_limit", keyword_limit)
        self._validate_limit("semantic_limit", semantic_limit)
        self._validate_limit("graph_seed_limit", graph_seed_limit)
        self._validate_limit(
            "graph_limit_per_seed",
            graph_limit_per_seed,
        )

        if temporal_mode not in {
            None,
            "recency",
            "event_date",
        }:
            raise ValueError(
                "temporal_mode must be None, 'recency', or 'event_date'"
            )

        if temporal_mode == "event_date":
            if temporal_start is None or temporal_end is None:
                raise ValueError(
                    "event-date retrieval requires temporal_start and "
                    "temporal_end"
                )

        if temporal_mode != "event_date" and (
            temporal_start is not None or temporal_end is not None
        ):
            raise ValueError(
                "temporal_start and temporal_end require "
                "temporal_mode='event_date'"
            )

        if temporal_mode != "recency" and reference_time is not None:
            raise ValueError(
                "reference_time requires temporal_mode='recency'"
            )

        temporal_query_intent = TemporalQueryIntent(
            start=(
                temporal_start
                if temporal_mode == "event_date"
                else None
            ),
            end=(
                temporal_end
                if temporal_mode == "event_date"
                else None
            ),
        )
        temporal_query_intent.validate()

        keyword_results = self.keyword_searcher.search(
            query,
            limit=keyword_limit,
            profile=profile,
        )

        embedding = self.encoder.generate(query)
        query_vector = self._decode_embedding(embedding)

        semantic_results = self.semantic_searcher.search(
            query_vector,
            top_k=semantic_limit,
            profile=profile,
        )

        seed_ids = self._unique_seed_ids(
            keyword_results,
            semantic_results,
            limit=graph_seed_limit,
        )

        graph_results = self.graph_searcher.expand(
            seed_ids,
            limit_per_seed=graph_limit_per_seed,
            profile=profile,
        ) if seed_ids else []

        entity_results = []

        if self.entity_searcher is not None:
            entity_results = self.entity_searcher.search(
                query,
                limit=candidate_limit,
                profile=profile,
            )

        temporal_results = []

        if temporal_mode == "recency":
            temporal_results = self.temporal_searcher.search_by_recency(
                reference_time=reference_time,
                limit=candidate_limit,
                profile=profile,
            )
        elif temporal_mode == "event_date":
            temporal_results = self.temporal_searcher.search_by_event_date(
                temporal_start,
                temporal_end,
                limit=candidate_limit,
                profile=profile,
            )

        temporal_contexts: dict[int, TemporalResultContext] = {}

        if (
            temporal_query_intent.is_complete_window
            and temporal_mode == "event_date"
        ):
            for temporal_result in temporal_results:
                memory_date = getattr(
                    temporal_result,
                    "memory_date",
                    None,
                )
                date_source = getattr(
                    temporal_result,
                    "date_source",
                    "unknown",
                )

                if memory_date is None:
                    continue

                temporal_score = score_temporal_result(
                    memory_date=memory_date,
                    query_start=temporal_query_intent.start,
                    query_end=temporal_query_intent.end,
                    date_source=date_source,
                )

                temporal_contexts[int(temporal_result.entry_id)] = (
                    build_temporal_result_context(
                        query_start=temporal_query_intent.start,
                        query_end=temporal_query_intent.end,
                        temporal_score=temporal_score,
                    )
                )

        candidate_generation_route = retrieval_route

        if not isinstance(candidate_generation_route, RetrievalRoute):
            candidate_generation_route = QueryRouter.route(
                classify_query(query),
            )

        candidate_set = self.candidate_generator.generate(
            candidate_generation_route,
            keyword_results=keyword_results,
            semantic_results=semantic_results,
            graph_results=graph_results,
            temporal_results=temporal_results,
            entity_results=entity_results,
            candidate_limit=candidate_limit,
        )

        candidate_ids = set(candidate_set.entry_ids)

        # Explicitly enabled channels remain eligible, but must still obey
        # the bounded candidate universe.
        if self.entity_searcher is not None:
            for result in entity_results:
                if len(candidate_ids) >= candidate_limit:
                    break
                candidate_ids.add(int(result.entry_id))

        if temporal_mode is not None:
            for result in temporal_results:
                if len(candidate_ids) >= candidate_limit:
                    break
                candidate_ids.add(int(result.entry_id))

        # Phase 15C evidence signals are descriptive metadata only.
        # Evidence is queried strictly after the candidate universe is
        # finalized, so evidence cannot expand or authorize retrieval.
        evidence_signals: dict[int, EvidenceSignal] = {}

        if self.evidence_dao is not None and candidate_ids:
            candidate_profiles: dict[int, str] = {}

            for result in (
                list(keyword_results)
                + list(semantic_results)
                + list(graph_results)
                + list(temporal_results)
                + list(entity_results)
            ):
                entry_id = int(result.entry_id)

                if entry_id not in candidate_ids:
                    continue

                source_profile = getattr(result, "source_profile", None)

                if source_profile is None:
                    continue

                candidate_profiles.setdefault(
                    entry_id,
                    str(source_profile),
                )

            for entry_id in sorted(candidate_ids):
                source_profile = candidate_profiles.get(entry_id)

                if source_profile is None:
                    continue

                evidence_records = self.evidence_dao.list(
                    collective_entry_id=entry_id,
                    source_profile=source_profile,
                )

                evidence_signals[entry_id] = build_evidence_signal(
                    evidence_records
                )

        keyword_results = self._filter_to_candidate_ids(
            keyword_results,
            candidate_ids,
        )
        semantic_results = self._filter_to_candidate_ids(
            semantic_results,
            candidate_ids,
        )
        graph_results = self._filter_to_candidate_ids(
            graph_results,
            candidate_ids,
        )
        temporal_results = self._filter_to_candidate_ids(
            temporal_results,
            candidate_ids,
        )
        entity_results = self._filter_to_candidate_ids(
            entity_results,
            candidate_ids,
        )

        fusion_kwargs = {
            "keyword_results": keyword_results,
            "semantic_results": semantic_results,
            "graph_results": graph_results,
            "temporal_results": temporal_results,
        }

        if self.entity_searcher is not None:
            fusion_kwargs["entity_results"] = entity_results

        fused_results = self.fusion.fuse(**fusion_kwargs)

        if not fused_results:
            return []

        if rerank and self.reranker is not None:
            reranked_results = self.reranker.rerank(
                query,
                fused_results,
                candidate_limit=candidate_limit,
                top_k=top_k,
            )

            explanations = explain_reranked(
                reranked_results,
                fused_results,
            )

            return self._to_hybrid_results(
                explanations,
                temporal_contexts=temporal_contexts,
            )

        explanations = explain_fused(
            fused_results[:top_k],
        )

        return self._to_hybrid_results(
            explanations,
            temporal_contexts=temporal_contexts,
            evidence_signals=evidence_signals,
        )
