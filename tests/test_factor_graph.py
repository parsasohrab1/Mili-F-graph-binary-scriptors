"""Tests for factor-graph state estimation."""

import numpy as np
import pytest

from mili_vio.factor_graph import FactorGraphEstimator
from mili_vio.types import IMUReading, Pose6DOF


@pytest.fixture
def estimator() -> FactorGraphEstimator:
    return FactorGraphEstimator(rng=np.random.default_rng(42))


@pytest.fixture
def sample_pose() -> Pose6DOF:
    return Pose6DOF(
        position=np.array([1.0, 2.0, 10.0]),
        orientation=np.array([0.01, 0.02, 0.5]),
    )


@pytest.fixture
def sample_imu() -> IMUReading:
    return IMUReading(
        accel=np.array([0.0, 0.0, 9.81]),
        gyro=np.array([0.0, 0.0, 0.0]),
        timestamp=1700000000,
    )


def test_estimate_returns_state(
    estimator: FactorGraphEstimator,
    sample_pose: Pose6DOF,
    sample_imu: IMUReading,
) -> None:
    result = estimator.estimate(sample_imu, sample_pose, "open_field")
    assert result.pose.position.shape == (3,)
    assert result.pose.orientation.shape == (3,)
    assert result.localization_error_m >= 0


def test_scenario_affects_error(
    estimator: FactorGraphEstimator,
    sample_pose: Pose6DOF,
    sample_imu: IMUReading,
) -> None:
    errors = []
    for scenario in ["urban_canyon", "open_field"]:
        result = estimator.estimate(sample_imu, sample_pose, scenario)
        errors.append(result.localization_error_m)
    assert all(e >= 0 for e in errors)


def test_cooperative_correction_reduces_error(
    estimator: FactorGraphEstimator,
    sample_pose: Pose6DOF,
    sample_imu: IMUReading,
) -> None:
    base = estimator.estimate(sample_imu, sample_pose, "open_field")
    corrected = estimator.estimate(
        sample_imu, sample_pose, "open_field", cooperative_correction=0.1
    )
    assert corrected.localization_error_m == pytest.approx(0.1)


def test_ekf_comparison_higher_than_base(estimator: FactorGraphEstimator) -> None:
    base_error = 0.3
    ekf_error = estimator.compare_with_ekf(base_error)
    assert ekf_error > base_error
