"""
Amadeus Core Domain Entities

This module contains all domain entities (Data Classes).
Entities are immutable and do not contain business logic.

Hierarchy:
    CommandRequest -> Intent -> ActionPlan -> Action -> ExecutionResult -> AuditEvent
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from functools import total_ordering
from typing import Any, Dict, List, Optional


@total_ordering
class RiskLevel(Enum):
    """
    Risk level of actions.
    
    Determines whether user confirmation is needed and what type.
    """
    SAFE = auto()        # Safe actions (list_dir, system_info)
    MEDIUM = auto()      # Requires attention (open_url for non-HTTPS)
    HIGH = auto()        # Requires confirmation (write_file, create_file)
    DESTRUCTIVE = auto() # Requires typed confirmation (delete_file)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self.value < other.value
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)


class IntentType(Enum):
    """Supported intent types for version 0.1.0 (MVP)."""
    OPEN_APP = "open_app"
    OPEN_URL = "open_url"
    WEB_SEARCH = "web_search"
    LIST_DIR = "list_dir"
    READ_FILE = "read_file"
    CREATE_FILE = "create_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    SYSTEM_INFO = "system_info"
    UNKNOWN = "unknown"


class ExecutionStatus(Enum):
    """Execution status of an action."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DENIED = "denied"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DRY_RUN = "dry_run"


@dataclass(frozen=True)
class CommandRequest:
    """
    User's initial request.

    Attributes:
        request_id: Unique request identifier
        raw_text: Original text after ASR
        timestamp: Request creation time
        source: Command source (voice, push_to_talk, text_input)
    """
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_text: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "voice"

    def __post_init__(self) -> None:
        # Validation: raw_text cannot be empty for processing
        if not self.raw_text.strip():
            object.__setattr__(self, 'raw_text', '')


@dataclass(frozen=True)
class Intent:
    """
    Recognized user intent.

    Attributes:
        intent_type: Type of intent
        slots: Extracted parameters (key-value)
        confidence: Confidence in recognition (0.0-1.0)
        original_request: Reference to the original request
    """
    intent_type: IntentType
    slots: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    original_request: Optional[CommandRequest] = None

    def __post_init__(self) -> None:
        # Validate confidence
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    @property
    def is_unknown(self) -> bool:
        return self.intent_type == IntentType.UNKNOWN
    
    def get_slot(self, key: str, default: Any = None) -> Any:
        """Safely retrieve a slot."""
        return self.slots.get(key, default)


@dataclass(frozen=True)
class Action:
    """
    One atomic action to be performed.

    Attributes:
        action_id: Unique action identifier
        tool_name: Tool name (filesystem, browser, process)
        function_name: Function name to call
        args: Function arguments
        risk: Risk level
        description: Human-readable description for UI
        requires_confirmation: Whether explicit confirmation is required
    """
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    function_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    risk: RiskLevel = RiskLevel.SAFE
    description: str = ""
    requires_confirmation: bool = False

    def __post_init__(self) -> None:
        # Automatically require confirmation for HIGH and DESTRUCTIVE
        if self.risk in (RiskLevel.HIGH, RiskLevel.DESTRUCTIVE) and not self.requires_confirmation:
            object.__setattr__(self, 'requires_confirmation', True)
    
    def to_human_readable(self) -> str:
        """Generates a human-readable description of the action."""
        if self.description:
            return self.description
        return f"{self.tool_name}.{self.function_name}({self.args})"


@dataclass(frozen=True)
class ActionPlan:
    """
    Represents a plan consisting of a sequence of actions.

    Attributes:
        plan_id: Unique plan identifier
        intent: Original intent
        actions: List of actions to be performed (in order)
        requires_confirmation: Whether the plan requires confirmation
        max_risk: Maximum risk level among actions
        dry_run: Whether this is a simulation without actual execution
        created_at: Plan creation time
    """
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent: Intent = field(default_factory=lambda: Intent(IntentType.UNKNOWN))
    actions: List[Action] = field(default_factory=list)
    requires_confirmation: bool = False
    dry_run: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def max_risk(self) -> RiskLevel:
        """Calculates the maximum risk level among all actions."""
        if not self.actions:
            return RiskLevel.SAFE
        return max(action.risk for action in self.actions)

    @property
    def is_empty(self) -> bool:
        return len(self.actions) == 0

    def to_preview_text(self) -> str:
        """Generates preview text for the UI."""
        if self.is_empty:
            return "No actions planned."
        
        lines = [f"Plan: {self.intent.intent_type.value}"]
        lines.append(f"Risk Level: {self.max_risk.name}")
        lines.append("")
        lines.append("Actions:")
        for i, action in enumerate(self.actions, 1):
            marker = "⚠️" if action.requires_confirmation else "✅"
            lines.append(f"  {i}. {marker} {action.to_human_readable()}")
        
        if self.requires_confirmation:
            lines.append("")
            lines.append("⚠️ This plan requires your confirmation before execution.")
        
        return "\n".join(lines)


@dataclass(frozen=True)
class ExecutionResult:
    """
    Represents the result of executing an action.

    Attributes:
        action: The executed action
        status: Execution status
        output: Output data (if any)
        error: Error message (if any)
        started_at: Start time of execution
        completed_at: Completion time of execution
    """
    action: Action
    status: ExecutionStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS
    
    @property
    def duration_ms(self) -> Optional[float]:
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return None


@dataclass(frozen=True)
class AuditEvent:
    """
    Represents an audit event (append-only).

    Attributes:
        event_id: Unique event identifier
        timestamp: Event time
        event_type: Event type (command, plan, confirmation, execution, error)
        actor: Who initiated (user, system, plugin:<name>)
        command_request: Original request (if applicable)
        plan: Action plan (if applicable)
        result: Execution result (if applicable)
        metadata: Additional data
        previous_hash: Hash of the previous event (for hash chain)
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = "generic"
    actor: str = "system"
    command_request: Optional[CommandRequest] = None
    plan: Optional[ActionPlan] = None
    result: Optional[ExecutionResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""

    def compute_hash(self) -> str:
        """Calculates SHA-256 hash of the event for chain integrity."""
        content = f"{self.event_id}|{self.timestamp.isoformat()}|{self.event_type}|{self.actor}|{self.previous_hash}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


# ============================================
# Capability System Entities
# ============================================

class CapabilityScope(Enum):
    """Represents the scope of a capability (capability scope)."""
    # Filesystem
    FS_READ = "fs.read"
    FS_WRITE = "fs.write"
    FS_DELETE = "fs.delete"
    FS_CREATE = "fs.create"
    
    # Process
    PROCESS_LAUNCH = "process.launch"
    PROCESS_KILL = "process.kill"
    
    # Network (browser-only for now)
    NET_BROWSER = "net.browser"
    
    # System
    SYSTEM_INFO = "system.info"
    
    # UI
    UI_NOTIFY = "ui.notify"
    UI_DIALOG = "ui.dialog"


@dataclass(frozen=True)
class Capability:
    """
    Represents a capability provided by a skill (skill).

    Attributes:
        scope: The scope of the capability
        constraints: Constraints (allowed_paths, max_size, etc.)
        risk: The risk level of this capability
    """
    scope: CapabilityScope
    constraints: Dict[str, Any] = field(default_factory=dict)
    risk: RiskLevel = RiskLevel.SAFE

    def allows_path(self, path: str) -> bool:
        """Перевіряє, чи дозволений шлях для filesystem операцій."""
        allowed_paths = self.constraints.get("allowed_paths", [])
        if not allowed_paths:
            return True  # No restrictions

        # Normalization and checking
        from pathlib import Path
        target = Path(path).resolve()
        for allowed in allowed_paths:
            allowed_path = Path(allowed).expanduser().resolve()
            try:
                target.relative_to(allowed_path)
                return True
            except ValueError:
                continue
        return False


@dataclass(frozen=True)
class CapabilityManifest:
    """
    Represents a capability manifest for a skill (plugin manifest).

    Attributes:
        skill_id: Unique skill identifier
        version: Skill version
        publisher_id: Publisher identifier
        capabilities: List of requested capabilities
        signature: Digital signature of the manifest
    """
    skill_id: str
    version: str
    publisher_id: str
    capabilities: List[Capability] = field(default_factory=list)
    signature: str = ""

    def has_capability(self, scope: CapabilityScope) -> bool:
        """Перевіряє наявність можливості."""
        return any(cap.scope == scope for cap in self.capabilities)
    
    def get_capability(self, scope: CapabilityScope) -> Optional[Capability]:
        """Отримує можливість за scope."""
        for cap in self.capabilities:
            if cap.scope == scope:
                return cap
        return None
