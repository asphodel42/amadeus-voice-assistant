"""
Tests for Voice Adapters

Unit tests for TTS, ASR, Wake Word, and Audio Input adapters.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from amadeus.adapters.voice.tts import Pyttsx3Adapter, SilentTTSAdapter
from amadeus.adapters.voice.asr import WhisperASRAdapter, MockASRAdapter
from amadeus.adapters.voice.wake_word import (
    PorcupineWakeWordAdapter,
    MockWakeWordAdapter,
    AVAILABLE_KEYWORDS,
)
from amadeus.adapters.voice.audio_input import MockAudioInputAdapter


class TestSilentTTSAdapter:
    """Tests for SilentTTSAdapter (mock TTS)."""
    
    def test_speak_does_nothing(self):
        """Silent adapter should not raise on speak()."""
        tts = SilentTTSAdapter()
        # Should not raise
        tts.speak("Hello world")
    
    def test_stop_does_nothing(self):
        """Silent adapter should not raise on stop()."""
        tts = SilentTTSAdapter()
        tts.stop()
    
    def test_get_available_voices_returns_empty(self):
        """Silent adapter should return empty list."""
        tts = SilentTTSAdapter()
        voices = tts.get_available_voices()
        assert voices == []
    
    def test_set_rate_does_nothing(self):
        """Silent adapter should not raise on set_rate()."""
        tts = SilentTTSAdapter()
        tts.set_rate(200)
    
    def test_set_volume_does_nothing(self):
        """Silent adapter should not raise on set_volume()."""
        tts = SilentTTSAdapter()
        tts.set_volume(0.5)


class TestMockASRAdapter:
    """Tests for MockASRAdapter."""
    
    def test_transcribe_buffers_audio(self):
        """Mock adapter should buffer audio (returns empty like Whisper)."""
        asr = MockASRAdapter(preset_text="open calculator")
        result = asr.transcribe(b"audio data")
        # Whisper-style: transcribe() just buffers, returns empty
        assert result == ""
    
    def test_stop_stream_returns_preset_text(self):
        """Mock adapter should return preset text on stop_stream."""
        asr = MockASRAdapter(preset_text="open calculator")
        asr.start_stream()
        asr.transcribe(b"audio data")
        result = asr.stop_stream()
        assert result == "open calculator"
    
    def test_transcribe_empty_by_default(self):
        """Mock adapter should return empty string by default."""
        asr = MockASRAdapter()
        result = asr.transcribe(b"audio data")
        assert result == ""
    
    def test_start_stop_stream(self):
        """Mock adapter should handle stream start/stop."""
        asr = MockASRAdapter()
        asr.start_stream()
        asr.stop_stream()
    
    def test_get_partial_result(self):
        """Mock adapter should return empty (Whisper has no partial results)."""
        asr = MockASRAdapter(preset_text="test")
        result = asr.get_partial_result()
        # Whisper doesn't support partial results
        assert result == ""


class TestMockWakeWordAdapter:
    """Tests for MockWakeWordAdapter."""
    
    def test_activate_after_frames(self):
        """Mock adapter should activate after N frames."""
        wake = MockWakeWordAdapter(activate_after_frames=3)
        
        # First 2 frames - not activated
        assert wake.process_frame([0] * 512) is False
        assert wake.process_frame([0] * 512) is False
        
        # Third frame - activated
        assert wake.process_frame([0] * 512) is True
    
    def test_is_activated(self):
        """Mock adapter should track activation state."""
        wake = MockWakeWordAdapter(activate_after_frames=1)
        
        assert wake.is_activated() is False
        wake.process_frame([0] * 512)
        assert wake.is_activated() is True
        # Should reset after check
        assert wake.is_activated() is False
    
    def test_frame_length(self):
        """Mock adapter should have frame_length attribute."""
        wake = MockWakeWordAdapter()
        assert wake.frame_length == 512
    
    def test_sample_rate(self):
        """Mock adapter should have sample_rate attribute."""
        wake = MockWakeWordAdapter()
        assert wake.sample_rate == 16000
    
    def test_cleanup(self):
        """Mock adapter should handle cleanup."""
        wake = MockWakeWordAdapter()
        wake.cleanup()  # Should not raise
    
    def test_reset(self):
        """Mock adapter should handle reset."""
        wake = MockWakeWordAdapter(activate_after_frames=2)
        wake.process_frame([0] * 512)
        wake.reset()
        # After reset, should need full count again
        assert wake.process_frame([0] * 512) is False


class TestMockAudioInputAdapter:
    """Tests for MockAudioInputAdapter."""
    
    def test_start_stop_stream(self):
        """Mock adapter should handle stream start/stop."""
        audio = MockAudioInputAdapter()
        audio.start_stream()
        assert audio.is_streaming() is True
        audio.stop_stream()
        assert audio.is_streaming() is False
    
    def test_read_frame_returns_silence(self):
        """Mock adapter should return silence."""
        audio = MockAudioInputAdapter(frame_length=512)
        frame = audio.read_frame()
        assert len(frame) == 512 * 2  # 2 bytes per int16
        assert frame == b'\x00' * (512 * 2)
    
    def test_read_frame_as_int16(self):
        """Mock adapter should return list of zeros."""
        audio = MockAudioInputAdapter(frame_length=512)
        frame = audio.read_frame_as_int16()
        assert len(frame) == 512
        assert all(x == 0 for x in frame)
    
    def test_cleanup(self):
        """Mock adapter should handle cleanup."""
        audio = MockAudioInputAdapter()
        audio.cleanup()


class TestAvailableKeywords:
    """Tests for wake word keywords."""
    
    def test_jarvis_in_available(self):
        """Jarvis should be an available keyword."""
        assert "jarvis" in AVAILABLE_KEYWORDS
    
    def test_computer_in_available(self):
        """Computer should be an available keyword."""
        assert "computer" in AVAILABLE_KEYWORDS
    
    def test_alexa_in_available(self):
        """Alexa should be an available keyword."""
        assert "alexa" in AVAILABLE_KEYWORDS


# Integration tests (require actual libraries)
class TestPyttsx3AdapterIntegration:
    """Integration tests for Pyttsx3Adapter."""
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires audio output
        reason="Requires audio output device"
    )
    def test_speak_integration(self):
        """Test actual speech synthesis."""
        tts = Pyttsx3Adapter()
        tts.speak("Test")


class TestWhisperASRAdapterIntegration:
    """Integration tests for WhisperASRAdapter."""
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires model download
        reason="Requires Whisper model download"
    )
    def test_transcribe_integration(self):
        """Test actual speech recognition."""
        asr = WhisperASRAdapter(model_size="tiny")
        asr.start_stream()
        asr.transcribe(b"\x00" * 16000)  # 1 second of silence
        result = asr.stop_stream()


class TestPorcupineAdapterIntegration:
    """Integration tests for PorcupineWakeWordAdapter."""
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires API key
        reason="Requires Picovoice AccessKey"
    )
    def test_process_frame_integration(self):
        """Test actual wake word detection."""
        wake = PorcupineWakeWordAdapter()
        result = wake.process_frame([0] * wake.frame_length)
