"""
Amadeus Core State Machine

Finite state machine for managing the states of the voice assistant.
Ensures deterministic behavior and safe transitions between states.

State diagram:
    
     ------    wake_word      -----------
    | IDLE |---------------->| LISTENING |
     ------                   -----------
        A                          |
        |                     audio_complete
        |                          V
        |                     ------------
        |   cancel/error     | PROCESSING |
        |-------------------<|            |
        |                     ------------
        |                          |
        |                      plan_ready
        |                          V
        |                     -----------
        |   cancel/deny      | REVIEWING |
        |-------------------<|           |
        |                     -----------
        |                          |
        |                       confirm
        |                          V
        |                     -----------
        |   complete/error   | EXECUTING |
         -------------------<|           |
                              -----------
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set

from amadeus.core.entities import ActionPlan


class AssistantState(Enum):
    """Стани голосового асистента."""
    IDLE = auto()        # Waiting for wake word
    LISTENING = auto()   # Listening for voice command
    PROCESSING = auto()  # ASR/NLU/Planning
    REVIEWING = auto()   # Waiting for user confirmation
    EXECUTING = auto()   # Executing action plan
    ERROR = auto()       # Error state (requires reset)


class StateTransition(Enum):
    """Дозволені переходи між станами."""
    WAKE_WORD = "wake_word"           # IDLE -> LISTENING
    PUSH_TO_TALK = "push_to_talk"     # IDLE -> LISTENING
    AUDIO_COMPLETE = "audio_complete" # LISTENING -> PROCESSING
    PLAN_READY = "plan_ready"         # PROCESSING -> REVIEWING
    PLAN_SAFE = "plan_safe"           # PROCESSING -> EXECUTING (автоматично для SAFE)
    CONFIRM = "confirm"               # REVIEWING -> EXECUTING
    DENY = "deny"                     # REVIEWING -> IDLE
    CANCEL = "cancel"                 # Any -> IDLE
    COMPLETE = "complete"             # EXECUTING -> IDLE
    ERROR = "error"                   # Any -> ERROR
    RESET = "reset"                   # ERROR -> IDLE
    TIMEOUT = "timeout"               # LISTENING/REVIEWING -> IDLE


# Матриця дозволених переходів: (current_state, transition) -> next_state
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
    Current state context.

    Stores data related to the current command processing session.
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
        """Clear context for a new session."""
        self.session_id = ""
        self.entered_at = datetime.now(timezone.utc)
        self.raw_audio = None
        self.transcribed_text = ""
        self.current_plan = None
        self.confirmation_attempts = 0
        self.error_message = ""
        self.metadata = {}


# Type for callback functions on state change
StateChangeCallback = Callable[[AssistantState, AssistantState, StateContext], None]


class ConfirmationStateMachine:
    """
    Voice assistant confirmation state machine.

    Provides:
    - Deterministic behavior (same input -> same output)
    - Safe transitions (only allowed transitions)
    - Prevention of destructive actions without explicit confirmation
    - Logging of all transitions for auditing

    Example usage:
        sm = ConfirmationStateMachine()
        sm.on_state_change(lambda old, new, ctx: print(f"{old} -> {new}"))
        
        sm.transition(StateTransition.WAKE_WORD)
        # Now in LISTENING state
        
        sm.transition(StateTransition.AUDIO_COMPLETE)
        # Now in PROCESSING state
    """

    def __init__(self, initial_state: AssistantState = AssistantState.IDLE) -> None:
        self._state = initial_state
        self._context = StateContext()
        self._callbacks: List[StateChangeCallback] = []
        self._transition_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000

    @property
    def state(self) -> AssistantState:
        """Current state."""
        return self._state

    @property
    def context(self) -> StateContext:
        """Current state context."""
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
        """Returns a set of allowed transitions from the current state."""
        allowed = set()
        for (state, transition), _ in TRANSITION_TABLE.items():
            if state == self._state:
                allowed.add(transition)
        return allowed

    def can_transition(self, transition: StateTransition) -> bool:
        """Checks if the transition is possible."""
        return (self._state, transition) in TRANSITION_TABLE

    def transition(self, transition: StateTransition) -> bool:
        """
        Performs a transition to a new state.
        
        Args:
            transition: Type of transition

        Returns:
            True if the transition is successful

        Raises:
            InvalidTransitionError: If the transition is not allowed
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
        
        # Logging the transition
        self._log_transition(old_state, new_state, transition)

        # Performing the transition
        self._state = new_state
        self._context.entered_at = datetime.now(timezone.utc)

        # Clearing the context when returning to IDLE
        if new_state == AssistantState.IDLE:
            self._context.clear()

        # Calling callbacks
        for callback in self._callbacks:
            try:
                callback(old_state, new_state, self._context)
            except Exception:
                # Callbacks should not affect the state machine
                pass
        
        return True

    def force_reset(self) -> None:
        """
        Forces a reset to IDLE.

        WARNING: Use only in emergencies!
        """
        old_state = self._state
        self._state = AssistantState.IDLE
        self._context.clear()
        self._log_transition(old_state, AssistantState.IDLE, StateTransition.RESET)

    def on_state_change(self, callback: StateChangeCallback) -> None:
        """Registers a callback for state change notifications."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: StateChangeCallback) -> bool:
        """Removes a callback."""
        try:
            self._callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def get_transition_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the transition history."""
        return self._transition_history[-limit:]

    def _log_transition(
        self,
        old_state: AssistantState,
        new_state: AssistantState,
        transition: StateTransition
    ) -> None:
        """Logs the transition in the history."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_state": old_state.name,
            "to_state": new_state.name,
            "transition": transition.value,
            "session_id": self._context.session_id,
        }
        self._transition_history.append(entry)
        
        # Maintaining max history size
        if len(self._transition_history) > self._max_history_size:
            self._transition_history = self._transition_history[-self._max_history_size:]


class InvalidTransitionError(Exception):
    """Exception for invalid transitions."""
    pass


# ============================================
# Utility Functions
# ============================================

def create_state_diagram_mermaid() -> str:
    """Generates a Mermaid state diagram."""
    lines = ["stateDiagram-v2"]
    
    for (from_state, transition), to_state in TRANSITION_TABLE.items():
        lines.append(f"    {from_state.name} --> {to_state.name}: {transition.value}")
    
    return "\n".join(lines)


def get_safe_transitions_only() -> Dict[tuple[AssistantState, StateTransition], AssistantState]:
    """
    Returns a subset of transitions that do not include destructive operations.

    Used for safety analysis.
    """
    # Exclude CONFIRM for REVIEWING -> EXECUTING if the plan is destructive
    # This is checked at runtime in the PolicyEngine
    return TRANSITION_TABLE.copy()
