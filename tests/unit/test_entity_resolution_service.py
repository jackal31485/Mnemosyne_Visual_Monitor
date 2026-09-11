import sqlite3

from src.domain.entities import EntityDAO
from src.domain.entity_mentions import EntityMentionDAO
from src.domain.entity_resolutions import EntityResolutionDAO
from src.services.entity_resolution_service import resolve_entities


def make_daos(tmp_path):
    db = tmp_path / "collective.db"

    entities = EntityDAO(db)
    mentions = EntityMentionDAO(db)
    resolutions = EntityResolutionDAO(db)

    entities.ensure_schema()
    mentions.ensure_schema()
    resolutions.ensure_schema()

    return entities, mentions, resolutions


def add_mention(
    mentions,
    mention_id,
    text,
    *,
    entity_type="technology",
    profile="athena",
):
    return mentions.add(
        mention_id=mention_id,
        collective_entry_id=1,
        source_memory_id=f"memory-{mention_id}",
        source_profile=profile,
        mention_text=text,
        entity_type=entity_type,
        confidence=0.95,
        extraction_method="deterministic-v1",
    )


def test_batch_resolves_unresolved_mentions(tmp_path):
    entities, mentions, resolutions = make_daos(tmp_path)

    entity_id = entities.create("Python", "technology")

    add_mention(mentions, "m1", "python")
    add_mention(mentions, "m2", "SQLite")

    report = resolve_entities(mentions, entities, resolutions)

    assert report.processed == 2
    assert report.resolutions_created == 2
    assert report.resolutions_existing == 0
    assert report.skipped == 0
    assert report.failures == ()

    assert resolutions.get_for_mention("m1")["proposed_entity_id"] == entity_id
    assert resolutions.get_for_mention("m2")["decision"] == "new_entity"


def test_batch_is_idempotent(tmp_path):
    entities, mentions, resolutions = make_daos(tmp_path)

    entities.create("Python", "technology")
    add_mention(mentions, "m1", "Python")

    first = resolve_entities(mentions, entities, resolutions)
    before = resolutions.get_for_mention("m1")

    second = resolve_entities(mentions, entities, resolutions)
    after = resolutions.get_for_mention("m1")

    assert first.resolutions_created == 1
    assert second.processed == 0
    assert second.resolutions_created == 0
    assert second.resolutions_existing == 1
    assert second.skipped == 0
    assert before == after


def test_batch_preserves_qualified_source_profile(tmp_path):
    entities, mentions, resolutions = make_daos(tmp_path)

    entities.create("Athena", "technology")

    add_mention(
        mentions,
        "m1",
        "Athena",
        profile="agent-a:athena",
    )

    resolve_entities(mentions, entities, resolutions)

    resolution = resolutions.get_for_mention("m1")

    assert resolution["evidence"]["source_profile"] == "agent-a:athena"
    assert resolution["proposed_entity_id"] is not None


def test_batch_does_not_create_entities(tmp_path):
    entities, mentions, resolutions = make_daos(tmp_path)

    add_mention(
        mentions,
        "m1",
        "Brand New Entity",
        entity_type="project",
    )

    before = entities.list()

    report = resolve_entities(mentions, entities, resolutions)

    assert report.resolutions_created == 1
    assert resolutions.get_for_mention("m1")["decision"] == "new_entity"
    assert entities.list() == before


def test_batch_records_ambiguous_match(tmp_path):
    entities, mentions, resolutions = make_daos(tmp_path)

    entities.create("Athena", "technology", entity_id="a")
    entities.create("ATHENA", "technology", entity_id="b")

    add_mention(mentions, "m1", "athena")

    report = resolve_entities(mentions, entities, resolutions)
    resolution = resolutions.get_for_mention("m1")

    assert report.failures == ()
    assert resolution["decision"] == "ambiguous"
    assert resolution["proposed_entity_id"] is None
    assert resolution["evidence"]["candidate_entity_ids"] == ["a", "b"]


def test_batch_continues_after_failure(tmp_path, monkeypatch):
    entities, mentions, resolutions = make_daos(tmp_path)

    add_mention(mentions, "m1", "Python")
    add_mention(mentions, "m2", "SQLite")

    original_create = resolutions.create
    calls = {"count": 0}

    def failing_create(**kwargs):
        calls["count"] += 1

        if calls["count"] == 1:
            raise sqlite3.OperationalError("simulated write failure")

        return original_create(**kwargs)

    monkeypatch.setattr(resolutions, "create", failing_create)

    report = resolve_entities(mentions, entities, resolutions)

    assert report.processed == 2
    assert report.resolutions_created == 1
    assert report.skipped == 1
    assert len(report.failures) == 1
    assert report.failures[0].mention_id == "m1"

    assert resolutions.get_for_mention("m1") is None
    assert resolutions.get_for_mention("m2") is not None


def test_batch_preserves_existing_resolution(tmp_path):
    entities, mentions, resolutions = make_daos(tmp_path)

    entity_id = entities.create("Python", "technology")

    add_mention(mentions, "m1", "Python")

    resolutions.create(
        mention_id="m1",
        proposed_entity_id=None,
        decision="ambiguous",
        confidence=0.0,
        resolution_method="manual-test",
        evidence={"reason": "preserve-existing"},
    )

    report = resolve_entities(mentions, entities, resolutions)
    result = resolutions.get_for_mention("m1")

    assert report.processed == 0
    assert report.resolutions_existing == 1
    assert result["decision"] == "ambiguous"
    assert result["proposed_entity_id"] is None
    assert result["evidence"] == {"reason": "preserve-existing"}

    assert entities.get(entity_id)["canonical_name"] == "Python"


def test_batch_empty_input(tmp_path):
    entities, mentions, resolutions = make_daos(tmp_path)

    report = resolve_entities(mentions, entities, resolutions)

    assert report.processed == 0
    assert report.resolutions_created == 0
    assert report.resolutions_existing == 0
    assert report.skipped == 0
    assert report.failures == ()
