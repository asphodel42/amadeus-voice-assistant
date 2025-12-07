"""
Unit Tests for Core Entities

Tests for domain entities.
"""

import pytest
from datetime import datetime, timezone

from amadeus.core.entities import (
    Action,
    ActionPlan,
    AuditEvent,
    Capability,
    CapabilityScope,
    CommandRequest,
    ExecutionResult,
    ExecutionStatus,
    Intent,
    IntentType,
    RiskLevel,
)


class TestRiskLevel:
    """Tests for RiskLevel."""

    def test_risk_ordering(self):
        """Tests the ordering of risk levels."""
        assert RiskLevel.SAFE.value < RiskLevel.MEDIUM.value
        assert RiskLevel.MEDIUM.value < RiskLevel.HIGH.value
        assert RiskLevel.HIGH.value < RiskLevel.DESTRUCTIVE.value


class TestIntent:
    """Tests for Intent."""

    def test_intent_creation(self):
        """Tests the creation of Intent."""
        intent = Intent(
            intent_type=IntentType.OPEN_APP,
            slots={"app_name": "calculator"},
            confidence=0.95,
        )
        
        assert intent.intent_type == IntentType.OPEN_APP
        assert intent.slots["app_name"] == "calculator"
        assert intent.confidence == 0.95
        assert not intent.is_unknown
    
    def test_unknown_intent(self):
        """Tests the unknown Intent."""
        intent = Intent(intent_type=IntentType.UNKNOWN)
        
        assert intent.is_unknown
        assert intent.confidence == 1.0  # default
    
    def test_invalid_confidence(self):
        """Tests the validation of confidence."""
        with pytest.raises(ValueError):
            Intent(intent_type=IntentType.OPEN_APP, confidence=1.5)
        
        with pytest.raises(ValueError):
            Intent(intent_type=IntentType.OPEN_APP, confidence=-0.1)
    
    def test_get_slot(self):
        """Tests the retrieval of slots."""
        intent = Intent(
            intent_type=IntentType.OPEN_APP,
            slots={"app_name": "notepad"},
        )
        
        assert intent.get_slot("app_name") == "notepad"
        assert intent.get_slot("missing") is None
        assert intent.get_slot("missing", "default") == "default"


class TestAction:
    """Tests for Action."""

    def test_action_creation(self):
        """Tests the creation of Action."""
        action = Action(
            tool_name="filesystem",
            function_name="list_dir",
            args={"path": "/tmp"},
            risk=RiskLevel.SAFE,
            description="List directory contents",
        )
        
        assert action.tool_name == "filesystem"
        assert action.function_name == "list_dir"
        assert action.risk == RiskLevel.SAFE
        assert not action.requires_confirmation
    
    def test_high_risk_auto_confirmation(self):
        """Tests automatic confirmation for HIGH risk."""
        action = Action(
            tool_name="filesystem",
            function_name="write_file",
            args={"path": "/tmp/test.txt"},
            risk=RiskLevel.HIGH,
        )
        
        assert action.requires_confirmation
    
    def test_destructive_auto_confirmation(self):
        """Tests automatic confirmation for DESTRUCTIVE."""
        action = Action(
            tool_name="filesystem",
            function_name="delete_path",
            args={"path": "/tmp/test"},
            risk=RiskLevel.DESTRUCTIVE,
        )
        
        assert action.requires_confirmation
    
    def test_human_readable(self):
        """Tests the generation of human-readable description."""
        action = Action(
            tool_name="browser",
            function_name="open_url",
            args={"url": "https://example.com"},
            description="Open URL in browser",
        )
        
        assert action.to_human_readable() == "Open URL in browser"

        # Without description
        action2 = Action(
            tool_name="test",
            function_name="func",
            args={"key": "value"},
        )
        assert "test.func" in action2.to_human_readable()


class TestActionPlan:
    """Tests for ActionPlan."""

    def test_empty_plan(self):
        """Tests the empty plan."""
        plan = ActionPlan()
        
        assert plan.is_empty
        assert plan.max_risk == RiskLevel.SAFE
    
    def test_plan_with_actions(self):
        """Tests the plan with actions."""
        actions = [
            Action(tool_name="fs", function_name="read", risk=RiskLevel.SAFE),
            Action(tool_name="fs", function_name="write", risk=RiskLevel.HIGH),
        ]
        
        plan = ActionPlan(actions=actions)
        
        assert not plan.is_empty
        assert len(plan.actions) == 2
        assert plan.max_risk == RiskLevel.HIGH
    
    def test_preview_text(self):
        """Tests the generation of preview text."""
        intent = Intent(intent_type=IntentType.LIST_DIR)
        actions = [
            Action(
                tool_name="filesystem",
                function_name="list_dir",
                risk=RiskLevel.SAFE,
                description="List files",
            ),
        ]
        
        plan = ActionPlan(intent=intent, actions=actions)
        preview = plan.to_preview_text()
        
        assert "list_dir" in preview.lower()
        assert "List files" in preview


class TestAuditEvent:
    """Tests for AuditEvent."""

    def test_event_creation(self):
        """Tests the creation of event."""
        event = AuditEvent(
            event_type="command",
            actor="user",
            metadata={"source": "voice"},
        )
        
        assert event.event_type == "command"
        assert event.actor == "user"
        assert event.metadata["source"] == "voice"
    
    def test_hash_computation(self):
        """Tests the hash computation."""
        event = AuditEvent(
            event_type="test",
            actor="system",
        )
        
        hash1 = event.compute_hash()

        # The same object should produce the same hash
        hash2 = event.compute_hash()
        assert hash1 == hash2

        # Hash should be 64 characters (SHA-256)
        assert len(hash1) == 64


class TestCapability:
    """Tests for Capability."""
    
    def test_capability_creation(self):
        """Tests the creation of Capability."""
        cap = Capability(
            scope=CapabilityScope.FS_READ,
            constraints={"allowed_paths": ["~/Documents"]},
        )
        
        assert cap.scope == CapabilityScope.FS_READ
        assert "allowed_paths" in cap.constraints
    
    def test_allows_path_no_constraints(self):
        """Tests path allowance without constraints."""
        cap = Capability(scope=CapabilityScope.FS_READ)
        
        assert cap.allows_path("/any/path")
    
    def test_allows_path_with_constraints(self):
        """Tests path allowance with constraints."""
        import os
        from pathlib import Path
        
        home = str(Path.home())
        docs = os.path.join(home, "Documents")
        
        cap = Capability(
            scope=CapabilityScope.FS_READ,
            constraints={"allowed_paths": [docs]},
        )

        # Path inside allowed directory
        assert cap.allows_path(os.path.join(docs, "test.txt"))

        # Path outside allowed directory
        assert not cap.allows_path("/etc/passwd")


class TestExecutionResult:
    """Tests for ExecutionResult."""
    
    def test_success_result(self):
        """Tests the successful result."""
        action = Action(tool_name="test", function_name="func")
        result = ExecutionResult(
            action=action,
            status=ExecutionStatus.SUCCESS,
            output="done",
        )
        
        assert result.is_success
        assert result.output == "done"
        assert result.error is None
    
    def test_failed_result(self):
        """Tests the failed result."""
        action = Action(tool_name="test", function_name="func")
        result = ExecutionResult(
            action=action,
            status=ExecutionStatus.FAILED,
            error="Something went wrong",
        )
        
        assert not result.is_success
        assert result.error == "Something went wrong"
    
    def test_duration_calculation(self):
        """Tests the duration calculation."""
        action = Action(tool_name="test", function_name="func")
        
        start = datetime.now(timezone.utc)
        # Simulate delay (in reality this would be time.sleep)
        end = datetime.now(timezone.utc)
        
        result = ExecutionResult(
            action=action,
            status=ExecutionStatus.SUCCESS,
            started_at=start,
            completed_at=end,
        )
        
        assert result.duration_ms is not None
        assert result.duration_ms >= 0
