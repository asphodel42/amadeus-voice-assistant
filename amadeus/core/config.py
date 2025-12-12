"""
Configuration utilities for Amadeus Voice Assistant.

Provides centralized access to configuration from environment variables.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_data_folder() -> Path:
    """
    Get the data folder path from environment or default.
    
    Returns:
        Path object pointing to the data folder
    """
    data_folder = os.getenv("DATA_FOLDER", "data")
    path = Path(data_folder)
    
    # Create folder if it doesn't exist
    path.mkdir(parents=True, exist_ok=True)
    
    return path


def get_audit_db_path() -> Path:
    """
    Get the audit database path.
    
    Returns:
        Path object pointing to audit.db
    """
    return get_data_folder() / "audit.db"


def get_picovoice_key() -> Optional[str]:
    """
    Get Picovoice access key from environment.
    
    Returns:
        Access key or None if not set
    """
    return os.getenv("PICOVOICE_ACCESS_KEY")


def get_vosk_model_path() -> Optional[str]:
    """
    Get Vosk model path from environment (legacy).
    
    Returns:
        Model path or None if not set
    """
    return os.getenv("VOSK_MODEL_PATH")
