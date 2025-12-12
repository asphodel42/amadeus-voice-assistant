"""
Amadeus TTS (Text-to-Speech) Adapter

Implementation of speech synthesis using pyttsx3.
Works offline without needing internet connection.

Features:
    - Emotional speech with different intonations
    - Natural pauses for better comprehension
    - SSML-like markup support (simplified)
    - Context-aware speech patterns

Usage:
    tts = Pyttsx3Adapter()
    tts.speak("Hello, I am Amadeus")
    
    # With emotion
    tts.speak_with_emotion("Task completed!", emotion="happy")
    
    # With pauses
    tts.speak("Please wait... <pause> Processing your request")
"""

from __future__ import annotations

import logging
import re
import time
from enum import Enum
from typing import Optional, Dict, Tuple

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from piper import PiperVoice
    from piper.config import SynthesisConfig
    import wave
    import io
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

from amadeus.core.ports import TTSPort

logger = logging.getLogger(__name__)


class EmotionType(Enum):
    """Types of emotional speech."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CONCERNED = "concerned"
    APOLOGETIC = "apologetic"
    CONFIDENT = "confident"
    FRIENDLY = "friendly"
    ALERT = "alert"


class TTSEmotion:
    """
    Configuration for emotional speech parameters.
    
    Attributes:
        rate_modifier: Multiplier for speech rate (1.0 = normal)
        pitch_modifier: Pitch adjustment (not supported by pyttsx3, kept for future)
        volume_modifier: Volume multiplier (1.0 = normal)
        pause_before: Pause before speech (seconds)
        pause_after: Pause after speech (seconds)
    """
    
    def __init__(
        self,
        rate_modifier: float = 1.0,
        pitch_modifier: float = 1.0,
        volume_modifier: float = 1.0,
        pause_before: float = 0.0,
        pause_after: float = 0.0,
    ):
        self.rate_modifier = rate_modifier
        self.pitch_modifier = pitch_modifier
        self.volume_modifier = volume_modifier
        self.pause_before = pause_before
        self.pause_after = pause_after


# Predefined emotional profiles
EMOTION_PROFILES: Dict[EmotionType, TTSEmotion] = {
    EmotionType.NEUTRAL: TTSEmotion(
        rate_modifier=1.0,
        volume_modifier=1.0,
    ),
    EmotionType.HAPPY: TTSEmotion(
        rate_modifier=1.05,  # Slightly faster
        volume_modifier=1.1,  # Slightly louder
        pause_after=0.2,
    ),
    EmotionType.EXCITED: TTSEmotion(
        rate_modifier=1.15,  # Faster
        volume_modifier=1.15,  # Louder
        pause_before=0.1,
    ),
    EmotionType.CONCERNED: TTSEmotion(
        rate_modifier=0.9,  # Slower
        volume_modifier=0.95,  # Slightly quieter
        pause_before=0.2,
        pause_after=0.3,
    ),
    EmotionType.APOLOGETIC: TTSEmotion(
        rate_modifier=0.85,  # Slower
        volume_modifier=0.9,  # Quieter
        pause_before=0.15,
        pause_after=0.2,
    ),
    EmotionType.CONFIDENT: TTSEmotion(
        rate_modifier=1.0,
        volume_modifier=1.1,  # Louder
        pause_after=0.15,
    ),
    EmotionType.FRIENDLY: TTSEmotion(
        rate_modifier=0.95,  # Slightly slower
        volume_modifier=1.0,
        pause_after=0.2,
    ),
    EmotionType.ALERT: TTSEmotion(
        rate_modifier=1.1,  # Faster
        volume_modifier=1.2,  # Much louder
        pause_before=0.1,
        pause_after=0.15,
    ),
}


class Pyttsx3Adapter(TTSPort):
    """
    TTS adapter based on pyttsx3 with emotional speech support.
    
    Advantages:
        - Offline operation
        - Cross-platform (Windows, Linux, macOS)
        - Low resource usage
        - Emotional speech with rate/volume adjustments
        - Natural pauses support
        - Simplified SSML-like markup
    
    Attributes:
        engine: pyttsx3 engine instance
        base_rate: Base speech rate (words/min)
        base_volume: Base volume (0.0 - 1.0)
        current_emotion: Current emotion being used
    """
    
    def __init__(
        self,
        rate: int = 170,
        volume: float = 1.0,
        voice_id: Optional[str] = None
    ) -> None:
        """
        Initialize TTS adapter.
        
        Args:
            rate: Speech rate in words per minute (default: 170)
            volume: Volume from 0.0 to 1.0
            voice_id: Specific voice ID (None = system default)
        
        Raises:
            RuntimeError: If pyttsx3 is not available
        """
        if not PYTTSX3_AVAILABLE:
            raise RuntimeError(
                "pyttsx3 is not installed. Install with: pip install pyttsx3"
            )
        
        self.engine = pyttsx3.init()
        self._is_speaking = False
        
        # Store base settings
        self.base_rate = rate
        self.base_volume = volume
        self.current_emotion = EmotionType.NEUTRAL
        
        # Set speech rate
        self.engine.setProperty('rate', rate)
        
        # Set volume
        self.engine.setProperty('volume', volume)
        
        # Set voice (optional)
        if voice_id:
            self.engine.setProperty('voice', voice_id)
        
        logger.info(f"TTS initialized: rate={rate}, volume={volume}")
    
    def speak(self, text: str) -> None:
        """
        Speaks the text aloud with neutral emotion.
        
        Args:
            text: Text to speak
        """
        self.speak_with_emotion(text, EmotionType.NEUTRAL)
    
    def speak_with_emotion(
        self, 
        text: str, 
        emotion: EmotionType = EmotionType.NEUTRAL
    ) -> None:
        """
        Speaks text with specific emotion.
        
        Args:
            text: Text to speak
            emotion: Emotion type to use
        """
        if not text or not text.strip():
            logger.warning("Empty text for speech synthesis")
            return
        
        try:
            self._is_speaking = True
            self.current_emotion = emotion
            
            # Get emotion profile
            emotion_config = EMOTION_PROFILES.get(emotion, EMOTION_PROFILES[EmotionType.NEUTRAL])
            
            # Process text for pauses and markup
            processed_text, pause_points = self._process_text_markup(text)
            
            # Apply emotion settings
            self._apply_emotion_settings(emotion_config)
            
            # Pause before speaking (if configured)
            if emotion_config.pause_before > 0:
                time.sleep(emotion_config.pause_before)
            
            logger.debug(f"TTS ({emotion.value}): {processed_text}")
            
            # Speak with pauses if needed
            if pause_points:
                self._speak_with_pauses(processed_text, pause_points)
            else:
                self.engine.say(processed_text)
                self.engine.runAndWait()
            
            # Pause after speaking (if configured)
            if emotion_config.pause_after > 0:
                time.sleep(emotion_config.pause_after)
            
            # Restore base settings
            self._restore_base_settings()
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            self._restore_base_settings()
        finally:
            self._is_speaking = False
    
    def _process_text_markup(self, text: str) -> Tuple[str, Dict[int, float]]:
        """
        Process simplified SSML-like markup for pauses.
        
        Supports:
            - <pause> or ... - short pause (0.3s)
            - <pause:1.0> - pause for 1.0 seconds
            - <break> - medium pause (0.5s)
        
        Args:
            text: Text with markup
            
        Returns:
            Tuple of (clean_text, pause_points_dict)
            pause_points_dict: {character_position: pause_duration}
        """
        pause_points = {}
        clean_text = text
        
        # Pattern for explicit pause tags: <pause> or <pause:1.0>
        pause_pattern = r'<pause(?::(\d+\.?\d*))?>|<break>'
        
        offset = 0
        for match in re.finditer(pause_pattern, text):
            pause_duration = 0.5  # default
            
            if match.group(0) == '<pause>':
                pause_duration = 0.3
            elif match.group(0) == '<break>':
                pause_duration = 0.5
            elif match.group(1):
                pause_duration = float(match.group(1))
            
            position = match.start() - offset
            pause_points[position] = pause_duration
            
            # Remove the tag from text
            clean_text = clean_text[:match.start() - offset] + clean_text[match.end() - offset:]
            offset += len(match.group(0))
        
        # Replace triple dots with pauses
        dots_pattern = r'\.\.\.'
        for match in re.finditer(dots_pattern, clean_text):
            pause_points[match.start()] = 0.3
        
        # Replace ... with single .
        clean_text = re.sub(r'\.\.\.', '.', clean_text)
        
        return clean_text, pause_points
    
    def _speak_with_pauses(self, text: str, pause_points: Dict[int, float]) -> None:
        """
        Speak text with pauses at specific points.
        
        Args:
            text: Clean text to speak
            pause_points: Dictionary of {position: duration}
        """
        # Sort pause points
        sorted_pauses = sorted(pause_points.items())
        
        # Split text into segments
        segments = []
        last_pos = 0
        
        for pos, duration in sorted_pauses:
            if pos > last_pos:
                segments.append((text[last_pos:pos], 0))
            segments.append(("", duration))  # Pause
            last_pos = pos
        
        # Add remaining text
        if last_pos < len(text):
            segments.append((text[last_pos:], 0))
        
        # Speak segments with pauses
        for segment_text, pause_duration in segments:
            if segment_text.strip():
                self.engine.say(segment_text)
                self.engine.runAndWait()
            if pause_duration > 0:
                time.sleep(pause_duration)
    
    def _apply_emotion_settings(self, emotion_config: TTSEmotion) -> None:
        """
        Apply emotion-specific settings to TTS engine.
        
        Args:
            emotion_config: Emotion configuration
        """
        # Adjust rate
        new_rate = int(self.base_rate * emotion_config.rate_modifier)
        self.engine.setProperty('rate', new_rate)
        
        # Adjust volume
        new_volume = min(1.0, self.base_volume * emotion_config.volume_modifier)
        self.engine.setProperty('volume', new_volume)
        
        logger.debug(f"Applied emotion settings: rate={new_rate}, volume={new_volume:.2f}")
    
    def _restore_base_settings(self) -> None:
        """Restore base TTS settings."""
        self.engine.setProperty('rate', self.base_rate)
        self.engine.setProperty('volume', self.base_volume)
        self.current_emotion = EmotionType.NEUTRAL
    
    def stop(self) -> None:
        """Stops current speech synthesis."""
        try:
            self.engine.stop()
            self._is_speaking = False
            logger.debug("TTS stopped")
        except Exception as e:
            logger.error(f"Error stopping TTS: {e}")
    
    def is_speaking(self) -> bool:
        """Checks if speech synthesis is in progress."""
        return self._is_speaking
    
    def get_available_voices(self) -> list:
        """
        Returns list of available voices.
        
        Returns:
            List of dicts with voice information:
            [{"id": "...", "name": "...", "languages": [...]}, ...]
        """
        voices = self.engine.getProperty('voices')
        return [
            {
                "id": voice.id,
                "name": voice.name,
                "languages": voice.languages,
            }
            for voice in voices
        ]
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Sets voice by ID.
        
        Args:
            voice_id: Voice ID
            
        Returns:
            True if successfully set
        """
        try:
            self.engine.setProperty('voice', voice_id)
            logger.info(f"Voice changed to: {voice_id}")
            return True
        except Exception as e:
            logger.error(f"Error changing voice: {e}")
            return False
    
    def set_rate(self, rate: int) -> None:
        """Sets speech rate."""
        self.engine.setProperty('rate', rate)
        logger.debug(f"TTS rate: {rate}")
    
    def set_volume(self, volume: float) -> None:
        """Sets volume (0.0 - 1.0)."""
        volume = max(0.0, min(1.0, volume))
        self.engine.setProperty('volume', volume)
        logger.debug(f"TTS volume: {volume}")


class SilentTTSAdapter(TTSPort):
    """
    Silent TTS adapter for testing.
    
    Does not produce any sound, only logs.
    """
    
    def speak(self, text: str) -> None:
        """Logs text instead of speaking."""
        logger.info(f"[Silent TTS]: {text}")
    
    def stop(self) -> None:
        """Does nothing."""
        pass
    
    def get_available_voices(self) -> list:
        """Returns empty list."""
        return []
    
    def set_voice(self, voice_id: str) -> bool:
        """Does nothing, returns True."""
        return True
    
    def set_rate(self, rate: int) -> None:
        """Does nothing."""
        pass
    
    def set_volume(self, volume: float) -> None:
        """Does nothing."""
        pass


class PiperTTSAdapter(TTSPort):
    """
    Piper TTS adapter for cross-platform offline speech synthesis.
    
    Uses Piper (https://github.com/rhasspy/piper) for high-quality,
    fast, offline text-to-speech. Supports Ukrainian and many other languages.
    
    Attributes:
        model_path: Path to the Piper voice model (.onnx file)
        config_path: Path to the model config (.json file)
        sample_rate: Audio sample rate (determined by model)
    """
    
    # Ukrainian voice models
    VOICE_MODELS = {
        "uk_UA-ukrainian_tts-medium": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/ukrainian_tts/medium/uk_UA-ukrainian_tts-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/ukrainian_tts/medium/uk_UA-ukrainian_tts-medium.onnx.json",
            "quality": "medium",
            "description": "Ukrainian female voice (medium quality)",
        },
        "uk_UA-lada-x_low": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/lada/x_low/uk_UA-lada-x_low.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/lada/x_low/uk_UA-lada-x_low.onnx.json",
            "quality": "x_low",
            "description": "Ukrainian female voice (low quality, faster)",
        },
        "en_US-amy-medium": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
            "quality": "medium",
            "description": "English US female voice",
        },
    }
    
    DEFAULT_VOICE = "uk_UA-ukrainian_tts-medium"
    
    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        models_dir: str = "models/piper",
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w: float = 0.8,
    ) -> None:
        """
        Initialize Piper TTS adapter.
        
        Args:
            voice: Voice model name (from VOICE_MODELS)
            models_dir: Directory to store downloaded models
            length_scale: Speech speed (1.0 = normal, <1.0 = faster, >1.0 = slower)
            noise_scale: Phoneme noise (affects expressiveness)
            noise_w: Phoneme width noise
        
        Raises:
            RuntimeError: If Piper is not available
        """
        if not PIPER_AVAILABLE:
            raise RuntimeError(
                "Piper TTS is not installed. Install with: pip install piper-tts"
            )
        
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError(
                "sounddevice is not installed. Install with: pip install sounddevice"
            )
        
        self.voice_name = voice
        self.models_dir = Path(models_dir)
        self.length_scale = length_scale
        self.noise_scale = noise_scale
        self.noise_w = noise_w
        
        self._voice: Optional[PiperVoice] = None
        self._sample_rate: int = 22050
        self._is_speaking = False
        
        # Ensure models directory exists
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Load voice model
        self._load_voice(voice)
        
        logger.info(f"Piper TTS initialized: voice={voice}, sample_rate={self._sample_rate}")
    
    def _load_voice(self, voice: str) -> None:
        """Load a Piper voice model, downloading if necessary."""
        if voice not in self.VOICE_MODELS:
            available = ", ".join(self.VOICE_MODELS.keys())
            raise ValueError(f"Unknown voice '{voice}'. Available: {available}")
        
        model_info = self.VOICE_MODELS[voice]
        model_path = self.models_dir / f"{voice}.onnx"
        config_path = self.models_dir / f"{voice}.onnx.json"
        
        # Download model if not exists
        if not model_path.exists():
            logger.info(f"Downloading Piper voice model: {voice}")
            self._download_file(model_info["url"], model_path)
        
        if not config_path.exists():
            logger.info(f"Downloading Piper voice config: {voice}")
            self._download_file(model_info["config_url"], config_path)
        
        # Load voice
        logger.info(f"Loading Piper voice: {voice}")
        self._voice = PiperVoice.load(str(model_path), config_path=str(config_path))
        self._sample_rate = self._voice.config.sample_rate
    
    def _download_file(self, url: str, path: Path) -> None:
        """Download a file from URL."""
        import urllib.request
        
        logger.info(f"Downloading: {url}")
        try:
            urllib.request.urlretrieve(url, path)
            logger.info(f"Downloaded to: {path}")
        except Exception as e:
            raise RuntimeError(f"Failed to download {url}: {e}")
    
    def speak(self, text: str) -> None:
        """
        Speak text using Piper TTS.
        
        Args:
            text: Text to speak
        """
        if not text or not text.strip():
            return
        
        if self._voice is None:
            logger.error("Voice not loaded")
            return
        
        try:
            self._is_speaking = True
            
            # Process text (remove markup tags) and lowercase for better phoneme mapping
            processed_text = self._process_text(text).lower()
            
            # Create synthesis config with our parameters
            syn_config = SynthesisConfig(
                length_scale=self.length_scale,
                noise_scale=self.noise_scale,
                noise_w_scale=self.noise_w,
            )
            
            # Synthesize audio using synthesize() method
            import numpy as np
            audio_chunks = []
            for chunk in self._voice.synthesize(processed_text, syn_config=syn_config):
                audio_chunks.append(chunk.audio_int16_array)
            
            # Combine audio chunks
            if audio_chunks:
                audio_array = np.concatenate(audio_chunks)
                
                # Play audio
                sd.play(audio_array, samplerate=self._sample_rate)
                sd.wait()  # Wait until audio is finished
            
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
        finally:
            self._is_speaking = False
    
    def speak_with_emotion(self, text: str, emotion: EmotionType = EmotionType.NEUTRAL) -> None:
        """
        Speak text with emotion (simulated via speech parameters).
        
        Piper doesn't have native emotion support, so we simulate it
        by adjusting length_scale (speed) and pauses.
        
        Args:
            text: Text to speak
            emotion: Emotion type
        """
        # Adjust parameters based on emotion
        original_length_scale = self.length_scale
        
        emotion_settings = {
            EmotionType.NEUTRAL: 1.0,
            EmotionType.HAPPY: 0.9,      # Slightly faster
            EmotionType.EXCITED: 0.85,   # Faster
            EmotionType.CONCERNED: 1.1,  # Slower
            EmotionType.APOLOGETIC: 1.15, # Slower
            EmotionType.CONFIDENT: 0.95, # Slightly faster
            EmotionType.FRIENDLY: 0.95,  # Slightly faster
            EmotionType.ALERT: 0.9,      # Slightly faster
        }
        
        self.length_scale = emotion_settings.get(emotion, 1.0)
        
        try:
            self.speak(text)
        finally:
            self.length_scale = original_length_scale
    
    def _process_text(self, text: str) -> str:
        """Process text, handling markup tags."""
        # Remove <pause>, <break> tags and add actual pauses via punctuation
        text = re.sub(r"<pause>|<break>", "...", text)
        
        # Clean up multiple dots
        text = re.sub(r"\.{4,}", "...", text)
        
        return text.strip()
    
    def stop(self) -> None:
        """Stop current speech."""
        if self._is_speaking:
            try:
                sd.stop()
            except Exception as e:
                logger.error(f"Error stopping Piper TTS: {e}")
            self._is_speaking = False
    
    def get_available_voices(self) -> list:
        """Return list of available voice models."""
        return [
            {
                "name": name,
                "id": name,
                "quality": info["quality"],
                "description": info["description"],
            }
            for name, info in self.VOICE_MODELS.items()
        ]
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Change voice model.
        
        Args:
            voice_id: Voice model name
            
        Returns:
            True if successful
        """
        try:
            self._load_voice(voice_id)
            self.voice_name = voice_id
            return True
        except Exception as e:
            logger.error(f"Failed to set voice: {e}")
            return False
    
    def set_rate(self, rate: int) -> None:
        """
        Set speech rate.
        
        Args:
            rate: Words per minute (approximate, mapped to length_scale)
        """
        # Map WPM to length_scale (180 WPM = 1.0, higher = faster = lower scale)
        self.length_scale = 180.0 / max(rate, 50)
    
    def set_volume(self, volume: float) -> None:
        """
        Set volume (not directly supported by Piper, would need audio processing).
        
        Args:
            volume: Volume level (0.0 to 1.0) - currently ignored
        """
        logger.debug(f"Volume setting not supported by Piper TTS: {volume}")


# Import Path at module level for PiperTTSAdapter
from pathlib import Path
