"""
OS Adapter Factory

Factory for creating OS-specific adapters.
Automatically detects the operating system and returns the appropriate adapter.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from amadeus.adapters.os.base import BaseOSAdapter


class OSAdapterFactory:
    """
    Factory for creating OS-specific adapters.

    Example usage:
        adapter = OSAdapterFactory.create()
        files = adapter.list_dir("~/Documents")
    """

    _instance: "BaseOSAdapter | None" = None

    @classmethod
    def create(cls) -> "BaseOSAdapter":
        """
        Creates an adapter for the current operating system.

        Returns:
            An instance of the adapter (WindowsAdapter or LinuxAdapter)

        Raises:
            NotImplementedError: For unsupported OS
        """
        if sys.platform == "win32":
            from amadeus.adapters.os.windows import WindowsAdapter
            return WindowsAdapter()
        elif sys.platform in ("linux", "linux2"):
            from amadeus.adapters.os.linux import LinuxAdapter
            return LinuxAdapter()
        elif sys.platform == "darwin":
            # macOS — architecture ready, but not implemented
            raise NotImplementedError(
                "macOS is not yet supported. "
                "Architecture is ready for future implementation."
            )
        else:
            raise NotImplementedError(f"Unsupported platform: {sys.platform}")

    @classmethod
    def get_singleton(cls) -> "BaseOSAdapter":
        """
        Returns the singleton instance of the adapter.

        Used for global access to the OS adapter.
        """
        if cls._instance is None:
            cls._instance = cls.create()
        return cls._instance

    @classmethod
    def reset_singleton(cls) -> None:
        """Resets the singleton instance (for testing)."""
        cls._instance = None


def get_os_adapter() -> "BaseOSAdapter":
    """
    Function to get the OS adapter.

    Returns:
        Singleton instance of the adapter
    """
    return OSAdapterFactory.get_singleton()
