"""
Linux OS Adapter

Adapter for Linux-specific operations.
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
    Adapter for Linux.
    
    Implements all OS-specific operations for Ubuntu/Debian and other distributions.
    """

    def _init_default_allowed_apps(self) -> None:
        """Initializes the whitelist of allowed apps for Linux."""
        self._allowed_apps = {
            # ============================================
            # File Managers
            # ============================================
            "nautilus": "nautilus",
            "files": "nautilus",  # GNOME alias
            "dolphin": "dolphin",  # KDE
            "thunar": "thunar",  # XFCE
            "nemo": "nemo",  # Cinnamon
            "pcmanfm": "pcmanfm",  # LXDE
            "spacefm": "spacefm",
            "ranger": "ranger",  # Terminal-based
            "vifm": "vifm",  # Terminal-based
            "caja": "caja",  # MATE
            "konqueror": "konqueror",  # KDE
            "krusader": "krusader",  # KDE Commander
            
            # ============================================
            # Terminals & Shells
            # ============================================
            "terminal": "gnome-terminal",
            "gnome-terminal": "gnome-terminal",
            "konsole": "konsole",  # KDE
            "xterm": "xterm",
            "urxvt": "urxvt",
            "rxvt-unicode": "urxvtd",
            "tilix": "tilix",  # GNOME tiling terminal
            "alacritty": "alacritty",  # GPU-accelerated
            "kitty": "kitty",  # GPU-based terminal
            "terminator": "terminator",
            "guake": "guake",  # Drop-down terminal
            "yakuake": "yakuake",  # KDE drop-down
            "tilda": "tilda",
            "mlterm": "mlterm",
            
            # ============================================
            # Text Editors
            # ============================================
            "gedit": "gedit",
            "kate": "kate",  # KDE
            "nano": "nano",
            "vim": "vim",
            "vi": "vi",
            "nano": "nano",
            "emacs": "emacs",
            "notepad": "gedit",  # Windows alias
            "pluma": "pluma",  # MATE
            "mousepad": "mousepad",  # XFCE
            "leafpad": "leafpad",  # LXDE
            "xed": "xed",  # Linux Mint
            "geany": "geany",
            "pluma": "pluma",
            "gvim": "gvim",
            
            # ============================================
            # Web Browsers
            # ============================================
            "browser": "",  # System default browser
            "firefox": "firefox",
            "chromium": "chromium",
            "chromium-browser": "chromium-browser",
            "chrome": "google-chrome",
            "google-chrome": "google-chrome",
            "brave": "brave",
            "edge": "microsoft-edge",
            "opera": "opera",
            "vivaldi": "vivaldi",
            "epiphany": "epiphany",  # GNOME Web
            "konqueror": "konqueror",  # KDE
            "w3m": "w3m",  # Terminal browser
            "lynx": "lynx",  # Terminal browser
            "links": "links",  # Terminal browser
            "tor": "tor-browser",
            "torbrowser": "tor-browser",
            
            # ============================================
            # Development & Code Editors
            # ============================================
            "code": "code",  # VS Code
            "vscode": "code",
            "visual-studio-code": "code",
            "sublime": "subl",
            "sublime-text": "subl",
            "sublime-text-3": "subl",
            "atom": "atom",
            "vim": "vim",
            "nvim": "nvim",  # Neovim
            "neovim": "nvim",
            "emacs": "emacs",
            "pycharm": "pycharm",
            "webstorm": "webstorm",
            "intellij": "idea",
            "idea": "idea",
            "studio": "android-studio",
            "android-studio": "android-studio",
            "geany": "geany",
            "codeblocks": "codeblocks",
            "netbeans": "netbeans",
            "eclipse": "eclipse",
            "lazarus": "lazarus",
            "kdevelop": "kdevelop",
            "qt-creator": "qtcreator",
            
            # ============================================
            # Office & Productivity
            # ============================================
            "libreoffice": "libreoffice",
            "libreoffice-writer": "libreoffice --writer",
            "libreoffice-calc": "libreoffice --calc",
            "libreoffice-impress": "libreoffice --impress",
            "libreoffice-draw": "libreoffice --draw",
            "writer": "libreoffice --writer",
            "calc": "libreoffice --calc",  # Also gnome-calculator
            "impress": "libreoffice --impress",
            "draw": "libreoffice --draw",
            "abiword": "abiword",
            "gnumeric": "gnumeric",
            "evolution": "evolution",  # Email & Calendar
            "thunderbird": "thunderbird",
            
            # ============================================
            # Communication & Social
            # ============================================
            "discord": "discord",
            "telegram": "telegram-desktop",
            "telegram-desktop": "telegram-desktop",
            "slack": "slack",
            "skype": "skype",
            "teams": "teams",
            "microsoft-teams": "teams",
            "zoom": "zoom",
            "wire": "wire",
            "signal": "signal-desktop",
            "signal-desktop": "signal-desktop",
            "riot": "element-desktop",
            "element": "element-desktop",
            "jitsi": "jitsi-meet",
            "mumble": "mumble",
            "tox": "qtox",
            
            # ============================================
            # Media & Entertainment
            # ============================================
            "vlc": "vlc",
            "mpv": "mpv",
            "ffplay": "ffplay",
            "totem": "totem",  # GNOME Videos
            "celluloid": "celluloid",  # GNOME frontend for mpv
            "kplayer": "kplayer",  # KDE
            "smplayer": "smplayer",
            "mplayer": "mplayer",
            "audacity": "audacity",
            "ffmpeg": "ffmpeg",
            "ffmpeg-full": "ffmpeg",
            "blender": "blender",
            "krita": "krita",
            "inkscape": "inkscape",
            "gimp": "gimp",
            "geeqie": "geeqie",  # Image viewer
            "eog": "eog",  # Eye of GNOME
            "feh": "feh",  # Image viewer
            "sxiv": "sxiv",  # Image viewer
            "spotify": "spotify",
            "vlc": "vlc",
            "rhythmbox": "rhythmbox",  # GNOME Music
            "banshee": "banshee",
            "amarok": "amarok",  # KDE
            "clementine": "clementine",
            "mpd": "mpd",  # Music Player Daemon
            "ncmpcpp": "ncmpcpp",  # MPD client
            
            # ============================================
            # Graphics & Design
            # ============================================
            "gimp": "gimp",
            "inkscape": "inkscape",
            "blender": "blender",
            "krita": "krita",
            "aseprite": "aseprite",
            "imagemagick": "convert",
            "convert": "convert",
            "graphicsmagick": "gm",
            "gm": "gm",
            "darktable": "darktable",  # Photo editor
            "rawtherapee": "rawtherapee",
            "scribus": "scribus",  # Desktop publishing
            "fontforge": "fontforge",
            "xara": "xara",
            "pinta": "pinta",
            "kolourpaint": "kolourpaint",  # KDE paint
            "mypaint": "mypaint",
            
            # ============================================
            # System & Monitoring
            # ============================================
            "htop": "htop",
            "top": "top",
            "iotop": "iotop",
            "nethogs": "nethogs",
            "iftop": "iftop",
            "btop": "btop",
            "glances": "glances",
            "gnome-system-monitor": "gnome-system-monitor",
            "system-monitor": "gnome-system-monitor",
            "ksysguard": "ksysguard",  # KDE
            "baobab": "baobab",  # Disk Usage Analyzer
            "filelight": "filelight",  # KDE Disk Usage
            "gparted": "gparted",  # Partition Manager
            "arandr": "arandr",  # Display manager
            "lxrandr": "lxrandr",  # LXDE Display
            
            # ============================================
            # Document Viewers
            # ============================================
            "evince": "evince",  # PDF Viewer (GNOME)
            "okular": "okular",  # PDF Viewer (KDE)
            "atril": "atril",  # PDF Viewer (MATE)
            "mupdf": "mupdf",
            "zathura": "zathura",  # Minimalist PDF viewer
            "nomacs": "nomacs",  # Image viewer
            "gpicview": "gpicview",  # LXDE image viewer
            "ristretto": "ristretto",  # XFCE image viewer
            
            # ============================================
            # Version Control
            # ============================================
            "git": "git",
            "git-gui": "git-gui",
            "gitk": "gitk",
            "github": "github-cli",
            "github-cli": "github-cli",
            "gitlab": "gitlab",
            "gitg": "gitg",  # GNOME Git client
            "kg": "kg",  # KDE Git client
            "tortoisegit": "tortoisegit",
            "smart-git": "smartgit",
            "subversion": "svn",
            "svn": "svn",
            "mercurial": "hg",
            "hg": "hg",
            
            # ============================================
            # Database Tools
            # ============================================
            "mysql": "mysql",
            "psql": "psql",
            "postgresql": "psql",
            "sqlite": "sqlite3",
            "sqlite3": "sqlite3",
            "mongodb": "mongo",
            "mongo": "mongo",
            "dbeaver": "dbeaver",
            "pgadmin": "pgadmin",
            "redis": "redis-cli",
            "redis-cli": "redis-cli",
            "nosqlclient": "nosqlclient",
            
            # ============================================
            # Package Management
            # ============================================
            "apt": "apt",
            "apt-get": "apt-get",
            "aptitude": "aptitude",
            "synaptic": "synaptic",
            "pacman": "pacman",
            "pamac": "pamac",
            "pamac-manager": "pamac-manager",
            "yum": "yum",
            "dnf": "dnf",
            "zypper": "zypper",
            "snap": "snap",
            "flatpak": "flatpak",
            "appimage": "appimage",
            
            # ============================================
            # Archive & Compression
            # ============================================
            "file-roller": "file-roller",  # GNOME Archive Manager
            "ark": "ark",  # KDE Archive Manager
            "xarchiver": "xarchiver",  # XFCE
            "engrampa": "engrampa",  # MATE
            "tar": "tar",
            "gzip": "gzip",
            "bzip2": "bzip2",
            "zip": "zip",
            "unzip": "unzip",
            "7z": "7z",
            "p7zip": "7z",
            "rar": "rar",
            "unrar": "unrar",
            
            # ============================================
            # Knowledge Management & Note Taking
            # ============================================
            "obsidian": "obsidian",
            "joplin": "joplin",
            "logseq": "logseq",
            "notion": "notion",
            "evernote": "evernote",
            "onenote": "onenote",
            "roam-research": "roam-research",
            "standard-notes": "standard-notes",
            "simplenote": "simplenote",
            "tiddlywiki": "tiddlywiki",
            "zim": "zim",  # Desktop wiki
            "tomboy": "tomboy",  # GNOME notes
            
            # ============================================
            # Project Management
            # ============================================
            "trello": "trello",
            "asana": "asana",
            "monday": "monday",
            "clickup": "clickup",
            "jira": "jira",
            "taiga": "taiga",
            "wekan": "wekan",  # Open source Trello
            "plane": "plane",
            "focalboard": "focalboard",
            
            # ============================================
            # Cloud & Sync
            # ============================================
            "nextcloud": "nextcloud",
            "owncloud": "owncloud",
            "synology": "synology",
            "rclone": "rclone",
            "restic": "restic",
            "duplicati": "duplicati",
            "syncthing": "syncthing",
            "dropbox": "dropbox",
            "google-drive": "google-drive",
            "mega": "megasync",
            
            # ============================================
            # Password & Security
            # ============================================
            "keepass": "keepass",
            "keepassxc": "keepassxc",
            "keepass2": "keepass2",
            "bitwarden": "bitwarden",
            "pass": "pass",  # CLI password manager
            "gopass": "gopass",
            "1password": "1password",
            "lastpass": "lastpass",
            "dashlane": "dashlane",
            "enpass": "enpass",
            "seahorse": "seahorse",  # GNOME Passwords
            "gnome-keyring": "gnome-keyring",
            
            # ============================================
            # VPN & Network
            # ============================================
            "openvpn": "openvpn",
            "wireguard": "wg-quick",
            "nordvpn": "nordvpn",
            "expressvpn": "expressvpn",
            "protonvpn": "protonvpn",
            "mullvad": "mullvad",
            "windscribe": "windscribe",
            "tunnelbear": "tunnelbear",
            "tailscale": "tailscale",
            "zerotier": "zerotier-one",
            
            # ============================================
            # Virtualization & Containers
            # ============================================
            "virtualbox": "virtualbox",
            "vmware": "vmware",
            "kvm": "kvm",
            "qemu": "qemu",
            "virt-manager": "virt-manager",
            "docker": "docker",
            "docker-compose": "docker-compose",
            "podman": "podman",
            "vagrant": "vagrant",
            "multipass": "multipass",
            
            # ============================================
            # Remote Access
            # ============================================
            "ssh": "ssh",
            "sshfs": "sshfs",
            "remmina": "remmina",
            "vinagre": "vinagre",  # GNOME Remote Desktop
            "krdc": "krdc",  # KDE Remote Desktop
            "x2goclient": "x2goclient",
            "xrdp": "xrdp",
            "teamviewer": "teamviewer",
            "anydesk": "anydesk",
            "nomachine": "nomachine",
            "parsec": "parsec",
            "sunshine": "sunshine",
            
            # ============================================
            # Backup & Recovery
            # ============================================
            "timeshift": "timeshift",
            "backintime": "backintime",
            "duplicati": "duplicati",
            "bacula": "bacula",
            "rsync": "rsync",
            "rclone": "rclone",
            "restic": "restic",
            "borg": "borg",
            "urbackup": "urbackupclient",
            
            # ============================================
            # Streaming & Recording
            # ============================================
            "obs": "obs",
            "obs-studio": "obs",
            "ffmpeg": "ffmpeg",
            "handbrake": "handbrake",
            "simplescreenrecorder": "simplescreenrecorder",
            "recordmydesktop": "recordmydesktop",
            "kazam": "kazam",
            "green-recorder": "green-recorder",
            
            # ============================================
            # Default/Fallback
            # ============================================
            "default": "",
            "system": "",
        }

    # ============================================
    # FileSystem Operations
    # ============================================

    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        """Returns a list of files and folders."""
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
        """Read the contents of a file."""
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
        """Create a new file."""
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
        """Writes content to a file."""
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
        """Deletes a file or folder."""
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
        """Opens an application."""
        if not self.is_app_allowed(app_name):
            raise PermissionError(f"Application not in allowed list: {app_name}")
        
        app_cmd = self._allowed_apps.get(app_name.lower(), app_name)
        
        if app_name.lower() == "browser":
            # Open default browser - use a real URL to ensure browser starts
            webbrowser.open("https://www.google.com")
            return True
        
        cmd = [app_cmd]
        if args:
            cmd.extend(args)
        
        try:
            # Use subprocess to launch in the background
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
        """Open URL in the default browser."""
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to open URL: {e}")

    # ============================================
    # System Info
    # ============================================

    def get_system_info(self) -> Dict[str, Any]:
        """Returns information about the system."""
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
        """Returns information about memory."""
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
        """Returns information about disks."""
        disks = []
        
        try:
            # Read /proc/mounts for a list of mounted filesystems
            with open("/proc/mounts") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        device = parts[0]
                        mountpoint = parts[1]

                        # Skip pseudo filesystems
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
