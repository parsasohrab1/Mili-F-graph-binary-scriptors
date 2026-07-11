"""Tests for event-driven landmark sharing."""

import numpy as np
import pytest

from mili_vio.sharing import EventDrivenSharing


@pytest.fixture
def sharing() -> EventDrivenSharing:
    return EventDrivenSharing(rng=np.random.default_rng(42))


def test_no_share_below_threshold(sharing: EventDrivenSharing) -> None:
    event = sharing.create_sharing_event(
        uncertainty=0.1, drone_id=0, timestamp=1700000000
    )
    assert not event.active
    assert event.num_landmarks_shared == 0
    assert event.shared_data_bytes == 0


def test_share_above_threshold(sharing: EventDrivenSharing) -> None:
    event = sharing.create_sharing_event(
        uncertainty=0.5, drone_id=0, timestamp=1700000000
    )
    assert event.active
    assert 3 <= event.num_landmarks_shared <= 15
    assert event.shared_data_bytes > 0
    assert len(event.landmarks) == event.num_landmarks_shared


def test_cooperative_correction_reduces_error(sharing: EventDrivenSharing) -> None:
    base_error = 1.0
    corrected = sharing.apply_cooperative_correction(base_error)
    assert corrected < base_error


def test_bandwidth_spec(sharing: EventDrivenSharing) -> None:
    event = sharing.create_sharing_event(
        uncertainty=0.5, drone_id=0, timestamp=1700000000
    )
    if event.active:
        assert sharing.meets_bandwidth_spec(event.shared_data_bytes)
