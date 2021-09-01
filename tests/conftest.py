"""Configure pytest."""
from pytest_socket import disable_socket  # type: ignore[import]


def pytest_runtest_setup() -> None:
    """Disable socket for all tests."""
    disable_socket()
