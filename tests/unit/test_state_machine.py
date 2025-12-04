"""
Unit Tests for State Machine

Тести для кінцевого автомата станів.
"""

import pytest

from amadeus.core.state_machine import (
    AssistantState,
    ConfirmationStateMachine,
    InvalidTransitionError,
    StateTransition,
)


class TestConfirmationStateMachine:
    """Тести для ConfirmationStateMachine."""
    
    def test_initial_state(self):
        """Перевіряє початковий стан."""
        sm = ConfirmationStateMachine()
        
        assert sm.state == AssistantState.IDLE
        assert sm.is_idle
    
    def test_custom_initial_state(self):
        """Перевіряє кастомний початковий стан."""
        sm = ConfirmationStateMachine(initial_state=AssistantState.LISTENING)
        
        assert sm.state == AssistantState.LISTENING
        assert sm.is_listening
    
    def test_wake_word_transition(self):
        """Перевіряє перехід по wake word."""
        sm = ConfirmationStateMachine()
        
        assert sm.can_transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.WAKE_WORD)
        
        assert sm.state == AssistantState.LISTENING
    
    def test_full_flow(self):
        """Перевіряє повний потік: IDLE → LISTENING → PROCESSING → REVIEWING → EXECUTING → IDLE."""
        sm = ConfirmationStateMachine()
        
        # IDLE → LISTENING
        sm.transition(StateTransition.WAKE_WORD)
        assert sm.is_listening
        
        # LISTENING → PROCESSING
        sm.transition(StateTransition.AUDIO_COMPLETE)
        assert sm.is_processing
        
        # PROCESSING → REVIEWING (план потребує підтвердження)
        sm.transition(StateTransition.PLAN_READY)
        assert sm.is_reviewing
        
        # REVIEWING → EXECUTING
        sm.transition(StateTransition.CONFIRM)
        assert sm.is_executing
        
        # EXECUTING → IDLE
        sm.transition(StateTransition.COMPLETE)
        assert sm.is_idle
    
    def test_auto_execute_safe_plan(self):
        """Перевіряє автоматичне виконання безпечного плану."""
        sm = ConfirmationStateMachine()
        
        # IDLE → LISTENING → PROCESSING
        sm.transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.AUDIO_COMPLETE)
        
        # PROCESSING → EXECUTING (безпечний план, без підтвердження)
        sm.transition(StateTransition.PLAN_SAFE)
        assert sm.is_executing
        
        sm.transition(StateTransition.COMPLETE)
        assert sm.is_idle
    
    def test_cancel_from_listening(self):
        """Перевіряє скасування з режиму прослуховування."""
        sm = ConfirmationStateMachine()
        
        sm.transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.CANCEL)
        
        assert sm.is_idle
    
    def test_deny_in_reviewing(self):
        """Перевіряє відмову в режимі перегляду."""
        sm = ConfirmationStateMachine()
        
        sm.transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.AUDIO_COMPLETE)
        sm.transition(StateTransition.PLAN_READY)
        
        assert sm.is_reviewing
        
        sm.transition(StateTransition.DENY)
        assert sm.is_idle
    
    def test_timeout_in_listening(self):
        """Перевіряє таймаут у режимі прослуховування."""
        sm = ConfirmationStateMachine()
        
        sm.transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.TIMEOUT)
        
        assert sm.is_idle
    
    def test_error_transition(self):
        """Перевіряє перехід у стан помилки."""
        sm = ConfirmationStateMachine()
        
        sm.transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.ERROR)
        
        assert sm.is_error
    
    def test_reset_from_error(self):
        """Перевіряє скидання зі стану помилки."""
        sm = ConfirmationStateMachine()
        
        sm.transition(StateTransition.ERROR)
        assert sm.is_error
        
        sm.transition(StateTransition.RESET)
        assert sm.is_idle
    
    def test_invalid_transition(self):
        """Перевіряє недозволений перехід."""
        sm = ConfirmationStateMachine()
        
        # IDLE → CONFIRM (неможливо)
        with pytest.raises(InvalidTransitionError):
            sm.transition(StateTransition.CONFIRM)
    
    def test_get_allowed_transitions(self):
        """Перевіряє отримання дозволених переходів."""
        sm = ConfirmationStateMachine()
        
        allowed = sm.get_allowed_transitions()
        
        assert StateTransition.WAKE_WORD in allowed
        assert StateTransition.PUSH_TO_TALK in allowed
        assert StateTransition.CONFIRM not in allowed
    
    def test_callback_on_transition(self):
        """Перевіряє callback при переході."""
        sm = ConfirmationStateMachine()
        
        transitions = []
        
        def callback(old_state, new_state, context):
            transitions.append((old_state, new_state))
        
        sm.on_state_change(callback)
        
        sm.transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.AUDIO_COMPLETE)
        
        assert len(transitions) == 2
        assert transitions[0] == (AssistantState.IDLE, AssistantState.LISTENING)
        assert transitions[1] == (AssistantState.LISTENING, AssistantState.PROCESSING)
    
    def test_remove_callback(self):
        """Перевіряє видалення callback."""
        sm = ConfirmationStateMachine()
        calls = []
        
        def callback(old, new, ctx):
            calls.append(1)
        
        sm.on_state_change(callback)
        sm.transition(StateTransition.WAKE_WORD)
        
        assert len(calls) == 1
        
        sm.remove_callback(callback)
        sm.transition(StateTransition.AUDIO_COMPLETE)
        
        assert len(calls) == 1  # Не збільшилось
    
    def test_force_reset(self):
        """Перевіряє примусове скидання."""
        sm = ConfirmationStateMachine()
        
        sm.transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.AUDIO_COMPLETE)
        
        sm.force_reset()
        
        assert sm.is_idle
    
    def test_transition_history(self):
        """Перевіряє історію переходів."""
        sm = ConfirmationStateMachine()
        
        sm.transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.AUDIO_COMPLETE)
        
        history = sm.get_transition_history()
        
        assert len(history) == 2
        assert history[0]["from_state"] == "IDLE"
        assert history[0]["to_state"] == "LISTENING"
    
    def test_context_cleared_on_idle(self):
        """Перевіряє очищення контексту при поверненні в IDLE."""
        sm = ConfirmationStateMachine()
        
        sm.context.transcribed_text = "test command"
        
        sm.transition(StateTransition.WAKE_WORD)
        sm.transition(StateTransition.CANCEL)
        
        assert sm.context.transcribed_text == ""
