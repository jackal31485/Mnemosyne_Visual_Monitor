import sqlite3

import pytest

from src.domain.entities import EntityDAO
from src.domain.entity_mentions import EntityMentionDAO
from src.domain.entity_resolutions import EntityResolutionDAO
from src.services.entity_resolution import (
    generate_candidates,
    normalize_entity_name,
    resolve_and_record,
    resolve_mention,
)


def make_daos(tmp_path):
    db = tmp_path / "collective.db"

    entity_dao = EntityDAO(db)
    entity_dao.ensure_schema()

    mention_dao = EntityMentionDAO(db)
    mention_dao.ensure_schema()

    resolution_dao = EntityResolutionDAO(db)
    resolution_dao.ensure_schema()

    return entity_dao, mention_dao, resolution_dao


def add_mention(
    mention_dao,
    *,
    mention_id,
    mention_text,
    entity_type="technology",
    source_profile="athena",
    source_memory_id="memory-1",
    collective_entry_id=1,
):
    return mention_dao.add(
        mention_id=mention_id,
        collective_entry_id=collective_entry_id,
        source_memory_id=source_memory_id,
        source_profile=source_profile,
        mention_text=mention_text,
        entity_type=entity_type,
        confidence=0.95,
        extraction_method="deterministic-v1",
    )


def test_normalization_is_case_and_punctuation_tolerant():
    assert normalize_entity_name(" Mnemosyne  Visual-Monitor ") == (
        "mnemosyne visual monitor"
    )


def test_normalization_does_not_reduce_to_shared_tokens():
    assert normalize_entity_name("Mnemosyne") != normalize_entity_name(
        "Mnemosyne Visual Monitor"
    )


def test_normalization_preserves_unicode_entity_names():
    assert normalize_entity_name("München") == "münchen"
    assert normalize_entity_name("東京") == "東京"


def test_exact_normalized_match_produces_single_candidate(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    entity_id = entity_dao.create(
        "Mnemosyne Visual Monitor",
        "project",
    )

    add_mention(
        mention_dao,
        mention_id="mention-1",
        mention_text="mnemosyne visual-monitor",
        entity_type="project",
    )

    mention = mention_dao.get("mention-1")
    candidates = generate_candidates(mention, entity_dao)

    assert len(candidates) == 1
    assert candidates[0].entity_id == entity_id
    assert candidates[0].score == pytest.approx(1.0)

    result = resolve_mention(mention, entity_dao)

    assert result.decision == "same_entity"
    assert result.proposed_entity_id == entity_id
    assert result.confidence == pytest.approx(1.0)

    assert resolution_dao.list() == []


def test_no_match_is_new_entity_without_creating_entity(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    add_mention(
        mention_dao,
        mention_id="mention-1",
        mention_text="Mnemosyne",
    )

    before = entity_dao.list()

    result = resolve_and_record(
        mention_dao,
        entity_dao,
        resolution_dao,
        mention_id="mention-1",
    )

    assert result.decision == "new_entity"
    assert result.proposed_entity_id is None
    assert result.confidence == pytest.approx(1.0)

    assert entity_dao.list() == before

    resolution = resolution_dao.get_for_mention("mention-1")
    assert resolution["decision"] == "new_entity"
    assert resolution["proposed_entity_id"] is None


def test_entity_type_mismatch_does_not_match(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    entity_id = entity_dao.create(
        "Mnemosyne",
        "project",
    )

    add_mention(
        mention_dao,
        mention_id="mention-1",
        mention_text="Mnemosyne",
        entity_type="technology",
    )

    result = resolve_mention(
        mention_dao.get("mention-1"),
        entity_dao,
    )

    assert result.decision == "new_entity"
    assert result.proposed_entity_id is None
    assert entity_dao.get(entity_id)["entity_type"] == "project"
    assert resolution_dao.list() == []


def test_inactive_entity_is_not_candidate(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    entity_id = entity_dao.create(
        "Mnemosyne",
        "technology",
    )
    entity_dao.update(entity_id, status="inactive")

    add_mention(
        mention_dao,
        mention_id="mention-1",
        mention_text="Mnemosyne",
    )

    result = resolve_mention(
        mention_dao.get("mention-1"),
        entity_dao,
    )

    assert result.decision == "new_entity"
    assert result.candidates == ()
    assert resolution_dao.list() == []


def test_multiple_exact_candidates_are_ambiguous(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    entity_dao.create(
        "Athena",
        "technology",
        entity_id="entity-a",
    )
    entity_dao.create(
        "ATHENA",
        "technology",
        entity_id="entity-b",
    )

    add_mention(
        mention_dao,
        mention_id="mention-1",
        mention_text="athena",
    )

    result = resolve_and_record(
        mention_dao,
        entity_dao,
        resolution_dao,
        mention_id="mention-1",
    )

    assert result.decision == "ambiguous"
    assert result.proposed_entity_id is None
    assert result.confidence == pytest.approx(0.0)
    assert [c.entity_id for c in result.candidates] == [
        "entity-a",
        "entity-b",
    ]

    resolution = resolution_dao.get_for_mention("mention-1")
    assert resolution["decision"] == "ambiguous"
    assert resolution["proposed_entity_id"] is None
    assert resolution["evidence"]["candidate_entity_ids"] == [
        "entity-a",
        "entity-b",
    ]


def test_qualified_identity_is_not_flattened(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    entity_id = entity_dao.create(
        "agent-a:athena",
        "technology",
    )

    add_mention(
        mention_dao,
        mention_id="mention-1",
        mention_text="agent-a:athena",
    )

    result = resolve_and_record(
        mention_dao,
        entity_dao,
        resolution_dao,
        mention_id="mention-1",
    )

    assert result.decision == "same_entity"
    assert result.proposed_entity_id == entity_id
    assert entity_dao.get(entity_id)["canonical_name"] == "agent-a:athena"


def test_similar_but_non_identical_name_is_not_silently_matched(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    entity_dao.create(
        "Mnemosyne Visual Monitor",
        "project",
    )

    add_mention(
        mention_dao,
        mention_id="mention-1",
        mention_text="Mnemosyne",
        entity_type="project",
    )

    result = resolve_mention(
        mention_dao.get("mention-1"),
        entity_dao,
    )

    assert result.decision == "new_entity"
    assert result.proposed_entity_id is None


def test_resolver_does_not_modify_existing_entity(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    entity_id = entity_dao.create(
        "Mnemosyne",
        "technology",
        confidence=0.8,
        metadata={"original": True},
    )

    add_mention(
        mention_dao,
        mention_id="mention-1",
        mention_text="MNEMOSYNE",
    )

    before = entity_dao.get(entity_id)

    resolve_and_record(
        mention_dao,
        entity_dao,
        resolution_dao,
        mention_id="mention-1",
    )

    after = entity_dao.get(entity_id)

    assert after == before


def test_duplicate_resolution_is_not_silently_replaced(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    entity_id = entity_dao.create(
        "Mnemosyne",
        "technology",
    )

    add_mention(
        mention_dao,
        mention_id="mention-1",
        mention_text="Mnemosyne",
    )

    resolve_and_record(
        mention_dao,
        entity_dao,
        resolution_dao,
        mention_id="mention-1",
    )

    with pytest.raises(sqlite3.IntegrityError):
        resolve_and_record(
            mention_dao,
            entity_dao,
            resolution_dao,
            mention_id="mention-1",
        )

    assert entity_dao.get(entity_id)["canonical_name"] == "Mnemosyne"


def test_missing_mention_is_rejected(tmp_path):
    entity_dao, mention_dao, resolution_dao = make_daos(tmp_path)

    with pytest.raises(KeyError):
        resolve_and_record(
            mention_dao,
            entity_dao,
            resolution_dao,
            mention_id="does-not-exist",
        )
