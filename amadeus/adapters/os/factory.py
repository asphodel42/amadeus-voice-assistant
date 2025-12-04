"""
OS Adapter Factory

Фабрика для створення OS-специфічних адаптерів.
Автоматично визначає операційну систему та повертає відповідний адаптер.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from amadeus.adapters.os.base import BaseOSAdapter


class OSAdapterFactory:
    """
    Фабрика адаптерів операційної системи.
    
    Приклад використання:
        adapter = OSAdapterFactory.create()
        files = adapter.list_dir("~/Documents")
    """

    _instance: "BaseOSAdapter | None" = None

    @classmethod
    def create(cls) -> "BaseOSAdapter":
        """
        Створює адаптер для поточної операційної системи.
        
        Returns:
            Екземпляр адаптера (WindowsAdapter або LinuxAdapter)
            
        Raises:
            NotImplementedError: Для непідтримуваних ОС
        """
        if sys.platform == "win32":
            from amadeus.adapters.os.windows import WindowsAdapter
            return WindowsAdapter()
        elif sys.platform in ("linux", "linux2"):
            from amadeus.adapters.os.linux import LinuxAdapter
            return LinuxAdapter()
        elif sys.platform == "darwin":
            # macOS — архітектурно готові, але не реалізовано
            raise NotImplementedError(
                "macOS is not yet supported. "
                "Architecture is ready for future implementation."
            )
        else:
            raise NotImplementedError(f"Unsupported platform: {sys.platform}")

    @classmethod
    def get_singleton(cls) -> "BaseOSAdapter":
        """
        Повертає singleton екземпляр адаптера.
        
        Використовується для глобального доступу до адаптера ОС.
        """
        if cls._instance is None:
            cls._instance = cls.create()
        return cls._instance

    @classmethod
    def reset_singleton(cls) -> None:
        """Скидає singleton (для тестування)."""
        cls._instance = None


def get_os_adapter() -> "BaseOSAdapter":
    """
    Зручна функція для отримання OS адаптера.
    
    Returns:
        Singleton екземпляр адаптера
    """
    return OSAdapterFactory.get_singleton()
