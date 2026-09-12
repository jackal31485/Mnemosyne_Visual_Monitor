import sqlite3

from src.domain.collective import CollectiveDAO
from src.domain.entities import EntityDAO
from src.domain.entity_evidence import EntityEvidenceDAO
from src.domain.entity_mentions import EntityMentionDAO
from src.domain.entity_resolutions import EntityResolutionDAO
from src.domain.memory_gateway import InMemoryMemoryGateway
from src.domain.relationship_evidence import RelationshipEvidenceDAO
from src.domain.relationships import RelationshipDAO
from src.services.entity_relationship_rebuild import (
    rebuild_entity_relationship_intelligence,
)


def make_environment(tmp_path):
    db = tmp_path / "collective.db"

    collective = CollectiveDAO(db)
    entities = EntityDAO(db)
    mentions = EntityMentionDAO(db)
    resolutions = EntityResolutionDAO(db)
    entity_evidence = EntityEvidenceDAO(db)
    relationships = RelationshipDAO(db)
    relationship_evidence = RelationshipEvidenceDAO(db)

    collective.ensure_schema()
    entities.ensure_schema()
    mentions.ensure_schema()
    resolutions.ensure_schema()
    entity_evidence.ensure_schema()
    relationships.ensure_schema()
    relationship_evidence.ensure_schema()

    return (
        collective,
        entities,
        mentions,
        resolutions,
        entity_evidence,
        relationships,
        relationship_evidence,
    )


def make_gateway(*memories):
    return InMemoryMemoryGateway(dict(memories))


def stable_snapshot(rows, excluded_fields=()):
    excluded = set(excluded_fields)
    return [
        {
            key: value
            for key, value in row.items()
            if key not in excluded
        }
        for row in rows
    ]


def promote(collective, source_profile, memory_id):
    entry_id = collective.insert_collective_entry(
        source_profile=source_profile,
        origin_memory_id=memory_id,
    )
    collective.update_entry_promoted(entry_id)
    return entry_id


def test_rebuild_bootstraps_entities_and_evidence(tmp_path):
    (
        collective,
        entities,
        mentions,
        resolutions,
        entity_evidence,
        relationships,
        relationship_evidence,
    ) = make_environment(tmp_path)

    entry_id = promote(collective, "agent-a:athena", "memory-1")

    gateway = make_gateway(
        (("agent-a:athena", "memory-1"), "Mnemosyne uses Python."),
    )

    report = rebuild_entity_relationship_intelligence(
        collective_dao=collective,
        entity_dao=entities,
        mention_dao=mentions,
        resolution_dao=resolutions,
        entity_evidence_dao=entity_evidence,
        relationship_dao=relationships,
        relationship_evidence_dao=relationship_evidence,
        gateway=gateway,
    )

    assert report.entity_extraction.processed == 1
    assert report.entity_extraction.failures == ()
    assert report.entity_bootstrap.mentions_examined == 2
    assert report.entity_bootstrap.entities_created == 2
    assert report.entity_bootstrap.resolutions_created == 2
    assert report.entity_bootstrap.failures == ()

    assert len(entities.list()) == 2
    assert len(mentions.list()) == 2
    assert len(resolutions.list()) == 2
    assert len(entity_evidence.list()) == 2

    evidence = entity_evidence.list(
        collective_entry_id=entry_id,
    )

    assert len(evidence) == 2
    assert {
        item["source_profile"]
        for item in evidence
    } == {"agent-a:athena"}

    assert {
        item["original_mention"]
        for item in evidence
    } == {"Mnemosyne", "Python"}

    collective_row = collective.get_by_id(entry_id)
    assert collective_row is not None
    assert collective_row[1] == "agent-a:athena"
    assert collective_row[2] == "memory-1"
    assert collective_row[7] == 0


def test_rebuild_extracts_relationships_and_evidence(tmp_path):
    (
        collective,
        entities,
        mentions,
        resolutions,
        entity_evidence,
        relationships,
        relationship_evidence,
    ) = make_environment(tmp_path)

    entry_id = promote(collective, "agent-a:athena", "memory-1")

    gateway = make_gateway(
        (("agent-a:athena", "memory-1"), "Mnemosyne uses Python."),
    )

    report = rebuild_entity_relationship_intelligence(
        collective_dao=collective,
        entity_dao=entities,
        mention_dao=mentions,
        resolution_dao=resolutions,
        entity_evidence_dao=entity_evidence,
        relationship_dao=relationships,
        relationship_evidence_dao=relationship_evidence,
        gateway=gateway,
    )

    assert report.relationship_extraction.failures == ()
    assert report.relationship_extraction.relationships_created == 1
    assert report.relationship_extraction.evidence_created == 1

    stored_relationships = relationships.list()
    assert len(stored_relationships) == 1

    relationship = stored_relationships[0]
    assert relationship["predicate"] == "uses"
    assert relationship["relationship_kind"] == "explicit"
    assert relationship["status"] == "active"

    evidence = relationship_evidence.list(
        relationship_id=relationship["relationship_id"],
    )

    assert len(evidence) == 1
    assert evidence[0]["collective_entry_id"] == entry_id
    assert evidence[0]["source_profile"] == "agent-a:athena"
    assert evidence[0]["source_memory_id"] == "memory-1"


def test_rebuild_ignores_unpromoted_and_revoked_entries(tmp_path):
    (
        collective,
        entities,
        mentions,
        resolutions,
        entity_evidence,
        relationships,
        relationship_evidence,
    ) = make_environment(tmp_path)

    promoted_id = promote(collective, "agent-a:athena", "promoted")

    unpromoted_id = collective.insert_collective_entry(
        source_profile="agent-a:athena",
        origin_memory_id="unpromoted",
    )

    revoked_id = promote(collective, "agent-a:athena", "revoked")
    collective.update_entry_revoked(revoked_id, "test revocation")

    gateway = make_gateway(
        (("agent-a:athena", "promoted"), "Mnemosyne uses Python."),
        (("agent-a:athena", "unpromoted"), "SQLite uses Python."),
        (("agent-a:athena", "revoked"), "Hermes uses Python."),
    )

    report = rebuild_entity_relationship_intelligence(
        collective_dao=collective,
        entity_dao=entities,
        mention_dao=mentions,
        resolution_dao=resolutions,
        entity_evidence_dao=entity_evidence,
        relationship_dao=relationships,
        relationship_evidence_dao=relationship_evidence,
        gateway=gateway,
    )

    assert report.entity_extraction.processed == 1
    assert report.entity_extraction.failures == ()

    mention_entries = {
        mention["collective_entry_id"]
        for mention in mentions.list()
    }

    assert mention_entries == {promoted_id}
    assert unpromoted_id not in mention_entries
    assert revoked_id not in mention_entries


def test_rebuild_preserves_collective_lifecycle_and_provenance(tmp_path):
    (
        collective,
        entities,
        mentions,
        resolutions,
        entity_evidence,
        relationships,
        relationship_evidence,
    ) = make_environment(tmp_path)

    entry_id = promote(collective, "agent-a:athena", "memory-1")

    collective.update_entry_revoked(entry_id, "test")
    before = collective.get_by_id(entry_id)

    gateway = make_gateway(
        (("agent-a:athena", "memory-1"), "Mnemosyne uses Python."),
    )

    rebuild_entity_relationship_intelligence(
        collective_dao=collective,
        entity_dao=entities,
        mention_dao=mentions,
        resolution_dao=resolutions,
        entity_evidence_dao=entity_evidence,
        relationship_dao=relationships,
        relationship_evidence_dao=relationship_evidence,
        gateway=gateway,
    )

    after = collective.get_by_id(entry_id)

    assert after == before
    assert mentions.list() == []
    assert entities.list() == []
    assert resolutions.list() == []
    assert entity_evidence.list() == []
    assert relationships.list() == []
    assert relationship_evidence.list() == []


def test_second_rebuild_is_deterministic_and_does_not_accumulate(tmp_path):
    (
        collective,
        entities,
        mentions,
        resolutions,
        entity_evidence,
        relationships,
        relationship_evidence,
    ) = make_environment(tmp_path)

    promote(collective, "agent-a:athena", "memory-1")
    promote(collective, "agent-b:horus", "memory-2")

    gateway = make_gateway(
        (("agent-a:athena", "memory-1"), "Mnemosyne uses Python."),
        (("agent-b:horus", "memory-2"), "Mnemosyne uses Python."),
    )

    first = rebuild_entity_relationship_intelligence(
        collective_dao=collective,
        entity_dao=entities,
        mention_dao=mentions,
        resolution_dao=resolutions,
        entity_evidence_dao=entity_evidence,
        relationship_dao=relationships,
        relationship_evidence_dao=relationship_evidence,
        gateway=gateway,
    )

    first_entities = entities.list()
    first_mentions = mentions.list()
    first_resolutions = resolutions.list()
    first_entity_evidence = entity_evidence.list()
    first_relationships = relationships.list()
    first_relationship_evidence = relationship_evidence.list()

    second = rebuild_entity_relationship_intelligence(
        collective_dao=collective,
        entity_dao=entities,
        mention_dao=mentions,
        resolution_dao=resolutions,
        entity_evidence_dao=entity_evidence,
        relationship_dao=relationships,
        relationship_evidence_dao=relationship_evidence,
        gateway=gateway,
    )

    assert first.entity_bootstrap.entities_created == 2
    assert second.entity_bootstrap.entities_created == 2

    assert stable_snapshot(
        entities.list(),
        excluded_fields=("created_at", "updated_at"),
    ) == stable_snapshot(
        first_entities,
        excluded_fields=("created_at", "updated_at"),
    )

    assert stable_snapshot(
        mentions.list(),
        excluded_fields=("extracted_at",),
    ) == stable_snapshot(
        first_mentions,
        excluded_fields=("extracted_at",),
    )

    assert stable_snapshot(
        resolutions.list(),
        excluded_fields=("decided_at",),
    ) == stable_snapshot(
        first_resolutions,
        excluded_fields=("decided_at",),
    )

    assert stable_snapshot(
        entity_evidence.list(),
        excluded_fields=("extracted_at",),
    ) == stable_snapshot(
        first_entity_evidence,
        excluded_fields=("extracted_at",),
    )

    assert stable_snapshot(
        relationships.list(),
        excluded_fields=("created_at", "updated_at"),
    ) == stable_snapshot(
        first_relationships,
        excluded_fields=("created_at", "updated_at"),
    )

    assert stable_snapshot(
        relationship_evidence.list(),
        excluded_fields=("created_at",),
    ) == stable_snapshot(
        first_relationship_evidence,
        excluded_fields=("created_at",),
    )

    assert second.relationship_extraction.relationships_created == 1
    assert len(entities.list()) == 2
    assert len(mentions.list()) == 4
    assert len(resolutions.list()) == 4
    assert len(entity_evidence.list()) == 4
    assert len(relationships.list()) == 1
    assert len(relationship_evidence.list()) == 2


def test_rebuild_does_not_create_duplicate_canonical_entities_for_same_name(
    tmp_path,
):
    (
        collective,
        entities,
        mentions,
        resolutions,
        entity_evidence,
        relationships,
        relationship_evidence,
    ) = make_environment(tmp_path)

    promote(collective, "agent-a:athena", "memory-1")
    promote(collective, "agent-b:horus", "memory-2")

    gateway = make_gateway(
        (("agent-a:athena", "memory-1"), "Python."),
        (("agent-b:horus", "memory-2"), "Python."),
    )

    rebuild_entity_relationship_intelligence(
        collective_dao=collective,
        entity_dao=entities,
        mention_dao=mentions,
        resolution_dao=resolutions,
        entity_evidence_dao=entity_evidence,
        relationship_dao=relationships,
        relationship_evidence_dao=relationship_evidence,
        gateway=gateway,
    )

    python_entities = [
        entity
        for entity in entities.list()
        if entity["canonical_name"].casefold() == "python"
    ]

    assert len(python_entities) == 1

    python_id = python_entities[0]["entity_id"]

    python_resolutions = [
        resolution
        for resolution in resolutions.list()
        if resolution["proposed_entity_id"] == python_id
    ]

    assert len(python_resolutions) == 2


def test_rebuild_does_not_modify_source_database(tmp_path):
    (
        collective,
        entities,
        mentions,
        resolutions,
        entity_evidence,
        relationships,
        relationship_evidence,
    ) = make_environment(tmp_path)

    promote(collective, "agent-a:athena", "memory-1")

    source_db = tmp_path / "source.db"
    source = sqlite3.connect(source_db)
    source.execute(
        "CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT)"
    )
    source.execute(
        "INSERT INTO memories VALUES (?, ?)",
        ("memory-1", "Mnemosyne uses Python."),
    )
    source.commit()
    before = source.execute(
        "SELECT * FROM memories"
    ).fetchall()
    source.close()

    class ReadOnlyGateway:
        def get_memory(self, profile, memory_id):
            connection = sqlite3.connect(source_db)
            try:
                row = connection.execute(
                    "SELECT content FROM memories WHERE id = ?",
                    (memory_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(memory_id)
                return row[0]
            finally:
                connection.close()

    rebuild_entity_relationship_intelligence(
        collective_dao=collective,
        entity_dao=entities,
        mention_dao=mentions,
        resolution_dao=resolutions,
        entity_evidence_dao=entity_evidence,
        relationship_dao=relationships,
        relationship_evidence_dao=relationship_evidence,
        gateway=ReadOnlyGateway(),
    )

    source = sqlite3.connect(source_db)
    after = source.execute(
        "SELECT * FROM memories"
    ).fetchall()
    source.close()

    assert after == before
