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
    Adapter for Windows.

    Implements all OS-specific operations for Windows 10/11.
    """

    def _init_default_allowed_apps(self) -> None:
        """Initializes the whitelist of allowed apps for Windows."""
        self._allowed_apps = {
            # ============================================
            # Windows Built-in Utilities
            # ============================================
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "pwsh": "pwsh.exe",
            "terminal": "wt.exe",  # Windows Terminal
            "windows terminal": "wt.exe",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "wordpad": "wordpad.exe",
            "task manager": "taskmgr.exe",
            "taskmgr": "taskmgr.exe",
            "device manager": "devmgmt.msc",
            "disk management": "diskmgmt.msc",
            "services": "services.msc",
            "event viewer": "eventvwr.exe",
            "registry editor": "regedit.exe",
            "regedit": "regedit.exe",
            "settings": "ms-settings:",
            "control panel": "control.exe",
            
            # ============================================
            # Web Browsers
            # ============================================
            "browser": "",  # System default browser
            "firefox": "firefox.exe",
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "chromium": "chromium.exe",
            "edge": "msedge.exe",
            "microsoft edge": "msedge.exe",
            "safari": "safari.exe",
            "opera": "opera.exe",
            "brave": "brave.exe",
            "vivaldi": "vivaldi.exe",
            "tor": "tor.exe",
            "torbrowser": "tor-browser.exe",
            
            # ============================================
            # Development & Code Editors
            # ============================================
            "code": "code.exe",
            "vscode": "code.exe",
            "visual studio code": "code.exe",
            "sublime": "subl.exe",
            "sublime text": "subl.exe",
            "sublime text 3": "subl.exe",
            "atom": "atom.exe",
            "vim": "vim.exe",
            "gvim": "gvim.exe",
            "emacs": "emacs.exe",
            "notepad++": "notepad++.exe",
            "pycharm": "pycharm.exe",
            "pycharm professional": "pycharm.exe",
            "pycharm community": "pycharm.exe",
            "webstorm": "webstorm.exe",
            "intellij": "idea.exe",
            "intellij idea": "idea.exe",
            "rider": "rider.exe",
            "clion": "clion.exe",
            "goland": "goland.exe",
            "android studio": "studio.exe",
            "visual studio": "devenv.exe",
            "vs": "devenv.exe",
            "netbeans": "netbeans.exe",
            "eclipse": "eclipse.exe",
            "codeblocks": "codeblocks.exe",
            "qt creator": "qtcreator.exe",
            "lazarus": "lazarus.exe",
            
            # ============================================
            # Office & Productivity
            # ============================================
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "access": "msaccess.exe",
            "outlook": "outlook.exe",
            "onenote": "onenote.exe",
            "publisher": "mspub.exe",
            "project": "winproj.exe",
            "visio": "visio.exe",
            "libreoffice": "libreoffice.exe",
            "libreoffice writer": "libreoffice.exe",
            "libreoffice calc": "libreoffice.exe",
            "libreoffice impress": "libreoffice.exe",
            "google docs": "chrome.exe",
            "google sheets": "chrome.exe",
            "google slides": "chrome.exe",
            "openoffice": "openoffice.exe",
            "abiword": "abiword.exe",
            "gnumeric": "gnumeric.exe",
            
            # ============================================
            # Communication & Social
            # ============================================
            "discord": "Discord.exe",
            "telegram": "Telegram.exe",
            "telegram desktop": "Telegram.exe",
            "skype": "skype.exe",
            "slack": "slack.exe",
            "teams": "Teams.exe",
            "microsoft teams": "Teams.exe",
            "zoom": "zoom.exe",
            "whatsapp": "WhatsApp.exe",
            "viber": "Viber.exe",
            "signal": "Signal.exe",
            "wire": "wire.exe",
            "google meet": "chrome.exe",
            "hangouts": "chrome.exe",
            "messenger": "Messenger.exe",
            "twitch": "chrome.exe",
            
            # ============================================
            # Media & Entertainment
            # ============================================
            "vlc": "vlc.exe",
            "vlc media player": "vlc.exe",
            "mpv": "mpv.exe",
            "kodi": "kodi.exe",
            "plex": "Plex Media Server.exe",
            "spotify": "Spotify.exe",
            "itunes": "iTunes.exe",
            "apple music": "iTunes.exe",
            "audacity": "audacity.exe",
            "youtube": "chrome.exe",
            "netflix": "chrome.exe",
            "hulu": "chrome.exe",
            "prime video": "chrome.exe",
            "steam": "steam.exe",
            "epic games": "EpicGamesLauncher.exe",
            "epicgames": "EpicGamesLauncher.exe",
            "origin": "Origin.exe",
            "uplay": "uplay.exe",
            "ubisoft": "uplay.exe",
            "gog galaxy": "GOG Galaxy.exe",
            "blender": "blender.exe",
            "obs": "obs64.exe",
            "obs studio": "obs64.exe",
            "obs-studio": "obs64.exe",
            "windows media player": "wmplayer.exe",
            "mediaplayer": "wmplayer.exe",
            "photos": "ms-photos:",
            "groove music": "groove.exe",
            
            # ============================================
            # Graphics & Design
            # ============================================
            "photoshop": "Photoshop.exe",
            "adobe photoshop": "Photoshop.exe",
            "illustrator": "illustrator.exe",
            "adobe illustrator": "illustrator.exe",
            "indesign": "indesign.exe",
            "adobe indesign": "indesign.exe",
            "premiere": "Premiere.exe",
            "adobe premiere": "Premiere.exe",
            "after effects": "AfterFX.exe",
            "adobe after effects": "AfterFX.exe",
            "lightroom": "lightroom.exe",
            "adobe lightroom": "lightroom.exe",
            "xd": "Adobe XD.exe",
            "adobe xd": "Adobe XD.exe",
            "figma": "Figma.exe",
            "sketch": "sketch.exe",
            "gimp": "gimp-2.10.exe",
            "inkscape": "inkscape.exe",
            "krita": "krita.exe",
            "aseprite": "aseprite.exe",
            "canva": "canva.exe",
            "pixlr": "pixlr.exe",
            "paint.net": "PaintDotNet.exe",
            "clip studio paint": "clip-studio-paint.exe",
            
            # ============================================
            # File Management & Archiving
            # ============================================
            "7-zip": "7zFM.exe",
            "7zip": "7zFM.exe",
            "winrar": "WinRAR.exe",
            "rar": "WinRAR.exe",
            "winzip": "winzip.exe",
            "peazip": "peazip.exe",
            "bandizip": "bandizip.exe",
            "file roller": "file-roller.exe",
            "total commander": "totalcmd.exe",
            "totalcmd": "totalcmd.exe",
            "double commander": "doublecmd.exe",
            "everything": "everything.exe",
            
            # ============================================
            # Database Tools
            # ============================================
            "mysql": "mysql.exe",
            "mysql workbench": "MySQLWorkbench.exe",
            "postgresql": "psql.exe",
            "pgadmin": "pgadmin.exe",
            "mongodb": "mongo.exe",
            "dbeaver": "dbeaver.exe",
            "sqlite": "sqlite3.exe",
            "sqlitebrowser": "sqlitebrowser.exe",
            "redis": "redis-cli.exe",
            "nosqlclient": "nosqlclient.exe",
            "mongodb compass": "MongoDBCompass.exe",
            
            # ============================================
            # Version Control
            # ============================================
            "git": "git.exe",
            "git gui": "git-gui.exe",
            "github desktop": "GitHubDesktop.exe",
            "tortoisegit": "TortoiseGit.exe",
            "smartgit": "smartgit.exe",
            "sourcetree": "SourceTree.exe",
            "tortoise svn": "TortoiseSVN.exe",
            "svn": "svn.exe",
            "mercurial": "hg.exe",
            "fossil": "fossil.exe",
            
            # ============================================
            # Password & Security
            # ============================================
            "keepass": "KeePass.exe",
            "keepassxc": "KeePassXC.exe",
            "bitwarden": "Bitwarden.exe",
            "1password": "1password.exe",
            "lastpass": "lastpass.exe",
            "dashlane": "dashlane.exe",
            "enpass": "enpass.exe",
            "pass": "pass.exe",
            "truecrypt": "truecrypt.exe",
            "veracrypt": "veracrypt.exe",
            
            # ============================================
            # VPN & Network
            # ============================================
            "openvpn": "openvpn-gui.exe",
            "wireguard": "wireguard.exe",
            "nordvpn": "NordVPN.exe",
            "expressvpn": "ExpressVPN.exe",
            "protonvpn": "ProtonVPN.exe",
            "mullvad": "mullvad.exe",
            "windscribe": "Windscribe.exe",
            "tunnelbear": "TunnelBear.exe",
            "surfshark": "Surfshark.exe",
            "tailscale": "tailscale.exe",
            "zerotier": "zerotier-one.exe",
            
            # ============================================
            # Virtualization & Containers
            # ============================================
            "virtualbox": "VirtualBox.exe",
            "vmware player": "vmplayer.exe",
            "vmware workstation": "vmware.exe",
            "hyper-v": "virtmgmt.msc",
            "parallels": "Parallels Desktop.exe",
            "docker": "Docker.exe",
            "docker desktop": "Docker.exe",
            "vagrant": "vagrant.exe",
            "multipass": "multipass.exe",
            
            # ============================================
            # Remote Access
            # ============================================
            "remote desktop": "mstsc.exe",
            "mstsc": "mstsc.exe",
            "putty": "putty.exe",
            "winscp": "WinSCP.exe",
            "filezilla": "filezilla.exe",
            "mobaxterm": "MobaXterm.exe",
            "teamviewer": "TeamViewer.exe",
            "anydesk": "AnyDesk.exe",
            "nomachine": "NXPlayer.exe",
            "chrome remote desktop": "chrome.exe",
            "parsec": "parsec.exe",
            "sunshine": "sunshine.exe",
            
            # ============================================
            # Backup & Recovery
            # ============================================
            "acronis true image": "TrueImageHome.exe",
            "backup and restore": "sdclt.exe",
            "file history": "ms-settings:",
            "duplicati": "Duplicati.exe",
            "bacula": "bacula.exe",
            "veeam": "Veeam.Backup.UI.exe",
            "macrium reflect": "reflect.exe",
            
            # ============================================
            # System Utilities
            # ============================================
            "ccleaner": "CCleaner.exe",
            "glary utilities": "Glary Utilities.exe",
            "advanced systemcare": "ASCService.exe",
            "winrar": "WinRAR.exe",
            "process explorer": "procexp.exe",
            "process monitor": "procmon.exe",
            "autoruns": "Autoruns.exe",
            "sysinternals suite": "Sysinternals.exe",
            "resource monitor": "resmon.exe",
            "performance monitor": "perfmon.exe",
            "disk management": "diskmgmt.msc",
            "partition wizard": "PartitionWizard.exe",
            "gparted": "gparted.exe",
            "arandr": "arandr.exe",
            
            # ============================================
            # Note Taking & Knowledge Management
            # ============================================
            "obsidian": "Obsidian.exe",
            "evernote": "Evernote.exe",
            "onenote": "onenote.exe",
            "notion": "notion.exe",
            "joplin": "Joplin.exe",
            "logseq": "Logseq.exe",
            "roam research": "roam-research.exe",
            "standard notes": "StandardNotes.exe",
            "simplenote": "Simplenote.exe",
            "tiddlywiki": "tiddlywiki.exe",
            "zim": "zim.exe",
            "tomboy": "tomboy.exe",
            
            # ============================================
            # Project Management
            # ============================================
            "trello": "trello.exe",
            "asana": "asana.exe",
            "monday": "monday.exe",
            "clickup": "ClickUp.exe",
            "jira": "jira.exe",
            "taiga": "taiga.exe",
            "wekan": "wekan.exe",
            "plane": "plane.exe",
            
            # ============================================
            # Cloud & Sync
            # ============================================
            "onedrive": "OneDrive.exe",
            "microsoft onedrive": "OneDrive.exe",
            "dropbox": "Dropbox.exe",
            "google drive": "GoogleDrive.exe",
            "box": "Box.exe",
            "icloud": "iCloud.exe",
            "mega": "MEGAsync.exe",
            "sync.com": "SyncClient.exe",
            "nextcloud": "nextcloud.exe",
            "owncloud": "owncloud.exe",
            "synology": "SynologyCloudStationBackup.exe",
            
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
        """Return list of files and folders."""
        # Check permissions
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
        """Read file contents."""
        if not self.is_path_allowed(path, "read"):
            raise PermissionError(f"Access denied to path: {path}")
        
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"File does not exist: {path}")
        if not target.is_file():
            raise IsADirectoryError(f"Path is a directory: {path}")
        
        # Check file size
        size = target.stat().st_size
        if size > max_bytes:
            # Read only the beginning of the file
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

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True

    def write_file(self, path: str, content: str, overwrite: bool = False) -> bool:
        """Write content to a file."""
        if not self.is_path_allowed(path, "write"):
            raise PermissionError(f"Access denied to path: {path}")
        
        target = Path(path).expanduser().resolve()
        
        if target.exists() and not overwrite:
            raise FileExistsError(f"File exists and overwrite=False: {path}")

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True

    def delete_path(self, path: str, recursive: bool = False) -> bool:
        """Delete a file or folder."""
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
                # Delete only empty directory
                target.rmdir()
        
        return True

    # ============================================
    # Process Operations
    # ============================================

    def open_app(self, app_name: str, args: Optional[List[str]] = None) -> bool:
        """Open an application."""
        if not self.is_app_allowed(app_name):
            raise PermissionError(f"Application not in allowed list: {app_name}")
        
        app_path = self._allowed_apps.get(app_name.lower(), "")
        
        # Special cases
        if app_name.lower() == "browser":
            # Open default browser with empty page
            import webbrowser
            webbrowser.open("about:blank")
            return True

        # If path starts with "ms-" it's a Windows Store app
        if app_path.startswith("ms-"):
            subprocess.Popen(["start", app_path], shell=True)
            return True
        
        cmd = [app_path] if app_path else [app_name]
        if args:
            cmd.extend(args)
        
        try:
            # Use start for Windows
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
        """Open URL in default browser."""
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to open URL: {e}")

    # ============================================
    # System Info
    # ============================================

    def get_system_info(self) -> Dict[str, Any]:
        """Return system information."""
        info = {
            "os": "Windows",
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
        }

        # Add memory and disk information
        info["memory"] = self.get_memory_info()
        info["disks"] = self.get_disk_info()
        
        return info

    def get_memory_info(self) -> Dict[str, int]:
        """Return memory information."""
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
