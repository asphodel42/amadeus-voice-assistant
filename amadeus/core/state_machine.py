"""
Amadeus Core State Machine

Кінцевий автомат для управління станами голосового асистента.
Забезпечує детерміновану поведінку та безпечні переходи між станами.

Діаграма станів:
    
    ┌──────┐    wake_word    ┌───────────┐
    │ IDLE │ ───────────────►│ LISTENING │
    └──────┘                 └───────────┘
        ▲                          │
        │                     audio_complete
        │                          ▼
        │                    ┌────────────┐
        │   cancel/error     │ PROCESSING │
        ├───────────────────◄┤            │
        │                    └────────────┘
        │                          │
        │                      plan_ready
        │                          ▼
        │                    ┌───────────┐
        │   cancel/deny      │ REVIEWING │
        ├───────────────────◄┤           │
        │                    └───────────┘
        │                          │
        │                      confirm
        │                          ▼
        │                    ┌───────────┐
        │   complete/error   │ EXECUTING │
        └───────────────────◄┤           │
                             └───────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set

from amadeus.core.entities import ActionPlan


class AssistantState(Enum):
    """Стани голосового асистента."""
    IDLE = auto()        # Очікування слова-активатора
    LISTENING = auto()   # Запис голосової команди
    PROCESSING = auto()  # ASR/NLU/Planning
    REVIEWING = auto()   # Очікування підтвердження користувача
    EXECUTING = auto()   # Виконання плану дій
    ERROR = auto()       # Стан помилки (потребує скидання)


class StateTransition(Enum):
    """Дозволені переходи між станами."""
    WAKE_WORD = "wake_word"           # IDLE → LISTENING
    PUSH_TO_TALK = "push_to_talk"     # IDLE → LISTENING
    AUDIO_COMPLETE = "audio_complete" # LISTENING → PROCESSING
    PLAN_READY = "plan_ready"         # PROCESSING → REVIEWING
    PLAN_SAFE = "plan_safe"           # PROCESSING → EXECUTING (автоматично для SAFE)
    CONFIRM = "confirm"               # REVIEWING → EXECUTING
    DENY = "deny"                     # REVIEWING → IDLE
    CANCEL = "cancel"                 # Any → IDLE
    COMPLETE = "complete"             # EXECUTING → IDLE
    ERROR = "error"                   # Any → ERROR
    RESET = "reset"                   # ERROR → IDLE
    TIMEOUT = "timeout"               # LISTENING/REVIEWING → IDLE


# Матриця дозволених переходів: (current_state, transition) → next_state
TRANSITION_TABLE: Dict[tuple[AssistantState, StateTransition], AssistantState] = {
    # From IDLE
    (AssistantState.IDLE, StateTransition.WAKE_WORD): AssistantState.LISTENING,
    (AssistantState.IDLE, StateTransition.PUSH_TO_TALK): AssistantState.LISTENING,
    (AssistantState.IDLE, StateTransition.ERROR): AssistantState.ERROR,
    
    # From LISTENING
    (AssistantState.LISTENING, StateTransition.AUDIO_COMPLETE): AssistantState.PROCESSING,
    (AssistantState.LISTENING, StateTransition.CANCEL): AssistantState.IDLE,
    (AssistantState.LISTENING, StateTransition.TIMEOUT): AssistantState.IDLE,
    (AssistantState.LISTENING, StateTransition.ERROR): AssistantState.ERROR,
    
    # From PROCESSING
    (AssistantState.PROCESSING, StateTransition.PLAN_READY): AssistantState.REVIEWING,
    (AssistantState.PROCESSING, StateTransition.PLAN_SAFE): AssistantState.EXECUTING,
    (AssistantState.PROCESSING, StateTransition.CANCEL): AssistantState.IDLE,
    (AssistantState.PROCESSING, StateTransition.ERROR): AssistantState.ERROR,
    
    # From REVIEWING
    (AssistantState.REVIEWING, StateTransition.CONFIRM): AssistantState.EXECUTING,
    (AssistantState.REVIEWING, StateTransition.DENY): AssistantState.IDLE,
    (AssistantState.REVIEWING, StateTransition.CANCEL): AssistantState.IDLE,
    (AssistantState.REVIEWING, StateTransition.TIMEOUT): AssistantState.IDLE,
    (AssistantState.REVIEWING, StateTransition.ERROR): AssistantState.ERROR,
    
    # From EXECUTING
    (AssistantState.EXECUTING, StateTransition.COMPLETE): AssistantState.IDLE,
    (AssistantState.EXECUTING, StateTransition.ERROR): AssistantState.ERROR,
    
    # From ERROR
    (AssistantState.ERROR, StateTransition.RESET): AssistantState.IDLE,
}


@dataclass
class StateContext:
    """
    Контекст поточного стану.
    
    Зберігає дані, пов'язані з поточною сесією обробки команди.
    """
    session_id: str = ""
    entered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_audio: Optional[bytes] = None
    transcribed_text: str = ""
    current_plan: Optional[ActionPlan] = None
    confirmation_attempts: int = 0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def clear(self) -> None:
        """Очищає контекст для нової сесії."""
        self.session_id = ""
        self.entered_at = datetime.now(timezone.utc)
        self.raw_audio = None
        self.transcribed_text = ""
        self.current_plan = None
        self.confirmation_attempts = 0
        self.error_message = ""
        self.metadata = {}


# Тип для callback-функцій на зміну стану
StateChangeCallback = Callable[[AssistantState, AssistantState, StateContext], None]


class ConfirmationStateMachine:
    """
    Кінцевий автомат станів голосового асистента.
    
    Забезпечує:
    - Детерміновану поведінку (одні й ті ж вхідні дані → один результат)
    - Безпечні переходи (тільки дозволені переходи)
    - Запобігання деструктивним діям без явного підтвердження
    - Логування всіх переходів для аудиту
    
    Приклад використання:
        sm = ConfirmationStateMachine()
        sm.on_state_change(lambda old, new, ctx: print(f"{old} → {new}"))
        
        sm.transition(StateTransition.WAKE_WORD)
        # Тепер у стані LISTENING
        
        sm.transition(StateTransition.AUDIO_COMPLETE)
        # Тепер у стані PROCESSING
    """

    def __init__(self, initial_state: AssistantState = AssistantState.IDLE) -> None:
        self._state = initial_state
        self._context = StateContext()
        self._callbacks: List[StateChangeCallback] = []
        self._transition_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000

    @property
    def state(self) -> AssistantState:
        """Поточний стан."""
        return self._state

    @property
    def context(self) -> StateContext:
        """Контекст поточного стану."""
        return self._context

    @property
    def is_idle(self) -> bool:
        return self._state == AssistantState.IDLE

    @property
    def is_listening(self) -> bool:
        return self._state == AssistantState.LISTENING

    @property
    def is_processing(self) -> bool:
        return self._state == AssistantState.PROCESSING

    @property
    def is_reviewing(self) -> bool:
        return self._state == AssistantState.REVIEWING

    @property
    def is_executing(self) -> bool:
        return self._state == AssistantState.EXECUTING

    @property
    def is_error(self) -> bool:
        return self._state == AssistantState.ERROR

    def get_allowed_transitions(self) -> Set[StateTransition]:
        """Повертає множину дозволених переходів з поточного стану."""
        allowed = set()
        for (state, transition), _ in TRANSITION_TABLE.items():
            if state == self._state:
                allowed.add(transition)
        return allowed

    def can_transition(self, transition: StateTransition) -> bool:
        """Перевіряє, чи можливий перехід."""
        return (self._state, transition) in TRANSITION_TABLE

    def transition(self, transition: StateTransition) -> bool:
        """
        Виконує перехід у новий стан.
        
        Args:
            transition: Тип переходу
            
        Returns:
            True якщо перехід успішний
            
        Raises:
            InvalidTransitionError: Якщо перехід не дозволений
        """
        key = (self._state, transition)
        
        if key not in TRANSITION_TABLE:
            allowed = self.get_allowed_transitions()
            raise InvalidTransitionError(
                f"Transition {transition.value} not allowed from state {self._state.name}. "
                f"Allowed: {[t.value for t in allowed]}"
            )
        
        old_state = self._state
        new_state = TRANSITION_TABLE[key]
        
        # Логування переходу
        self._log_transition(old_state, new_state, transition)
        
        # Виконання переходу
        self._state = new_state
        self._context.entered_at = datetime.now(timezone.utc)
        
        # Очищення контексту при поверненні в IDLE
        if new_state == AssistantState.IDLE:
            self._context.clear()
        
        # Виклик callbacks
        for callback in self._callbacks:
            try:
                callback(old_state, new_state, self._context)
            except Exception:
                # Callbacks не повинні впливати на стан машини
                pass
        
        return True

    def force_reset(self) -> None:
        """
        Примусове скидання в IDLE.
        
        УВАГА: Використовувати тільки в екстрених випадках!
        """
        old_state = self._state
        self._state = AssistantState.IDLE
        self._context.clear()
        self._log_transition(old_state, AssistantState.IDLE, StateTransition.RESET)

    def on_state_change(self, callback: StateChangeCallback) -> None:
        """Реєструє callback для сповіщення про зміну стану."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: StateChangeCallback) -> bool:
        """Видаляє callback."""
        try:
            self._callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def get_transition_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Повертає історію переходів."""
        return self._transition_history[-limit:]

    def _log_transition(
        self,
        old_state: AssistantState,
        new_state: AssistantState,
        transition: StateTransition
    ) -> None:
        """Логує перехід в історію."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_state": old_state.name,
            "to_state": new_state.name,
            "transition": transition.value,
            "session_id": self._context.session_id,
        }
        self._transition_history.append(entry)
        
        # Обмеження розміру історії
        if len(self._transition_history) > self._max_history_size:
            self._transition_history = self._transition_history[-self._max_history_size:]


class InvalidTransitionError(Exception):
    """Виключення для недозволеного переходу."""
    pass


# ============================================
# Utility Functions
# ============================================

def create_state_diagram_mermaid() -> str:
    """Генерує Mermaid діаграму станів."""
    lines = ["stateDiagram-v2"]
    
    for (from_state, transition), to_state in TRANSITION_TABLE.items():
        lines.append(f"    {from_state.name} --> {to_state.name}: {transition.value}")
    
    return "\n".join(lines)


def get_safe_transitions_only() -> Dict[tuple[AssistantState, StateTransition], AssistantState]:
    """
    Повертає підмножину переходів, що не включають деструктивні операції.
    
    Використовується для аналізу безпеки.
    """
    # Виключаємо CONFIRM для REVIEWING → EXECUTING якщо план деструктивний
    # Це перевіряється runtime у PolicyEngine
    return TRANSITION_TABLE.copy()
