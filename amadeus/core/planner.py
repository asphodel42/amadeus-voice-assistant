"""
Amadeus Core Planner

Action Planner — central component of the domain logic.
Responsible for transforming Intent -> ActionPlan.

Principles:
- Deterministic behavior: one Intent -> one ActionPlan
- Safe defaults: high risk = requires confirmation
- Readable plans: humans must understand what will be executed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from amadeus.core.entities import (
    Action,
    ActionPlan,
    Intent,
    IntentType,
    RiskLevel,
)


@dataclass
class PlannerConfig:
    """Configuration for the planner."""

    # Allowed directories for file operations
    allowed_directories: List[str] = field(default_factory=lambda: [
        "~/Documents",
        "~/Downloads",
        "~/Desktop",
    ])

    # White list of applications
    allowed_apps: List[str] = field(default_factory=lambda: [
        # ============================================
        # Windows Built-in
        # ============================================
        "notepad", "notepad++",
        "calculator", "calc",
        "wordpad",
        "cmd", "powershell", "terminal", "windows terminal",
        "explorer", "file explorer",
        "paint", "mspaint",
        "settings", "control panel",
        "task manager", "taskmgr",
        "disk management",
        
        # ============================================
        # Web Browsers (Windows/Linux/macOS)
        # ============================================
        "browser", "firefox", "mozilla firefox",
        "chrome", "google chrome", "chromium",
        "edge", "microsoft edge",
        "safari",
        "opera",
        "brave",
        "vivaldi",
        "tor", "torbrowser",
        
        # ============================================
        # Development & Code Editors
        # ============================================
        "code", "vscode", "visual studio code",
        "sublime", "sublime text", "sublime_text",
        "atom",
        "notepad++",
        "vim",
        "nano",
        "emacs",
        "pycharm",
        "webstorm",
        "intellij", "idea",
        "studio", "android studio",
        
        # ============================================
        # Office & Productivity
        # ============================================
        "word", "winword",
        "excel",
        "powerpoint", "pptview",
        "outlook",
        "oneword",
        "access",
        "libreoffice", "libreoffice writer", "swriter",
        "calc", "libreoffice calc", "scalc",
        "impress", "libreoffice impress", "simpress",
        "base", "libreoffice base",
        "draw", "libreoffice draw", "sdraw",
        
        # ============================================
        # Communication & Social
        # ============================================
        "discord",
        "telegram",
        "slack",
        "teams", "microsoft teams",
        "zoom",
        "whatsapp",
        "viber",
        "messenger",
        "signal",
        "wire",
        "google meet",
        "hangouts",
        
        # ============================================
        # Media & Entertainment
        # ============================================
        "vlc", "vlcmediaplayer",
        "mpv",
        "kodi",
        "plex", "plexmediaplayer",
        "spotify",
        "apple music", "itunes",
        "audacity",
        "youtube", "youtube music",
        "netflix",
        "hulu",
        "prime video",
        "steam",
        "epic", "epicgames",
        "origin",
        "uplay", "ubisoft",
        "gog",
        "twitch",
        "ott", "obs", "obs studio",
        
        # ============================================
        # Graphics & Design
        # ============================================
        "photoshop", "adobe photoshop",
        "illustrator", "adobe illustrator",
        "indesign", "adobe indesign",
        "premiere", "adobe premiere",
        "aftereffects", "adobe after effects",
        "lightroom", "adobe lightroom",
        "gimp",
        "inkscape",
        "blender",
        "krita",
        "aseprite",
        "figma",
        "xd", "adobe xd",
        "sketch",
        "canva",
        "pixlr",
        "paint.net",
        
        # ============================================
        # File Management & Archiving
        # ============================================
        "explorer", "file explorer",
        "nautilus", "files", "gnome files",
        "dolphin", "kde dolphin",
        "thunar", "xfce thunar",
        "7zip", "7z",
        "winrar", "unrar",
        "winzip",
        "peazip",
        
        # ============================================
        # Version Control
        # ============================================
        "git", "git bash",
        "github", "github desktop",
        "gitlab",
        "bitbucket",
        "tortoisegit",
        "sourcetree",
        
        # ============================================
        # Database Tools
        # ============================================
        "mysql", "mysql workbench",
        "postgresql", "pgadmin",
        "mongodb", "mongoclient",
        "dbeaver",
        "sqlite", "sqlitebrowser",
        "redis",
        "phpmyadmin",
        
        # ============================================
        # Terminal & Shell (Linux/macOS/Windows)
        # ============================================
        "terminal", "gnome terminal",
        "konsole", "kde konsole",
        "xterm",
        "urxvt", "rxvt",
        "tilix",
        "alacritty",
        "kitty",
        "bash",
        "zsh",
        "fish",
        "powershell", "pwsh",
        "cmd", "command prompt",
        "windows terminal",
        
        # ============================================
        # System & Monitoring
        # ============================================
        "htop",
        "top",
        "iotop",
        "nethogs",
        "gmonitor", "gnome monitor",
        "gnome system monitor",
        "task manager",
        "resource monitor",
        
        # ============================================
        # Document & Viewers
        # ============================================
        "acrobat", "adobe reader",
        "sumatrapdf",
        "foxit reader",
        "evince", "document viewer",
        "okular",
        "zathura",
        "nomacs",
        
        # ============================================
        # Knowledge Management & Note Taking
        # ============================================
        "obsidian",
        "evernote",
        "notion",
        "onenote", "microsoft onenote",
        "roam research",
        "logseq",
        "joplin",
        "standard notes",
        "simplenote",
        "tiddlywiki",
        
        # ============================================
        # Project Management & Productivity
        # ============================================
        "trello",
        "asana",
        "monday.com",
        "clickup",
        "jira",
        "confluence",
        "todoist",
        "microsoft todo",
        "notion",
        "basecamp",
        
        # ============================================
        # Cloud & Sync
        # ============================================
        "onedrive", "microsoft onedrive",
        "dropbox",
        "google drive", "drive",
        "box",
        "icloud",
        "mega",
        "sync.com",
        "nextcloud",
        "owncloud",
        "synology",
        
        # ============================================
        # Password & Security
        # ============================================
        "keepass",
        "keepassxc",
        "bitwarden",
        "1password",
        "lastpass",
        "dashlane",
        "enpass",
        "pass",
        
        # ============================================
        # VPN & Network
        # ============================================
        "openvpn",
        "wireguard",
        "nordvpn",
        "expressvpn",
        "protonvpn",
        "windscribe",
        "tunnelbear",
        "surfshark",
        "mullvad",
        
        # ============================================
        # Virtualization
        # ============================================
        "virtualbox",
        "vmware", "vmplayer",
        "hyper-v",
        "parallels",
        "docker", "docker desktop",
        "vagrant",
        
        # ============================================
        # System Utilities
        # ============================================
        "ccleaner",
        "glary utilities",
        "winaero tweaker",
        "autoruns",
        "procexp", "process explorer",
        "dependency walker",
        "procmon", "process monitor",
        "sysinternals suite",
        
        # ============================================
        # FTP & Remote Access
        # ============================================
        "filezilla",
        "putty",
        "winscp",
        "mobaxterm",
        "remote desktop", "mstsc",
        "teamviewer",
        "anydesk",
        "chrome remote desktop",
        "nomachine",
        "remmina",
        
        # ============================================
        # Media Converters
        # ============================================
        "handbrake",
        "ffmpeg",
        "imagemagick",
        "conversion studio",
        "winff",
        
        # ============================================
        # Torrent
        # ============================================
        "qbittorrent",
        "transmission",
        "deluge",
        "syncthing",
        
        # ============================================
        # AI & Machine Learning
        # ============================================
        "python",
        "jupyter",
        "anaconda",
        "miniconda",
        "tensorflow",
        "pytorch",
        "chatgpt",
        
        # ============================================
        # Default/Fallback
        # ============================================
        "default app",
        "system default",
    ])

    # Search engines
    search_engines: Dict[str, str] = field(default_factory=lambda: {
        "default": "https://duckduckgo.com/?q={}",
        "duckduckgo": "https://duckduckgo.com/?q={}",
        "google": "https://www.google.com/search?q={}",
    })

    # Max read size (bytes)
    max_read_size: int = 10240  # 10 KB

    # Max write size (bytes)
    max_write_size: int = 1048576  # 1 MB
    
    # Automatic confirmation for SAFE operations
    auto_confirm_safe: bool = True

    # Dry run by default for destructive operations
    dry_run_destructive: bool = True


class Planner:
    """
    Action Planner.

    Transforms Intent into ActionPlan by adding:
    - Specific actions to be performed
    - Risk levels
    - Confirmation requirements
    - Human-readable descriptions
    """

    def __init__(self, config: Optional[PlannerConfig] = None) -> None:
        self.config = config or PlannerConfig()
        
        # Map IntentType to handler methods
        self._intent_handlers: Dict[IntentType, callable] = {
            IntentType.OPEN_APP: self._plan_open_app,
            IntentType.OPEN_FILE: self._plan_open_file,
            IntentType.OPEN_URL: self._plan_open_url,
            IntentType.WEB_SEARCH: self._plan_web_search,
            IntentType.LIST_DIR: self._plan_list_dir,
            IntentType.READ_FILE: self._plan_read_file,
            IntentType.CREATE_FILE: self._plan_create_file,
            IntentType.WRITE_FILE: self._plan_write_file,
            IntentType.DELETE_FILE: self._plan_delete_file,
            IntentType.SYSTEM_INFO: self._plan_system_info,
            IntentType.CONFIRM: self._plan_confirm,
            IntentType.DENY: self._plan_deny,
            IntentType.UNKNOWN: self._plan_unknown,
        }

    def create_plan(self, intent: Intent) -> ActionPlan:
        """
        Creates an action plan for the given intent.

        Args:
            intent: Recognized intent

        Returns:
            Action plan for execution
        """
        handler = self._intent_handlers.get(intent.intent_type, self._plan_unknown)
        actions = handler(intent)

        # Determine if confirmation is needed
        requires_confirmation = any(
            action.risk in (RiskLevel.HIGH, RiskLevel.DESTRUCTIVE)
            for action in actions
        )

        # For SAFE operations, confirmation can be automatically granted
        if not requires_confirmation and self.config.auto_confirm_safe:
            requires_confirmation = False
        
        return ActionPlan(
            intent=intent,
            actions=actions,
            requires_confirmation=requires_confirmation,
        )

    # ============================================
    # Intent Handlers
    # ============================================

    def _plan_open_app(self, intent: Intent) -> List[Action]:
        """Plans to open an application."""
        app_name = intent.get_slot("app_name", "").lower()
        
        # Check white list
        is_allowed = app_name in self.config.allowed_apps
        
        if not is_allowed:
            return [self._create_denied_action(
                f"Application '{app_name}' is not in the allowed list. "
                f"Allowed apps: {', '.join(self.config.allowed_apps)}"
            )]
        
        return [
            Action(
                tool_name="process",
                function_name="open_app",
                args={"app_name": app_name},
                risk=RiskLevel.SAFE,
                description=f"Open application: {app_name}",
                requires_confirmation=False,
            )
        ]

    def _plan_open_url(self, intent: Intent) -> List[Action]:
        """Plans to open a URL."""
        url = intent.get_slot("url", "")
        
        # Check URL safety
        is_https = url.startswith("https://")
        risk = RiskLevel.SAFE if is_https else RiskLevel.MEDIUM
        
        return [
            Action(
                tool_name="browser",
                function_name="open_url",
                args={"url": url},
                risk=risk,
                description=f"Open URL in browser: {url}",
                requires_confirmation=not is_https,
            )
        ]

    def _plan_web_search(self, intent: Intent) -> List[Action]:
        """Plans a web search."""
        query = intent.get_slot("query", "")
        engine = intent.get_slot("engine", "default")

        # Get URL template for search engine
        url_template = self.config.search_engines.get(
            engine, 
            self.config.search_engines["default"]
        )
        
        return [
            Action(
                tool_name="browser",
                function_name="search_web",
                args={"query": query, "engine": engine},
                risk=RiskLevel.SAFE,
                description=f"Search the web for: {query}",
                requires_confirmation=False,
            )
        ]

    def _plan_list_dir(self, intent: Intent) -> List[Action]:
        """Plans to list a directory."""
        path = intent.get_slot("path", ".")
        
        return [
            Action(
                tool_name="filesystem",
                function_name="list_dir",
                args={"path": path},
                risk=RiskLevel.SAFE,
                description=f"List contents of directory: {path}",
                requires_confirmation=False,
            )
        ]

    def _plan_read_file(self, intent: Intent) -> List[Action]:
        """Plans to read a file."""
        path = intent.get_slot("path", "")
        
        return [
            Action(
                tool_name="filesystem",
                function_name="read_file",
                args={
                    "path": path,
                    "max_bytes": self.config.max_read_size,
                },
                risk=RiskLevel.SAFE,
                description=f"Read file contents: {path} (max {self.config.max_read_size} bytes)",
                requires_confirmation=False,
            )
        ]

    def _plan_create_file(self, intent: Intent) -> List[Action]:
        """Plans to create a file."""
        path = intent.get_slot("path", "")
        content = intent.get_slot("content", "")
        
        return [
            Action(
                tool_name="filesystem",
                function_name="create_file",
                args={
                    "path": path,
                    "content": content,
                },
                risk=RiskLevel.HIGH,
                description=f"Create new file: {path}",
                requires_confirmation=True,
            )
        ]

    def _plan_write_file(self, intent: Intent) -> List[Action]:
        """Plans to write to a file."""
        path = intent.get_slot("path", "")
        content = intent.get_slot("content", "")
        overwrite = intent.get_slot("overwrite", False)
        
        risk = RiskLevel.HIGH
        if overwrite:
            risk = RiskLevel.DESTRUCTIVE
        
        return [
            Action(
                tool_name="filesystem",
                function_name="write_file",
                args={
                    "path": path,
                    "content": content,
                    "overwrite": overwrite,
                },
                risk=risk,
                description=f"Write to file: {path} (overwrite={overwrite})",
                requires_confirmation=True,
            )
        ]

    def _plan_delete_file(self, intent: Intent) -> List[Action]:
        """Plans to delete a file."""
        path = intent.get_slot("path", "")
        recursive = intent.get_slot("recursive", False)
        
        return [
            Action(
                tool_name="filesystem",
                function_name="delete_path",
                args={
                    "path": path,
                    "recursive": recursive,
                },
                risk=RiskLevel.DESTRUCTIVE,
                description=f"⚠️ DELETE {'recursively ' if recursive else ''}: {path}",
                requires_confirmation=True,
            )
        ]

    def _plan_system_info(self, intent: Intent) -> List[Action]:
        """Plans to get system information."""
        return [
            Action(
                tool_name="system",
                function_name="get_system_info",
                args={},
                risk=RiskLevel.SAFE,
                description="Get system information",
                requires_confirmation=False,
            )
        ]

    def _plan_unknown(self, intent: Intent) -> List[Action]:
        """Handles unknown intent."""
        return []
    
    def _plan_open_file(self, intent: Intent) -> List[Action]:
        """Plans to open a file with default application."""
        path = intent.get_slot("path", "")
        
        return [
            Action(
                tool_name="filesystem",
                function_name="open_file",
                args={"path": path},
                risk=RiskLevel.SAFE,
                description=f"Open file: {path}",
                requires_confirmation=False,
            )
        ]
    
    def _plan_confirm(self, intent: Intent) -> List[Action]:
        """
        Handles CONFIRM intent.
        
        This is a special case - CONFIRM doesn't create actions,
        it's handled by the state machine to proceed with pending actions.
        """
        return []
    
    def _plan_deny(self, intent: Intent) -> List[Action]:
        """
        Handles DENY intent.
        
        This is a special case - DENY doesn't create actions,
        it's handled by the state machine to cancel pending actions.
        """
        return []

    def _create_denied_action(self, reason: str) -> Action:
        """Creates a no-op action for denied operation."""
        return Action(
            tool_name="system",
            function_name="denied",
            args={"reason": reason},
            risk=RiskLevel.SAFE,
            description=f"Operation denied: {reason}",
            requires_confirmation=False,
        )


# ============================================
# Plan Renderer
# ============================================

class PlanRenderer:
    """
    Plan renderer for human-readable format.

    Used for UI and logging.
    """

    @staticmethod
    def to_text(plan: ActionPlan) -> str:
        """Render the plan in text format."""
        if plan.is_empty:
            return "❓ No actions planned for this command."
        
        lines = [
            "═══════════════════════════════════════════",
            f"📋 Action Plan: {plan.intent.intent_type.value.upper()}",
            f"🔐 Risk Level: {plan.max_risk.name}",
            "═══════════════════════════════════════════",
            "",
        ]
        
        for i, action in enumerate(plan.actions, 1):
            risk_emoji = {
                RiskLevel.SAFE: "✅",
                RiskLevel.MEDIUM: "⚡",
                RiskLevel.HIGH: "⚠️",
                RiskLevel.DESTRUCTIVE: "🔴",
            }.get(action.risk, "❓")
            
            lines.append(f"{i}. {risk_emoji} {action.description}")
            
            if action.args:
                for key, value in action.args.items():
                    lines.append(f"      {key}: {value}")
        
        lines.append("")
        
        if plan.requires_confirmation:
            if plan.max_risk == RiskLevel.DESTRUCTIVE:
                lines.append("⛔ DESTRUCTIVE OPERATION - Typed confirmation required!")
            else:
                lines.append("⚠️ This plan requires your confirmation to proceed.")
        else:
            lines.append("✅ This plan is safe and will execute automatically.")
        
        lines.append("═══════════════════════════════════════════")
        
        return "\n".join(lines)

    @staticmethod
    def to_dict(plan: ActionPlan) -> Dict[str, Any]:
        """Render the plan as a dictionary (for JSON/API)."""
        return {
            "plan_id": plan.plan_id,
            "intent": {
                "type": plan.intent.intent_type.value,
                "slots": plan.intent.slots,
                "confidence": plan.intent.confidence,
            },
            "actions": [
                {
                    "id": action.action_id,
                    "tool": action.tool_name,
                    "function": action.function_name,
                    "args": action.args,
                    "risk": action.risk.name,
                    "description": action.description,
                    "requires_confirmation": action.requires_confirmation,
                }
                for action in plan.actions
            ],
            "max_risk": plan.max_risk.name,
            "requires_confirmation": plan.requires_confirmation,
            "is_dry_run": plan.dry_run,
            "created_at": plan.created_at.isoformat(),
        }
