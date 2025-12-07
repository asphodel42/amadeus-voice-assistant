"""
Amadeus Voice Adapters Package

Adapters for voice processing:
- Wake Word Detection (Porcupine)
- ASR (Automatic Speech Recognition / Faster-Whisper)
- NLU (Natural Language Understanding)
- TTS (Text-to-Speech / pyttsx3)
- Audio Input (PyAudio)
"""

from amadeus.adapters.voice.nlu import DeterministicNLU
from amadeus.adapters.voice.tts import Pyttsx3Adapter, SilentTTSAdapter
from amadeus.adapters.voice.asr import WhisperASRAdapter, MockASRAdapter
from amadeus.adapters.voice.wake_word import PorcupineWakeWordAdapter, MockWakeWordAdapter
from amadeus.adapters.voice.audio_input import PyAudioInputAdapter, MockAudioInputAdapter

__all__ = [
    # NLU
    "DeterministicNLU",
    # TTS
    "Pyttsx3Adapter",
    "SilentTTSAdapter",
    # ASR
    "WhisperASRAdapter",
    "MockASRAdapter",
    # Wake Word
    "PorcupineWakeWordAdapter",
    "MockWakeWordAdapter",
    # Audio Input
    "PyAudioInputAdapter",
    "MockAudioInputAdapter",
]
