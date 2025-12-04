"""
Windows OS Adapter

Адаптер для Windows-специфічних операцій.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

from amadeus.adapters.os.base import BaseOSAdapter


class WindowsAdapter(BaseOSAdapter):
    """
    Адаптер для Windows.
    
    Реалізує всі OS-специфічні операції для Windows 10/11.
    """

    def _init_default_allowed_apps(self) -> None:
        """Ініціалізує білий список додатків для Windows."""
        self._allowed_apps = {
            # Системні утиліти
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "terminal": "wt.exe",  # Windows Terminal
            
            # Браузери (шляхи визначаються динамічно)
            "browser": "",  # Системний браузер за замовчуванням
            "edge": "msedge.exe",
            
            # Офісні додатки (базові)
            "paint": "mspaint.exe",
            "wordpad": "wordpad.exe",
            
            # Медіа
            "mediaplayer": "wmplayer.exe",
            "photos": "ms-photos:",
        }

    # ============================================
    # FileSystem Operations
    # ============================================

    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        """Повертає список файлів та папок."""
        # Перевірка дозволу
        if not self.is_path_allowed(path, "read"):
            raise PermissionError(f"Access denied to path: {path}")
        
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        if not target.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")
        
        result = []
        try:
            for item in target.iterdir():
                entry = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item),
                }
                
                if item.is_file():
                    try:
                        stat = item.stat()
                        entry["size"] = stat.st_size
                        entry["modified"] = stat.st_mtime
                    except OSError:
                        entry["size"] = 0
                
                result.append(entry)
        except PermissionError as e:
            raise PermissionError(f"Cannot list directory: {e}")
        
        return sorted(result, key=lambda x: (x["type"] == "file", x["name"].lower()))

    def read_file(self, path: str, max_bytes: int = 10240) -> str:
        """Читає вміст файлу."""
        if not self.is_path_allowed(path, "read"):
            raise PermissionError(f"Access denied to path: {path}")
        
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"File does not exist: {path}")
        if not target.is_file():
            raise IsADirectoryError(f"Path is a directory: {path}")
        
        # Перевірка розміру
        size = target.stat().st_size
        if size > max_bytes:
            # Читаємо тільки початок файлу
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)
            return content + f"\n\n... [Truncated. File size: {size} bytes, shown: {max_bytes} bytes]"
        
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def create_file(self, path: str, content: str = "") -> bool:
        """Створює новий файл."""
        if not self.is_path_allowed(path, "write"):
            raise PermissionError(f"Access denied to path: {path}")
        
        target = Path(path).expanduser().resolve()
        if target.exists():
            raise FileExistsError(f"File already exists: {path}")
        
        # Створюємо батьківські директорії якщо потрібно
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True

    def write_file(self, path: str, content: str, overwrite: bool = False) -> bool:
        """Записує вміст у файл."""
        if not self.is_path_allowed(path, "write"):
            raise PermissionError(f"Access denied to path: {path}")
        
        target = Path(path).expanduser().resolve()
        
        if target.exists() and not overwrite:
            raise FileExistsError(f"File exists and overwrite=False: {path}")
        
        # Створюємо батьківські директорії якщо потрібно
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True

    def delete_path(self, path: str, recursive: bool = False) -> bool:
        """Видаляє файл або папку."""
        if not self.is_path_allowed(path, "delete"):
            raise PermissionError(f"Access denied to path: {path}")
        
        target = Path(path).expanduser().resolve()
        
        if not target.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            if recursive:
                shutil.rmtree(target)
            else:
                # Видаляємо тільки порожню директорію
                target.rmdir()
        
        return True

    # ============================================
    # Process Operations
    # ============================================

    def open_app(self, app_name: str, args: Optional[List[str]] = None) -> bool:
        """Відкриває додаток."""
        if not self.is_app_allowed(app_name):
            raise PermissionError(f"Application not in allowed list: {app_name}")
        
        app_path = self._allowed_apps.get(app_name.lower(), "")
        
        # Спеціальні випадки
        if app_name.lower() == "browser":
            # Відкриваємо браузер за замовчуванням з порожньою сторінкою
            import webbrowser
            webbrowser.open("about:blank")
            return True
        
        # Якщо шлях починається з "ms-" — це Windows Store app
        if app_path.startswith("ms-"):
            subprocess.Popen(["start", app_path], shell=True)
            return True
        
        cmd = [app_path] if app_path else [app_name]
        if args:
            cmd.extend(args)
        
        try:
            # Використовуємо start для Windows
            subprocess.Popen(
                ["start", "", *cmd],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to open application: {e}")

    # ============================================
    # Browser Operations
    # ============================================

    def open_url(self, url: str) -> bool:
        """Відкриває URL у браузері за замовчуванням."""
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to open URL: {e}")

    # ============================================
    # System Info
    # ============================================

    def get_system_info(self) -> Dict[str, Any]:
        """Повертає інформацію про систему."""
        import platform
        
        info = {
            "os": "Windows",
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
        }
        
        # Додаємо інформацію про пам'ять та диски
        info["memory"] = self.get_memory_info()
        info["disks"] = self.get_disk_info()
        
        return info

    def get_memory_info(self) -> Dict[str, int]:
        """Повертає інформацію про пам'ять."""
        try:
            import ctypes
            
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            
            meminfo = MEMORYSTATUSEX()
            meminfo.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(meminfo))
            
            return {
                "total": meminfo.ullTotalPhys,
                "available": meminfo.ullAvailPhys,
                "used": meminfo.ullTotalPhys - meminfo.ullAvailPhys,
                "percent": meminfo.dwMemoryLoad,
            }
        except Exception:
            return {"total": 0, "available": 0, "used": 0, "percent": 0}

    def get_disk_info(self) -> List[Dict[str, Any]]:
        """Повертає інформацію про диски."""
        disks = []
        
        try:
            import ctypes
            import string
            
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        total, used, free = shutil.disk_usage(drive)
                        disks.append({
                            "device": drive,
                            "mountpoint": drive,
                            "total": total,
                            "used": used,
                            "free": free,
                            "percent": round((used / total) * 100, 1) if total > 0 else 0,
                        })
                    except Exception:
                        continue
        except Exception:
            pass
        
        return disks
