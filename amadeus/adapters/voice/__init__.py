"""
Amadeus Voice Adapters Package

Adapters for voice processing:
- Wake Word Detection
- ASR (Automatic Speech Recognition)
- NLU (Natural Language Understanding)
- TTS (Text-to-Speech)
"""

from amadeus.adapters.voice.nlu import DeterministicNLU

__all__ = [
    "DeterministicNLU",
]
