"""
Base OS Adapter

Base class for OS-specific adapters.
Contains shared logic and interface.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class BaseOSAdapter(ABC):
    """
    Base class for OS-specific adapters.

    Contains shared logic for security checks and provides
    abstract methods for OS-specific implementations.
    """

    def __init__(self) -> None:
        # Allowed directories for file operations
        self._allowed_directories: Set[Path] = set()
        self._init_default_allowed_directories()

        # Whitelist of allowed apps
        self._allowed_apps: Dict[str, str] = {}
        self._init_default_allowed_apps()

        # Search engines
        self._search_engines: Dict[str, str] = {
            "default": "https://duckduckgo.com/?q={}",
            "duckduckgo": "https://duckduckgo.com/?q={}",
            "google": "https://www.google.com/search?q={}",
        }

    def _init_default_allowed_directories(self) -> None:
        """Init allowed directories by default."""
        home = Path.home()
        self._allowed_directories = {
            home / "Documents",
            home / "Downloads",
            home / "Desktop",
            home / "Pictures",
            home / "Music",
            home / "Videos",
        }

        # Create directories if they don't exist
        for directory in self._allowed_directories:
            directory.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def _init_default_allowed_apps(self) -> None:
        """Init whitelist of allowed apps (OS-specific)."""
        ...

    # ============================================
    # Path Validation
    # ============================================

    def is_path_allowed(self, path: str, operation: str = "read") -> bool:
        """
        Checks if the operation is allowed for the path.

        Args:
            path: Path to check
            operation: Type of operation (read, write, delete)

        Returns:
            True if allowed
        """
        try:
            # Security: Block obvious path traversal attempts before resolution
            path_str = str(path)
            if ".." in path_str or path_str.startswith("/") or (len(path_str) > 1 and path_str[1] == ":"):
                # Allow absolute paths, but be careful with ..
                if ".." in path_str:
                    # Check if .. is used for traversal
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Path traversal attempt detected: {path}")
            
            target = Path(path).expanduser().resolve()
            
            # Security: Check for symlinks (they could point outside allowed dirs)
            if target.is_symlink():
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Symlink detected: {path} -> {target}")
                # Resolve and check the actual target
                target = target.resolve(strict=False)

            # Check if the path is within allowed directories
            for allowed in self._allowed_directories:
                try:
                    # Security: Ensure target is actually under allowed directory
                    # This handles the resolved path, preventing traversal
                    target.relative_to(allowed)
                    
                    # Additional check: Make sure resolved path is really under allowed
                    if not str(target).startswith(str(allowed)):
                        continue
                    
                    return True
                except ValueError:
                    continue
            
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Path validation error for '{path}': {e}")
            return False

    def add_allowed_directory(self, path: str) -> bool:
        """Adds a directory to the allowed list."""
        try:
            directory = Path(path).expanduser().resolve()
            if directory.is_dir():
                self._allowed_directories.add(directory)
                return True
            return False
        except Exception:
            return False

    def remove_allowed_directory(self, path: str) -> bool:
        """Removes a directory from the allowed list."""
        try:
            directory = Path(path).expanduser().resolve()
            self._allowed_directories.discard(directory)
            return True
        except Exception:
            return False

    def get_allowed_directories(self) -> List[str]:
        """Returns a list of allowed directories."""
        return [str(d) for d in self._allowed_directories]

    # ============================================
    # App Management
    # ============================================

    def is_app_allowed(self, app_name: str) -> bool:
        """Checks if the app is in the whitelist."""
        return app_name.lower() in self._allowed_apps

    def get_app_path(self, app_name: str) -> Optional[Path]:
        """Gets the full path to the app."""
        app_key = app_name.lower()
        if app_key in self._allowed_apps:
            path_str = self._allowed_apps[app_key]
            if path_str:
                return Path(path_str)
        return None

    def add_allowed_app(self, name: str, path: str = "") -> None:
        """Adds an app to the whitelist."""
        self._allowed_apps[name.lower()] = path

    def get_allowed_apps(self) -> List[str]:
        """Returns a list of allowed apps."""
        return list(self._allowed_apps.keys())

    # ============================================
    # FileSystem Operations (Abstract)
    # ============================================

    @abstractmethod
    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        """Returns a list of files and folders."""
        ...

    @abstractmethod
    def read_file(self, path: str, max_bytes: int = 10240) -> str:
        """Reads the contents of a file."""
        ...

    @abstractmethod
    def create_file(self, path: str, content: str = "") -> bool:
        """Creates a new file."""
        ...

    @abstractmethod
    def write_file(self, path: str, content: str, overwrite: bool = False) -> bool:
        """Writes content to a file."""
        ...

    @abstractmethod
    def delete_path(self, path: str, recursive: bool = False) -> bool:
        """Deletes a file or folder."""
        ...

    def path_exists(self, path: str) -> bool:
        """Checks if a path exists."""
        try:
            return Path(path).expanduser().exists()
        except Exception:
            return False

    # ============================================
    # Process Operations (Abstract)
    # ============================================

    @abstractmethod
    def open_app(self, app_name: str, args: Optional[List[str]] = None) -> bool:
        """Opens the app."""
        ...

    # ============================================
    # Browser Operations (Abstract)
    # ============================================

    @abstractmethod
    def open_url(self, url: str) -> bool:
        """Opens the URL in the browser."""
        ...

    def search_web(self, query: str, engine: str = "default") -> bool:
        """Performs a web search."""
        url_template = self._search_engines.get(engine, self._search_engines["default"])
        # URL encode query
        from urllib.parse import quote_plus
        url = url_template.format(quote_plus(query))
        return self.open_url(url)

    def is_url_safe(self, url: str) -> bool:
        """Checks if the URL is safe."""
        url_lower = url.lower()
        return url_lower.startswith("https://") or url_lower.startswith("http://localhost")

    # ============================================
    # System Info (Abstract)
    # ============================================

    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """Returns information about the system."""
        ...

    @abstractmethod
    def get_memory_info(self) -> Dict[str, int]:
        """Returns information about memory."""
        ...

    @abstractmethod
    def get_disk_info(self) -> List[Dict[str, Any]]:
        """Returns information about disks."""
        ...
