"""Configure pytest."""

from __future__ import annotations

from pytest_socket import disable_socket  # type: ignore[import-not-found]


def pytest_runtest_setup() -> None:
    """Disable socket for all tests."""
    disable_socket()
