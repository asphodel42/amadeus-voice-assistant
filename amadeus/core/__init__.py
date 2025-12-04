"""
Amadeus Voice Assistant - Core Domain Package

Цей пакет містить чисту доменну логіку без залежностей від інфраструктури.
Всі залежності спрямовані всередину (до цього пакету).
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
