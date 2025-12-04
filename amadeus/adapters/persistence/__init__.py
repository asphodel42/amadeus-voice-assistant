"""
Amadeus Persistence Adapters Package

Адаптери для збереження даних:
- Audit Log (SQLite)
- Configuration
"""

from amadeus.adapters.persistence.audit import SQLiteAuditAdapter

__all__ = [
    "SQLiteAuditAdapter",
]
