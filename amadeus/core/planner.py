"""
Amadeus Core Planner

Планувальник дій — центральний компонент доменної логіки.
Відповідає за перетворення Intent → ActionPlan.

Принципи:
- Детермінована поведінка: один Intent → один ActionPlan
- Безпечні defaults: високий ризик = потребує підтвердження
- Читабельні плани: людина повинна розуміти, що буде виконано
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
    """Конфігурація планувальника."""
    
    # Дозволені директорії для операцій з файлами
    allowed_directories: List[str] = field(default_factory=lambda: [
        "~/Documents",
        "~/Downloads",
        "~/Desktop",
    ])
    
    # Білий список додатків
    allowed_apps: List[str] = field(default_factory=lambda: [
        "notepad", "calculator", "browser", "explorer",
        "terminal", "cmd", "powershell",
        # Linux
        "nautilus", "gedit", "gnome-terminal",
    ])
    
    # Пошукові системи
    search_engines: Dict[str, str] = field(default_factory=lambda: {
        "default": "https://duckduckgo.com/?q={}",
        "duckduckgo": "https://duckduckgo.com/?q={}",
        "google": "https://www.google.com/search?q={}",
    })
    
    # Максимальний розмір файлу для читання (bytes)
    max_read_size: int = 10240  # 10 KB
    
    # Максимальний розмір файлу для запису (bytes)
    max_write_size: int = 1048576  # 1 MB
    
    # Автоматичне підтвердження для SAFE операцій
    auto_confirm_safe: bool = True
    
    # Сухий запуск за замовчуванням для деструктивних операцій
    dry_run_destructive: bool = True


class Planner:
    """
    Планувальник дій.
    
    Перетворює Intent у ActionPlan, додаючи:
    - Конкретні дії для виконання
    - Рівні ризику
    - Вимоги до підтвердження
    - Людино-читабельні описи
    """

    def __init__(self, config: Optional[PlannerConfig] = None) -> None:
        self.config = config or PlannerConfig()
        
        # Реєстр обробників намірів
        self._intent_handlers: Dict[IntentType, callable] = {
            IntentType.OPEN_APP: self._plan_open_app,
            IntentType.OPEN_URL: self._plan_open_url,
            IntentType.WEB_SEARCH: self._plan_web_search,
            IntentType.LIST_DIR: self._plan_list_dir,
            IntentType.READ_FILE: self._plan_read_file,
            IntentType.CREATE_FILE: self._plan_create_file,
            IntentType.WRITE_FILE: self._plan_write_file,
            IntentType.DELETE_FILE: self._plan_delete_file,
            IntentType.SYSTEM_INFO: self._plan_system_info,
            IntentType.UNKNOWN: self._plan_unknown,
        }

    def create_plan(self, intent: Intent) -> ActionPlan:
        """
        Створює план дій для наміру.
        
        Args:
            intent: Розпізнаний намір
            
        Returns:
            План дій для виконання
        """
        handler = self._intent_handlers.get(intent.intent_type, self._plan_unknown)
        actions = handler(intent)
        
        # Визначаємо, чи потрібне підтвердження
        requires_confirmation = any(
            action.risk in (RiskLevel.HIGH, RiskLevel.DESTRUCTIVE)
            for action in actions
        )
        
        # Для SAFE операцій можна автоматично підтверджувати
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
        """Планує відкриття додатку."""
        app_name = intent.get_slot("app_name", "").lower()
        
        # Перевірка білого списку
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
        """Планує відкриття URL."""
        url = intent.get_slot("url", "")
        
        # Перевірка безпеки URL
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
        """Планує веб-пошук."""
        query = intent.get_slot("query", "")
        engine = intent.get_slot("engine", "default")
        
        # Отримуємо URL шаблон для пошукової системи
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
        """Планує перегляд директорії."""
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
        """Планує читання файлу."""
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
        """Планує створення файлу."""
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
        """Планує запис у файл."""
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
        """Планує видалення файлу."""
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
        """Планує отримання інформації про систему."""
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
        """Обробка невідомого наміру."""
        return []

    def _create_denied_action(self, reason: str) -> Action:
        """Створює дію-заглушку для забороненої операції."""
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
    Рендерер планів у людино-читабельний формат.
    
    Використовується для UI та логування.
    """

    @staticmethod
    def to_text(plan: ActionPlan) -> str:
        """Рендерить план у текстовий формат."""
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
        """Рендерить план у словник (для JSON/API)."""
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
