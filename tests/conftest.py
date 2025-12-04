"""
Pytest Configuration

Конфігурація та фікстури для тестів.
"""

import pytest
import sys
import os

# Додаємо кореневу директорію до path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_command_text():
    """Приклад команди для тестування."""
    return "open calculator"


@pytest.fixture
def sample_unsafe_command():
    """Приклад небезпечної команди."""
    return "delete file /etc/passwd"


@pytest.fixture
def temp_allowed_dir(tmp_path):
    """Створює тимчасову дозволену директорію."""
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    return allowed_dir


@pytest.fixture
def mock_os_adapter(mocker):
    """Мок для OS адаптера."""
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
