"""Diagnostics utilities for the Mediation Plane.

This module provides an on‑dial diagnostics helper that is intended to be used
internally by the mediation API (and possibly by external monitoring tooling).
It does **not** expose any HTTP endpoints – all interaction happens through
Python objects.

The implementation deliberately remains lightweight and depends only on the
standard library.  It pulls a small amount of introspection data from the
``MediationAPI`` instance that is passed in at construction time.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Dict, Any

try:
    # Import the MediationAPI class for type checking.  The module lives in the same
    # package as this file and imports are safe, but we guard against circular
    # imports when diagnostics is imported from tests before ``api``.
    from .api import MediationAPI  # noqa: F401
except Exception:
    MediationAPI = None  # type: ignore[assignment]

__all__: list[str] = ["Diagnostics"]


class Diagnostics:
    """Gather runtime diagnostics for a :class:`MediationAPI` instance.

    Parameters
    ----------
    mediation_api:
        The mediation API object to introspect.  It **must** expose the public
        ``get_metrics`` method and have an accessible ``proposals`` mapping.
    """

    def __init__(self, mediation_api: MediationAPI) -> None:
        self.api = mediation_api
        self._start_time = time.time()

    # ---------------------------------------------------------------------
    # Basic diagnostic queries
    # ---------------------------------------------------------------------
    def uptime(self) -> float:
        """Return seconds since the ``Diagnostics`` instance was created."""
        return time.time() - self._start_time

    def queue_depth(self) -> int:
        """Return the number of proposals currently tracked.

        The mediation API keeps an in‑memory dictionary mapping proposal IDs to
        proposal states.  We simply count those entries.
        """
        return len(getattr(self.api, "proposals", {}))

    def memory_usage(self) -> int:
        """Approximate memory usage (in bytes) of the mediation API object.

        This is intentionally simple and uses :func:`sys.getsizeof` on a few
        representative objects: the API instance itself, its metrics collector,
        and the proposals dictionary.  It does *not* aim to be exact – the
        contract for diagnostics is low‑precision uptime/queue depth.
        """
        total = sys.getsizeof(self.api)
        # Include metrics collector – it tracks counters which may grow.
        if hasattr(self.api, "metrics"):
            total += sys.getsizeof(getattr(self.api, "metrics"))
        proposals = getattr(self.api, "proposals", {})
        total += sys.getsizeof(proposals)
        for v in proposals.values():
            total += sys.getsizeof(v)
        return total

    # ---------------------------------------------------------------------
    # Composite health report
    # ---------------------------------------------------------------------
    def health_report(self) -> Dict[str, Any]:
        """Return a JSON‑serialisable diagnostics snapshot.

        The returned dictionary contains:

        ``uptime``
            Seconds since diagnostics was instantiated.
        ``queue_depth``
            Number of tracked proposals (proposals mapping length).
        ``memory_usage_bytes``
            Rough memory footprint of the mediated API object.
        ``metrics_snapshot``
            Copied output from :py:meth:`MediationAPI.get_metrics` if
            available; otherwise an empty dict.
        """
        snapshot: Dict[str, Any] = {
            "uptime": self.uptime(),
            "queue_depth": self.queue_depth(),
            "memory_usage_bytes": self.memory_usage(),
            "metrics_snapshot": {},
        }
        try:
            snapshot["metrics_snapshot"] = self.api.get_metrics()  # type: ignore[attr-defined]
        except Exception:
            pass
        return snapshot
