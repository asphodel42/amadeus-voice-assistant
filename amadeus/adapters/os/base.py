"""
Base OS Adapter

Базовий клас для OS-специфічних адаптерів.
Містить спільну логіку та інтерфейс.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class BaseOSAdapter(ABC):
    """
    Базовий клас для адаптерів операційної системи.
    
    Реалізує спільну логіку перевірки безпеки та надає
    абстрактні методи для OS-специфічних реалізацій.
    """

    def __init__(self) -> None:
        # Дозволені директорії для файлових операцій
        self._allowed_directories: Set[Path] = set()
        self._init_default_allowed_directories()
        
        # Білий список додатків
        self._allowed_apps: Dict[str, str] = {}
        self._init_default_allowed_apps()
        
        # Пошукові системи
        self._search_engines: Dict[str, str] = {
            "default": "https://duckduckgo.com/?q={}",
            "duckduckgo": "https://duckduckgo.com/?q={}",
            "google": "https://www.google.com/search?q={}",
        }

    def _init_default_allowed_directories(self) -> None:
        """Ініціалізує дозволені директорії за замовчуванням."""
        home = Path.home()
        self._allowed_directories = {
            home / "Documents",
            home / "Downloads",
            home / "Desktop",
        }
        
        # Створюємо директорії якщо не існують
        for directory in self._allowed_directories:
            directory.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def _init_default_allowed_apps(self) -> None:
        """Ініціалізує білий список додатків (OS-специфічно)."""
        ...

    # ============================================
    # Path Validation
    # ============================================

    def is_path_allowed(self, path: str, operation: str = "read") -> bool:
        """
        Перевіряє, чи дозволена операція для шляху.
        
        Args:
            path: Шлях для перевірки
            operation: Тип операції (read, write, delete)
            
        Returns:
            True якщо дозволено
        """
        try:
            target = Path(path).expanduser().resolve()
            
            # Перевіряємо, чи шлях всередині дозволених директорій
            for allowed in self._allowed_directories:
                try:
                    target.relative_to(allowed)
                    return True
                except ValueError:
                    continue
            
            return False
        except Exception:
            return False

    def add_allowed_directory(self, path: str) -> bool:
        """Додає директорію до дозволених."""
        try:
            directory = Path(path).expanduser().resolve()
            if directory.is_dir():
                self._allowed_directories.add(directory)
                return True
            return False
        except Exception:
            return False

    def remove_allowed_directory(self, path: str) -> bool:
        """Видаляє директорію з дозволених."""
        try:
            directory = Path(path).expanduser().resolve()
            self._allowed_directories.discard(directory)
            return True
        except Exception:
            return False

    def get_allowed_directories(self) -> List[str]:
        """Повертає список дозволених директорій."""
        return [str(d) for d in self._allowed_directories]

    # ============================================
    # App Management
    # ============================================

    def is_app_allowed(self, app_name: str) -> bool:
        """Перевіряє, чи додаток у білому списку."""
        return app_name.lower() in self._allowed_apps

    def get_app_path(self, app_name: str) -> Optional[Path]:
        """Отримує повний шлях до додатку."""
        app_key = app_name.lower()
        if app_key in self._allowed_apps:
            path_str = self._allowed_apps[app_key]
            if path_str:
                return Path(path_str)
        return None

    def add_allowed_app(self, name: str, path: str = "") -> None:
        """Додає додаток до білого списку."""
        self._allowed_apps[name.lower()] = path

    def get_allowed_apps(self) -> List[str]:
        """Повертає список дозволених додатків."""
        return list(self._allowed_apps.keys())

    # ============================================
    # FileSystem Operations (Abstract)
    # ============================================

    @abstractmethod
    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        """Повертає список файлів та папок."""
        ...

    @abstractmethod
    def read_file(self, path: str, max_bytes: int = 10240) -> str:
        """Читає вміст файлу."""
        ...

    @abstractmethod
    def create_file(self, path: str, content: str = "") -> bool:
        """Створює новий файл."""
        ...

    @abstractmethod
    def write_file(self, path: str, content: str, overwrite: bool = False) -> bool:
        """Записує вміст у файл."""
        ...

    @abstractmethod
    def delete_path(self, path: str, recursive: bool = False) -> bool:
        """Видаляє файл або папку."""
        ...

    def path_exists(self, path: str) -> bool:
        """Перевіряє, чи існує шлях."""
        try:
            return Path(path).expanduser().exists()
        except Exception:
            return False

    # ============================================
    # Process Operations (Abstract)
    # ============================================

    @abstractmethod
    def open_app(self, app_name: str, args: Optional[List[str]] = None) -> bool:
        """Відкриває додаток."""
        ...

    # ============================================
    # Browser Operations (Abstract)
    # ============================================

    @abstractmethod
    def open_url(self, url: str) -> bool:
        """Відкриває URL у браузері."""
        ...

    def search_web(self, query: str, engine: str = "default") -> bool:
        """Виконує пошук у вебі."""
        url_template = self._search_engines.get(engine, self._search_engines["default"])
        # URL encode query
        from urllib.parse import quote_plus
        url = url_template.format(quote_plus(query))
        return self.open_url(url)

    def is_url_safe(self, url: str) -> bool:
        """Перевіряє безпечність URL."""
        url_lower = url.lower()
        return url_lower.startswith("https://") or url_lower.startswith("http://localhost")

    # ============================================
    # System Info (Abstract)
    # ============================================

    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """Повертає інформацію про систему."""
        ...

    @abstractmethod
    def get_memory_info(self) -> Dict[str, int]:
        """Повертає інформацію про пам'ять."""
        ...

    @abstractmethod
    def get_disk_info(self) -> List[Dict[str, Any]]:
        """Повертає інформацію про диски."""
        ...
