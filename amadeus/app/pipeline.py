"""
Amadeus Voice Pipeline

Головний оркестратор обробки голосових команд.
Координує всі етапи: Wake → ASR → NLU → Plan → Policy → Confirm → Execute → Respond

Принципи:
- Детермінована поведінка через State Machine
- Кожен етап ізольований та тестований
- Явне логування для аудиту
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from amadeus.core.entities import (
    ActionPlan,
    AuditEvent,
    CommandRequest,
    ExecutionResult,
    ExecutionStatus,
    Intent,
    IntentType,
)
from amadeus.core.planner import Planner, PlanRenderer
from amadeus.core.policy import PolicyDecision, PolicyEngine
from amadeus.core.state_machine import (
    AssistantState,
    ConfirmationStateMachine,
    StateTransition,
)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Конфігурація пайплайну."""
    
    # Таймаути
    listening_timeout_seconds: float = 10.0
    confirmation_timeout_seconds: float = 30.0
    execution_timeout_seconds: float = 60.0
    
    # Режими
    dry_run_by_default: bool = False
    auto_confirm_safe: bool = True
    require_wake_word: bool = True
    
    # Логування
    log_all_events: bool = True
    verbose_logging: bool = False


@dataclass
class PipelineResult:
    """Результат обробки команди."""
    
    success: bool
    request: Optional[CommandRequest] = None
    intent: Optional[Intent] = None
    plan: Optional[ActionPlan] = None
    decision: Optional[PolicyDecision] = None
    results: List[ExecutionResult] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: float = 0.0

    @property
    def is_unknown_intent(self) -> bool:
        return self.intent is not None and self.intent.is_unknown


# Типи для callbacks
PipelineCallback = Callable[["VoicePipeline", str, Any], None]


class VoicePipeline:
    """
    Головний пайплайн обробки голосових команд.
    
    Послідовність обробки:
    1. Wake Word Detection (опціонально)
    2. Audio Recording
    3. ASR (Speech-to-Text)
    4. NLU (Intent Recognition)
    5. Planning (Intent → ActionPlan)
    6. Policy Evaluation (Security Check)
    7. Confirmation (якщо потрібно)
    8. Execution
    9. Response
    
    Приклад використання:
        pipeline = VoicePipeline()
        
        # Реєструємо callbacks
        pipeline.on("plan_ready", lambda p, e, d: show_plan(d))
        pipeline.on("confirmation_needed", lambda p, e, d: ask_user(d))
        
        # Обробляємо текстову команду (для тестування)
        result = pipeline.process_text("open calculator")
        
        if result.success:
            print(f"Executed: {result.plan.to_preview_text()}")
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        planner: Optional[Planner] = None,
        policy_engine: Optional[PolicyEngine] = None,
    ) -> None:
        self.config = config or PipelineConfig()
        self.state_machine = ConfirmationStateMachine()
        self.planner = planner or Planner()
        self.policy_engine = policy_engine or PolicyEngine()
        
        # Callbacks для різних подій
        self._callbacks: Dict[str, List[PipelineCallback]] = {}
        
        # Адаптери (ініціалізуються лениво)
        self._nlu = None
        self._os_adapter = None
        self._audit = None
        
        # Лічильник сесій
        self._session_counter = 0

    # ============================================
    # Public API
    # ============================================

    def process_text(
        self,
        text: str,
        dry_run: bool = False,
        skip_confirmation: bool = False,
    ) -> PipelineResult:
        """
        Обробляє текстову команду (bypass ASR).
        
        Використовується для тестування та текстового вводу.
        
        Args:
            text: Текст команди
            dry_run: Якщо True, тільки симуляція без виконання
            skip_confirmation: Пропустити підтвердження (для тестів)
            
        Returns:
            Результат обробки
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Створюємо запит
            request = CommandRequest(
                request_id=self._generate_session_id(),
                raw_text=text,
                source="text_input",
            )
            
            # Логуємо початок
            self._emit("command_received", {"request": request})
            self._log_audit("command_received", request=request)
            
            # NLU
            intent = self._parse_intent(text)
            self._emit("intent_recognized", {"intent": intent})
            
            if intent.is_unknown:
                return PipelineResult(
                    success=False,
                    request=request,
                    intent=intent,
                    error="Could not understand the command",
                    duration_ms=self._calc_duration(start_time),
                )
            
            # Planning
            plan = self.planner.create_plan(intent)
            plan = ActionPlan(
                plan_id=plan.plan_id,
                intent=plan.intent,
                actions=plan.actions,
                requires_confirmation=plan.requires_confirmation,
                dry_run=dry_run or self.config.dry_run_by_default,
                created_at=plan.created_at,
            )
            self._emit("plan_ready", {"plan": plan})
            
            if plan.is_empty:
                return PipelineResult(
                    success=False,
                    request=request,
                    intent=intent,
                    plan=plan,
                    error="No actions planned for this command",
                    duration_ms=self._calc_duration(start_time),
                )
            
            # Policy Evaluation
            decision = self.policy_engine.evaluate(plan)
            self._emit("policy_evaluated", {"decision": decision})
            
            if not decision.allowed:
                self._log_audit("policy_denied", request=request, plan=plan)
                return PipelineResult(
                    success=False,
                    request=request,
                    intent=intent,
                    plan=plan,
                    decision=decision,
                    error=f"Policy denied: {decision.reason}",
                    duration_ms=self._calc_duration(start_time),
                )
            
            # Confirmation (якщо потрібно)
            if decision.requires_confirmation and not skip_confirmation:
                self._emit("confirmation_needed", {
                    "plan": plan,
                    "decision": decision,
                })
                # У реальному UI тут буде очікування відповіді
                # Для тестів — автоматично підтверджуємо
                logger.info(f"Confirmation required for plan: {plan.plan_id}")
            
            # Execution
            if not plan.dry_run:
                results = self._execute_plan(plan)
            else:
                results = self._simulate_plan(plan)
            
            self._emit("execution_complete", {"results": results})
            self._log_audit("execution_complete", request=request, plan=plan)
            
            # Перевіряємо успішність
            all_success = all(r.is_success for r in results)
            
            return PipelineResult(
                success=all_success,
                request=request,
                intent=intent,
                plan=plan,
                decision=decision,
                results=results,
                duration_ms=self._calc_duration(start_time),
            )
            
        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            self._emit("error", {"error": str(e)})
            return PipelineResult(
                success=False,
                error=str(e),
                duration_ms=self._calc_duration(start_time),
            )

    def get_state(self) -> AssistantState:
        """Повертає поточний стан асистента."""
        return self.state_machine.state

    def reset(self) -> None:
        """Скидає стан пайплайну."""
        self.state_machine.force_reset()
        self._emit("reset", {})

    # ============================================
    # Event System
    # ============================================

    def on(self, event: str, callback: PipelineCallback) -> None:
        """
        Реєструє callback для події.
        
        Події:
        - command_received: Отримано команду
        - intent_recognized: Розпізнано намір
        - plan_ready: Готовий план дій
        - policy_evaluated: Оцінено політику
        - confirmation_needed: Потрібне підтвердження
        - execution_complete: Виконання завершено
        - error: Помилка
        - reset: Скидання стану
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def off(self, event: str, callback: PipelineCallback) -> bool:
        """Видаляє callback."""
        if event in self._callbacks:
            try:
                self._callbacks[event].remove(callback)
                return True
            except ValueError:
                pass
        return False

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        """Викликає всі callbacks для події."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(self, event, data)
                except Exception as e:
                    logger.error(f"Callback error for event '{event}': {e}")

    # ============================================
    # Internal Methods
    # ============================================

    def _parse_intent(self, text: str) -> Intent:
        """Парсить текст у Intent."""
        if self._nlu is None:
            from amadeus.adapters.voice.nlu import DeterministicNLU
            self._nlu = DeterministicNLU()
        
        return self._nlu.parse(text)

    def _execute_plan(self, plan: ActionPlan) -> List[ExecutionResult]:
        """Виконує план дій."""
        from amadeus.app.executor import ActionExecutor
        
        if self._os_adapter is None:
            from amadeus.adapters.os import get_os_adapter
            self._os_adapter = get_os_adapter()
        
        executor = ActionExecutor(self._os_adapter)
        return executor.execute_plan(plan)

    def _simulate_plan(self, plan: ActionPlan) -> List[ExecutionResult]:
        """Симулює план (dry run)."""
        results = []
        for action in plan.actions:
            results.append(ExecutionResult(
                action=action,
                status=ExecutionStatus.DRY_RUN,
                output=f"[DRY RUN] Would execute: {action.to_human_readable()}",
            ))
        return results

    def _log_audit(
        self,
        event_type: str,
        request: Optional[CommandRequest] = None,
        plan: Optional[ActionPlan] = None,
    ) -> None:
        """Логує подію в аудит."""
        if not self.config.log_all_events:
            return
        
        if self._audit is None:
            try:
                from amadeus.adapters.persistence.audit import SQLiteAuditAdapter
                self._audit = SQLiteAuditAdapter()
            except Exception as e:
                logger.warning(f"Could not initialize audit log: {e}")
                return
        
        event = AuditEvent(
            event_type=event_type,
            actor="user",
            command_request=request,
            plan=plan,
        )
        
        try:
            self._audit.append_event(event)
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    def _generate_session_id(self) -> str:
        """Генерує унікальний ID сесії."""
        self._session_counter += 1
        return f"session-{self._session_counter}-{uuid.uuid4().hex[:8]}"

    def _calc_duration(self, start_time: datetime) -> float:
        """Обчислює тривалість у мілісекундах."""
        delta = datetime.now(timezone.utc) - start_time
        return delta.total_seconds() * 1000


# ============================================
# Convenience Functions
# ============================================

def create_pipeline(
    dry_run: bool = False,
    verbose: bool = False,
) -> VoicePipeline:
    """
    Створює налаштований пайплайн.
    
    Args:
        dry_run: Режим симуляції
        verbose: Детальне логування
        
    Returns:
        Налаштований VoicePipeline
    """
    config = PipelineConfig(
        dry_run_by_default=dry_run,
        verbose_logging=verbose,
    )
    return VoicePipeline(config=config)
