"""Governed candidate-generation orchestration for Phase 15B.

Candidate generation selects and bounds results produced by existing
retrieval channels. It does not perform authorization, governance,
persistence, scoring, reranking, or raw-memory access.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from src.retrieval.query_routing import (
    RetrievalChannel,
    RetrievalRoute,
)


class CandidateChannel(str, Enum):
    """Existing retrieval channels that can contribute candidates."""

    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    GRAPH = "graph"
    TEMPORAL = "temporal"
    ENTITY = "entity"


@dataclass(frozen=True)
class CandidateSet:
    """Deterministic bounded candidate set."""

    entry_ids: tuple[int, ...]
    channels: tuple[CandidateChannel, ...]


@dataclass(frozen=True)
class CandidateGenerationPolicy:
    """Immutable candidate-generation policy."""

    candidate_limit: int = 20

    def __post_init__(self) -> None:
        if (
            not isinstance(self.candidate_limit, int)
            or isinstance(self.candidate_limit, bool)
            or self.candidate_limit < 1
        ):
            raise ValueError(
                "candidate_limit must be a positive integer"
            )


class CandidateGenerator:
    """Generate bounded candidates from existing channel results."""

    _ROUTE_CHANNELS: dict[
        RetrievalChannel,
        tuple[CandidateChannel, ...],
    ] = {
        RetrievalChannel.SEMANTIC: (
            CandidateChannel.KEYWORD,
            CandidateChannel.SEMANTIC,
            CandidateChannel.GRAPH,
        ),
        RetrievalChannel.LEXICAL: (
            CandidateChannel.KEYWORD,
            CandidateChannel.SEMANTIC,
            CandidateChannel.GRAPH,
        ),
        RetrievalChannel.TEMPORAL: (
            CandidateChannel.KEYWORD,
            CandidateChannel.SEMANTIC,
            CandidateChannel.TEMPORAL,
            CandidateChannel.GRAPH,
        ),
        RetrievalChannel.ENTITY: (
            CandidateChannel.KEYWORD,
            CandidateChannel.SEMANTIC,
            CandidateChannel.ENTITY,
            CandidateChannel.GRAPH,
        ),
        RetrievalChannel.RELATIONSHIP: (
            CandidateChannel.KEYWORD,
            CandidateChannel.SEMANTIC,
            CandidateChannel.ENTITY,
            CandidateChannel.GRAPH,
        ),
    }

    @classmethod
    def channels_for_route(
        cls,
        route: RetrievalRoute,
    ) -> tuple[CandidateChannel, ...]:
        """Return deterministic candidate channels for a retrieval route."""

        if not isinstance(route, RetrievalRoute):
            raise TypeError("route must be a RetrievalRoute")

        selected: set[CandidateChannel] = set()

        for retrieval_channel in route.channels:
            channels = cls._ROUTE_CHANNELS.get(retrieval_channel)

            if channels is None:
                raise ValueError(
                    "unsupported retrieval channel: "
                    f"{retrieval_channel!r}"
                )

            selected.update(channels)

        canonical_order = (
            CandidateChannel.KEYWORD,
            CandidateChannel.SEMANTIC,
            CandidateChannel.TEMPORAL,
            CandidateChannel.ENTITY,
            CandidateChannel.GRAPH,
        )

        return tuple(
            channel
            for channel in canonical_order
            if channel in selected
        )


    @staticmethod
    def _entry_id(result: object) -> int:
        """Extract and validate a candidate entry identifier."""

        try:
            entry_id = int(getattr(result, "entry_id"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(
                "retrieval result must expose an integer entry_id"
            ) from exc

        return entry_id

    @classmethod
    def generate(
        cls,
        route: RetrievalRoute,
        *,
        keyword_results: Sequence = (),
        semantic_results: Sequence = (),
        graph_results: Sequence = (),
        temporal_results: Sequence = (),
        entity_results: Sequence = (),
        policy: CandidateGenerationPolicy | None = None,
        candidate_limit: int | None = None,
    ) -> CandidateSet:
        """Generate a deterministic bounded set of candidate entry IDs.

        Results are consumed in deterministic channel order. The result
        objects themselves are not modified and no governance decision is
        made here; authorization remains the responsibility of the existing
        retrieval channels.
        """

        if not isinstance(route, RetrievalRoute):
            raise TypeError("route must be a RetrievalRoute")

        if policy is not None and candidate_limit is not None:
            raise ValueError(
                "provide either policy or candidate_limit, not both"
            )

        if candidate_limit is not None:
            policy = CandidateGenerationPolicy(
                candidate_limit=candidate_limit,
            )

        if policy is None:
            policy = CandidateGenerationPolicy()

        channel_results: Mapping[
            CandidateChannel,
            Sequence,
        ] = {
            CandidateChannel.KEYWORD: keyword_results,
            CandidateChannel.SEMANTIC: semantic_results,
            CandidateChannel.GRAPH: graph_results,
            CandidateChannel.TEMPORAL: temporal_results,
            CandidateChannel.ENTITY: entity_results,
        }

        channels = cls.channels_for_route(route)

        entry_ids: list[int] = []
        seen: set[int] = set()

        for channel in channels:
            for result in channel_results[channel]:
                entry_id = cls._entry_id(result)

                if entry_id in seen:
                    continue

                seen.add(entry_id)
                entry_ids.append(entry_id)

                if len(entry_ids) >= policy.candidate_limit:
                    return CandidateSet(
                        entry_ids=tuple(entry_ids),
                        channels=channels,
                    )

        return CandidateSet(
            entry_ids=tuple(entry_ids),
            channels=channels,
        )


def generate_candidates(
    route: RetrievalRoute,
    *,
    keyword_results: Sequence = (),
    semantic_results: Sequence = (),
    graph_results: Sequence = (),
    temporal_results: Sequence = (),
    entity_results: Sequence = (),
    candidate_limit: int = 20,
) -> CandidateSet:
    """Convenience wrapper for deterministic candidate generation."""

    return CandidateGenerator.generate(
        route,
        keyword_results=keyword_results,
        semantic_results=semantic_results,
        graph_results=graph_results,
        temporal_results=temporal_results,
        entity_results=entity_results,
        candidate_limit=candidate_limit,
    )
