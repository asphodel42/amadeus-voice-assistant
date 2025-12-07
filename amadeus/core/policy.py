"""
Amadeus Core Policy Engine

Core policy engine — responsible for action authorization.
Verifies ActionPlan against Capabilities and risk rules.

Zero-Trust Principles:
1. All actions are verified before execution
2. Capabilities are explicitly declared
3. High-risk actions require confirmation
4. Destructive actions require typed confirmation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set

from amadeus.core.entities import (
    Action,
    ActionPlan,
    Capability,
    CapabilityManifest,
    CapabilityScope,
    RiskLevel,
)


class ConfirmationType(Enum):
    """Confirmation types."""
    NONE = auto()           # No confirmation required
    SIMPLE = auto()         # Simple Yes/No confirmation
    TYPED = auto()          # Typed confirmation phrase required
    PASSCODE = auto()       # Passcode/PIN entry required (future)


@dataclass(frozen=True)
class PolicyDecision:
    """
    Policy evaluation result.

    Attributes:
        allowed: Whether the action is allowed
        reason: Reason for the decision
        requires_confirmation: Whether confirmation is required
        confirmation_type: Type of confirmation required
        denied_actions: List of denied actions (if any)
    """
    allowed: bool
    reason: str
    requires_confirmation: bool = False
    confirmation_type: ConfirmationType = ConfirmationType.NONE
    denied_actions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @staticmethod
    def allow(reason: str = "Action allowed") -> "PolicyDecision":
        """Create an allow decision without confirmation."""
        return PolicyDecision(allowed=True, reason=reason)

    @staticmethod
    def allow_with_confirmation(
        reason: str,
        confirmation_type: ConfirmationType = ConfirmationType.SIMPLE
    ) -> "PolicyDecision":
        """Create an allow decision with confirmation."""
        return PolicyDecision(
            allowed=True,
            reason=reason,
            requires_confirmation=True,
            confirmation_type=confirmation_type,
        )

    @staticmethod
    def deny(reason: str, denied_actions: Optional[List[str]] = None) -> "PolicyDecision":
        """Create a deny decision."""
        return PolicyDecision(
            allowed=False,
            reason=reason,
            denied_actions=denied_actions or [],
        )


@dataclass
class PolicyRule:
    """
    Security policy rule.

    Attributes:
        rule_id: Rule identifier
        description: Rule description
        scope: Scope of application (optional)
        risk_threshold: Minimum risk level for triggering
        confirmation_type: Type of confirmation required
        enabled: Whether the rule is enabled
    """
    rule_id: str
    description: str
    scope: Optional[CapabilityScope] = None
    risk_threshold: RiskLevel = RiskLevel.HIGH
    confirmation_type: ConfirmationType = ConfirmationType.SIMPLE
    enabled: bool = True


# Default policy rules
DEFAULT_POLICY_RULES: List[PolicyRule] = [
    PolicyRule(
        rule_id="destructive_confirmation",
        description="Destructive actions require typed confirmation",
        risk_threshold=RiskLevel.DESTRUCTIVE,
        confirmation_type=ConfirmationType.TYPED,
    ),
    PolicyRule(
        rule_id="high_risk_confirmation",
        description="High-risk actions require simple confirmation",
        risk_threshold=RiskLevel.HIGH,
        confirmation_type=ConfirmationType.SIMPLE,
    ),
    PolicyRule(
        rule_id="fs_delete_always_confirm",
        description="File deletion always requires typed confirmation",
        scope=CapabilityScope.FS_DELETE,
        risk_threshold=RiskLevel.SAFE,  # Always, regardless of risk
        confirmation_type=ConfirmationType.TYPED,
    ),
    PolicyRule(
        rule_id="fs_write_confirm",
        description="File writing requires confirmation",
        scope=CapabilityScope.FS_WRITE,
        risk_threshold=RiskLevel.SAFE,
        confirmation_type=ConfirmationType.SIMPLE,
    ),
]


class PolicyEngine:
    """
    Security policy engine.

    Performs a two-step verification:
    1. Capability Check: whether the skill has permission for the operation
    2. Risk Assessment: what level of confirmation is required

    Example usage:
        engine = PolicyEngine()
        decision = engine.evaluate(plan, skill_capabilities)
        
        if decision.allowed:
            if decision.requires_confirmation:
                # Show confirmation dialog
                pass
            else:
                # Execute automatically
                pass
        else:
            # Deny with explanation
            print(decision.reason)
    """

    def __init__(self, rules: Optional[List[PolicyRule]] = None) -> None:
        self.rules = rules or DEFAULT_POLICY_RULES.copy()
        
        # Mapping: function_name -> required capability scope
        self._function_to_scope: Dict[str, CapabilityScope] = {
            "list_dir": CapabilityScope.FS_READ,
            "read_file": CapabilityScope.FS_READ,
            "create_file": CapabilityScope.FS_CREATE,
            "write_file": CapabilityScope.FS_WRITE,
            "delete_path": CapabilityScope.FS_DELETE,
            "open_app": CapabilityScope.PROCESS_LAUNCH,
            "open_url": CapabilityScope.NET_BROWSER,
            "search_web": CapabilityScope.NET_BROWSER,
            "get_system_info": CapabilityScope.SYSTEM_INFO,
        }

    def evaluate(
        self,
        plan: ActionPlan,
        capabilities: Optional[List[Capability]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        """
        Evaluates the action plan against security policies.

        Args:
            plan: Action plan to evaluate
            capabilities: Available capabilities (if None - system defaults)
            context: Additional context (user, session, etc.)

        Returns:
            Policy decision
        """
        if plan.is_empty:
            return PolicyDecision.allow("Empty plan, nothing to execute")

        # Stage 1: Capability Check
        capability_result = self._check_capabilities(plan, capabilities)
        if not capability_result.allowed:
            return capability_result

        # Stage 2: Risk Assessment
        risk_result = self._assess_risk(plan)

        # Merge results
        return self._merge_decisions(capability_result, risk_result)

    def _check_capabilities(
        self,
        plan: ActionPlan,
        capabilities: Optional[List[Capability]],
    ) -> PolicyDecision:
        """Checks if all actions are allowed by capabilities."""

        # If capabilities are not specified - allow (system level)
        if capabilities is None:
            return PolicyDecision.allow("System-level access granted")
        
        denied_actions: List[str] = []
        warnings: List[str] = []
        
        for action in plan.actions:
            required_scope = self._function_to_scope.get(action.function_name)
            
            if required_scope is None:
                # Unknown function - warning
                warnings.append(f"Unknown function: {action.function_name}")
                continue

            # Look for matching capability
            matching_cap = None
            for cap in capabilities:
                if cap.scope == required_scope:
                    matching_cap = cap
                    break
            
            if matching_cap is None:
                denied_actions.append(
                    f"Action '{action.function_name}' requires capability '{required_scope.value}'"
                )
                continue

            # Check constraints (e.g., allowed_paths)
            if "path" in action.args and hasattr(matching_cap, "allows_path"):
                path = action.args["path"]
                if not matching_cap.allows_path(path):
                    denied_actions.append(
                        f"Path '{path}' is not allowed for capability '{required_scope.value}'"
                    )
        
        if denied_actions:
            return PolicyDecision.deny(
                reason="Insufficient capabilities",
                denied_actions=denied_actions,
            )
        
        decision = PolicyDecision.allow("All capabilities verified")
        object.__setattr__(decision, "warnings", warnings)
        return decision

    def _assess_risk(self, plan: ActionPlan) -> PolicyDecision:
        """Оцінює ризик плану та визначає потрібне підтвердження."""
        
        max_risk = plan.max_risk
        required_confirmation = ConfirmationType.NONE
        reasons: List[str] = []

        # Apply rules
        for rule in self.rules:
            if not rule.enabled:
                continue

            # Check scope-specific rules
            if rule.scope is not None:
                for action in plan.actions:
                    action_scope = self._function_to_scope.get(action.function_name)
                    if action_scope == rule.scope:
                        if action.risk.value >= rule.risk_threshold.value:
                            if rule.confirmation_type.value > required_confirmation.value:
                                required_confirmation = rule.confirmation_type
                                reasons.append(rule.description)
            else:
                # General risk-based rules
                if max_risk.value >= rule.risk_threshold.value:
                    if rule.confirmation_type.value > required_confirmation.value:
                        required_confirmation = rule.confirmation_type
                        reasons.append(rule.description)
        
        if required_confirmation == ConfirmationType.NONE:
            return PolicyDecision.allow("Risk level acceptable")
        
        return PolicyDecision.allow_with_confirmation(
            reason="; ".join(reasons),
            confirmation_type=required_confirmation,
        )

    def _merge_decisions(
        self,
        cap_decision: PolicyDecision,
        risk_decision: PolicyDecision,
    ) -> PolicyDecision:
        """Merges capability and risk assessment decisions."""

        # If capability denied - deny
        if not cap_decision.allowed:
            return cap_decision

        # If risk denied - deny
        if not risk_decision.allowed:
            return risk_decision

        # Merge confirmation requirements
        requires_confirmation = (
            cap_decision.requires_confirmation or 
            risk_decision.requires_confirmation
        )

        # Take the highest confirmation type
        confirmation_type = max(
            cap_decision.confirmation_type,
            risk_decision.confirmation_type,
            key=lambda x: x.value,
        )

        # Merge reasons
        reasons = []
        if cap_decision.reason and cap_decision.reason != "System-level access granted":
            reasons.append(cap_decision.reason)
        if risk_decision.reason and risk_decision.reason != "Risk level acceptable":
            reasons.append(risk_decision.reason)
        
        reason = "; ".join(reasons) if reasons else "Action allowed"
        
        return PolicyDecision(
            allowed=True,
            reason=reason,
            requires_confirmation=requires_confirmation,
            confirmation_type=confirmation_type,
            warnings=cap_decision.warnings + risk_decision.warnings,
        )

    def get_confirmation_phrase(self, plan: ActionPlan) -> str:
        """
        Generate a confirmation phrase.

        For destructive operations, the user must enter this phrase.
        """
        if plan.max_risk != RiskLevel.DESTRUCTIVE:
            return ""

        # Find the first destructive action
        for action in plan.actions:
            if action.risk == RiskLevel.DESTRUCTIVE:
                if action.function_name == "delete_path":
                    path = action.args.get("path", "unknown")
                    return f"DELETE {path}"
        
        return "CONFIRM DELETE"

    def add_rule(self, rule: PolicyRule) -> None:
        """Adds a new rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Removes a rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                self.rules.pop(i)
                return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Activates a rule."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Deactivates a rule."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                return True
        return False


# ============================================
# Pre-execution Validator
# ============================================

class PreExecutionValidator:
    """
    Validator before execution.

    Performs a final check right before executing each action.
    This is the second line of defense after PolicyEngine.
    """

    def __init__(self) -> None:
        self._blocked_paths: Set[str] = {
            "/",
            "/etc",
            "/usr",
            "/bin",
            "/sbin",
            "/boot",
            "C:\\Windows",
            "C:\\Windows\\System32",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
        }
        
        self._blocked_commands: Set[str] = {
            "rm -rf",
            "format",
            "mkfs",
            "dd if=",
            "shutdown",
            "reboot",
            "init 0",
            "init 6",
        }

    def validate_action(self, action: Action) -> PolicyDecision:
        """
        Validates an action before execution.

        Returns:
            PolicyDecision з результатом валідації
        """
        # Check blocked paths
        path = action.args.get("path", "")
        if path and self._is_blocked_path(path):
            return PolicyDecision.deny(
                f"Path '{path}' is in the blocked list for safety"
            )

        # Check blocked commands
        for blocked in self._blocked_commands:
            for value in action.args.values():
                if isinstance(value, str) and blocked in value.lower():
                    return PolicyDecision.deny(
                        f"Command contains blocked pattern: {blocked}"
                    )
        
        return PolicyDecision.allow("Pre-execution validation passed")

    def _is_blocked_path(self, path: str) -> bool:
        """Checks if a path is blocked."""
        from pathlib import Path
        
        try:
            normalized = str(Path(path).resolve())
            for blocked in self._blocked_paths:
                if normalized.lower().startswith(blocked.lower()):
                    return True
        except Exception:
            # If normalization fails, block the path
            return True
        
        return False

    def add_blocked_path(self, path: str) -> None:
        """Adds a path to the blocked list."""
        self._blocked_paths.add(path)

    def remove_blocked_path(self, path: str) -> bool:
        """Removes a path from the blocked list."""
        try:
            self._blocked_paths.remove(path)
            return True
        except KeyError:
            return False
