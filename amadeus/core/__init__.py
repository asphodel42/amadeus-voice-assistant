"""
Amadeus Voice Assistant - Core Domain Package

This package contains pure domain logic without infrastructure dependencies.
All dependencies are inward-facing (towards this package).
"""

from amadeus.core.entities import (
    Action,
    ActionPlan,
    AuditEvent,
    Capability,
    CapabilityScope,
    CommandRequest,
    ExecutionResult,
    Intent,
    RiskLevel,
)
from amadeus.core.state_machine import AssistantState, ConfirmationStateMachine

__all__ = [
    # Entities
    "RiskLevel",
    "Intent",
    "Action",
    "ActionPlan",
    "CommandRequest",
    "ExecutionResult",
    "AuditEvent",
    "Capability",
    "CapabilityScope",
    # State Machine
    "AssistantState",
    "ConfirmationStateMachine",
]
