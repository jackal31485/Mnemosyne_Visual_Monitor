"""Deterministic retrieval routing for Phase 15A.

Query routing selects retrieval channels based on query classification.
It does not perform authorization, governance, filtering, or retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.retrieval.query_classification import (
    QueryClassification,
    QueryIntent,
    classify_query,
)


class RetrievalChannel(str, Enum):
    """Existing retrieval capabilities that may be selected by the router."""

    SEMANTIC = "semantic"
    LEXICAL = "lexical"
    TEMPORAL = "temporal"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"


@dataclass(frozen=True)
class RetrievalRoute:
    """Immutable retrieval-channel selection."""

    intent: QueryIntent
    normalized_query: str
    channels: tuple[RetrievalChannel, ...]
    signals: tuple[str, ...]


class QueryRouter:
    """Map query classifications to deterministic retrieval channels."""

    _ROUTES: dict[QueryIntent, tuple[RetrievalChannel, ...]] = {
        QueryIntent.SEMANTIC: (
            RetrievalChannel.SEMANTIC,
        ),
        QueryIntent.LEXICAL: (
            RetrievalChannel.LEXICAL,
        ),
        QueryIntent.TEMPORAL: (
            RetrievalChannel.TEMPORAL,
            RetrievalChannel.SEMANTIC,
        ),
        QueryIntent.ENTITY: (
            RetrievalChannel.ENTITY,
            RetrievalChannel.SEMANTIC,
        ),
        QueryIntent.RELATIONSHIP: (
            RetrievalChannel.RELATIONSHIP,
            RetrievalChannel.ENTITY,
            RetrievalChannel.SEMANTIC,
        ),
        QueryIntent.HYBRID: (
            RetrievalChannel.LEXICAL,
            RetrievalChannel.SEMANTIC,
            RetrievalChannel.TEMPORAL,
            RetrievalChannel.ENTITY,
            RetrievalChannel.RELATIONSHIP,
        ),
    }

    @classmethod
    def route(
        cls,
        classification: QueryClassification,
    ) -> RetrievalRoute:
        """Create a deterministic route from a validated classification."""

        if not isinstance(classification, QueryClassification):
            raise TypeError(
                "classification must be a QueryClassification"
            )

        channels = cls._ROUTES.get(classification.intent)

        if channels is None:
            raise ValueError(
                f"unsupported query intent: {classification.intent!r}"
            )

        return RetrievalRoute(
            intent=classification.intent,
            normalized_query=classification.normalized_query,
            channels=channels,
            signals=classification.signals,
        )

    @classmethod
    def route_query(cls, query: str) -> RetrievalRoute:
        """Classify and route a raw query."""

        return cls.route(classify_query(query))


def route_query(query: str) -> RetrievalRoute:
    """Convenience wrapper for query classification and routing."""

    return QueryRouter.route_query(query)
