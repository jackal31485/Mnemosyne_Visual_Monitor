from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from src.domain.collective import CollectiveDAO
from src.domain.temporal_evidence import TemporalEvidenceDAO


def _prepare_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "collective.db"
    dao = CollectiveDAO(db_path)
    dao.ensure_schema()

    dao.conn.execute(
        """
        INSERT INTO collective_entries (
            source_profile,
            origin_memory_id,
            proposed_at,
            validated_at,
            validation_score,
            validator_profile,
            is_revoked,
            revocation_reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Horus",
            "mem-1",
            "2026-01-01T00:00:00",
            "2026-01-02T00:00:00",
            1.0,
            "validator",
            0,
            None,
        ),
    )
    dao.conn.commit()
    dao.update_entry_promoted(1)

    TemporalEvidenceDAO(db_path).ensure_schema()

    dao.conn.execute(
        """
        INSERT INTO temporal_evidence (
            temporal_evidence_id,
            collective_entry_id,
            subject_type,
            subject_id,
            object_type,
            object_id,
            temporal_relation,
            start_time,
            end_time,
            precision,
            confidence,
            evidence_kind,
            extraction_method,
            source_memory_id,
            source_profile,
            created_at
        )
        VALUES (
            'te-route-1', 1, 'entity', '10', NULL, NULL,
            'active', '2026-01-01', NULL, 'day', 0.9,
            'observed', 'test', 'mem-1', 'Horus',
            '2026-01-02T00:00:00'
        )
        """
    )
    dao.conn.commit()
    dao.close()

    return db_path


def test_temporal_history_routes_are_registered() -> None:
    client = TestClient(app)

    response = client.get("/api/temporal/history")

    assert response.status_code == 200
    assert response.json()["governance"]["promoted_only"] is True


def test_temporal_history_view_is_available() -> None:
    client = TestClient(app)

    response = client.get("/api/temporal/history/view")

    assert response.status_code == 200
    assert "Temporal History" in response.text
    assert "Missing evidence does not imply" in response.text


def test_relationship_temporal_history_rejects_self_reference() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/temporal/history/relationship",
        params={
            "source_entity_id": "10",
            "target_entity_id": "10",
            "relation": "friend",
        },
    )

    assert response.status_code == 400


def test_entity_history_service_backed(monkeypatch, tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)
    monkeypatch.setattr(
        "app.routes.temporal_history.DB_PATH",
        db_path,
    )

    client = TestClient(app)
    response = client.get("/api/temporal/history/entity/10")

    assert response.status_code == 200
    payload = response.json()

    assert payload["entity_id"] == "10"
    assert payload["history"]["observation_count"] == 1
    assert payload["summary"]["evidence_count"] == 1
    assert payload["summary"]["observed_states"] == ["active"]


def test_relationship_history_service_backed(monkeypatch, tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)

    dao = CollectiveDAO(db_path)
    dao.conn.execute(
        """
        INSERT INTO collective_entries (
            source_profile,
            origin_memory_id,
            proposed_at,
            validated_at,
            validation_score,
            validator_profile,
            is_revoked,
            revocation_reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Horus",
            "mem-2",
            "2026-02-01T00:00:00",
            "2026-02-02T00:00:00",
            1.0,
            "validator",
            0,
            None,
        ),
    )
    dao.conn.commit()

    dao.conn.execute(
        """
        INSERT INTO temporal_evidence (
            temporal_evidence_id,
            collective_entry_id,
            subject_type,
            subject_id,
            object_type,
            object_id,
            temporal_relation,
            start_time,
            end_time,
            precision,
            confidence,
            evidence_kind,
            extraction_method,
            source_memory_id,
            source_profile,
            created_at
        )
        VALUES (
            'te-route-2', 2, 'entity', '10', 'entity', '20',
            'knows', '2026-02-01', NULL, 'day', 0.8,
            'observed', 'test', 'mem-2', 'Horus',
            '2026-02-02T00:00:00'
        )
        """
    )
    dao.conn.commit()
    dao.update_entry_promoted(2)
    dao.close()

    monkeypatch.setattr(
        "app.routes.temporal_history.DB_PATH",
        db_path,
    )

    client = TestClient(app)
    response = client.get(
        "/api/temporal/history/relationship",
        params={
            "source_entity_id": "10",
            "target_entity_id": "20",
            "relation": "knows",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["history"]["observation_count"] == 1
    assert payload["summary"]["evidence_count"] == 1
    assert payload["ended_inferred"] is False
    assert payload["governance"]["missing_evidence_does_not_imply_ended"] is True


def test_revoked_temporal_evidence_is_hidden(monkeypatch, tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)

    dao = CollectiveDAO(db_path)
    dao.conn.execute(
        """
        UPDATE collective_entries
        SET is_revoked = 1, revocation_reason = 'test'
        WHERE id = 1
        """
    )
    dao.conn.commit()
    dao.update_entry_promoted(2)
    dao.close()

    monkeypatch.setattr(
        "app.routes.temporal_history.DB_PATH",
        db_path,
    )

    client = TestClient(app)
    response = client.get("/api/temporal/history/entity/10")

    assert response.status_code == 200
    assert response.json()["history"]["observation_count"] == 0


def test_source_memory_mismatch_is_hidden(monkeypatch, tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)

    dao = CollectiveDAO(db_path)
    dao.conn.execute(
        """
        UPDATE temporal_evidence
        SET source_memory_id = 'different-memory'
        WHERE temporal_evidence_id = 'te-route-1'
        """
    )
    dao.conn.commit()
    dao.close()

    monkeypatch.setattr(
        "app.routes.temporal_history.DB_PATH",
        db_path,
    )

    client = TestClient(app)
    response = client.get("/api/temporal/history/entity/10")

    assert response.status_code == 200
    assert response.json()["history"]["observation_count"] == 0


def test_source_profile_mismatch_is_hidden(monkeypatch, tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)

    dao = CollectiveDAO(db_path)
    dao.conn.execute(
        """
        UPDATE temporal_evidence
        SET source_profile = 'Odin'
        WHERE temporal_evidence_id = 'te-route-1'
        """
    )
    dao.conn.commit()
    dao.close()

    monkeypatch.setattr(
        "app.routes.temporal_history.DB_PATH",
        db_path,
    )

    client = TestClient(app)
    response = client.get("/api/temporal/history/entity/10")

    assert response.status_code == 200
    assert response.json()["history"]["observation_count"] == 0


def test_route_does_not_mutate_temporal_evidence(monkeypatch, tmp_path: Path) -> None:
    db_path = _prepare_db(tmp_path)

    before = sqlite3.connect(db_path).execute(
        """
        SELECT temporal_evidence_id, source_memory_id, source_profile
        FROM temporal_evidence
        ORDER BY temporal_evidence_id
        """
    ).fetchall()

    monkeypatch.setattr(
        "app.routes.temporal_history.DB_PATH",
        db_path,
    )

    client = TestClient(app)
    response = client.get("/api/temporal/history/entity/10")
    assert response.status_code == 200

    after = sqlite3.connect(db_path).execute(
        """
        SELECT temporal_evidence_id, source_memory_id, source_profile
        FROM temporal_evidence
        ORDER BY temporal_evidence_id
        """
    ).fetchall()

    assert before == after
