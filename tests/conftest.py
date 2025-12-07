"""
Pytest Configuration

Configuration and fixtures for tests.
"""

import pytest
import sys
import os

# Adds the root directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_command_text():
    """Example command for testing."""
    return "open calculator"


@pytest.fixture
def sample_unsafe_command():
    """Example of an unsafe command."""
    return "delete file /etc/passwd"


@pytest.fixture
def temp_allowed_dir(tmp_path):
    """Creates a temporary allowed directory."""
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    return allowed_dir


@pytest.fixture
def mock_os_adapter(mocker):
    """Mock for OS adapter."""
    adapter = mocker.MagicMock()
    adapter.is_path_allowed.return_value = True
    adapter.is_app_allowed.return_value = True
    adapter.list_dir.return_value = [
        {"name": "file.txt", "type": "file", "size": 100},
        {"name": "folder", "type": "directory"},
    ]
    adapter.get_system_info.return_value = {
        "os": "TestOS",
        "version": "1.0",
    }
    return adapter
