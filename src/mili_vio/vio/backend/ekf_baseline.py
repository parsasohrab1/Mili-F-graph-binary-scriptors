"""EKF baseline for benchmark comparison."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation

from mili_vio.vio.backend.scipy_backend import PoseNode
from mili_vio.vio.imu_preintegration import IMUPreintegrator


@dataclass
class EKFState:
    position: NDArray[np.float64]
    velocity: NDArray[np.float64]
    rotation: NDArray[np.float64]
    P: NDArray[np.float64]  # 9x9 covariance


@dataclass
class EKFResult:
    poses: list[PoseNode]
    optimization_time_ms: float
    backend: str = "ekf"


class VisualInertialEKF:
    """Simplified visual-inertial EKF baseline."""

    def __init__(self) -> None:
        self.preintegrator = IMUPreintegrator()
        self.state = EKFState(
            position=np.zeros(3),
            velocity=np.zeros(3),
            rotation=np.eye(3),
            P=np.eye(9) * 0.1,
        )
        self.poses: list[PoseNode] = []

    def initialize(self, timestamp_ns: int) -> None:
        self.poses = [PoseNode(0, timestamp_ns, self.state.position.copy(), self.state.rotation.copy())]

    def predict_imu(self, gyro: NDArray[np.float64], accel: NDArray[np.float64], dt: float) -> None:
        if dt <= 0:
            return
        omega = gyro
        dR = Rotation.from_rotvec(omega * dt).as_matrix()
        self.state.rotation = self.state.rotation @ dR

        world_a = self.state.rotation @ accel
        world_a[2] -= 9.81
        self.state.position += self.state.velocity * dt + 0.5 * world_a * dt * dt
        self.state.velocity += world_a * dt

        Q = np.eye(9) * 1e-3
        self.state.P = self.state.P + Q

    def update_visual(self, measured_translation: NDArray[np.float64], measured_rotation: NDArray[np.float64]) -> None:
        z = np.concatenate([measured_translation, Rotation.from_matrix(measured_rotation).as_rotvec()])
        H = np.zeros((6, 9))
        H[:3, :3] = np.eye(3)
        H[3:, 6:9] = np.eye(3)

        x = np.concatenate([
            self.state.position,
            self.state.velocity,
            Rotation.from_rotvec(Rotation.from_matrix(self.state.rotation).as_rotvec()).as_rotvec(),
        ])
        R = np.eye(6) * 0.05
        y = z - H @ x
        S = H @ self.state.P @ H.T + R
        K = self.state.P @ H.T @ np.linalg.inv(S)
        x_upd = x + K @ y
        self.state.P = (np.eye(9) - K @ H) @ self.state.P

        self.state.position = x_upd[:3]
        self.state.velocity = x_upd[3:6]
        self.state.rotation = Rotation.from_rotvec(x_upd[6:9]).as_matrix()

    def record_pose(self, index: int, timestamp_ns: int) -> None:
        self.poses.append(
            PoseNode(index, timestamp_ns, self.state.position.copy(), self.state.rotation.copy())
        )

    def run_sequence(
        self,
        timestamps: list[int],
        imu_batches: list[list],
        visual_measurements: list[tuple[NDArray[np.float64], NDArray[np.float64]]],
    ) -> EKFResult:
        start = time.perf_counter()
        self.initialize(timestamps[0])

        for i in range(1, len(timestamps)):
            batch = imu_batches[i - 1] if i - 1 < len(imu_batches) else []
            for j, sample in enumerate(batch):
                prev_ts = batch[j - 1].timestamp_ns if j > 0 else timestamps[i - 1]
                dt = (sample.timestamp_ns - prev_ts) * 1e-9
                self.predict_imu(sample.gyro, sample.accel, dt)

            if i - 1 < len(visual_measurements):
                trans, rot = visual_measurements[i - 1]
                self.update_visual(trans, rot)

            self.record_pose(i, timestamps[i])

        elapsed_ms = (time.perf_counter() - start) * 1000
        return EKFResult(poses=self.poses, optimization_time_ms=elapsed_ms)
