"""IMU preintegration for factor-graph backends."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation

from mili_vio.vio.datasets.base import IMUSample


@dataclass
class IMUPreintegrated:
    """Preintegrated IMU measurements between two keyframes."""

    delta_p: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))
    delta_v: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))
    delta_R: NDArray[np.float64] = field(default_factory=lambda: np.eye(3))
    dt: float = 0.0
    gyro_bias: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))
    accel_bias: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))


class IMUPreintegrator:
    """
    Simplified IMU preintegration (Forster et al. style).

    Suitable for desktop prototyping; production uses GTSAM PreintegratedImuMeasurements.
    """

    def __init__(
        self,
        gravity: float = 9.81,
        gyro_noise: float = 1.6e-4,
        accel_noise: float = 2.0e-3,
    ) -> None:
        self.gravity = gravity
        self.gyro_noise = gyro_noise
        self.accel_noise = accel_noise

    def integrate(self, samples: list[IMUSample]) -> IMUPreintegrated:
        if len(samples) < 2:
            return IMUPreintegrated()

        result = IMUPreintegrated()
        prev_ts = samples[0].timestamp_ns

        for sample in samples[1:]:
            dt = (sample.timestamp_ns - prev_ts) * 1e-9
            if dt <= 0:
                continue

            omega = sample.gyro - result.gyro_bias
            accel = sample.accel - result.accel_bias

            dR = Rotation.from_rotvec(omega * dt).as_matrix()
            result.delta_R = result.delta_R @ dR

            world_accel = result.delta_R @ accel
            world_accel[2] -= self.gravity

            result.delta_p += result.delta_v * dt + 0.5 * world_accel * dt * dt
            result.delta_v += world_accel * dt
            result.dt += dt
            prev_ts = sample.timestamp_ns

        return result

    def predict_pose(
        self,
        position: NDArray[np.float64],
        velocity: NDArray[np.float64],
        rotation: NDArray[np.float64],
        preint: IMUPreintegrated,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        R = rotation @ preint.delta_R
        p = position + velocity * preint.dt + rotation @ preint.delta_p
        v = velocity + rotation @ preint.delta_v
        return p, v, R
