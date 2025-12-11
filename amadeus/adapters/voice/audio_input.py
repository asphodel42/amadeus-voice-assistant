"""
Amadeus Audio Input Adapter

Implements collected audio from microphone using PyAudio.
Provides streaming audio reading for ASR and Wake Word detection.

Usage:
    audio = PyAudioInputAdapter()
    audio.start_stream()
    
    while True:
        frame = audio.read_frame()
        if frame:
            process(frame)
    
    audio.stop_stream()
"""

from __future__ import annotations

import logging
import struct
from typing import Callable, List, Optional, Tuple

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

logger = logging.getLogger(__name__)


class PyAudioInputAdapter:
    """
    PyAudio-based audio adapter.
    
    Provides streaming audio reading from microphone.
    
    Attributes:
        sample_rate: Sample rate (typically 16000 Hz)
        frame_length: Number of samples per frame
        channels: Number of channels (1 = mono)
    """
    
    DEFAULT_SAMPLE_RATE = 16000
    DEFAULT_CHANNELS = 1
    DEFAULT_FORMAT = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
    
    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        frame_length: int = 512,
        channels: int = DEFAULT_CHANNELS,
        input_device_index: Optional[int] = None
    ) -> None:
        """
        Initialize PyAudio adapter.
        
        Args:
            sample_rate: Sample rate in Hz (default: 16000)
            frame_length: Number of samples per frame (for Porcupine = 512)
            channels: Number of channels (1 = mono)
            input_device_index: Input device index (None = default)
        
        Raises:
            RuntimeError: If PyAudio is not available
        """
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError(
                "PyAudio is not installed. Install with: pip install pyaudio\n"
                "On Linux: sudo apt install python3-pyaudio portaudio19-dev"
            )
        
        self.sample_rate = sample_rate
        self.frame_length = frame_length
        self.channels = channels
        self.input_device_index = input_device_index
        
        # Initialize PyAudio
        self._pa = pyaudio.PyAudio()
        self._stream: Optional[pyaudio.Stream] = None
        self._is_streaming = False
        
        logger.info(
            f"PyAudio initialized: sample_rate={sample_rate}, "
            f"frame_length={frame_length}, channels={channels}"
        )
    
    def start_stream(self) -> None:
        """
        Opens audio stream from microphone.
        
        Raises:
            RuntimeError: If unable to open stream
        """
        if self._stream is not None:
            logger.warning("Stream is already open")
            return
        
        try:
            self._stream = self._pa.open(
                rate=self.sample_rate,
                channels=self.channels,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.frame_length,
                input_device_index=self.input_device_index
            )
            self._is_streaming = True
            logger.info("Audio stream opened")
        except Exception as e:
            raise RuntimeError(f"Error opening audio stream: {e}")
    
    def stop_stream(self) -> None:
        """Closes audio stream."""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
                logger.info("Audio stream closed")
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
            finally:
                self._stream = None
                self._is_streaming = False
    
    def pause_stream(self) -> None:
        """
        Temporarily pauses the audio stream without closing it.
        Useful when TTS needs to use the audio output.
        """
        if self._stream and self._is_streaming:
            try:
                self._stream.stop_stream()
                logger.debug("Audio stream paused")
            except Exception as e:
                logger.error(f"Error pausing stream: {e}")
    
    def resume_stream(self) -> None:
        """
        Resumes a paused audio stream.
        """
        if self._stream and not self._stream.is_active():
            try:
                self._stream.start_stream()
                logger.debug("Audio stream resumed")
            except Exception as e:
                logger.error(f"Error resuming stream: {e}")
    
    @property
    def is_active(self) -> bool:
        """Returns True if stream is active."""
        return self._stream is not None and self._stream.is_active()
    
    def read_frame(self) -> Optional[bytes]:
        """
        Reads one frame of audio data.
        
        Returns:
            bytes with audio data or None if error
        """
        if not self._stream:
            logger.warning("Stream is not open")
            return None
        
        try:
            # Check if data is available (to support Ctrl+C on Windows)
            available = self._stream.get_read_available()
            if available < self.frame_length:
                # Not enough data - wait a bit
                import time
                time.sleep(0.01)  # 10ms - allows Ctrl+C to be processed
                return None
            
            data = self._stream.read(
                self.frame_length,
                exception_on_overflow=False
            )
            return data
        except KeyboardInterrupt:
            raise  # Pass Ctrl+C further
        except Exception as e:
            logger.error(f"Error reading audio: {e}")
            return None
    
    def read_frame_as_int16(self) -> Optional[List[int]]:
        """
        Reads one frame and converts to int16 list.
        
        This format is required for Porcupine.
        
        Returns:
            List of int16 values or None
        """
        data = self.read_frame()
        if data is None:
            return None
        
        try:
            # Unpack bytes to int16 list
            unpacked = struct.unpack_from(
                "h" * self.frame_length,
                data
            )
            return list(unpacked)
        except Exception as e:
            logger.error(f"Error converting audio: {e}")
            return None
    
    def read_seconds(
        self, 
        seconds: float,
        stop_check: Optional[Callable[[], bool]] = None,
        stop_on_silence: bool = False,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.0,
        min_speech_duration: float = 0.3,
    ) -> bytes:
        """
        Reads audio for specified number of seconds.
        
        Args:
            seconds: Maximum recording duration in seconds
            stop_check: Function to check if should stop
                       (returns True if should stop)
            stop_on_silence: If True, stop recording after silence is detected
            silence_threshold: RMS threshold below which audio is considered silence (0.0-1.0)
            silence_duration: Seconds of silence before stopping
            min_speech_duration: Minimum speech duration before silence detection kicks in
            
        Returns:
            bytes with audio data
        """
        if not self._stream:
            logger.warning("Stream is not open")
            return b""
        
        num_frames = int(self.sample_rate * seconds / self.frame_length)
        audio_chunks = []
        frames_read = 0
        
        # VAD state
        silence_frames = 0
        speech_detected = False
        frames_per_second = self.sample_rate / self.frame_length
        silence_frames_threshold = int(silence_duration * frames_per_second)
        min_speech_frames = int(min_speech_duration * frames_per_second)
        speech_frames = 0
        
        logger.debug(f"Reading up to {num_frames} frames ({seconds} sec), VAD={'on' if stop_on_silence else 'off'}")
        
        while frames_read < num_frames:
            # Check if should stop
            if stop_check and stop_check():
                logger.debug(f"Stopping recording at frame {frames_read}")
                break
                
            frame = self.read_frame()
            if frame:
                audio_chunks.append(frame)
                frames_read += 1
                
                # VAD: Check if this frame has speech
                if stop_on_silence:
                    rms = self._calculate_rms(frame)
                    
                    if rms > silence_threshold:
                        # Speech detected
                        speech_detected = True
                        speech_frames += 1
                        silence_frames = 0
                    else:
                        # Silence
                        silence_frames += 1
                    
                    # Stop if we had enough speech and now have enough silence
                    if speech_detected and speech_frames >= min_speech_frames:
                        if silence_frames >= silence_frames_threshold:
                            logger.debug(f"Silence detected after {speech_frames} speech frames, stopping")
                            break
            # If frame is None, we just wait (sleep is in read_frame)
        
        audio_data = b"".join(audio_chunks)
        logger.debug(f"Recorded {len(audio_data)} bytes of audio ({frames_read} frames)")
        
        return audio_data
    
    def _calculate_rms(self, audio_data: bytes) -> float:
        """
        Calculate RMS (Root Mean Square) energy of audio frame.
        
        Args:
            audio_data: Raw audio bytes (int16)
            
        Returns:
            Normalized RMS value (0.0 to 1.0)
        """
        try:
            # Unpack bytes to int16 array
            samples = struct.unpack_from("h" * (len(audio_data) // 2), audio_data)
            
            # Calculate RMS
            sum_squares = sum(s * s for s in samples)
            rms = (sum_squares / len(samples)) ** 0.5
            
            # Normalize to 0-1 range (max int16 is 32767)
            return rms / 32767.0
        except Exception:
            return 0.0
        
        return audio_data
    
    def is_streaming(self) -> bool:
        """Checks if stream is active."""
        return self._is_streaming and self._stream is not None
    
    def get_available_devices(self) -> List[dict]:
        """
        Returns list of available input audio devices.
        
        Returns:
            List of dicts with device information:
            [{"index": 0, "name": "Microphone", "channels": 2, ...}, ...]
        """
        devices = []
        
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            
            # Only input devices
            if info.get("maxInputChannels", 0) > 0:
                devices.append({
                    "index": i,
                    "name": info.get("name", "Unknown"),
                    "channels": info.get("maxInputChannels", 0),
                    "sample_rate": int(info.get("defaultSampleRate", 0)),
                    "is_default": i == self._pa.get_default_input_device_info().get("index")
                })
        
        return devices
    
    def set_device(self, device_index: int) -> bool:
        """
        Sets input device.
        
        WARNING: If stream is open, it will be restarted!
        
        Args:
            device_index: Device index
            
        Returns:
            True if successful
        """
        was_streaming = self._is_streaming
        
        if was_streaming:
            self.stop_stream()
        
        self.input_device_index = device_index
        logger.info(f"Input device changed to: {device_index}")
        
        if was_streaming:
            self.start_stream()
        
        return True
    
    def cleanup(self) -> None:
        """Releases all PyAudio resources."""
        self.stop_stream()
        if self._pa:
            self._pa.terminate()
            logger.debug("PyAudio terminated")
    
    def __del__(self) -> None:
        """Destructor — releases resources."""
        self.cleanup()
    
    def __enter__(self) -> "PyAudioInputAdapter":
        """Context manager entry."""
        self.start_stream()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()


class MockAudioInputAdapter:
    """
    Mock audio adapter for testing.
    
    Generates silence or predefined data.
    """
    
    def __init__(self, frame_length: int = 512) -> None:
        self.frame_length = frame_length
        self.sample_rate = 16000
        self._is_streaming = False
    
    def start_stream(self) -> None:
        """Starts mock stream."""
        self._is_streaming = True
    
    def stop_stream(self) -> None:
        """Stops mock stream."""
        self._is_streaming = False
    
    def read_frame(self) -> bytes:
        """Returns silence (zeros)."""
        return b'\x00' * (self.frame_length * 2)  # 2 bytes per int16
    
    def read_frame_as_int16(self) -> List[int]:
        """Returns list of zeros."""
        return [0] * self.frame_length
    
    def is_streaming(self) -> bool:
        """Checks mock state."""
        return self._is_streaming
    
    def cleanup(self) -> None:
        """Does nothing."""
        pass
