"""
Amadeus Core Policy Engine

Двигун політик безпеки — відповідає за авторизацію дій.
Перевіряє ActionPlan проти Capabilities та правил ризику.

Принципи Zero-Trust:
1. Всі дії перевіряються перед виконанням
2. Можливості (capabilities) явно декларуються
3. Високоризикові дії потребують підтвердження
4. Деструктивні дії потребують typed confirmation
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
    """Типи підтвердження."""
    NONE = auto()           # Не потрібне
    SIMPLE = auto()         # Просте Yes/No
    TYPED = auto()          # Введення підтверджувальної фрази
    PASSCODE = auto()       # Введення пароля/PIN (майбутнє)


@dataclass(frozen=True)
class PolicyDecision:
    """
    Результат оцінки політики.
    
    Attributes:
        allowed: Чи дозволено виконання
        reason: Причина рішення
        requires_confirmation: Чи потрібне підтвердження
        confirmation_type: Тип підтвердження
        denied_actions: Список заборонених дій (якщо є)
    """
    allowed: bool
    reason: str
    requires_confirmation: bool = False
    confirmation_type: ConfirmationType = ConfirmationType.NONE
    denied_actions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @staticmethod
    def allow(reason: str = "Action allowed") -> "PolicyDecision":
        """Створює дозвіл без підтвердження."""
        return PolicyDecision(allowed=True, reason=reason)

    @staticmethod
    def allow_with_confirmation(
        reason: str,
        confirmation_type: ConfirmationType = ConfirmationType.SIMPLE
    ) -> "PolicyDecision":
        """Створює дозвіл з підтвердженням."""
        return PolicyDecision(
            allowed=True,
            reason=reason,
            requires_confirmation=True,
            confirmation_type=confirmation_type,
        )

    @staticmethod
    def deny(reason: str, denied_actions: Optional[List[str]] = None) -> "PolicyDecision":
        """Створює відмову."""
        return PolicyDecision(
            allowed=False,
            reason=reason,
            denied_actions=denied_actions or [],
        )


@dataclass
class PolicyRule:
    """
    Правило політики безпеки.
    
    Attributes:
        rule_id: Ідентифікатор правила
        description: Опис правила
        scope: Область застосування (опціонально)
        risk_threshold: Мінімальний рівень ризику для спрацювання
        confirmation_type: Тип підтвердження при спрацюванні
        enabled: Чи активне правило
    """
    rule_id: str
    description: str
    scope: Optional[CapabilityScope] = None
    risk_threshold: RiskLevel = RiskLevel.HIGH
    confirmation_type: ConfirmationType = ConfirmationType.SIMPLE
    enabled: bool = True


# Стандартні правила безпеки
DEFAULT_POLICY_RULES: List[PolicyRule] = [
    PolicyRule(
        rule_id="destructive_confirmation",
        description="Деструктивні операції потребують typed confirmation",
        risk_threshold=RiskLevel.DESTRUCTIVE,
        confirmation_type=ConfirmationType.TYPED,
    ),
    PolicyRule(
        rule_id="high_risk_confirmation",
        description="Високоризикові операції потребують простого підтвердження",
        risk_threshold=RiskLevel.HIGH,
        confirmation_type=ConfirmationType.SIMPLE,
    ),
    PolicyRule(
        rule_id="fs_delete_always_confirm",
        description="Видалення файлів завжди потребує typed confirmation",
        scope=CapabilityScope.FS_DELETE,
        risk_threshold=RiskLevel.SAFE,  # Завжди, незалежно від ризику
        confirmation_type=ConfirmationType.TYPED,
    ),
    PolicyRule(
        rule_id="fs_write_confirm",
        description="Запис у файли потребує підтвердження",
        scope=CapabilityScope.FS_WRITE,
        risk_threshold=RiskLevel.SAFE,
        confirmation_type=ConfirmationType.SIMPLE,
    ),
]


class PolicyEngine:
    """
    Двигун політик безпеки.
    
    Виконує двоетапну перевірку:
    1. Capability Check: чи має навичка право на операцію
    2. Risk Assessment: який рівень підтвердження потрібен
    
    Приклад використання:
        engine = PolicyEngine()
        decision = engine.evaluate(plan, skill_capabilities)
        
        if decision.allowed:
            if decision.requires_confirmation:
                # Показати діалог підтвердження
                pass
            else:
                # Виконати автоматично
                pass
        else:
            # Відмовити з поясненням
            print(decision.reason)
    """

    def __init__(self, rules: Optional[List[PolicyRule]] = None) -> None:
        self.rules = rules or DEFAULT_POLICY_RULES.copy()
        
        # Mapping: function_name → required capability scope
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
        Оцінює план дій.
        
        Args:
            plan: План для оцінки
            capabilities: Доступні можливості (якщо None — системні defaults)
            context: Додатковий контекст (user, session, etc.)
            
        Returns:
            Рішення політики
        """
        if plan.is_empty:
            return PolicyDecision.allow("Empty plan, nothing to execute")
        
        # Етап 1: Перевірка capabilities
        capability_result = self._check_capabilities(plan, capabilities)
        if not capability_result.allowed:
            return capability_result
        
        # Етап 2: Оцінка ризиків
        risk_result = self._assess_risk(plan)
        
        # Об'єднуємо результати
        return self._merge_decisions(capability_result, risk_result)

    def _check_capabilities(
        self,
        plan: ActionPlan,
        capabilities: Optional[List[Capability]],
    ) -> PolicyDecision:
        """Перевіряє, чи всі дії дозволені capabilities."""
        
        # Якщо capabilities не вказані — дозволяємо (системний рівень)
        if capabilities is None:
            return PolicyDecision.allow("System-level access granted")
        
        denied_actions: List[str] = []
        warnings: List[str] = []
        
        for action in plan.actions:
            required_scope = self._function_to_scope.get(action.function_name)
            
            if required_scope is None:
                # Невідома функція — попередження
                warnings.append(f"Unknown function: {action.function_name}")
                continue
            
            # Шукаємо відповідну capability
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
            
            # Перевіряємо constraints (наприклад, allowed_paths)
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
        
        # Застосовуємо правила
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # Перевіряємо scope-specific правила
            if rule.scope is not None:
                for action in plan.actions:
                    action_scope = self._function_to_scope.get(action.function_name)
                    if action_scope == rule.scope:
                        if action.risk.value >= rule.risk_threshold.value:
                            if rule.confirmation_type.value > required_confirmation.value:
                                required_confirmation = rule.confirmation_type
                                reasons.append(rule.description)
            else:
                # Загальні правила за рівнем ризику
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
        """Об'єднує рішення capability та risk assessment."""
        
        # Якщо capability denied — відмовляємо
        if not cap_decision.allowed:
            return cap_decision
        
        # Якщо risk denied — відмовляємо
        if not risk_decision.allowed:
            return risk_decision
        
        # Об'єднуємо вимоги до підтвердження
        requires_confirmation = (
            cap_decision.requires_confirmation or 
            risk_decision.requires_confirmation
        )
        
        # Беремо вищий тип підтвердження
        confirmation_type = max(
            cap_decision.confirmation_type,
            risk_decision.confirmation_type,
            key=lambda x: x.value,
        )
        
        # Об'єднуємо причини
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
        Генерує фразу для typed confirmation.
        
        Для деструктивних операцій користувач повинен ввести цю фразу.
        """
        if plan.max_risk != RiskLevel.DESTRUCTIVE:
            return ""
        
        # Знаходимо першу деструктивну дію
        for action in plan.actions:
            if action.risk == RiskLevel.DESTRUCTIVE:
                if action.function_name == "delete_path":
                    path = action.args.get("path", "unknown")
                    return f"DELETE {path}"
        
        return "CONFIRM DELETE"

    def add_rule(self, rule: PolicyRule) -> None:
        """Додає нове правило."""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Видаляє правило за ID."""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                self.rules.pop(i)
                return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Активує правило."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Деактивує правило."""
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
    Валідатор перед виконанням.
    
    Виконує фінальну перевірку безпосередньо перед виконанням кожної дії.
    Це друга лінія захисту після PolicyEngine.
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
        Валідує окрему дію перед виконанням.
        
        Returns:
            PolicyDecision з результатом валідації
        """
        # Перевірка заблокованих шляхів
        path = action.args.get("path", "")
        if path and self._is_blocked_path(path):
            return PolicyDecision.deny(
                f"Path '{path}' is in the blocked list for safety"
            )
        
        # Перевірка заблокованих команд
        for blocked in self._blocked_commands:
            for value in action.args.values():
                if isinstance(value, str) and blocked in value.lower():
                    return PolicyDecision.deny(
                        f"Command contains blocked pattern: {blocked}"
                    )
        
        return PolicyDecision.allow("Pre-execution validation passed")

    def _is_blocked_path(self, path: str) -> bool:
        """Перевіряє, чи шлях заблокований."""
        from pathlib import Path
        
        try:
            normalized = str(Path(path).resolve())
            for blocked in self._blocked_paths:
                if normalized.lower().startswith(blocked.lower()):
                    return True
        except Exception:
            # При помилці нормалізації — блокуємо
            return True
        
        return False

    def add_blocked_path(self, path: str) -> None:
        """Додає шлях до списку заблокованих."""
        self._blocked_paths.add(path)

    def remove_blocked_path(self, path: str) -> bool:
        """Видаляє шлях зі списку заблокованих."""
        try:
            self._blocked_paths.remove(path)
            return True
        except KeyError:
            return False
