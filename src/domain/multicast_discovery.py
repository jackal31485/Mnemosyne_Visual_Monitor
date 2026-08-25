"""Phases 6.5C UDP multicast discovery.

Design constraints:
- No HTTP endpoints, credentials or authentication.
- Broadcasts are simple JSON payloads containing only ``client_id`` (required),
  ``hostname`` and ``installed_version`` (optional).
- The module exposes a :class:`DiscoveryRegistry` that keeps track of the most
  recent packet from each *client_id*.
- A discovery is considered stale after ``stale_after_seconds`` (default = 30s).
- The registry offers read‑only accessors that expose exactly those fields – no
  profile or memory identifiers are present here, satisfying the isolation rule.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

DEFAULT_MULTICAST_GROUP = "224.1.1.1"
DEFAULT_MULTICAST_PORT = 12345
STALENESS_THRESHOLD_SECONDS = 30


@dataclass
class DiscoveredClient:
    client_id: str
    hostname: Optional[str] = None
    installed_version: Optional[str] = None
    last_seen_ts: float = field(default_factory=time.time)

    @property
    def stale(self) -> bool:
        return time.time() - self.last_seen_ts > STALENESS_THRESHOLD_SECONDS

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "client_id": self.client_id,
            "hostname": self.hostname,
            "installed_version": self.installed_version,
            "last_seen_ts": self.last_seen_ts,
            "stale": self.stale,
        }


class DiscoveryRegistry:
    """Keep an in‑memory snapshot of all clients seen on the multicast network.

    The public API is purposely small – consumers read the current set via
    :meth:`get_all` and optionally add packets through :meth:`process_payload`.
    The class does *not* publish any network sockets; that behaviour is
    implemented in :func:`start_listener` so tests can call the registry directly
    without starting a real server.
    """

    def __init__(self, stale_threshold: float = STALENESS_THRESHOLD_SECONDS):
        self._clients: Dict[str, DiscoveredClient] = {}
        self._lock = threading.Lock()
        self.stale_threshold = stale_threshold

    # ---- public API -----------------------------------------------------
    def process_payload(self, payload_bytes: bytes) -> None:
        """Parse and store a single multicast packet.

        Raises ``ValueError`` if the payload is not valid JSON or does not contain
        a ``client_id`` field. Unknown additional fields are ignored, preserving
        isolation from forbidden data.
        """

        try:
            obj = json.loads(payload_bytes.decode("utf-8", errors="strict"))
        except Exception as exc:  # pragma: no cover – defensive
            raise ValueError(f"Invalid JSON packet: {exc}") from exc

        if not isinstance(obj, dict):  # pragma: no cover
            raise ValueError("payload must be a JSON object")

        client_id = obj.get("client_id")
        if not client_id or not isinstance(client_id, str):  # pragma: no cover
            raise ValueError("missing or invalid 'client_id' field")

        hostname = obj.get("hostname")
        installed_version = obj.get("installed_version")

        with self._lock:
            client = self._clients.get(client_id)
            if client is None:
                self._clients[client_id] = DiscoveredClient(
                    client_id=client_id,
                    hostname=hostname,
                    installed_version=installed_version,
                )
            else:
                # Update fields that may have changed and refresh timestamp
                if hostname is not None:
                    client.hostname = hostname
                if installed_version is not None:
                    client.installed_version = installed_version
                client.last_seen_ts = time.time()

    def get_all(self) -> List[DiscoveredClient]:
        """Return a snapshot list of all stored clients."""

        with self._lock:
            return list(self._clients.values())

    # ---- helpers for tests ----------------------------------------------
    def client_ids(self) -> Iterable[str]:  # pragma: no cover – trivial helper
        return (c.client_id for c in self.get_all())


def _socket_setup(group: str, port: int) -> socket.socket:
    """Return a UDP multicast listening socket bound to *group*:*port*.

    The returned socket is ready to call ``recvfrom``.  It uses IPv4 since the
    project does not support IPv6 yet and most developers use it locally.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # Allow multiple sockets to bind to same port (for tests on the same host).
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('', port))
    except OSError as exc:  # pragma: no cover – rare edge case
        raise RuntimeError(f"Unable to bind multicast socket: {exc}") from exc

    mreq = struct.pack('=4sL', socket.inet_aton(group), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return sock


def start_listener(
    registry: DiscoveryRegistry,
    group: str = DEFAULT_MULTICAST_GROUP,
    port: int = DEFAULT_MULTICAST_PORT,
    run_event: Optional[threading.Event] = None,
):
    """Spawn a background thread that feeds multicast packets into *registry*.

    The function returns immediately with the ``Thread`` instance.  The caller
    may keep the reference; when testing, they should signal ``run_event.clear()``
    to stop the loop.
    """

    if run_event is None:
        run_event = threading.Event()
        run_event.set()
    sock = _socket_setup(group, port)

    def _loop():  # pragma: no cover – exercised in integration test
        while run_event.is_set():
            try:
                data, _ = sock.recvfrom(4096)  # 4 KiB max payload
                registry.process_payload(data)
            except OSError:
                break

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread
