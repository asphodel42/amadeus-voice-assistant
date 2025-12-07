"""
Amadeus TTS (Text-to-Speech) Adapter

Implementation of speech synthesis using pyttsx3.
Works offline without needing internet connection.

Usage:
    tts = Pyttsx3Adapter()
    tts.speak("Hello, I am Amadeus")
"""

from __future__ import annotations

import logging
from typing import Optional

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

from amadeus.core.ports import TTSPort

logger = logging.getLogger(__name__)


class Pyttsx3Adapter(TTSPort):
    """
    TTS adapter based on pyttsx3.
    
    Advantages:
        - Offline operation
        - Cross-platform (Windows, Linux, macOS)
        - Low resource usage
    
    Attributes:
        engine: pyttsx3 engine instance
        rate: Speech rate (words/min)
        volume: Volume (0.0 - 1.0)
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
        Speaks the text aloud.
        
        Args:
            text: Text to speak
        """
        if not text or not text.strip():
            logger.warning("Empty text for speech synthesis")
            return
        
        try:
            self._is_speaking = True
            logger.debug(f"TTS: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            self._is_speaking = False
    
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
