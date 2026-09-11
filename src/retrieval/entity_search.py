"""Governed entity-aware retrieval for Mnemosyne Phase 10H."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.collective import CollectiveDAO
from src.domain.entities import EntityDAO
from src.domain.entity_mentions import EntityMentionDAO
from src.domain.entity_resolutions import EntityResolutionDAO
from src.services.entity_resolution import normalize_entity_name


@dataclass(frozen=True)
class EntityResult:
    """One collective memory surfaced through an explicitly resolved entity."""

    entry_id: int
    source_profile: str
    origin_memory_id: str
    entity_score: float
    provenance: Any


class EntitySearcher:
    """Retrieve governed collective memories through canonical entities.

    Entity retrieval is deliberately conservative:

    * only active canonical entities are eligible;
    * only explicit ``same_entity`` resolutions are followed;
    * only promoted, non-revoked collective entries are returned;
    * profile filtering preserves qualified profile identity;
    * no relationship traversal is performed;
    * no source-memory content is accessed or returned.
    """

    def __init__(
        self,
        collective_dao: CollectiveDAO,
        entity_dao: EntityDAO,
        mention_dao: EntityMentionDAO,
        resolution_dao: EntityResolutionDAO,
    ) -> None:
        self.collective_dao = collective_dao
        self.entity_dao = entity_dao
        self.mention_dao = mention_dao
        self.resolution_dao = resolution_dao

    @staticmethod
    def _validate_limit(name: str, value: int) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ValueError(f"{name} must be a positive integer")

    @staticmethod
    def _normalize_profile(profile: str | None) -> str | None:
        if profile is None:
            return None

        if not isinstance(profile, str) or not profile.strip():
            raise ValueError("profile must be a non-empty string")

        return profile.strip()

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        profile: str | None = None,
    ) -> list[EntityResult]:
        """Return deterministic entity-channel candidates for a query."""

        if not isinstance(query, str):
            raise TypeError("query must be a string")

        if not query.strip():
            return []

        self._validate_limit("limit", limit)
        profile = self._normalize_profile(profile)

        normalized_query = normalize_entity_name(query)

        if not normalized_query:
            return []

        matching_entities = [
            entity
            for entity in self.entity_dao.list(status="active")
            if normalize_entity_name(entity["canonical_name"])
            == normalized_query
        ]

        if not matching_entities:
            return []

        entity_ids = {
            entity["entity_id"]
            for entity in matching_entities
        }

        resolved_mention_ids = {
            resolution["mention_id"]
            for resolution in self.resolution_dao.list(
                decision="same_entity",
            )
            if resolution["proposed_entity_id"] in entity_ids
        }

        if not resolved_mention_ids:
            return []

        candidates: dict[tuple[int, str, str], EntityResult] = {}

        for mention in self.mention_dao.list():
            mention_id = mention["mention_id"]

            if mention_id not in resolved_mention_ids:
                continue

            mention_profile = mention["source_profile"]

            if profile is not None and mention_profile != profile:
                continue

            entry_id = int(mention["collective_entry_id"])

            lifecycle = self.collective_dao.get_lifecycle_state(entry_id)
            if lifecycle is None:
                continue

            _validated_at, is_revoked, _revocation_reason, is_promoted = (
                lifecycle
            )

            if is_revoked or not is_promoted:
                continue

            provenance_rows = self.collective_dao.get_provenance(entry_id)

            for provenance in provenance_rows:
                source_profile = provenance["source_profile"]
                origin_memory_id = provenance["origin_memory_id"]

                if source_profile != mention_profile:
                    continue

                if profile is not None and source_profile != profile:
                    continue

                provenance_key = (
                    entry_id,
                    source_profile,
                    origin_memory_id,
                )

                candidates[provenance_key] = EntityResult(
                    entry_id=entry_id,
                    source_profile=source_profile,
                    origin_memory_id=origin_memory_id,
                    entity_score=1.0,
                    provenance=provenance,
                )

        results = sorted(
            candidates.values(),
            key=lambda result: (
                -result.entity_score,
                result.entry_id,
                result.source_profile,
                result.origin_memory_id,
            ),
        )

        return results[:limit]
