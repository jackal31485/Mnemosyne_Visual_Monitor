from types import SimpleNamespace

import pytest

from src.retrieval.entity_search import EntitySearcher


class FakeEntityDAO:
    def __init__(self, entities):
        self.entities = entities

    def list(self, *, status=None):
        if status is None:
            return list(self.entities)
        return [
            entity
            for entity in self.entities
            if entity["status"] == status
        ]


class FakeResolutionDAO:
    def __init__(self, resolutions):
        self.resolutions = resolutions

    def list(self, *, decision=None, proposed_entity_id=None):
        results = list(self.resolutions)

        if decision is not None:
            results = [
                item for item in results
                if item["decision"] == decision
            ]

        if proposed_entity_id is not None:
            results = [
                item
                for item in results
                if item["proposed_entity_id"] == proposed_entity_id
            ]

        return results


class FakeMentionDAO:
    def __init__(self, mentions):
        self.mentions = mentions

    def list(
        self,
        *,
        collective_entry_id=None,
        source_profile=None,
        entity_type=None,
    ):
        results = list(self.mentions)

        if collective_entry_id is not None:
            results = [
                item
                for item in results
                if item["collective_entry_id"] == collective_entry_id
            ]

        if source_profile is not None:
            results = [
                item
                for item in results
                if item["source_profile"] == source_profile
            ]

        if entity_type is not None:
            results = [
                item
                for item in results
                if item["entity_type"] == entity_type
            ]

        return results


class FakeCollectiveDAO:
    def __init__(self, lifecycle, provenance):
        self.lifecycle = lifecycle
        self.provenance = provenance
        self.content_accessed = False

    def get_lifecycle_state(self, entry_id):
        return self.lifecycle.get(entry_id)

    def get_provenance(self, entry_id):
        return list(self.provenance.get(entry_id, []))

    def __getattr__(self, name):
        if name in {"get_content", "get_memory", "get_entry_content"}:
            self.content_accessed = True
            raise AssertionError("entity retrieval must not access memory content")
        raise AttributeError(name)


def make_searcher(
    *,
    entities,
    mentions,
    resolutions,
    lifecycle,
    provenance,
):
    collective = FakeCollectiveDAO(lifecycle, provenance)

    searcher = EntitySearcher(
        collective_dao=collective,
        entity_dao=FakeEntityDAO(entities),
        mention_dao=FakeMentionDAO(mentions),
        resolution_dao=FakeResolutionDAO(resolutions),
    )

    return searcher, collective


def entity(entity_id="entity-python", name="Python", status="active"):
    return {
        "entity_id": entity_id,
        "canonical_name": name,
        "entity_type": "technology",
        "status": status,
    }


def mention(
    mention_id="mention-1",
    entry_id=1,
    profile="profile-a",
    text="Python",
):
    return {
        "mention_id": mention_id,
        "collective_entry_id": entry_id,
        "source_memory_id": "memory-1",
        "source_profile": profile,
        "mention_text": text,
        "entity_type": "technology",
        "confidence": 1.0,
        "extraction_method": "deterministic-v1",
    }


def resolution(
    mention_id="mention-1",
    entity_id="entity-python",
    decision="same_entity",
):
    return {
        "resolution_id": f"resolution-{mention_id}",
        "mention_id": mention_id,
        "proposed_entity_id": entity_id,
        "decision": decision,
        "confidence": 1.0,
        "resolution_method": "normalized-name-v1",
    }


def lifecycle(*, promoted=True, revoked=False):
    return (
        "2026-09-10T12:00:00",
        int(revoked),
        None,
        int(promoted),
    )


def provenance(profile="profile-a", memory_id="memory-1"):
    return {
        "source_profile": profile,
        "origin_memory_id": memory_id,
        "created_at": "2026-09-10T12:00:00",
    }


def test_exact_entity_match_returns_governed_memory():
    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[mention()],
        resolutions=[resolution()],
        lifecycle={1: lifecycle()},
        provenance={1: [provenance()]},
    )

    results = searcher.search("Python")

    assert len(results) == 1
    assert results[0].entry_id == 1
    assert results[0].source_profile == "profile-a"
    assert results[0].origin_memory_id == "memory-1"
    assert results[0].entity_score == 1.0


def test_entity_name_matching_is_normalized():
    searcher, _ = make_searcher(
        entities=[entity(name="Python")],
        mentions=[mention()],
        resolutions=[resolution()],
        lifecycle={1: lifecycle()},
        provenance={1: [provenance()]},
    )

    results = searcher.search("  PYTHON  ")

    assert [result.entry_id for result in results] == [1]


def test_non_matching_entity_returns_empty():
    searcher, _ = make_searcher(
        entities=[entity(name="Python")],
        mentions=[mention()],
        resolutions=[resolution()],
        lifecycle={1: lifecycle()},
        provenance={1: [provenance()]},
    )

    assert searcher.search("FastAPI") == []


@pytest.mark.parametrize(
    "decision",
    ["new_entity", "ambiguous", "unresolved", "rejected"],
)
def test_only_same_entity_resolution_is_followed(decision):
    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[mention()],
        resolutions=[resolution(decision=decision)],
        lifecycle={1: lifecycle()},
        provenance={1: [provenance()]},
    )

    assert searcher.search("Python") == []


def test_inactive_entity_is_not_retrieved():
    searcher, _ = make_searcher(
        entities=[entity(status="inactive")],
        mentions=[mention()],
        resolutions=[resolution()],
        lifecycle={1: lifecycle()},
        provenance={1: [provenance()]},
    )

    assert searcher.search("Python") == []


def test_revoked_memory_is_not_retrieved():
    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[mention()],
        resolutions=[resolution()],
        lifecycle={1: lifecycle(revoked=True)},
        provenance={1: [provenance()]},
    )

    assert searcher.search("Python") == []


def test_unpromoted_memory_is_not_retrieved():
    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[mention()],
        resolutions=[resolution()],
        lifecycle={1: lifecycle(promoted=False)},
        provenance={1: [provenance()]},
    )

    assert searcher.search("Python") == []


def test_profile_filter_preserves_qualified_identity():
    qualified_a = "uuid-a:athena"
    qualified_b = "uuid-b:athena"

    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[
            mention(
                mention_id="mention-a",
                entry_id=1,
                profile=qualified_a,
            ),
            mention(
                mention_id="mention-b",
                entry_id=2,
                profile=qualified_b,
            ),
        ],
        resolutions=[
            resolution(mention_id="mention-a"),
            resolution(mention_id="mention-b"),
        ],
        lifecycle={
            1: lifecycle(),
            2: lifecycle(),
        },
        provenance={
            1: [provenance(qualified_a, "memory-a")],
            2: [provenance(qualified_b, "memory-b")],
        },
    )

    results = searcher.search("Python", profile=qualified_a)

    assert [
        (result.entry_id, result.source_profile, result.origin_memory_id)
        for result in results
    ] == [
        (1, qualified_a, "memory-a"),
    ]


def test_multiple_provenance_rows_remain_qualified():
    profile_a = "uuid-a:athena"
    profile_b = "uuid-b:athena"

    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[
            mention(
                mention_id="mention-a",
                entry_id=1,
                profile=profile_a,
            ),
            mention(
                mention_id="mention-b",
                entry_id=1,
                profile=profile_b,
            ),
        ],
        resolutions=[
            resolution(mention_id="mention-a"),
            resolution(mention_id="mention-b"),
        ],
        lifecycle={1: lifecycle()},
        provenance={
            1: [
                provenance(profile_a, "memory-a"),
                provenance(profile_b, "memory-b"),
            ],
        },
    )

    results = searcher.search("Python")

    assert [
        (result.entry_id, result.source_profile, result.origin_memory_id)
        for result in results
    ] == [
        (1, profile_a, "memory-a"),
        (1, profile_b, "memory-b"),
    ]


def test_duplicate_mentions_do_not_duplicate_same_provenance_identity():
    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[
            mention(
                mention_id="mention-1",
                entry_id=1,
            ),
            mention(
                mention_id="mention-2",
                entry_id=1,
            ),
        ],
        resolutions=[
            resolution(mention_id="mention-1"),
            resolution(mention_id="mention-2"),
        ],
        lifecycle={1: lifecycle()},
        provenance={1: [provenance()]},
    )

    results = searcher.search("Python")

    assert [
        (result.entry_id, result.source_profile, result.origin_memory_id)
        for result in results
    ] == [(1, "profile-a", "memory-1")]


def test_results_are_deterministically_sorted():
    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[
            mention(
                mention_id="mention-2",
                entry_id=2,
            ),
            mention(
                mention_id="mention-1",
                entry_id=1,
            ),
        ],
        resolutions=[
            resolution(mention_id="mention-2"),
            resolution(mention_id="mention-1"),
        ],
        lifecycle={
            1: lifecycle(),
            2: lifecycle(),
        },
        provenance={
            1: [provenance(memory_id="memory-1")],
            2: [provenance(memory_id="memory-2")],
        },
    )

    first = searcher.search("Python")
    second = searcher.search("Python")

    assert first == second
    assert [result.entry_id for result in first] == [1, 2]


def test_limit_is_enforced():
    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[
            mention(
                mention_id="mention-1",
                entry_id=1,
            ),
            mention(
                mention_id="mention-2",
                entry_id=2,
            ),
        ],
        resolutions=[
            resolution(mention_id="mention-1"),
            resolution(mention_id="mention-2"),
        ],
        lifecycle={
            1: lifecycle(),
            2: lifecycle(),
        },
        provenance={
            1: [provenance(memory_id="memory-1")],
            2: [provenance(memory_id="memory-2")],
        },
    )

    results = searcher.search("Python", limit=1)

    assert len(results) == 1


def test_invalid_inputs_are_rejected():
    searcher, _ = make_searcher(
        entities=[entity()],
        mentions=[],
        resolutions=[],
        lifecycle={},
        provenance={},
    )

    with pytest.raises(TypeError):
        searcher.search(None)

    with pytest.raises(ValueError):
        searcher.search("Python", limit=0)

    with pytest.raises(ValueError):
        searcher.search("Python", profile="")

    assert searcher.search("   ") == []


def test_entity_search_never_accesses_memory_content():
    searcher, collective = make_searcher(
        entities=[entity()],
        mentions=[mention()],
        resolutions=[resolution()],
        lifecycle={1: lifecycle()},
        provenance={1: [provenance()]},
    )

    results = searcher.search("Python")

    assert results
    assert collective.content_accessed is False
    assert all(
        not hasattr(result, "content")
        for result in results
    )
