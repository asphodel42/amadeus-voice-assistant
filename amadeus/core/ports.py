"""
Amadeus Core Domain Ports (Interfaces)

This module defines all ports (interfaces) of the system.
Ports are contracts that are implemented by adapters in the infrastructure layer.

Principle: The domain defines WHAT needs to be done.
           Adapters define HOW to do it.
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from amadeus.core.entities import (
        ActionPlan,
        AuditEvent,
        Capability,
        CapabilityManifest,
        ExecutionResult,
        Intent,
    )


# ============================================
# OS Adapter Ports
# ============================================

@runtime_checkable
class ProcessPort(Protocol):
    """
    Port for process management.

    Implementations:
        - WindowsAdapter
        - LinuxAdapter
    """

    @abstractmethod
    def open_app(self, app_name: str, args: Optional[List[str]] = None) -> bool:
        """
        Open application by name.
        
        Args:
            app_name: Name or path to the application
            args: Command line arguments

        Returns:
            True if successfully launched

        Raises:
            PermissionError: If permission is denied
            FileNotFoundError: If application is not found
        """
        ...

    @abstractmethod
    def is_app_allowed(self, app_name: str) -> bool:
        """Checks if an application is in the allowed list."""
        ...

    @abstractmethod
    def get_app_path(self, app_name: str) -> Optional[Path]:
        """Gets the full path to the application."""
        ...


@runtime_checkable
class FileSystemPort(Protocol):
    """
    Port for file system operations.

    SECURITY: All operations are checked against allowed paths.
    """

    @abstractmethod
    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        """
        Returns a list of files and folders.

        Args:
            path: Path to the directory

        Returns:
            A list of dictionaries with file information:
            [{"name": "file.txt", "type": "file", "size": 1024}, ...]
        """
        ...

    @abstractmethod
    def read_file(self, path: str, max_bytes: int = 10240) -> str:
        """
        Reads the contents of a file (with size limits).

        Args:
            path: Path to the file
            max_bytes: Maximum size to read

        Returns:
            File content as a string
        """
        ...

    @abstractmethod
    def create_file(self, path: str, content: str = "") -> bool:
        """
        Creates a new file.

        Args:
            path: Path to the file
            content: Initial content

        Returns:
            True if successfully created

        Raises:
            FileExistsError: If file already exists
            PermissionError: If permission is denied
        """
        ...

    @abstractmethod
    def write_file(self, path: str, content: str, overwrite: bool = False) -> bool:
        """
        Writes content to a file.

        Args:
            path: Path to the file
            content: Content to write
            overwrite: Whether to overwrite existing file

        Returns:
            True if successfully written
        """
        ...

    @abstractmethod
    def delete_path(self, path: str, recursive: bool = False) -> bool:
        """
        Deletes a file or folder.

        Args:
            path: Path to the file/folder
            recursive: Whether to delete recursively (for folders)

        Returns:
            True if successfully deleted
        """
        ...

    @abstractmethod
    def delete_path(self, path: str, recursive: bool = False) -> bool:
        """
        Deletes a file or folder.

        WARNING: Destructive operation! Requires typed confirmation.

        Args:
            path: Path to the file/folder
            recursive: Whether to delete recursively (for folders)

        Returns:
            True if successfully deleted
        """
        ...

    @abstractmethod
    def is_path_allowed(self, path: str, operation: str) -> bool:
        """
        Checks if an operation is allowed for a path.

        Args:
            path: Path to check
            operation: Type of operation (read, write, delete)

        Returns:
            True if allowed
        """
        ...

    @abstractmethod
    def path_exists(self, path: str) -> bool:
        """Checks if a path exists."""
        ...


@runtime_checkable
class BrowserPort(Protocol):
    """
    Port for browser operations.

    SECURITY: Only opening URLs via the system browser.
             No hidden network requests.
    """

    @abstractmethod
    def open_url(self, url: str) -> bool:
        """
        Opens a URL in the default browser.

        Args:
            url: URL to open

        Returns:
            True if successfully opened
        """
        ...

    @abstractmethod
    def search_web(self, query: str, engine: str = "default") -> bool:
        """
        Performs a web search.

        Args:
            query: Search query
            engine: Search engine (default, google, duckduckgo)

        Returns:
            True if successfully opened search
        """
        ...

    @abstractmethod
    def is_url_safe(self, url: str) -> bool:
        """
        Checks if a URL is safe.

        Args:
            url: URL to check

        Returns:
            True for HTTPS URLs and allowed domains
        """
        ...


@runtime_checkable
class SystemInfoPort(Protocol):
    """Port for system information retrieval."""

    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """
        Returns general information about the system.
        
        Returns:
            {"os": "Windows 11", "cpu": "...", "memory": {...}, ...}
        """
        ...

    @abstractmethod
    def get_memory_info(self) -> Dict[str, int]:
        """Returns memory information."""
        ...

    @abstractmethod
    def get_disk_info(self) -> List[Dict[str, Any]]:
        """Returns disk information."""
        ...


# ============================================
# Voice Pipeline Ports
# ============================================

@runtime_checkable
class WakeWordPort(Protocol):
    """Port for wake word recognition."""

    @abstractmethod
    def start_listening(self) -> None:
        """Starts listening for the wake word."""
        ...

    @abstractmethod
    def stop_listening(self) -> None:
        """Stops listening for the wake word."""
        ...

    @abstractmethod
    def is_activated(self) -> bool:
        """Checks if the wake word has been detected."""
        ...

    @abstractmethod
    def set_wake_word(self, word: str) -> bool:
        """Sets the wake word."""
        ...


@runtime_checkable
class ASRPort(Protocol):
    """Порт для розпізнавання мови (Automatic Speech Recognition)."""

    @abstractmethod
    def transcribe(self, audio_data: bytes) -> str:
        """
        Transcribes audio to text.

        Args:
            audio_data: Audio data in PCM format

        Returns:
            Recognized text
        """
        ...

    @abstractmethod
    def start_stream(self) -> None:
        """Starts streaming recognition."""
        ...

    @abstractmethod
    def stop_stream(self) -> str:
        """
        Stops streaming recognition.

        Returns:
            Final recognized text
        """
        ...


@runtime_checkable
class NLUPort(Protocol):
    """Port for natural language understanding (NLU)."""

    @abstractmethod
    def parse(self, text: str) -> "Intent":
        """
        Parses text into a structured intent.
        
        Args:
            text: Command text

        Returns:
            Recognized intent with slots
        """
        ...


@runtime_checkable
class TTSPort(Protocol):
    """Port for text-to-speech synthesis (TTS)."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """
        Speaks the given text.
        
        Args:
            text: Text to be spoken
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stops the current speech."""
        ...


# ============================================
# Persistence Ports
# ============================================

@runtime_checkable
class AuditPort(Protocol):
    """
    Port for audit logging.

    IMPORTANT: The log is append-only to ensure integrity.
    """

    @abstractmethod
    def append_event(self, event: "AuditEvent") -> str:
        """
        Adds an event to the log.

        Args:
            event: Event to log

        Returns:
            ID of the created event
        """
        ...

    @abstractmethod
    def get_events(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List["AuditEvent"]:
        """
        Retrieves events from the log.

        Args:
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            event_type: Filter by event type
            limit: Maximum number of events
            
        Returns:
            List of events
        """
        ...

    @abstractmethod
    def verify_integrity(self) -> bool:
        """
        Verifies the integrity of the log (hash chain).

        Returns:
            True if the log has not been modified
        """
        ...

    @abstractmethod
    def get_last_hash(self) -> str:
        """Returns the hash of the last event."""
        ...


@runtime_checkable
class ConfigPort(Protocol):
    """Port for configuration storage."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value."""
        ...

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Sets a configuration value."""
        ...

    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """Returns all configuration."""
        ...


# ============================================
# Security Ports
# ============================================

@runtime_checkable
class PolicyPort(Protocol):
    """
    Port for the security policy engine.

    Evaluates ActionPlan against capabilities and risk rules.
    """

    @abstractmethod
    def evaluate(
        self,
        plan: "ActionPlan",
        capabilities: List["Capability"]
    ) -> "PolicyDecision":
        """
        Evaluates the action plan.

        Args:
            plan: Action plan to evaluate
            capabilities: Available capabilities

        Returns:
            Policy decision (allowed/denied + reason)
        """
        ...

    @abstractmethod
    def get_required_confirmations(self, plan: "ActionPlan") -> List[str]:
        """
        Determines the required confirmations for plan.

        Args:
            plan: Action plan to evaluate

        Returns:
            List of confirmation descriptions
        """
        ...


@runtime_checkable
class SignaturePort(Protocol):
    """Port for verifying plugin signatures."""

    @abstractmethod
    def verify_manifest(self, manifest: "CapabilityManifest") -> bool:
        """
        Verifies the signature of the manifest.
        
        Returns:
            True if the signature is valid
        """
        ...

    @abstractmethod
    def sign_manifest(self, manifest: "CapabilityManifest", private_key: bytes) -> str:
        """
        Signs the manifest.

        Returns:
            Signature in Base64 format
        """
        ...

    @abstractmethod
    def add_trusted_publisher(self, publisher_id: str, public_key: bytes) -> None:
        """Adds a trusted publisher."""
        ...


# ============================================
# UI Ports
# ============================================

@runtime_checkable
class DialogPort(Protocol):
    """Port for user dialog."""

    @abstractmethod
    def show_message(self, message: str, title: str = "Amadeus") -> None:
        """Shows an informational message."""
        ...

    @abstractmethod
    def show_error(self, message: str, title: str = "Error") -> None:
        """Shows an error message."""
        ...

    @abstractmethod
    def show_confirmation(
        self,
        plan: "ActionPlan",
        timeout_seconds: int = 30
    ) -> bool:
        """
        Shows a confirmation dialog for the plan.

        Args:
            plan: Action plan to confirm
            timeout_seconds: Timeout duration

        Returns:
            True if the user confirmed
        """
        ...

    @abstractmethod
    def show_typed_confirmation(
        self,
        plan: "ActionPlan",
        confirmation_phrase: str
    ) -> bool:
        """
        Shows a dialog with typed confirmation for destructive operations.

        Args:
            plan: Action plan to confirm
            confirmation_phrase: Phrase that the user must enter

        Returns:
            True if the user entered the correct phrase
        """
        ...


# ============================================
# Supporting Types
# ============================================

@runtime_checkable
class PolicyDecision(Protocol):
    """Result of policy evaluation."""

    @property
    def allowed(self) -> bool:
        """Is execution allowed?"""
        ...
    
    @property
    def reason(self) -> str:
        """Reason for the decision."""
        ...
    
    @property
    def requires_confirmation(self) -> bool:
        """Is confirmation required?"""
        ...
    
    @property
    def confirmation_type(self) -> str:
        """Type of confirmation (simple, typed, passcode)."""
        ...
