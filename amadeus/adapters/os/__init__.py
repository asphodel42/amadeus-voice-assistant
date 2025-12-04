"""
Amadeus OS Adapters Package

Адаптери для взаємодії з операційною системою.
Реалізують порти, визначені в core/ports.py.
"""

from amadeus.adapters.os.factory import get_os_adapter, OSAdapterFactory
from amadeus.adapters.os.base import BaseOSAdapter

__all__ = [
    "get_os_adapter",
    "OSAdapterFactory",
    "BaseOSAdapter",
]
