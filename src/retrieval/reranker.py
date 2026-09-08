"""Query-time reranking for hybrid collective retrieval.

Phase 8F:
- reranks bounded RRF candidates;
- retrieves source content through MemoryGateway;
- preserves collective identity, RRF metadata, and provenance;
- remains independent of any specific CrossEncoder implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from src.domain.memory_gateway import MemoryGateway
from src.retrieval.rank_fusion import FusedResult


class CrossEncoderProtocol(Protocol):
    """Minimal interface required from a local CrossEncoder."""

    def predict(self, pairs: Sequence[tuple[str, str]]) -> Sequence[float]:
        """Return one relevance score for each query/content pair."""
        ...


@dataclass(frozen=True)
class RerankedResult:
    """A hybrid result augmented with an optional reranker score."""

    entry_id: int
    source_profile: str
    origin_memory_id: str

    fused_score: float
    reranker_score: float
    reranker_rank: int

    keyword_rank: int | None
    semantic_rank: int | None
    graph_rank: int | None
    temporal_rank: int | None

    keyword_contribution: float
    semantic_contribution: float
    graph_contribution: float
    temporal_contribution: float

    provenance: object


class Reranker:
    """Rerank a bounded set of governed hybrid candidates."""

    def __init__(
        self,
        encoder: CrossEncoderProtocol,
        gateway: MemoryGateway,
    ) -> None:
        self.encoder = encoder
        self.gateway = gateway

    @staticmethod
    def _validate_limit(name: str, value: int) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ValueError(f"{name} must be a positive integer")

    def rerank(
        self,
        query: str,
        candidates: Sequence[FusedResult],
        *,
        candidate_limit: int = 20,
        top_k: int = 5,
    ) -> list[RerankedResult]:
        """Rerank the first bounded RRF candidates.

        Candidates are assumed to have already passed the governed retrieval
        channels and RRF fusion. This layer does not expand the candidate set
        or bypass lifecycle authorization.
        """

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")

        self._validate_limit("candidate_limit", candidate_limit)
        self._validate_limit("top_k", top_k)

        bounded = list(candidates[:candidate_limit])

        if not bounded:
            return []

        pairs: list[tuple[str, str]] = []

        for candidate in bounded:
            content = self.gateway.get_memory(
                candidate.source_profile,
                candidate.origin_memory_id,
            )

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"memory content must be non-empty for entry "
                    f"{candidate.entry_id}"
                )

            pairs.append((query, content))

        raw_scores = list(self.encoder.predict(pairs))

        if len(raw_scores) != len(bounded):
            raise ValueError(
                "CrossEncoder returned a different number of scores "
                "than candidates"
            )

        scored = []

        for candidate, raw_score in zip(bounded, raw_scores):
            score = float(raw_score)

            if score != score or score in (float("inf"), float("-inf")):
                raise ValueError(
                    f"CrossEncoder returned a non-finite score for "
                    f"entry {candidate.entry_id}"
                )

            scored.append((score, candidate))

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].entry_id,
            )
        )

        results: list[RerankedResult] = []

        for rank, (score, candidate) in enumerate(scored[:top_k], start=1):
            results.append(
                RerankedResult(
                    entry_id=candidate.entry_id,
                    source_profile=candidate.source_profile,
                    origin_memory_id=candidate.origin_memory_id,
                    fused_score=candidate.fused_score,
                    reranker_score=score,
                    reranker_rank=rank,
                    keyword_rank=candidate.keyword_rank,
                    semantic_rank=candidate.semantic_rank,
                    graph_rank=candidate.graph_rank,
                    temporal_rank=candidate.temporal_rank,
                    keyword_contribution=candidate.keyword_contribution,
                    semantic_contribution=candidate.semantic_contribution,
                    graph_contribution=candidate.graph_contribution,
                    temporal_contribution=candidate.temporal_contribution,
                    provenance=candidate.provenance,
                )
            )

        return results
