from __future__ import annotations

import json
import os
import socket
import threading
import time
import uuid

from app.discovery import (
    LAN_DISCOVERY_GROUP,
    LAN_DISCOVERY_PORT,
)


BEACON_INTERVAL = 5.0


class DiscoveryBeacon:
    """
    Periodically announces this Mnemosyne instance on the LAN.

    Discovery contains identity and connectivity information only.
    No memory content or memory identifiers are broadcast.
    """

    def __init__(
        self,
        api_port: int = 8000,
    ):
        self.api_port = api_port
        self.client_id = self._load_client_id()
        self.hostname = socket.gethostname()
        self.version = os.getenv(
            "MNEMOSYNE_VERSION",
            "0.20.0",
        )

        self._stop = threading.Event()
        self._thread = None

    def _load_client_id(self) -> str:
        path = (
            os.path.expanduser(
                "~/.mnemosyne_client_id"
            )
        )

        try:
            if os.path.isfile(path):
                value = open(
                    path,
                    "r",
                    encoding="utf-8",
                ).read().strip()

                if value:
                    return value
        except OSError:
            pass

        value = str(uuid.uuid4())

        try:
            with open(
                path,
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write(value)
        except OSError:
            pass

        return value

    def payload(self) -> dict:
        return {
            "client_id": self.client_id,
            "hostname": self.hostname,
            "installed_version": self.version,
            "api_port": self.api_port,
        }

    def start(self) -> None:
        if (
            self._thread
            and self._thread.is_alive()
        ):
            return

        self._stop.clear()

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="mnemosyne-discovery-beacon",
        )

        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

        if self._thread:
            self._thread.join(
                timeout=2
            )

    def _run(self) -> None:
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
        )

        try:
            sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_MULTICAST_TTL,
                1,
            )

            payload = json.dumps(
                self.payload()
            ).encode("utf-8")

            while not self._stop.is_set():
                try:
                    sock.sendto(
                        payload,
                        (
                            LAN_DISCOVERY_GROUP,
                            LAN_DISCOVERY_PORT,
                        ),
                    )
                except OSError:
                    pass

                self._stop.wait(
                    BEACON_INTERVAL
                )

        finally:
            sock.close()
