"""
Amadeus Voice Adapters Package

Адаптери для голосової обробки:
- Wake Word Detection
- ASR (Automatic Speech Recognition)
- NLU (Natural Language Understanding)
- TTS (Text-to-Speech)
"""

from amadeus.adapters.voice.nlu import DeterministicNLU

__all__ = [
    "DeterministicNLU",
]
