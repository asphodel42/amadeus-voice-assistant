"""
Linux OS Adapter

Адаптер для Linux-специфічних операцій.
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


class LinuxAdapter(BaseOSAdapter):
    """
    Адаптер для Linux.
    
    Реалізує всі OS-специфічні операції для Ubuntu/Debian та інших дистрибутивів.
    """

    def _init_default_allowed_apps(self) -> None:
        """Ініціалізує білий список додатків для Linux."""
        self._allowed_apps = {
            # Файлові менеджери
            "nautilus": "nautilus",
            "thunar": "thunar",
            "dolphin": "dolphin",
            "nemo": "nemo",
            "files": "nautilus",  # alias
            
            # Термінали
            "terminal": "gnome-terminal",
            "gnome-terminal": "gnome-terminal",
            "konsole": "konsole",
            "xterm": "xterm",
            
            # Текстові редактори
            "gedit": "gedit",
            "kate": "kate",
            "nano": "nano",
            "vim": "vim",
            "notepad": "gedit",  # alias for Windows compatibility
            
            # Браузери
            "browser": "",  # Системний браузер
            "firefox": "firefox",
            "chromium": "chromium-browser",
            "chrome": "google-chrome",
            
            # Утиліти
            "calculator": "gnome-calculator",
            "calc": "gnome-calculator",
            
            # Медіа
            "totem": "totem",
            "vlc": "vlc",
            "eog": "eog",  # Eye of GNOME (image viewer)
        }

    # ============================================
    # FileSystem Operations
    # ============================================

    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        """Повертає список файлів та папок."""
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
                        entry["permissions"] = oct(stat.st_mode)[-3:]
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
        
        size = target.stat().st_size
        if size > max_bytes:
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
        
        if target.is_file() or target.is_symlink():
            target.unlink()
        elif target.is_dir():
            if recursive:
                shutil.rmtree(target)
            else:
                target.rmdir()
        
        return True

    # ============================================
    # Process Operations
    # ============================================

    def open_app(self, app_name: str, args: Optional[List[str]] = None) -> bool:
        """Відкриває додаток."""
        if not self.is_app_allowed(app_name):
            raise PermissionError(f"Application not in allowed list: {app_name}")
        
        app_cmd = self._allowed_apps.get(app_name.lower(), app_name)
        
        if app_name.lower() == "browser":
            webbrowser.open("about:blank")
            return True
        
        cmd = [app_cmd]
        if args:
            cmd.extend(args)
        
        try:
            # Використовуємо subprocess для запуску у фоні
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent process
            )
            return True
        except FileNotFoundError:
            raise FileNotFoundError(f"Application not found: {app_cmd}")
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
        info = {
            "os": "Linux",
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
        }
        
        # Спроба отримати назву дистрибутиву
        try:
            import distro
            info["distro"] = distro.name(pretty=True)
        except ImportError:
            # Fallback: читаємо /etc/os-release
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            info["distro"] = line.split("=")[1].strip().strip('"')
                            break
            except Exception:
                info["distro"] = "Unknown Linux"
        
        info["memory"] = self.get_memory_info()
        info["disks"] = self.get_disk_info()
        
        return info

    def get_memory_info(self) -> Dict[str, int]:
        """Повертає інформацію про пам'ять."""
        try:
            with open("/proc/meminfo") as f:
                meminfo = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().split()[0]
                        meminfo[key] = int(value) * 1024  # Convert KB to bytes
            
            total = meminfo.get("MemTotal", 0)
            available = meminfo.get("MemAvailable", 0)
            used = total - available
            percent = round((used / total) * 100) if total > 0 else 0
            
            return {
                "total": total,
                "available": available,
                "used": used,
                "percent": percent,
            }
        except Exception:
            return {"total": 0, "available": 0, "used": 0, "percent": 0}

    def get_disk_info(self) -> List[Dict[str, Any]]:
        """Повертає інформацію про диски."""
        disks = []
        
        try:
            # Читаємо /proc/mounts для списку змонтованих файлових систем
            with open("/proc/mounts") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        device = parts[0]
                        mountpoint = parts[1]
                        
                        # Пропускаємо псевдо файлові системи
                        if not device.startswith("/dev/") and device != "tmpfs":
                            continue
                        if mountpoint.startswith("/snap/"):
                            continue
                        
                        try:
                            stat = os.statvfs(mountpoint)
                            total = stat.f_blocks * stat.f_frsize
                            free = stat.f_bavail * stat.f_frsize
                            used = total - free
                            
                            if total > 0:
                                disks.append({
                                    "device": device,
                                    "mountpoint": mountpoint,
                                    "total": total,
                                    "used": used,
                                    "free": free,
                                    "percent": round((used / total) * 100, 1),
                                })
                        except OSError:
                            continue
        except Exception:
            pass
        
        return disks
