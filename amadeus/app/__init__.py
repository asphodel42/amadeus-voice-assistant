"""
Amadeus Application Layer Package

Оркестрація та управління пайплайном обробки команд.
"""

from amadeus.app.pipeline import VoicePipeline
from amadeus.app.executor import ActionExecutor

__all__ = [
    "VoicePipeline",
    "ActionExecutor",
]
