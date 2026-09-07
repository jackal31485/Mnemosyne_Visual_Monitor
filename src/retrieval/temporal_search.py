from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.collective import CollectiveDAO
from src.domain.live_memory_gateway import LiveMemoryGateway


@dataclass(frozen=True)
class TemporalResult:
    """A governed temporal retrieval result."""

    entry_id: int
    source_profile: str
    origin_memory_id: str
    temporal_score: float
    memory_date: datetime
    date_source: str
    event_date_precision: str
    provenance: tuple


class TemporalSearcher:
    """Governed temporal retrieval over collective memories.

    Event-date retrieval uses explicit source-memory event dates.

    Recency retrieval uses memory recording timestamps when available.

    The collective database remains authoritative for lifecycle state.
    """

    def __init__(
        self,
        dao: CollectiveDAO,
        gateway: LiveMemoryGateway,
    ) -> None:
        self.dao = dao
        self.gateway = gateway
        self.dao.ensure_schema()

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise ValueError("limit must be a positive integer")

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if not isinstance(value, str):
            return None

        text = value.strip()

        if not text:
            return None

        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    def _authorized_entries(
        self,
        profile: Optional[str],
    ):
        sql = """
            SELECT
                id,
                source_profile,
                origin_memory_id
            FROM collective_entries
            WHERE is_promoted = 1
              AND is_revoked = 0
        """

        params: list[object] = []

        if profile is not None:
            sql += " AND source_profile = ?"
            params.append(str(profile))

        sql += " ORDER BY id ASC"

        return self.dao.conn.execute(sql, params).fetchall()

    def _metadata(
        self,
        source_profile: str,
        origin_memory_id: str,
    ) -> dict[str, object] | None:
        try:
            return self.gateway.get_memory_metadata(
                source_profile,
                origin_memory_id,
            )
        except (
            KeyError,
            FileNotFoundError,
            ValueError,
        ):
            return None

    def _provenance(self, entry_id: int) -> tuple:
        rows = self.dao.get_provenance(entry_id)

        return tuple(
            (
                row["source_profile"],
                row["origin_memory_id"],
                row["created_at"],
            )
            for row in rows
        )

    def search_by_event_date(
        self,
        start: datetime,
        end: datetime,
        *,
        limit: int = 10,
        profile: Optional[str] = None,
    ) -> list[TemporalResult]:
        """Return promoted, non-revoked memories within an event-date window.

        Only explicit day-precision event dates participate. Recording
        timestamps are never substituted for an unknown event date.
        """

        self._validate_limit(limit)

        if not isinstance(start, datetime):
            raise TypeError("start must be a datetime")

        if not isinstance(end, datetime):
            raise TypeError("end must be a datetime")

        if start > end:
            raise ValueError("start must not be after end")

        candidates: list[TemporalResult] = []

        for row in self._authorized_entries(profile):
            entry_id = int(row["id"])
            source_profile = str(row["source_profile"])
            origin_memory_id = str(row["origin_memory_id"])

            metadata = self._metadata(
                source_profile,
                origin_memory_id,
            )

            if metadata is None:
                continue

            precision = str(
                metadata.get("event_date_precision")
                or "unknown"
            )

            if precision != "day":
                continue

            memory_date = self._parse_datetime(
                metadata.get("event_date")
            )

            if memory_date is None:
                continue

            if memory_date < start or memory_date > end:
                continue

            candidates.append(
                TemporalResult(
                    entry_id=entry_id,
                    source_profile=source_profile,
                    origin_memory_id=origin_memory_id,
                    temporal_score=1.0,
                    memory_date=memory_date,
                    date_source="event_date",
                    event_date_precision=precision,
                    provenance=self._provenance(entry_id),
                )
            )

        candidates.sort(
            key=lambda result: (
                result.memory_date,
                result.entry_id,
            )
        )

        return candidates[:limit]

    def search_by_recency(
        self,
        *,
        reference_time: datetime | None = None,
        limit: int = 10,
        profile: Optional[str] = None,
    ) -> list[TemporalResult]:
        """Return memories ordered by recording recency.

        Timestamp is preferred over created_at. Unknown event-date
        precision does not prevent a memory from participating because
        this operation concerns recording time rather than event time.
        """

        self._validate_limit(limit)

        if reference_time is None:
            reference_time = datetime.now()

        if not isinstance(reference_time, datetime):
            raise TypeError("reference_time must be a datetime")

        candidates: list[TemporalResult] = []

        for row in self._authorized_entries(profile):
            entry_id = int(row["id"])
            source_profile = str(row["source_profile"])
            origin_memory_id = str(row["origin_memory_id"])

            metadata = self._metadata(
                source_profile,
                origin_memory_id,
            )

            if metadata is None:
                continue

            date_source = "timestamp"

            memory_date = self._parse_datetime(
                metadata.get("timestamp")
            )

            if memory_date is None:
                date_source = "created_at"

                memory_date = self._parse_datetime(
                    metadata.get("created_at")
                )

            if memory_date is None:
                continue

            age_seconds = (
                reference_time - memory_date
            ).total_seconds()

            # Future timestamps receive the maximum recency score.
            age_days = max(age_seconds / 86400.0, 0.0)

            temporal_score = 1.0 / (1.0 + age_days)

            candidates.append(
                TemporalResult(
                    entry_id=entry_id,
                    source_profile=source_profile,
                    origin_memory_id=origin_memory_id,
                    temporal_score=temporal_score,
                    memory_date=memory_date,
                    date_source=date_source,
                    event_date_precision=str(
                        metadata.get("event_date_precision")
                        or "unknown"
                    ),
                    provenance=self._provenance(entry_id),
                )
            )

        candidates.sort(
            key=lambda result: (
                -result.temporal_score,
                -result.memory_date.timestamp(),
                -result.entry_id,
            )
        )

        return candidates[:limit]
