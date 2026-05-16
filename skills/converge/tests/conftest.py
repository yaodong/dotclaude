"""Test configuration and fixtures."""
from unittest.mock import patch as mock_patch

import pytest


class _Mocker:
    """Simple mocker that wraps unittest.mock.patch."""

    def __init__(self):
        self.patches = []

    def patch(self, target, **kwargs):
        """Patch a module/function and return the mock."""
        p = mock_patch(target, **kwargs)
        mock = p.start()
        self.patches.append(p)
        return mock

    def stop_all(self):
        """Stop all active patches."""
        for p in self.patches:
            p.stop()
        self.patches.clear()


@pytest.fixture
def mocker():
    """Provide a mocker fixture using unittest.mock."""
    m = _Mocker()
    yield m
    m.stop_all()
