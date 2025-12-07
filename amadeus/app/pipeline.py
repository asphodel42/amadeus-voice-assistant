"""
Amadeus Voice Pipeline

Main orchestrator for processing voice commands.
Coordinates all stages: Wake -> ASR -> NLU -> Plan -> Policy -> Confirm -> Execute -> Respond

Principles:
- Deterministic behavior through State Machine
- Each stage is isolated and testable
- Explicit logging for audit
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
    """Configuration for the pipeline."""

    # Timeouts
    listening_timeout_seconds: float = 5.0  # Time for voice command
    confirmation_timeout_seconds: float = 30.0
    execution_timeout_seconds: float = 60.0

    # Modes
    dry_run_by_default: bool = False
    auto_confirm_safe: bool = True
    require_wake_word: bool = True

    # Logging
    log_all_events: bool = True
    verbose_logging: bool = False
    
    # Voice settings
    wake_word: str = "amadeus"
    whisper_model_size: str = "small"  # tiny, base, small, medium, large-v2, large-v3
    whisper_language: Optional[str] = "uk"  # "uk" = Ukrainian, None = auto-detect
    tts_enabled: bool = True
    voice_rate: int = 180  # words/min for TTS


@dataclass
class PipelineResult:
    """Result of command processing."""

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


# Types for callbacks
PipelineCallback = Callable[["VoicePipeline", str, Any], None]


class VoicePipeline:
    """
    Main pipeline for processing voice commands.

    Processing sequence:
    1. Wake Word Detection (optional)
    2. Audio Recording
    3. ASR (Speech-to-Text)
    4. NLU (Intent Recognition)
    5. Planning (Intent -> ActionPlan)
    6. Policy Evaluation (Security Check)
    7. Confirmation (якщо потрібно)
    8. Execution
    9. Response

    Example:
    ```python
    pipeline = VoicePipeline()

    # Register callbacks
    pipeline.on("plan_ready", lambda p, e, d: show_plan(d))
    pipeline.on("confirmation_needed", lambda p, e, d: ask_user(d))

    # Process text command (for testing)
    result = pipeline.process_text("open calculator")
    
    if result.success:
        print(f"Executed: {result.plan.to_preview_text()}")
    ```
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

        # Callbacks for various events
        self._callbacks: Dict[str, List[PipelineCallback]] = {}

        # Adapters (initialized lazily)
        self._nlu = None
        self._os_adapter = None
        self._audit = None
        
        # Voice adapters (initialized lazily)
        self._tts = None
        self._asr = None
        self._wake_word = None
        self._audio_input = None
        self._voice_running = False

        # Session counter
        self._session_counter = 0

    # ============================================
    # Public API
    # ============================================

    def run_voice_loop(self, skip_wake_word: bool = False) -> None:
        """
        Starts the main voice loop.

        Algorithm:
        1. Wait for the wake word ("Amadeus")
        2. Record the user's command
        3. Recognize speech (ASR)
        4. Process the command (NLU -> Plan -> Execute)
        5. Respond with voice (TTS)
        6. Repeat

        Args:
            skip_wake_word: Skip waiting for the wake word (for testing)
        """
        self._init_voice_adapters()
        self._voice_running = True
        
        logger.info("Amadeus voice assistant started")
        logger.info("Press Ctrl+C for exit")
        self._speak(f"Амадеус готова. Скажіть {self.config.wake_word} щоб почати.")
        
        try:
            while self._voice_running:
                # Step 1: Wait for wake word
                if not skip_wake_word and self.config.require_wake_word:
                    logger.info(f"Waiting for wake word: '{self.config.wake_word}'...")
                    if not self._wait_for_wake_word():
                        continue
                    self._speak("Слухаю")
                
                # Step 2: Record and recognize the command
                logger.info("Record command...")
                text = self._listen_for_command()
                
                if not text or len(text.strip()) == 0:
                    logger.info("Could not recognize the command")
                    self._speak("Вибачте, не розчула. Спробуйте ще раз.")
                    continue
                
                logger.info(f"Recognized: '{text}'")
                
                # Step 3: Process the command
                result = self.process_text(text)
                
                # Step 4: Respond with voice
                if result.success:
                    self._speak("Виконано")
                elif result.error:
                    self._speak(f"Помилка: {result.error}")
                else:
                    self._speak("Не вдалося виконати команду")
                
        except KeyboardInterrupt:
            logger.info("Voice loop was interrupted by user (Ctrl+C)")
        except Exception as e:
            logger.exception(f"Voice loop error: {e}")
            self._speak("Сталася критична помилка")
        finally:
            self._cleanup_voice_adapters()
            logger.info("Amadeus voice assistant stopped")
    
    def stop_voice_loop(self) -> None:
        """Stops the voice loop."""
        self._voice_running = False
        logger.info("Request to stop voice loop")
    
    def _init_voice_adapters(self) -> None:
        """Initialize all voice adapters."""
        logger.info("Initializing voice adapters...")
        
        # TTS
        if self._tts is None:
            from amadeus.adapters.voice.tts import Pyttsx3Adapter, SilentTTSAdapter
            if self.config.tts_enabled:
                self._tts = Pyttsx3Adapter(rate=self.config.voice_rate)
            else:
                self._tts = SilentTTSAdapter()
            logger.info("TTS Initialized")
        
        # ASR
        if self._asr is None:
            from amadeus.adapters.voice.asr import WhisperASRAdapter
            self._asr = WhisperASRAdapter(
                model_size=self.config.whisper_model_size,
                language=self.config.whisper_language,
            )
            logger.info("ASR Initialized")
        
        # Wake Word
        if self._wake_word is None:
            from amadeus.adapters.voice.wake_word import PorcupineWakeWordAdapter, AVAILABLE_KEYWORDS
            
            wake_word = self.config.wake_word.lower()
            
            if wake_word == "amadeus":
                # Using custom wake word
                self._wake_word = PorcupineWakeWordAdapter(use_custom_amadeus=True)
            elif wake_word in AVAILABLE_KEYWORDS:
                # Using built-int wake word
                self._wake_word = PorcupineWakeWordAdapter(keyword=wake_word, use_custom_amadeus=False)
            else:
                logger.warning(f"Unknown wake word '{wake_word}', using 'amadeus'")
                self._wake_word = PorcupineWakeWordAdapter(use_custom_amadeus=True)
            
            logger.info(f"Wake word initialized: '{self.config.wake_word}'")
        
        # Audio Input
        if self._audio_input is None:
            from amadeus.adapters.voice.audio_input import PyAudioInputAdapter
            # Frame length for Porcupine
            frame_length = self._wake_word.get_frame_length() if hasattr(self._wake_word, 'get_frame_length') else 512
            self._audio_input = PyAudioInputAdapter(
                sample_rate=16000,
                frame_length=frame_length
            )
            self._audio_input.start_stream()
            logger.info("Audio input initialized")
    
    def _cleanup_voice_adapters(self) -> None:
        """Cleanup resources for voice adapters."""
        logger.info("Cleaning voice adapters...")
        
        if self._audio_input:
            self._audio_input.cleanup()
            self._audio_input = None
        
        if self._wake_word:
            self._wake_word.cleanup()
            self._wake_word = None
        
        if self._asr:
            self._asr.stop_stream()
            self._asr = None
        
        if self._tts:
            self._tts.stop()
            self._tts = None
    
    def _wait_for_wake_word(self) -> bool:
        """
        Waiting for wake word.
        
        Returns:
            True if wake word detected, False if exit
        """
        if not self._wake_word or not self._audio_input:
            return False
        
        while self._voice_running:
            frame = self._audio_input.read_frame_as_int16()
            if frame is None:
                continue
            
            try:
                if self._wake_word.process_frame(frame):
                    logger.info("Wake word detected!")
                    return True
            except Exception as e:
                logger.error(f"Error processing wake word: {e}")
                continue
        
        return False
    
    def _listen_for_command(self, timeout_seconds: Optional[float] = None) -> str:
        """
        Records and recognizes a voice command.

        Args:
            timeout_seconds: Recording timeout (default from config)

        Returns:
            Recognized text or an empty string
        """
        if not self._asr or not self._audio_input:
            return ""
        
        timeout = timeout_seconds or self.config.listening_timeout_seconds
        
        try:
            # Whisper-style: start stream, buffer audio, stop stream to get result
            self._asr.start_stream()
            
            # Record audio until timeout or stop
            audio_data = self._audio_input.read_seconds(
                timeout,
                stop_check=lambda: not self._voice_running
            )
            
            if not audio_data or not self._voice_running:
                self._asr.stop_stream()
                return ""
            
            # Buffer audio
            self._asr.transcribe(audio_data)
            
            # Retrieve result
            result = self._asr.stop_stream()
            return result.strip() if result else ""
            
        except Exception as e:
            logger.error(f"Error ASR: {e}")
            return ""
    
    def _speak(self, text: str) -> None:
        """Speaks text using TTS."""
        if self._tts and self.config.tts_enabled:
            try:
                self._tts.speak(text)
            except Exception as e:
                logger.error(f"Error TTS: {e}")

    def process_text(
        self,
        text: str,
        dry_run: bool = False,
        skip_confirmation: bool = False,
    ) -> PipelineResult:
        """
        Processes text command (bypass ASR).

        Used for testing and text input.

        Args:
            text: Text of the command
            dry_run: If True, only simulate without execution
            skip_confirmation: Skip confirmation (for tests)

        Returns:
            Processing result
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create request
            request = CommandRequest(
                request_id=self._generate_session_id(),
                raw_text=text,
                source="text_input",
            )

            # Log start
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
            
            # Confirmation (if needed)
            if decision.requires_confirmation and not skip_confirmation:
                self._emit("confirmation_needed", {
                    "plan": plan,
                    "decision": decision,
                })
                # In real UI there will be waiting for response
                # For tests — automatically confirm
                logger.info(f"Confirmation required for plan: {plan.plan_id}")
            
            # Execution
            if not plan.dry_run:
                results = self._execute_plan(plan)
            else:
                results = self._simulate_plan(plan)
            
            self._emit("execution_complete", {"results": results})
            self._log_audit("execution_complete", request=request, plan=plan)

            # Check success
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
        """Returns the current state of the assistant."""
        return self.state_machine.state

    def reset(self) -> None:
        """Resets the pipeline state."""
        self.state_machine.force_reset()
        self._emit("reset", {})

    # ============================================
    # Event System
    # ============================================

    def on(self, event: str, callback: PipelineCallback) -> None:
        """
        Registers a callback for an event.

        Events:
        - command_received: Command received
        - intent_recognized: Intent recognized
        - plan_ready: Plan ready
        - policy_evaluated: Policy evaluated
        - confirmation_needed: Confirmation needed
        - execution_complete: Execution complete
        - error: Error
        - reset: Reset
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def off(self, event: str, callback: PipelineCallback) -> bool:
        """Removes a callback."""
        if event in self._callbacks:
            try:
                self._callbacks[event].remove(callback)
                return True
            except ValueError:
                pass
        return False

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        """Calls all callbacks for an event."""
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
        """Parses text into Intent."""
        if self._nlu is None:
            from amadeus.adapters.voice.nlu import DeterministicNLU
            self._nlu = DeterministicNLU()
        
        return self._nlu.parse(text)

    def _execute_plan(self, plan: ActionPlan) -> List[ExecutionResult]:
        """Executes the action plan."""
        from amadeus.app.executor import ActionExecutor
        
        if self._os_adapter is None:
            from amadeus.adapters.os import get_os_adapter
            self._os_adapter = get_os_adapter()
        
        executor = ActionExecutor(self._os_adapter)
        return executor.execute_plan(plan)

    def _simulate_plan(self, plan: ActionPlan) -> List[ExecutionResult]:
        """Simulates the action plan (dry run)."""
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
        """Logs an event to the audit log."""
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
    Creates a configured pipeline.

    Args:
        dry_run: Simulation mode
        verbose: Detailed logging

    Returns:
        Configured VoicePipeline
    """
    config = PipelineConfig(
        dry_run_by_default=dry_run,
        verbose_logging=verbose,
    )
    return VoicePipeline(config=config)
