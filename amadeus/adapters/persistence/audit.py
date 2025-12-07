"""
SQLite Audit Adapter

Append-only audit journal with hash chain integrity.
Stores all events for analysis and compliance.

Security:
- Append-only: events cannot be deleted or modified
- Hash chain: each record contains the hash of the previous one
- Periodic verification: ability to verify integrity
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from amadeus.core.entities import (
    ActionPlan,
    AuditEvent,
    CommandRequest,
    ExecutionResult,
)


class SQLiteAuditAdapter:
    """
    SQLite-based append-only audit log.

    Implements AuditPort from core/ports.py.

    Examples:

    ```
    audit = SQLiteAuditAdapter("~/.amadeus/audit.db")
    
    event = AuditEvent(
        event_type="command",
        actor="user",
        command_request=request,
    )
    audit.append_event(event)
    
    # Verify integrity
    if not audit.verify_integrity():
        print("WARNING: Audit log has been tampered with!")
    ```
    """

    def __init__(
        self,
        db_path: str = "~/.amadeus/audit.db",
        create_if_missing: bool = True,
    ) -> None:
        self.db_path = Path(db_path).expanduser()
        self._lock = threading.Lock()
        
        if create_if_missing:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()

    def _init_database(self) -> None:
        """Ініціалізує структуру бази даних."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main table for events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    data TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for fast searching
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON audit_events(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type 
                ON audit_events(event_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_actor 
                ON audit_events(actor)
            """)

            # Table for checkpoints (periodic signed snapshots)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS integrity_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checkpoint_time TEXT NOT NULL,
                    last_event_id INTEGER NOT NULL,
                    cumulative_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def append_event(self, event: AuditEvent) -> str:
        """
        Add event to the log.

        Args:
            event: Event to log

        Returns:
            ID of the created event
        """
        with self._lock:
            # Get the hash of the last event
            previous_hash = self.get_last_hash()

            # Serialize event data
            event_data = self._serialize_event(event)

            # Compute event hash
            event_hash = self._compute_hash(
                event.event_id,
                event.timestamp.isoformat(),
                event.event_type,
                event.actor,
                event_data,
                previous_hash,
            )
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_events 
                    (event_id, timestamp, event_type, actor, data, previous_hash, event_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.event_type,
                    event.actor,
                    event_data,
                    previous_hash,
                    event_hash,
                ))
                conn.commit()
        
        return event.event_id

    def get_events(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEvent]:
        """
        Get events from the log.

        Args:
            start_time: Start of the period (ISO format)
            end_time: End of the period (ISO format)
            event_type: Filter by event type
            actor: Filter by actor
            limit: Maximum number of events
            offset: Offset for pagination

        Returns:
            List of events
        """
        query = "SELECT * FROM audit_events WHERE 1=1"
        params: List[Any] = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if actor:
            query += " AND actor = ?"
            params.append(actor)
        
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        return [self._row_to_event(row) for row in rows]

    def get_last_hash(self) -> str:
        """Get the hash of the last event."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_hash FROM audit_events 
                ORDER BY id DESC LIMIT 1
            """)
            row = cursor.fetchone()
        
        if row:
            return row["event_hash"]
        return "GENESIS"  # Initial hash for the first event

    def verify_integrity(self) -> bool:
        """
        Verify the integrity of the log (hash chain).

        Returns:
            True if the log has not been modified
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_id, timestamp, event_type, actor, data, 
                       previous_hash, event_hash
                FROM audit_events ORDER BY id ASC
            """)
            rows = cursor.fetchall()
        
        if not rows:
            return True  # Empty log is valid

        expected_previous_hash = "GENESIS"
        
        for row in rows:
            # Check that previous_hash matches
            if row["previous_hash"] != expected_previous_hash:
                return False

            # Check that event_hash is correct
            computed_hash = self._compute_hash(
                row["event_id"],
                row["timestamp"],
                row["event_type"],
                row["actor"],
                row["data"],
                row["previous_hash"],
            )
            
            if computed_hash != row["event_hash"]:
                return False
            
            expected_previous_hash = row["event_hash"]
        
        return True

    def create_checkpoint(self) -> str:
        """
        Create checkpoint for periodic verification.
        
        Returns:
            Cumulative hash for checkpoint
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get the last event
                cursor.execute("""
                    SELECT id, event_hash FROM audit_events 
                    ORDER BY id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                
                if not row:
                    return "EMPTY"
                
                last_id = row["id"]
                cumulative_hash = row["event_hash"]

                # Save checkpoint
                cursor.execute("""
                    INSERT INTO integrity_checkpoints 
                    (checkpoint_time, last_event_id, cumulative_hash)
                    VALUES (?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    last_id,
                    cumulative_hash,
                ))
                conn.commit()
        
        return cumulative_hash

    def get_event_count(self) -> int:
        """Повертає загальну кількість подій."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM audit_events")
            row = cursor.fetchone()
        return row["count"] if row else 0

    def export_to_json(self, filepath: str, limit: int = 10000) -> int:
        """
        Export the log to a JSON file.

        Args:
            filepath: Path to the file
            limit: Maximum number of events

        Returns:
            Number of exported events
        """
        events = self.get_events(limit=limit, offset=0)
        
        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_events": len(events),
            "events": [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "actor": e.actor,
                    "metadata": e.metadata,
                }
                for e in events
            ],
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return len(events)

    def _serialize_event(self, event: AuditEvent) -> str:
        """Serialize event to JSON."""
        data: Dict[str, Any] = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "actor": event.actor,
            "metadata": event.metadata,
        }
        
        if event.command_request:
            data["command_request"] = {
                "request_id": event.command_request.request_id,
                "raw_text": event.command_request.raw_text,
                "source": event.command_request.source,
            }
        
        if event.plan:
            data["plan"] = {
                "plan_id": event.plan.plan_id,
                "intent_type": event.plan.intent.intent_type.value,
                "action_count": len(event.plan.actions),
                "requires_confirmation": event.plan.requires_confirmation,
            }
        
        if event.result:
            data["result"] = {
                "status": event.result.status.value,
                "error": event.result.error,
            }
        
        return json.dumps(data, ensure_ascii=False)

    def _row_to_event(self, row: sqlite3.Row) -> AuditEvent:
        """Convert a database row to an AuditEvent."""
        data = json.loads(row["data"])
        
        return AuditEvent(
            event_id=row["event_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            event_type=row["event_type"],
            actor=row["actor"],
            metadata=data.get("metadata", {}),
            previous_hash=row["previous_hash"],
        )

    def _compute_hash(self, *args: str) -> str:
        """Compute SHA-256 hash."""
        content = "|".join(str(arg) for arg in args)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
