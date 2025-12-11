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
import time
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
    RiskLevel,
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
    whisper_language: Optional[str] = None  # None = auto-detect, "uk" = Ukrainian, "en" = English
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
        audit: Optional[Any] = None,
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
        self._audit = audit  # Use provided audit adapter
        
        # Voice adapters (initialized lazily)
        self._tts = None
        self._asr = None
        self._wake_word = None
        self._audio_input = None
        self._voice_running = False

        # Session counter
        self._session_counter = 0
        
        # Pending plan awaiting confirmation
        self._pending_plan: Optional[ActionPlan] = None
        self._pending_request: Optional[CommandRequest] = None

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
        self._speak_emotional(
            f"Hello! I am Amadeus. <pause> Ready to help you. Say {self.config.wake_word} to begin.",
            emotion="friendly"
        )
        
        try:
            while self._voice_running:
                # Step 1: Wait for wake word
                if not skip_wake_word and self.config.require_wake_word:
                    logger.info(f"Waiting for wake word: '{self.config.wake_word}'...")
                    if not self._wait_for_wake_word():
                        continue
                    self._speak_emotional("Yes, I'm listening", emotion="friendly")
                
                # Step 2: Record and recognize the command
                logger.info("Record command...")
                text = self._listen_for_command()
                
                if not text or len(text.strip()) == 0:
                    logger.info("Could not recognize the command")
                    self._speak_emotional(
                        "Sorry, I didn't catch that. <pause> Could you repeat please?",
                        emotion="apologetic"
                    )
                    continue
                
                logger.info(f"Recognized: '{text}'")
                
                # Step 3: Process the command
                result = self.process_text(text)
                
                # Step 4: Respond with voice
                if result.success:
                    self._speak_emotional("Got it. <pause> Done", emotion="confident")
                elif result.error == "CONFIRMATION_REQUIRED":
                    # Special case: confirmation needed
                    plan = result.plan
                    if plan:
                        risk_text = {
                            RiskLevel.HIGH: "risky",
                            RiskLevel.DESTRUCTIVE: "dangerous",
                        }.get(plan.max_risk, "requires confirmation")
                        
                        self._speak_emotional(
                            f"Warning! <break> This command is {risk_text}. Do you confirm?",
                            emotion="alert"
                        )
                        
                        # Wait for confirmation response
                        logger.info("Waiting for confirmation (yes/no)...")
                        confirmation_text = self._listen_for_command(timeout_seconds=10.0)
                        
                        if confirmation_text:
                            logger.info(f"Confirmation response: '{confirmation_text}'")
                            # Process confirmation
                            confirm_result = self.process_text(confirmation_text)
                            
                            if confirm_result.success:
                                self._speak_emotional("Okay. <pause> Done", emotion="happy")
                            else:
                                self._speak_emotional("Alright. <pause> Cancelled", emotion="neutral")
                        else:
                            logger.info("No confirmation received, timing out")
                            self._speak_emotional("Time's up. <pause> Command cancelled", emotion="concerned")
                            # Timeout - cancel the pending action
                            self.state_machine.transition(StateTransition.TIMEOUT)
                            self._pending_plan = None
                            self._pending_request = None
                elif result.error:
                    self._speak_emotional(f"Error: <pause> {result.error}", emotion="concerned")
                else:
                    self._speak_emotional("Sorry, could not execute the command", emotion="apologetic")
                
        except KeyboardInterrupt:
            logger.info("Voice loop was interrupted by user (Ctrl+C)")
        except Exception as e:
            logger.exception(f"Voice loop error: {e}")
            self._speak_emotional("A critical error occurred", emotion="concerned")
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
            from amadeus.adapters.voice.tts import PiperTTSAdapter, SilentTTSAdapter, PIPER_AVAILABLE
            
            if self.config.tts_enabled:
                if PIPER_AVAILABLE:
                    try:
                        # Use Piper TTS with English voice
                        self._tts = PiperTTSAdapter(
                            voice="en_US-amy-medium",
                            models_dir="models/piper",
                        )
                        logger.info("TTS initialized: Piper (English voice)")
                    except Exception as e:
                        logger.error(f"Failed to initialize Piper TTS: {e}")
                        logger.warning("Falling back to silent TTS")
                        self._tts = SilentTTSAdapter()
                else:
                    logger.warning("Piper TTS not available, using silent TTS")
                    self._tts = SilentTTSAdapter()
            else:
                self._tts = SilentTTSAdapter()
                logger.info("TTS disabled by config")
        
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
            
            # Record audio until timeout or silence detected (VAD)
            audio_data = self._audio_input.read_seconds(
                timeout,
                stop_check=lambda: not self._voice_running,
                stop_on_silence=True,  # Enable VAD
                silence_threshold=0.01,  # Adjust based on mic sensitivity
                silence_duration=1.2,  # Stop after 1.2 seconds of silence
                min_speech_duration=0.5,  # Require at least 0.5s of speech
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
        """Speaks text using TTS with neutral emotion."""
        self._speak_emotional(text, emotion="neutral")
    
    def _speak_emotional(self, text: str, emotion: str = "neutral") -> None:
        """
        Speaks text using TTS with specific emotion.
        
        Args:
            text: Text to speak (supports <pause>, <break> markup)
            emotion: Emotion type (neutral, happy, excited, concerned, 
                     apologetic, confident, friendly, alert)
        """
        if not self.config.tts_enabled:
            logger.debug(f"TTS disabled, skipping: {text}")
            return
        
        if self._tts is None:
            logger.warning("TTS not initialized")
            return
        
        # Temporarily pause audio input during TTS to avoid conflicts
        audio_was_active = False
        if self._audio_input and hasattr(self._audio_input, 'pause_stream'):
            audio_was_active = self._audio_input.is_active
            if audio_was_active:
                logger.debug("Pausing audio input for TTS")
                self._audio_input.pause_stream()
                # Small delay to ensure audio device is released
                time.sleep(0.1)
        
        try:
            logger.info(f"TTS Speaking ({emotion}): {text}")
            
            # Check if TTS adapter supports emotional speech
            if hasattr(self._tts, 'speak_with_emotion'):
                from amadeus.adapters.voice.tts import EmotionType
                
                # Map string to EmotionType enum
                emotion_map = {
                    "neutral": EmotionType.NEUTRAL,
                    "happy": EmotionType.HAPPY,
                    "excited": EmotionType.EXCITED,
                    "concerned": EmotionType.CONCERNED,
                    "apologetic": EmotionType.APOLOGETIC,
                    "confident": EmotionType.CONFIDENT,
                    "friendly": EmotionType.FRIENDLY,
                    "alert": EmotionType.ALERT,
                }
                
                emotion_type = emotion_map.get(emotion.lower(), EmotionType.NEUTRAL)
                self._tts.speak_with_emotion(text, emotion_type)
                logger.info("TTS completed")
            else:
                # Fallback to regular speak if emotion not supported
                self._tts.speak(text)
                logger.info("TTS completed")
        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
        finally:
            # Resume audio input after TTS
            if audio_was_active and self._audio_input and hasattr(self._audio_input, 'resume_stream'):
                # Small delay to ensure TTS audio is fully played
                time.sleep(0.2)
                logger.debug("Resuming audio input after TTS")
                self._audio_input.resume_stream()

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
            # Reset if in error state, then transition to LISTENING
            if self.state_machine.is_error:
                self.state_machine.transition(StateTransition.RESET)
            
            # Simulate push-to-talk: IDLE -> LISTENING
            if self.state_machine.is_idle:
                self.state_machine.transition(StateTransition.PUSH_TO_TALK)
            
            # Transition to PROCESSING: LISTENING -> PROCESSING
            if self.state_machine.is_listening:
                self.state_machine.transition(StateTransition.AUDIO_COMPLETE)
            
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
            
            # Handle CONFIRM intent (proceed with pending plan)
            if intent.intent_type == IntentType.CONFIRM:
                if self._pending_plan is not None and self.state_machine.is_reviewing:
                    logger.info("User confirmed pending action")
                    self.state_machine.transition(StateTransition.CONFIRM)
                    
                    # Execute the pending plan
                    results = self._execute_plan(self._pending_plan)
                    self._emit("execution_complete", {"results": results})
                    self._log_audit("execution_complete", request=self._pending_request, plan=self._pending_plan)
                    
                    # Clear pending
                    plan = self._pending_plan
                    self._pending_plan = None
                    self._pending_request = None
                    
                    # Return to IDLE
                    self.state_machine.transition(StateTransition.COMPLETE)
                    
                    all_success = all(r.is_success for r in results)
                    return PipelineResult(
                        success=all_success,
                        request=request,
                        intent=intent,
                        plan=plan,
                        results=results,
                        duration_ms=self._calc_duration(start_time),
                    )
                else:
                    return PipelineResult(
                        success=False,
                        request=request,
                        intent=intent,
                        error="No pending action to confirm",
                        duration_ms=self._calc_duration(start_time),
                    )
            
            # Handle DENY intent (cancel pending plan)
            if intent.intent_type == IntentType.DENY:
                if self._pending_plan is not None and self.state_machine.is_reviewing:
                    logger.info("User denied pending action")
                    self.state_machine.transition(StateTransition.DENY)
                    
                    # Clear pending
                    self._pending_plan = None
                    self._pending_request = None
                    
                    return PipelineResult(
                        success=True,
                        request=request,
                        intent=intent,
                        error="Action cancelled by user",
                        duration_ms=self._calc_duration(start_time),
                    )
                else:
                    return PipelineResult(
                        success=False,
                        request=request,
                        intent=intent,
                        error="No pending action to cancel",
                        duration_ms=self._calc_duration(start_time),
                    )
            
            if intent.is_unknown:
                # LISTENING -> IDLE (via ERROR)
                self.state_machine.transition(StateTransition.ERROR)
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
                # LISTENING -> IDLE (via ERROR)
                self.state_machine.transition(StateTransition.ERROR)
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
                # LISTENING -> IDLE (via ERROR)
                self.state_machine.transition(StateTransition.ERROR)
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
                # Transition to REVIEWING state
                self.state_machine.transition(StateTransition.PLAN_READY)
                
                # Store pending plan
                self._pending_plan = plan
                self._pending_request = request
                
                # Emit confirmation needed event
                self._emit("confirmation_needed", {
                    "plan": plan,
                    "decision": decision,
                })
                
                logger.info(f"Confirmation required for plan: {plan.plan_id}")
                logger.info(f"Risk level: {plan.max_risk.name}")
                
                # For voice interface, we need to wait for user response
                # Return a special result indicating confirmation is needed
                return PipelineResult(
                    success=False,
                    request=request,
                    intent=intent,
                    plan=plan,
                    decision=decision,
                    error="CONFIRMATION_REQUIRED",  # Special marker
                    duration_ms=self._calc_duration(start_time),
                )
            
            # Auto-confirm safe operations or if confirmation is skipped
            if decision.requires_confirmation:
                self.state_machine.transition(StateTransition.PLAN_READY)
                self.state_machine.transition(StateTransition.CONFIRM)
            else:
                self.state_machine.transition(StateTransition.PLAN_SAFE)
            
            # Execution
            if not plan.dry_run:
                results = self._execute_plan(plan)
            else:
                results = self._simulate_plan(plan)
            
            self._emit("execution_complete", {"results": results})
            self._log_audit("execution_complete", request=request, plan=plan)

            # Check success
            all_success = all(r.is_success for r in results)
            
            # Transition back to IDLE: EXECUTING -> IDLE
            if all_success:
                self.state_machine.transition(StateTransition.COMPLETE)
            else:
                self.state_machine.transition(StateTransition.ERROR)
            
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
            # Try to recover to IDLE
            try:
                if not self.state_machine.is_idle:
                    self.state_machine.transition(StateTransition.ERROR)
            except Exception:
                pass  # Ignore transition errors during error handling
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
        
        # Clean up ASR artifacts: remove punctuation that breaks regex patterns
        # Whisper tends to add commas, periods, hyphens etc. based on pauses
        import re
        cleaned_text = re.sub(r'[,;:!?]', '', text)  # Remove common punctuation
        cleaned_text = re.sub(r'-', ' ', cleaned_text)  # Replace hyphens with spaces
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Collapse multiple spaces
        cleaned_text = cleaned_text.strip()
        
        return self._nlu.parse(cleaned_text)

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
