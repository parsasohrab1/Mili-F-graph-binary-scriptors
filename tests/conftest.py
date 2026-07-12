"""Pytest configuration and markers."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: long-running integration tests (excluded from default CI)")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    slow_modules = {
        "test_phase6_validation",
        "test_embedded_build",
    }
    for item in items:
        module = item.module.__name__.split(".")[-1]
        if module in slow_modules:
            item.add_marker(pytest.mark.slow)
