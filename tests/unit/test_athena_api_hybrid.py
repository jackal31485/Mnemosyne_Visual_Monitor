from unittest.mock import Mock

import pytest

from src.domain.athena_api import AthenaAPI


def test_search_hybrid_requires_configured_service():
    api = AthenaAPI()

    with pytest.raises(RuntimeError, match="hybrid retrieval service is not configured"):
        api.search_hybrid("test query")


def test_search_hybrid_delegates_to_injected_service():
    service = Mock()
    expected = [
        Mock(
            entry_id=123,
            source_profile="athena",
            origin_memory_id="memory-123",
        )
    ]
    service.search.return_value = expected

    api = AthenaAPI(hybrid_service=service)

    results = api.search_hybrid(
        "How did we fix the timeline API?",
        top_k=5,
        candidate_limit=20,
        keyword_limit=15,
        semantic_limit=17,
        graph_seed_limit=4,
        graph_limit_per_seed=3,
        profile="athena",
        temporal_mode="recency",
        reference_time="REFERENCE_TIME",
        rerank=True,
    )

    assert results == expected

    service.search.assert_called_once_with(
        "How did we fix the timeline API?",
        top_k=5,
        candidate_limit=20,
        keyword_limit=15,
        semantic_limit=17,
        graph_seed_limit=4,
        graph_limit_per_seed=3,
        profile="athena",
        temporal_mode="recency",
        temporal_start=None,
        temporal_end=None,
        reference_time="REFERENCE_TIME",
        rerank=True,
    )


def test_search_hybrid_forwards_event_date_arguments():
    service = Mock()
    service.search.return_value = []

    api = AthenaAPI(hybrid_service=service)

    api.search_hybrid(
        "phase 7",
        top_k=3,
        temporal_mode="event_date",
        temporal_start="START",
        temporal_end="END",
        rerank=False,
    )

    service.search.assert_called_once_with(
        "phase 7",
        top_k=3,
        candidate_limit=20,
        keyword_limit=20,
        semantic_limit=20,
        graph_seed_limit=5,
        graph_limit_per_seed=4,
        profile=None,
        temporal_mode="event_date",
        temporal_start="START",
        temporal_end="END",
        reference_time=None,
        rerank=False,
    )
