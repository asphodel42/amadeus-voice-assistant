"""
Amadeus OS Adapters Package

Adapter for interacting with the operating system.
Implements the ports defined in core/ports.py.
"""

from amadeus.adapters.os.factory import get_os_adapter, OSAdapterFactory
from amadeus.adapters.os.base import BaseOSAdapter

__all__ = [
    "get_os_adapter",
    "OSAdapterFactory",
    "BaseOSAdapter",
]
