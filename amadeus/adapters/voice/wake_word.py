"""
Amadeus Wake Word Detection Adapter

Implementation of wake word recognition using Picovoice Porcupine.
Supports built-in keywords: "jarvis", "computer", "alexa", etc.
Also supports custom wake words via .ppn files.

Usage:
    # Built-in wake word
    wake = PorcupineWakeWordAdapter(keyword="jarvis")
    
    # Custom wake word
    wake = PorcupineWakeWordAdapter(keyword_path="models/wake_words/amadeus_en_windows_v3_0_0.ppn")
    
    if wake.process_frame(audio_frame):
        print("Wake word detected!")
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False

from dotenv import load_dotenv

from amadeus.core.ports import WakeWordPort

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


# Available built-in Porcupine keywords
AVAILABLE_KEYWORDS = [
    "alexa",
    "americano",
    "blueberry",
    "bumblebee",
    "computer",
    "grapefruit",
    "grasshopper",
    "hey google",
    "hey siri",
    "jarvis",
    "ok google",
    "picovoice",
    "porcupine",
    "terminator",
]

# Path to custom "Amadeus" wake word
DEFAULT_CUSTOM_WAKE_WORD_PATH = "models/wake_words/amadeus_en_windows_v3_0_0.ppn"


class PorcupineWakeWordAdapter(WakeWordPort):
    """
    Wake Word adapter based on Picovoice Porcupine.
    
    Advantages:
        - Very low CPU usage
        - High accuracy
        - Offline operation
        - Built-in popular keywords
    
    Attributes:
        porcupine: Porcupine engine instance
        keywords: List of activated keywords
        frame_length: Audio frame size for processing
    """
    
    def __init__(
        self,
        access_key: Optional[str] = None,
        keyword: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        keyword_path: Optional[str] = None,
        keyword_paths: Optional[List[str]] = None,
        sensitivities: Optional[List[float]] = None,
        use_custom_amadeus: bool = True
    ) -> None:
        """
        Initialize Porcupine Wake Word adapter.
        
        Args:
            access_key: Picovoice AccessKey (if None - read from .env)
            keyword: Single built-in keyword (jarvis, computer, etc.)
            keywords: List of built-in keywords
            keyword_path: Path to custom .ppn file
            keyword_paths: List of paths to custom .ppn files
            sensitivities: Sensitivity for each word (0.0 - 1.0)
            use_custom_amadeus: If True and no other settings,
                               uses custom "Amadeus" wake word
        
        Raises:
            RuntimeError: If Porcupine is not available
            ValueError: If AccessKey not found
        """
        if not PORCUPINE_AVAILABLE:
            raise RuntimeError(
                "pvporcupine is not installed. Install with: pip install pvporcupine"
            )
        
        # Get AccessKey
        self._access_key = access_key or os.getenv("PICOVOICE_ACCESS_KEY")
        if not self._access_key:
            raise ValueError(
                "PICOVOICE_ACCESS_KEY not found.\n"
                "Add it to .env file or pass as parameter.\n"
                "Get key from https://console.picovoice.ai/"
            )
        
        # Determine mode: custom or built-in
        self._keyword_paths: Optional[List[str]] = None
        self.keywords: Optional[List[str]] = None
        
        # Priority: keyword_path > keyword_paths > keyword > keywords > amadeus custom
        if keyword_path:
            self._keyword_paths = [keyword_path]
            self.keywords = [self._extract_keyword_name(keyword_path)]
        elif keyword_paths:
            self._keyword_paths = keyword_paths
            self.keywords = [self._extract_keyword_name(p) for p in keyword_paths]
        elif keyword:
            self.keywords = [keyword]
        elif keywords:
            self.keywords = keywords
        elif use_custom_amadeus and Path(DEFAULT_CUSTOM_WAKE_WORD_PATH).exists():
            # Use custom Amadeus by default
            self._keyword_paths = [DEFAULT_CUSTOM_WAKE_WORD_PATH]
            self.keywords = ["amadeus"]
            logger.info("Using custom wake word: 'Amadeus'")
        else:
            # Fallback to jarvis
            self.keywords = ["jarvis"]
        
        # Validate built-in keywords (if not custom)
        if not self._keyword_paths:
            for kw in self.keywords:
                if kw.lower() not in AVAILABLE_KEYWORDS:
                    logger.warning(
                        f"Keyword '{kw}' is not built-in. "
                        f"Available: {AVAILABLE_KEYWORDS}"
                    )
        
        # Configure sensitivity
        num_keywords = len(self._keyword_paths) if self._keyword_paths else len(self.keywords)
        if sensitivities:
            self._sensitivities = sensitivities
        else:
            self._sensitivities = [0.5] * num_keywords
        
        # Initialize Porcupine
        try:
            if self._keyword_paths:
                # Custom wake words
                self.porcupine = pvporcupine.create(
                    access_key=self._access_key,
                    keyword_paths=self._keyword_paths,
                    sensitivities=self._sensitivities
                )
                logger.info(
                    f"Porcupine initialized with custom wake words: {self.keywords}, "
                    f"frame_length={self.porcupine.frame_length}"
                )
            else:
                # Built-in wake words
                self.porcupine = pvporcupine.create(
                    access_key=self._access_key,
                    keywords=self.keywords,
                    sensitivities=self._sensitivities
                )
                logger.info(
                    f"Porcupine initialized: keywords={self.keywords}, "
                    f"frame_length={self.porcupine.frame_length}"
                )
        except pvporcupine.PorcupineError as e:
            raise RuntimeError(f"Porcupine initialization error: {e}")
        
        # Properties
        self.frame_length = self.porcupine.frame_length
        self.sample_rate = self.porcupine.sample_rate
        
        self._activated = False
        self._is_listening = False
        self._last_keyword: Optional[str] = None
    
    @staticmethod
    def _extract_keyword_name(path: str) -> str:
        """Extracts keyword name from .ppn file path."""
        # amadeus_en_windows_v3_0_0.ppn -> amadeus
        filename = Path(path).stem
        parts = filename.split("_")
        return parts[0] if parts else filename
    
    def process_frame(self, audio_frame: List[int]) -> bool:
        """
        Processes one audio frame for wake word detection.
        
        Args:
            audio_frame: List of int16 audio values.
                         Length must equal self.frame_length
        
        Returns:
            True if wake word is detected
        """
        if len(audio_frame) != self.frame_length:
            logger.warning(
                f"Incorrect frame length: {len(audio_frame)}, "
                f"expected {self.frame_length}"
            )
            return False
        
        try:
            keyword_index = self.porcupine.process(audio_frame)
            
            if keyword_index >= 0:
                self._activated = True
                self._last_keyword = self.keywords[keyword_index]
                logger.info(f"Wake word detected: '{self._last_keyword}'")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error processing wake word: {e}")
            return False
    
    def is_activated(self) -> bool:
        """
        Checks if wake word was detected.
        
        Resets activation flag after call.
        
        Returns:
            True if wake word was detected since last check
        """
        if self._activated:
            self._activated = False
            return True
        return False
    
    def get_last_keyword(self) -> Optional[str]:
        """
        Returns last detected keyword.
        
        Returns:
            Keyword or None
        """
        return self._last_keyword
    
    def start_listening(self) -> None:
        """Starts listening for wake word."""
        self._is_listening = True
        self._activated = False
        logger.debug("Wake word listening started")
    
    def stop_listening(self) -> None:
        """Stops listening."""
        self._is_listening = False
        logger.debug("Wake word listening stopped")
    
    def set_wake_word(self, word: str) -> bool:
        """
        Changes the wake word.
        
        WARNING: Requires Porcupine reinitialization!
        
        Args:
            word: New wake word (must be from AVAILABLE_KEYWORDS)
            
        Returns:
            True if successfully changed
        """
        if word.lower() not in AVAILABLE_KEYWORDS:
            logger.error(
                f"Wake word '{word}' is not supported. "
                f"Available: {AVAILABLE_KEYWORDS}"
            )
            return False
        
        try:
            # Release previous resource
            if hasattr(self, 'porcupine'):
                self.porcupine.delete()
            
            # Create new with new word
            self.keywords = [word]
            self._sensitivities = [0.5]
            
            self.porcupine = pvporcupine.create(
                access_key=self._access_key,
                keywords=self.keywords,
                sensitivities=self._sensitivities
            )
            
            self.frame_length = self.porcupine.frame_length
            logger.info(f"Wake word changed to: '{word}'")
            return True
            
        except Exception as e:
            logger.error(f"Error changing wake word: {e}")
            return False
    
    def get_frame_length(self) -> int:
        """Returns audio frame size for processing."""
        return self.frame_length
    
    def get_sample_rate(self) -> int:
        """Returns sample rate."""
        return self.sample_rate
    
    def cleanup(self) -> None:
        """Releases Porcupine resources."""
        if hasattr(self, 'porcupine') and self.porcupine:
            self.porcupine.delete()
            logger.debug("Porcupine resources released")
    
    def __del__(self) -> None:
        """Destructor — releases resources."""
        self.cleanup()


class MockWakeWordAdapter(WakeWordPort):
    """
    Mock Wake Word adapter for testing.
    
    Simulates wake word detection after N frames.
    """
    
    def __init__(self, activate_after_frames: int = 10) -> None:
        self._activate_after = activate_after_frames
        self._frame_count = 0
        self._activated = False
        self.frame_length = 512
        self.sample_rate = 16000
    
    def process_frame(self, audio_frame: List[int]) -> bool:
        """Simulates detection after N frames."""
        self._frame_count += 1
        if self._frame_count >= self._activate_after:
            self._activated = True
            self._frame_count = 0
            return True
        return False
    
    def is_activated(self) -> bool:
        """Checks activation."""
        if self._activated:
            self._activated = False
            return True
        return False
    
    def start_listening(self) -> None:
        """Resets counter."""
        self._frame_count = 0
        self._activated = False
    
    def stop_listening(self) -> None:
        """Does nothing."""
        pass
    
    def set_wake_word(self, word: str) -> bool:
        """Always successful."""
        return True
    
    def reset(self) -> None:
        """Resets adapter state."""
        self._frame_count = 0
        self._activated = False
    
    def cleanup(self) -> None:
        """Does nothing."""
        pass
    
    def get_frame_length(self) -> int:
        """Returns frame size."""
        return self.frame_length
