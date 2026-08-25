import unittest
import socket
import struct
import json
import time
import uuid
import tempfile
import sqlite3
from pathlib import Path
from app.discovery import DiscoveryListener

class TestMulticastListener(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.group = "224.10.0.1"
        cls.port = 34600
        tmp_dir = tempfile.mkdtemp()
        cls.db_path = Path(tmp_dir) / "discovery.db"
        cls.listener = DiscoveryListener(
            shutdown_event=None,
            db_path=cls.db_path,
            group=cls.group,
            port=cls.port,
        )
        cls.listener.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.listener.stop()
        if cls.listener.thread:
            cls.listener.thread.join(timeout=2)

    @staticmethod
    def _send(group, port, payload):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                            socket.IPPROTO_UDP)
        ttl = struct.pack("b", 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        sock.sendto(json.dumps(payload).encode('utf-8'), (group, port))
        sock.close()

    def test_valid_packet_persists(self):
        pkt = {"client_id": str(uuid.uuid4()), "hostname": "host1", "installed_version": "1.0"}
        self._send(self.group, self.port, pkt)
        time.sleep(0.2)
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "SELECT hostname, installed_version FROM discovery_records WHERE client_id=?", (pkt["client_id"],)
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "host1")
            self.assertEqual(row[1], "1.0")

    def test_duplicate_updates_last_seen(self):
        uid = str(uuid.uuid4())
        first = {"client_id": uid, "hostname": "h1", "installed_version": "v1"}
        second = {"client_id": uid, "hostname": "h2", "installed_version": None}
        self._send(self.group, self.port, first)
        time.sleep(0.2)
        ts_before = int(time.time())
        self._send(self.group, self.port, second)
        time.sleep(0.2)

        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "SELECT hostname, installed_version, first_seen, last_seen FROM discovery_records WHERE client_id=?",
                (uid,),
            )
            row = cur.fetchone()
            self.assertEqual(row[0], "h2")
            self.assertIsNone(row[1])
            self.assertLessEqual(ts_before, row[3])

    def test_invalid_packet_does_not_create_row(self):
        bad = {"client_id": "bad", "hostname": "h", "installed_version": None}
        self._send(self.group, self.port, bad)
        time.sleep(0.2)
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM discovery_records WHERE client_id=?",
                (bad["client_id"],),
            )
            count = cur.fetchone()[0]
            self.assertEqual(count, 0)

    def test_shutdown_terminates_thread(self):
        new_listener = DiscoveryListener(shutdown_event=None, db_path=self.db_path)
        new_listener.start()
        time.sleep(0.1)
        new_listener.stop()
        self.assertFalse(new_listener.thread.is_alive())

if __name__ == "__main__":
    unittest.main()
