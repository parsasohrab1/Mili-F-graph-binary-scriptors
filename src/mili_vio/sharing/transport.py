"""Network transport layer for FR-3 cooperative sharing."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from mili_vio.sharing.network import DeliveryRecord, NetworkConfig, SimulatedNetwork
from mili_vio.sharing.protocol import LandmarkShareMessage, decode_message


@runtime_checkable
class NetworkTransport(Protocol):
    """Unified transport API for simulated or real UDP/UWB."""

    def broadcast(self, from_drone: int, data: bytes) -> int: ...

    def poll(self, drone_id: int) -> list[LandmarkShareMessage]: ...

    @property
    def is_hardware(self) -> bool: ...

    @property
    def mean_latency_ms(self) -> float: ...

    @property
    def max_latency_ms(self) -> float: ...


class SimulatedTransportAdapter:
    """Adapter wrapping SimulatedNetwork for NetworkTransport protocol."""

    def __init__(self, network: SimulatedNetwork) -> None:
        self._net = network

    @property
    def is_hardware(self) -> bool:
        return False

    def broadcast(self, from_drone: int, data: bytes) -> int:
        return self._net.broadcast(from_drone, data)

    def poll(self, drone_id: int) -> list[LandmarkShareMessage]:
        return self._net.poll(drone_id)

    @property
    def mean_latency_ms(self) -> float:
        return self._net.mean_latency_ms

    @property
    def max_latency_ms(self) -> float:
        return self._net.max_latency_ms


@dataclass
class UDPTransportConfig:
    host: str = "127.0.0.1"
    base_port: int = 7700
    max_drones: int = 12
    multicast_group: str = "239.255.77.77"
    use_multicast: bool = False


class RealUDPNetwork:
    """
    Real UDP transport for up to 12 drones (Product integration / HIL).

    Uses kernel UDP stack — measures actual send/receive latency.
    Supports unicast (per-drone port) or multicast fan-out.
    """

    def __init__(
        self,
        config: Optional[NetworkConfig] = None,
        udp_config: Optional[UDPTransportConfig] = None,
    ) -> None:
        net = config or NetworkConfig()
        self._cfg = udp_config or UDPTransportConfig(
            base_port=net.base_port,
            max_drones=net.max_drones,
        )
        self._sockets: dict[int, socket.socket] = {}
        self._delivery_log: list[DeliveryRecord] = []
        self._send_times: list[tuple[float, int, int]] = []
        self._open_sockets()

    @property
    def is_hardware(self) -> bool:
        return True

    def _open_sockets(self) -> None:
        for drone_id in range(self._cfg.max_drones):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            port = self._cfg.base_port + drone_id
            sock.bind((self._cfg.host, port))
            sock.setblocking(False)
            if self._cfg.use_multicast:
                mreq = socket.inet_aton(self._cfg.multicast_group) + socket.inet_aton(
                    self._cfg.host
                )
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self._sockets[drone_id] = sock

    def broadcast(self, from_drone: int, data: bytes) -> int:
        if from_drone not in self._sockets:
            return 0
        sock = self._sockets[from_drone]
        sent = 0
        t0 = time.perf_counter()
        if self._cfg.use_multicast:
            target = (self._cfg.multicast_group, self._cfg.base_port)
            try:
                sock.sendto(data, target)
                sent = self._cfg.max_drones - 1
            except OSError:
                return 0
        else:
            for drone_id in range(self._cfg.max_drones):
                if drone_id == from_drone:
                    continue
                port = self._cfg.base_port + drone_id
                try:
                    sock.sendto(data, (self._cfg.host, port))
                    sent += 1
                except OSError:
                    continue
        self._send_times.append((t0, from_drone, len(data)))
        return sent

    def poll(self, drone_id: int) -> list[LandmarkShareMessage]:
        if drone_id not in self._sockets:
            return []
        sock = self._sockets[drone_id]
        messages: list[LandmarkShareMessage] = []
        recv_start = time.perf_counter()

        while True:
            try:
                data, _addr = sock.recvfrom(4096)
            except BlockingIOError:
                break
            except OSError:
                break
            try:
                messages.append(decode_message(data))
                latency_ms = (time.perf_counter() - recv_start) * 1000
                self._delivery_log.append(
                    DeliveryRecord(recv_start, time.perf_counter(), latency_ms, len(data), drone_id)
                )
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

    def close(self) -> None:
        for sock in self._sockets.values():
            sock.close()
        self._sockets.clear()


def create_network_transport(
    transport: str = "simulated",
    config: Optional[NetworkConfig] = None,
    rng=None,
    host: str = "127.0.0.1",
    use_multicast: bool = False,
) -> NetworkTransport:
    """Factory for FR-3 network backends."""
    net_cfg = config or NetworkConfig()
    mode = transport.lower()

    if mode in ("simulated", "sim"):
        sim = SimulatedNetwork(net_cfg, rng=rng)
        return SimulatedTransportAdapter(sim)

    if mode in ("udp", "real", "unicast"):
        return RealUDPNetwork(net_cfg, UDPTransportConfig(host=host, use_multicast=False))

    if mode in ("multicast", "udp_multicast"):
        return RealUDPNetwork(
            net_cfg,
            UDPTransportConfig(host=host, use_multicast=True),
        )

    if mode in ("uwb", "wifi"):
        # Python side uses real UDP; embedded uses comm_uwb/wifi drivers
        return RealUDPNetwork(net_cfg, UDPTransportConfig(host=host, use_multicast=False))

    raise ValueError(f"Unknown sharing transport: {transport}")
