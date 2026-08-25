import json
import os
import socket
import struct
import sys
import time
import uuid
import threading
import pathlib
import sqlite3
from typing import Final, Optional

# Configuration – overridable via environment
DEFAULT_GROUP: Final[str] = "224.10.0.1"
DEFAULT_PORT: Final[int] = 34567
LAN_DISCOVERY_GROUP: Final[str] = os.getenv("LAN_DISCOVERY_GROUP", DEFAULT_GROUP)
LAN_DISCOVERY_PORT: Final[int] = int(os.getenv("LAN_DISCOVERY_PORT", str(DEFAULT_PORT)))

# Database path – may be overridden at runtime via DiscoveryListener(db_path=…)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_DIR = PROJECT_ROOT / "app" / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH: Final[pathlib.Path] = DB_DIR / "discovery.db"

# Table schema – exact as per spec
TABLE_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS discovery_records ("
    "  client_id TEXT PRIMARY KEY,"
    "  hostname TEXT,"
    "  installed_version TEXT,"
    "  first_seen INTEGER,"
    "  last_seen INTEGER,"
    "  state TEXT NOT NULL DEFAULT 'DISCOVERED'"
    ")"
)

# ---------------------------------------------------------------------------

def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(TABLE_SCHEMA)
    conn.commit()

REQUIRED_KEYS = {"client_id", "hostname", "installed_version"}


def _is_valid_uuid4(value: str) -> bool:
    try:
        parsed = uuid.UUID(value, version=4)
    except Exception:
        return False
    # enforce canonical lowercase form and no commas
    return "," not in value and str(parsed) == value.lower()

# ---------------------------------------------------------------------------

def validate_payload(payload: dict) -> None:
    """Validate a multicast payload dictionary.

    Raises ValueError on any validation error.
    """
    if set(payload.keys()) != REQUIRED_KEYS:
        raise ValueError("payload must contain exactly client_id, hostname, installed_version")

    client_id = payload["client_id"]
    hostname = payload["hostname"]
    installed_version = payload["installed_version"]

    if not isinstance(client_id, str) or not _is_valid_uuid4(client_id):
        raise ValueError("client_id must be a UUID‑v4 string")

    for field in (hostname, installed_version):
        if field is not None and not isinstance(field, str):
            raise ValueError("hostname and installed_version must be strings or null")

# ---------------------------------------------------------------------------
class _DB:
    """Context manager that opens SQLite database.

    The path is passed explicitly to allow tests to supply temporary files.
    """
    def __init__(self, db_path: pathlib.Path):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        _ensure_schema(conn)
        self._conn = conn
        return conn

    def __exit__(self, exc_type, exc_val, tb) -> None:  # noqa: ANN001
        if self._conn:
            try:
                if exc_type is not None:
                    self._conn.rollback()
                else:
                    self._conn.commit()
            finally:
                self._conn.close()
                self._conn = None

# ---------------------------------------------------------------------------
class DiscoveryListener:
    """UDP multicast listener that persists incoming packets.

    The listener runs in a daemon thread and shuts down cleanly via ``stop()``.
    """

    def __init__(
        self,
        shutdown_event: Optional[threading.Event] = None,
        db_path: Optional[pathlib.Path] = None,
        group: Optional[str] = None,
        port: Optional[int] = None,
        interface: Optional[str] = None,
    ):
        self.shutdown_event = shutdown_event or threading.Event()
        self.thread: Optional[threading.Thread] = None
        # Default path if none supplied – tests can override.
        self.db_path = db_path or DB_PATH

        # Ensure the database and schema exist when the listener is created.
        with _DB(self.db_path):
            pass

        self.LAN_DISCOVERY_GROUP = group or LAN_DISCOVERY_GROUP
        self.LAN_DISCOVERY_PORT = port or LAN_DISCOVERY_PORT
        self.LAN_DISCOVERY_INTERFACE = interface

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.shutdown_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    # -------------------------------------------------------------------
    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        # Allow reuse for repeated tests
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", self.LAN_DISCOVERY_PORT))
        except OSError as exc:  # pragma: no cover
            sys.stderr.write(f"Failed to bind listener on port {self.LAN_DISCOVERY_PORT}: {exc}\n")
            return

        interface = self.LAN_DISCOVERY_INTERFACE
        if interface:
            mreq = socket.inet_aton(self.LAN_DISCOVERY_GROUP) + socket.inet_aton(interface)
        else:
            mreq = struct.pack(
                "=4sL",
                socket.inet_aton(self.LAN_DISCOVERY_GROUP),
                socket.INADDR_ANY,
            )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.settimeout(0.5)  # short timeout to poll shutdown_event

        while not self.shutdown_event.is_set():
            try:
                data, _ = sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:  # pragma: no cover
                if self.shutdown_event.is_set():
                    break
                continue

            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue

            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue

            try:
                validate_payload(payload)
            except ValueError:
                continue

            client_id: str = payload["client_id"]
            hostname = payload["hostname"]
            installed_version = payload["installed_version"]
            ts = int(time.time())

            with _DB(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT first_seen FROM discovery_records WHERE client_id=?",
                    (client_id,),
                )
                row = cur.fetchone()
                if row is None:
                    cur.execute(
                        "INSERT INTO discovery_records (client_id, hostname, installed_version, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",  # noqa: E501
                        (client_id, hostname, installed_version, ts, ts),
                    )
                else:
                    cur.execute(
                        "UPDATE discovery_records SET hostname=?, installed_version=?, last_seen=? WHERE client_id=?",
                        (hostname, installed_version, ts, client_id),
                    )

        sock.close()

# ---------------------------------------------------------------------------
STALE_THRESHOLD_SECONDS: Final[int] = 30


def is_stale(client_id: str) -> bool:
    """Return True if a record's last_seen is older than STALE_THRESHOLD_SECONDS or does not exist."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT last_seen FROM discovery_records WHERE client_id=?",
            (client_id,),
        )
        row = cur.fetchone()
        if not row:
            return True
        last_seen_ts: int = row[0]
    now = int(time.time())
    return now - last_seen_ts > STALE_THRESHOLD_SECONDS

__all__ = ["DiscoveryListener", "validate_payload", "is_stale", "DB_PATH"]
