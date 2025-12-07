"""
Amadeus ASR (Automatic Speech Recognition) Adapter

Implementation of speech recognition using Faster-Whisper.
Works fully offline, accepts ukrainian + english words.

Usage:
```
    asr = WhisperASRAdapter(model_size="small")
    asr.start_stream()
    # ... accumulate audio ...
    final_text = asr.stop_stream()
```
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

import numpy as np

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from amadeus.core.ports import ASRPort

logger = logging.getLogger(__name__)


# Types of model sizes
ModelSize = Literal["tiny", "base", "small", "medium", "large-v2", "large-v3"]


class WhisperASRAdapter(ASRPort):
    """
    ASR adapter based on Faster-Whisper.
    
    Benefits:
        - Fully offline
        - Multilanguage
        - High quality recognition
        - Optimized speed (CTranslate2)
    
    Size of models:
        - tiny: 39MB, fast, basic speed
        - base: 74MB, fast, good quality
        - small: 244MB, medium, very good quality
        - medium: 769MB, slow, perfect quality
        - large-v3: 1.5GB, very small, the best quality
    
    Attributes:
        model: Faster-Whisper model
        sample_rate: Frequency of discrete (16000 Hz)
        language: Language for recognition (None = auto-detection)
    """
    
    DEFAULT_SAMPLE_RATE = 16000
    DEFAULT_MODEL_SIZE: ModelSize = "small"
    
    def __init__(
        self,
        model_size: ModelSize = DEFAULT_MODEL_SIZE,
        language: Optional[str] = None,
        device: str = "cpu",
        compute_type: str = "auto",
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> None:
        """
        Initialize Faster-Whisper ASR adapter.
        
        Args:
            model_size: Size of model (tiny/base/small/medium/large-v2/large-v3)
            language: Language for recognition (None = auto, "uk" = ukrainian)
            device: Device for calculations ("cpu", "cuda", "auto")
            compute_type: Type of calculations ("auto", "int8", "float16", "float32")
            sample_rate: Frequency of discrete (for default 16000 Hz)
        
        Raises:
            RuntimeError: If faster-whisper is not available
        """
        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "faster-whisper is not installed. Install it with: pip install faster-whisper"
            )
        
        self.model_size = model_size
        self.language = language
        self.sample_rate = sample_rate
        
        # On CPU use int8 for speed
        if compute_type == "auto":
            compute_type = "int8" if device == "cpu" else "float16"
        
        # Loading model
        logger.info(f"Завантаження Whisper моделі: {model_size} (device={device}, compute={compute_type})")
        
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        
        self._is_streaming = False
        self._audio_buffer: List[bytes] = []
        self._partial_result = ""
        
        logger.info(f"Whisper ASR ініціалізовано: model={model_size}, language={language or 'auto'}")
    
    def transcribe(self, audio_data: bytes) -> str:
        """
        Add audio data to buffer.
        
        Whisper does not accept stream recognition, so we store
        audio and recognize all together in stop_stream().
        
        Args:
            audio_data: Audio data in PCM 16-bit mono format
        
        Returns:
            Empty string (result will be in stop_stream)
        """
        if audio_data:
            self._audio_buffer.append(audio_data)
        return ""
    
    def start_stream(self) -> None:
        """
        Starts a new recognition session.
        
        Clear audio buffer.
        """
        self._audio_buffer = []
        self._is_streaming = True
        self._partial_result = ""
        logger.debug("Whisper streaming started")
    
    def stop_stream(self) -> str:
        """
        Stops recognition and transcribe accumulated audio.
        
        Returns:
            Recognized text
        """
        self._is_streaming = False
        
        if not self._audio_buffer:
            logger.debug("Audio buffer is empty")
            return ""
        
        try:
            # Combine all audio chunks
            audio_bytes = b"".join(self._audio_buffer)
            
            # Converts bytes in numpy array (float32)
            audio_array = self._bytes_to_float32(audio_bytes)
            
            audio_duration = len(audio_array) / self.sample_rate
            logger.debug(f"Audio duration: {audio_duration:.2f} sec, samples: {len(audio_array)}")
            
            if len(audio_array) < self.sample_rate * 0.3:  # Less than 0.3 seconds
                logger.debug("Audio is too short for recognition")
                return ""
            
            # Transcribve with less aggressive settings
            segments, info = self.model.transcribe(
                audio_array,
                language=self.language,
                beam_size=5,
                best_of=5,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=False,  # Disabled - may filter out quiet speech
            )
            
            # Collect text from all segments (segments - is generator!)
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
                logger.debug(f"Segment: '{segment.text.strip()}'")
            
            text = " ".join(text_parts).strip()
            
            if text:
                detected_lang = info.language if hasattr(info, 'language') else "unknown"
                logger.info(f"Whisper result: '{text}' (lang={detected_lang})")
            else:
                logger.debug("Whisper does not recognize any speech")
            
            return text
            
        except Exception as e:
            logger.error(f"Whisper ASR error: {e}")
            return ""
        finally:
            self._audio_buffer = []
    
    def get_partial_result(self) -> str:
        """
        Returns current partial result.
        
        Whisper does not support partial results in real time,
        so return empty string.
        
        Returns:
            Empty string
        """
        return ""
    
    def is_streaming(self) -> bool:
        """Checks if a streaming session is active."""
        return self._is_streaming
    
    def _bytes_to_float32(self, audio_bytes: bytes) -> np.ndarray:
        """
        Converts PCM 16-bit audio bytes to float32 numpy array.
        
        Args:
            audio_bytes: Audio in PCM 16-bit mono format
            
        Returns:
            Numpy array with float32 values [-1.0, 1.0]
        """
        # Convert bytes to int16
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        
        # Normalize to float32 [-1.0, 1.0]
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        return audio_float32
    
    @staticmethod
    def list_available_models() -> List[str]:
        """
        Return a list of allowed sizes of models.
        
        Returns:
            List of model names
        """
        return ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
    
    @staticmethod
    def get_model_info(model_size: str) -> dict:
        """
        Returns information about the model.
        
        Args:
            model_size: Model name
            
        Returns:
            Dictionary with information
        """
        info = {
            "tiny": {"size_mb": 39, "speed": "fast", "quality": "basic"},
            "base": {"size_mb": 74, "speed": "fast", "quality": "good"},
            "small": {"size_mb": 244, "speed": "medium", "quality": "very good"},
            "medium": {"size_mb": 769, "speed": "slow", "quality": "excellent"},
            "large-v2": {"size_mb": 1550, "speed": "very slow", "quality": "best"},
            "large-v3": {"size_mb": 1550, "speed": "very slow", "quality": "best"},
        }
        return info.get(model_size, {})


class MockASRAdapter(ASRPort):
    """
    Mock ASR adapter for test.
    
    Return pre-writtent text.
    """
    
    def __init__(self, preset_text: str = "") -> None:
        self.preset_text = preset_text
        self._call_count = 0
        self._is_streaming = False
    
    def transcribe(self, audio_data: bytes) -> str:
        """Returns empty text (as Whisper)."""
        return ""
    
    def start_stream(self) -> None:
        """Starts mock session."""
        self._call_count = 0
        self._is_streaming = True
    
    def stop_stream(self) -> str:
        """Stops mock session."""
        self._call_count += 1
        self._is_streaming = False
        return self.preset_text
    
    def get_partial_result(self) -> str:
        """Returns empty text."""
        return ""
