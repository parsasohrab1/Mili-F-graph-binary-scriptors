"""Tests for cooperative VIO data generation."""

import numpy as np
import pandas as pd
import pytest

from mili_vio.config import load_config
from mili_vio.data import CooperativeVIODataGenerator


@pytest.fixture
def small_config():
    config = load_config()
    config.data_generation.num_groups = 1
    config.data_generation.drones_per_group = 2
    config.data_generation.time_steps = 5
    return config


def test_generate_returns_dataframe(small_config) -> None:
    generator = CooperativeVIODataGenerator(
        config=small_config, rng=np.random.default_rng(42)
    )
    df = generator.generate()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 10  # 1 group * 2 drones * 5 steps


def test_required_columns_present(small_config) -> None:
    generator = CooperativeVIODataGenerator(
        config=small_config, rng=np.random.default_rng(42)
    )
    df = generator.generate()
    required = [
        "group_id", "drone_id", "timestamp", "scenario",
        "localization_error_m", "sharing_active", "graph_error_m",
        "method_type",
    ]
    for col in required:
        assert col in df.columns


def test_save_creates_file(small_config, tmp_path) -> None:
    generator = CooperativeVIODataGenerator(
        config=small_config, rng=np.random.default_rng(42)
    )
    output = tmp_path / "test_output.csv"
    df = generator.save(output)
    assert output.exists()
    assert len(df) == 10
