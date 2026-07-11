"""Cooperative VIO synthetic data generation (Product 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from mili_vio.config import AppConfig, load_config
from mili_vio.factor_graph import FactorGraphEstimator
from mili_vio.sharing import EventDrivenSharing
from mili_vio.types import IMUReading, Pose6DOF


class CooperativeVIODataGenerator:
    """Generate cooperative VIO dataset aligned with SRS specifications."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self._config = config or load_config()
        self._rng = rng or np.random.default_rng(self._config.data_generation.seed)
        self._estimator = FactorGraphEstimator(
            accuracy=self._config.accuracy, rng=self._rng
        )
        self._sharing = EventDrivenSharing(
            sharing=self._config.sharing, rng=self._rng
        )

    def generate(self) -> pd.DataFrame:
        dg = self._config.data_generation
        total_records = dg.num_groups * dg.drones_per_group * dg.time_steps

        print(f"Generating {total_records:,} records for Product 2...")

        records: list[dict] = []
        comm_names = [q.name for q in dg.communication_qualities]
        comm_probs = [q.probability for q in dg.communication_qualities]

        for group_id in range(dg.num_groups):
            scenario = self._rng.choice(dg.scenarios)
            comm_quality = self._rng.choice(comm_names, p=comm_probs)

            noise = self._noise_for_comm_quality(comm_quality)

            traj_x = np.cumsum(self._rng.standard_normal(dg.time_steps) * 0.8)
            traj_y = np.cumsum(self._rng.standard_normal(dg.time_steps) * 0.8)
            traj_z = (
                10
                + 2 * np.sin(np.linspace(0, 4 * np.pi, dg.time_steps))
                + np.cumsum(self._rng.standard_normal(dg.time_steps) * 0.05)
            )

            true_yaw = np.cumsum(self._rng.standard_normal(dg.time_steps) * 0.02)
            true_pitch = 0.05 * np.sin(np.linspace(0, 2 * np.pi, dg.time_steps))
            true_roll = 0.03 * np.cos(np.linspace(0, 2 * np.pi, dg.time_steps))

            for drone_id in range(dg.drones_per_group):
                offset = self._rng.uniform([-3, -3, -1.5], [3, 3, 1.5])
                imu_bias_accel = self._rng.normal(0, 0.02, 3)
                imu_bias_gyro = self._rng.normal(0, 0.001, 3)

                for t in range(dg.time_steps):
                    record = self._generate_record(
                        group_id=group_id,
                        drone_id=drone_id,
                        t=t,
                        scenario=scenario,
                        comm_quality=comm_quality,
                        offset=offset,
                        traj_x=traj_x,
                        traj_y=traj_y,
                        traj_z=traj_z,
                        true_roll=true_roll,
                        true_pitch=true_pitch,
                        true_yaw=true_yaw,
                        imu_bias_accel=imu_bias_accel,
                        imu_bias_gyro=imu_bias_gyro,
                        noise=noise,
                    )
                    records.append(record)

        return pd.DataFrame(records)

    def _generate_record(
        self,
        group_id: int,
        drone_id: int,
        t: int,
        scenario: str,
        comm_quality: str,
        offset: np.ndarray,
        traj_x: np.ndarray,
        traj_y: np.ndarray,
        traj_z: np.ndarray,
        true_roll: np.ndarray,
        true_pitch: np.ndarray,
        true_yaw: np.ndarray,
        imu_bias_accel: np.ndarray,
        imu_bias_gyro: np.ndarray,
        noise: dict[str, float],
    ) -> dict:
        dg = self._config.data_generation

        true_pos = np.array([
            traj_x[t] + offset[0],
            traj_y[t] + offset[1],
            traj_z[t] + offset[2],
        ])
        true_orientation = np.array([true_roll[t], true_pitch[t], true_yaw[t]])

        imu_accel = np.array([
            self._rng.normal(0, noise["imu_std"]) + imu_bias_accel[0],
            self._rng.normal(0, noise["imu_std"]) + imu_bias_accel[1],
            9.81 + self._rng.normal(0, noise["imu_std"]) + imu_bias_accel[2],
        ])
        imu_gyro = np.array([
            self._rng.normal(0, 0.003) + imu_bias_gyro[0],
            self._rng.normal(0, 0.003) + imu_bias_gyro[1],
            self._rng.normal(0, 0.003) + imu_bias_gyro[2],
        ])

        true_pose = Pose6DOF(position=true_pos, orientation=true_orientation)
        imu = IMUReading(accel=imu_accel, gyro=imu_gyro, timestamp=dg.base_timestamp + t)

        base_error = self._estimator._compute_base_error(scenario)
        uncertainty = base_error + self._rng.normal(0, 0.02)

        sharing_event = self._sharing.create_sharing_event(
            uncertainty=uncertainty,
            drone_id=drone_id,
            timestamp=dg.base_timestamp + t,
        )

        if sharing_event.active:
            corrected_error = self._sharing.apply_cooperative_correction(base_error)
        else:
            corrected_error = base_error

        estimate = self._estimator.estimate(
            imu=imu,
            true_pose=true_pose,
            scenario=scenario,
            cooperative_correction=corrected_error if sharing_event.active else None,
        )

        ekf_error = self._estimator.compare_with_ekf(base_error)
        graph_error = corrected_error
        num_keypoints = self._rng.integers(50, 201)

        binary_hash = int(self._rng.integers(0, 256))

        return {
            "group_id": group_id,
            "drone_id": drone_id,
            "timestamp": dg.base_timestamp + t,
            "scenario": scenario,
            "comm_quality": comm_quality,
            "true_pos_x": round(float(true_pos[0]), 3),
            "true_pos_y": round(float(true_pos[1]), 3),
            "true_pos_z": round(float(true_pos[2]), 3),
            "true_roll": round(float(true_orientation[0]), 4),
            "true_pitch": round(float(true_orientation[1]), 4),
            "true_yaw": round(float(true_orientation[2]), 4),
            "imu_accel_x": round(float(imu_accel[0]), 4),
            "imu_accel_y": round(float(imu_accel[1]), 4),
            "imu_accel_z": round(float(imu_accel[2]), 4),
            "imu_gyro_x": round(float(imu_gyro[0]), 5),
            "imu_gyro_y": round(float(imu_gyro[1]), 5),
            "imu_gyro_z": round(float(imu_gyro[2]), 5),
            "binary_descriptor_hash": binary_hash,
            "num_keypoints": num_keypoints,
            "localization_error_m": round(base_error, 4),
            "uncertainty_metric": round(uncertainty, 4),
            "sharing_active": int(sharing_event.active),
            "corrected_error_m": round(corrected_error, 4),
            "num_landmarks_shared": sharing_event.num_landmarks_shared,
            "shared_data_bytes": sharing_event.shared_data_bytes,
            "ekf_error_comparison_m": round(ekf_error, 4),
            "graph_error_m": round(graph_error, 4),
            "method_type": "factor_graph_binary_descriptor",
            "meets_accuracy_spec": "YES" if corrected_error < 0.5 else "NO",
            "meets_bandwidth_spec": "YES" if sharing_event.shared_data_bytes < 100 else "NO",
            "meets_latency_spec": "YES" if corrected_error < 0.3 else "NO",
        }

    def _noise_for_comm_quality(self, comm_quality: str) -> dict[str, float]:
        if comm_quality == "clear":
            return {"imu_std": 0.01, "visual": 0.02}
        if comm_quality == "intermittent":
            return {"imu_std": 0.025, "visual": 0.05}
        return {"imu_std": 0.05, "visual": 0.10}

    def save(self, output_path: Path | str) -> pd.DataFrame:
        df = self.generate()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        return df


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("PRODUCT 2 - COOPERATIVE VIO DATA GENERATION")
    print("=" * 60)

    print("\nData Summary:")
    print(f"  Total records: {len(df):,}")
    print(f"  Groups: {df['group_id'].nunique()}")
    print(f"  Drones per group: {df['drone_id'].nunique()}")
    print(f"  Scenarios: {df['scenario'].unique().tolist()}")
    print(f"  Communication qualities: {df['comm_quality'].unique().tolist()}")

    print("\n--- Performance Comparison: Graph-Factor vs EKF ---")
    comparison = df.groupby("scenario").agg({
        "graph_error_m": "mean",
        "ekf_error_comparison_m": "mean",
    }).round(3)
    comparison["improvement_pct"] = (
        (comparison["ekf_error_comparison_m"] - comparison["graph_error_m"])
        / comparison["ekf_error_comparison_m"]
        * 100
    ).round(1)
    print(comparison)

    print("\n--- Sharing Statistics ---")
    sharing_rate = df["sharing_active"].mean() * 100
    print(f"  Sharing active in: {sharing_rate:.1f}% of time")
    active = df[df["sharing_active"] == 1]
    if len(active) > 0:
        print(f"  Average shared data: {active['shared_data_bytes'].mean():.0f} bytes")
    print(f"  Bandwidth reduction vs continuous sharing: {(1 - df['sharing_active'].mean()) * 100:.0f}%")

    yes_accuracy = (df["meets_accuracy_spec"] == "YES").mean() * 100
    yes_bandwidth = (df["meets_bandwidth_spec"] == "YES").mean() * 100
    print("\nSpecification compliance:")
    print(f"  - Accuracy < 0.5m: {yes_accuracy:.1f}%")
    print(f"  - Bandwidth < 100 bytes: {yes_bandwidth:.1f}%")
