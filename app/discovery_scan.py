from __future__ import annotations

import threading
from typing import Optional

from app.discovery import DiscoveryListener, DB_PATH


class DiscoveryScanController:
    """Owns the lifecycle of an active LAN discovery scan."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._listener: Optional[DiscoveryListener] = None

    def _running_locked(self) -> bool:
        """Return whether the active listener thread is running.

        The caller must already hold ``self._lock``.
        """
        return (
            self._listener is not None
            and self._listener.thread is not None
            and self._listener.thread.is_alive()
        )

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running_locked()

    def start(self) -> bool:
        with self._lock:
            if self._running_locked():
                return False

            listener = DiscoveryListener(db_path=DB_PATH)
            listener.start()
            self._listener = listener
            return True

    def stop(self) -> bool:
        with self._lock:
            listener = self._listener
            if listener is None:
                return False

            self._listener = None

        listener.stop()
        return True

    def status(self) -> dict:
        return {
            "running": self.running,
        }


scan_controller = DiscoveryScanController()
