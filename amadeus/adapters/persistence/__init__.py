"""
Amadeus Persistence Adapters Package

Adapters for data storage:
- Audit Log (SQLite)
- Configuration
"""

from amadeus.adapters.persistence.audit import SQLiteAuditAdapter

__all__ = [
    "SQLiteAuditAdapter",
]
