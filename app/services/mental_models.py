"""Read-only projection boundary for Phase 13 mental models.

This module deliberately does not persist mental models.

Phase 13G exposes the already-governed domain objects through a narrow,
read-only application boundary. A future repository can replace the
in-memory provider without changing the HTTP contract.

Governance boundary:
- only VALIDATED and ACTIVE models are current/retrievable;
- no raw source-memory content is returned;
- provenance remains identifier-based;
- HTTP access cannot mutate or synthesize a mental model.
"""

from __future__ import annotations

from collections.abc import Iterable
from threading import RLock

from src.domain.mental_model import MentalModel, MentalModelStatus


class MentalModelProjection:
    """Read-only application projection over governed mental models."""

    _CURRENT_STATUSES = frozenset(
        {
            MentalModelStatus.VALIDATED,
            MentalModelStatus.ACTIVE,
        }
    )

    def __init__(self, models: Iterable[MentalModel] = ()) -> None:
        self._lock = RLock()
        self._models: dict[str, MentalModel] = {}

        for model in models:
            self._models[model.model_id] = model

    def replace(self, models: Iterable[MentalModel]) -> None:
        """Replace the projection contents.

        This is an application/integration operation, not a domain mutation.
        Domain MentalModel instances remain immutable.
        """
        with self._lock:
            self._models = {model.model_id: model for model in models}

    def add(self, model: MentalModel) -> None:
        """Add or replace one immutable model in the projection."""
        with self._lock:
            self._models[model.model_id] = model

    def clear(self) -> None:
        """Clear the process-local integration projection."""
        with self._lock:
            self._models.clear()

    def list_current(
        self,
        *,
        source_profile: str | None = None,
        model_type: str | None = None,
    ) -> list[MentalModel]:
        """Return only currently retrievable mental models."""
        with self._lock:
            models = [
                model
                for model in self._models.values()
                if model.status in self._CURRENT_STATUSES
            ]

        if source_profile:
            models = [
                model
                for model in models
                if source_profile in model.provenance.source_profiles
            ]

        if model_type:
            models = [
                model
                for model in models
                if model.model_type.value == model_type
            ]

        return sorted(
            models,
            key=lambda model: (
                model.title.casefold(),
                model.model_id,
                model.version,
            ),
        )

    def get_current(self, model_id: str) -> MentalModel | None:
        """Return one current/retrievable model, if present."""
        with self._lock:
            model = self._models.get(model_id)

        if model is None or model.status not in self._CURRENT_STATUSES:
            return None

        return model


mental_model_projection = MentalModelProjection()


def get_mental_model_projection() -> MentalModelProjection:
    """Dependency seam for the HTTP layer and future persistence."""
    return mental_model_projection
