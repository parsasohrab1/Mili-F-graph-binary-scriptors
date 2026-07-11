"""UDP transport and multi-drone network simulator."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from mili_vio.sharing.protocol import LandmarkShareMessage, decode_message, encode_message


@dataclass
class NetworkConfig:
    base_port: int = 7700
    max_drones: int = 12
    latency_ms: float = 10.0
    jitter_ms: float = 5.0
    packet_loss_rate: float = 0.0


@dataclass
class DeliveryRecord:
    send_time: float
    receive_time: float
    latency_ms: float
    bytes_sent: int
    drone_id: int


class SimulatedNetwork:
    """
    Multi-drone UDP network simulator (up to 12 drones).

    Models latency, jitter, and packet loss for FR-3 testing.
    """

    def __init__(self, config: Optional[NetworkConfig] = None, rng=None) -> None:
        import numpy as np
        self.config = config or NetworkConfig()
        self._rng = rng or np.random.default_rng()
        self._mailboxes: dict[int, list[bytes]] = {
            i: [] for i in range(self.config.max_drones)
        }
        self._delivery_log: list[DeliveryRecord] = []
        self._pending: list[tuple[float, int, bytes]] = []

    def send(self, from_drone: int, to_drone: int, data: bytes) -> bool:
        if to_drone >= self.config.max_drones:
            return False
        if self._rng.random() < self.config.packet_loss_rate:
            return False

        latency = self.config.latency_ms + self._rng.uniform(0, self.config.jitter_ms)
        deliver_at = time.perf_counter() + latency / 1000.0
        self._pending.append((deliver_at, to_drone, data))
        return True

    def broadcast(self, from_drone: int, data: bytes) -> int:
        sent = 0
        for drone_id in range(self.config.max_drones):
            if drone_id != from_drone:
                if self.send(from_drone, drone_id, data):
                    sent += 1
        return sent

    def poll(self, drone_id: int) -> list[LandmarkShareMessage]:
        now = time.perf_counter()
        still_pending = []
        for deliver_at, target, data in self._pending:
            if target == drone_id and now >= deliver_at:
                self._mailboxes[drone_id].append(data)
                latency_ms = (now - (deliver_at - self.config.latency_ms / 1000)) * 1000
                self._delivery_log.append(
                    DeliveryRecord(deliver_at, now, latency_ms, len(data), drone_id)
                )
            elif now < deliver_at:
                still_pending.append((deliver_at, target, data))
        self._pending = still_pending

        messages: list[LandmarkShareMessage] = []
        while self._mailboxes[drone_id]:
            raw = self._mailboxes[drone_id].pop(0)
            try:
                messages.append(decode_message(raw))
            except ValueError:
                continue
        return messages

    @property
    def mean_latency_ms(self) -> float:
        if not self._delivery_log:
            return 0.0
        return sum(r.latency_ms for r in self._delivery_log) / len(self._delivery_log)

    @property
    def max_latency_ms(self) -> float:
        if not self._delivery_log:
            return 0.0
        return max(r.latency_ms for r in self._delivery_log)


class UDPTransport:
    """Real UDP transport for integration tests (optional)."""

    def __init__(self, drone_id: int, config: NetworkConfig) -> None:
        self.drone_id = drone_id
        self.config = config
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = config.base_port + drone_id
        self._sock.bind(("127.0.0.1", port))
        self._sock.setblocking(False)

    def send(self, to_drone: int, msg: LandmarkShareMessage) -> None:
        data = encode_message(msg)
        port = self.config.base_port + to_drone
        self._sock.sendto(data, ("127.0.0.1", port))

    def broadcast(self, msg: LandmarkShareMessage) -> None:
        for i in range(self.config.max_drones):
            if i != self.drone_id:
                self.send(i, msg)

    def receive(self) -> list[LandmarkShareMessage]:
        messages: list[LandmarkShareMessage] = []
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
                messages.append(decode_message(data))
            except BlockingIOError:
                break
        return messages

    def close(self) -> None:
        self._sock.close()
