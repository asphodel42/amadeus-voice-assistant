"""
Amadeus Core Domain Entities

Цей модуль містить всі доменні сутності (Data Classes).
Сутності є незмінними (immutable) та не містять бізнес-логіки.

Ієрархія:
    CommandRequest → Intent → ActionPlan → Action → ExecutionResult → AuditEvent
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from functools import total_ordering
from typing import Any, Dict, List, Optional


@total_ordering
class RiskLevel(Enum):
    """
    Рівень ризику дії.
    
    Визначає, чи потрібне підтвердження користувача та який тип.
    """
    SAFE = auto()        # Безпечні дії (list_dir, system_info)
    MEDIUM = auto()      # Потребують уваги (open_url для non-HTTPS)
    HIGH = auto()        # Потребують підтвердження (write_file, create_file)
    DESTRUCTIVE = auto() # Потребують typed confirmation (delete_file)
    
    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self.value < other.value
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RiskLevel):
            return NotImplemented
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)


class IntentType(Enum):
    """Типи підтримуваних намірів (MVP)."""
    OPEN_APP = "open_app"
    OPEN_URL = "open_url"
    WEB_SEARCH = "web_search"
    LIST_DIR = "list_dir"
    READ_FILE = "read_file"
    CREATE_FILE = "create_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    SYSTEM_INFO = "system_info"
    UNKNOWN = "unknown"


class ExecutionStatus(Enum):
    """Статус виконання дії."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DENIED = "denied"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DRY_RUN = "dry_run"


@dataclass(frozen=True)
class CommandRequest:
    """
    Початковий запит користувача.
    
    Attributes:
        request_id: Унікальний ідентифікатор запиту
        raw_text: Оригінальний текст після ASR
        timestamp: Час створення запиту
        source: Джерело команди (voice, push_to_talk, text_input)
    """
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_text: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "voice"

    def __post_init__(self) -> None:
        # Валідація: raw_text не може бути порожнім для обробки
        if not self.raw_text.strip():
            object.__setattr__(self, 'raw_text', '')


@dataclass(frozen=True)
class Intent:
    """
    Розпізнаний намір користувача.
    
    Attributes:
        intent_type: Тип наміру
        slots: Витягнуті параметри (ключ-значення)
        confidence: Впевненість у розпізнаванні (0.0-1.0)
        original_request: Посилання на оригінальний запит
    """
    intent_type: IntentType
    slots: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    original_request: Optional[CommandRequest] = None

    def __post_init__(self) -> None:
        # Валідація confidence
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    @property
    def is_unknown(self) -> bool:
        return self.intent_type == IntentType.UNKNOWN
    
    def get_slot(self, key: str, default: Any = None) -> Any:
        """Безпечне отримання слота."""
        return self.slots.get(key, default)


@dataclass(frozen=True)
class Action:
    """
    Одна атомарна дія для виконання.
    
    Attributes:
        action_id: Унікальний ідентифікатор дії
        tool_name: Ім'я інструменту (filesystem, browser, process)
        function_name: Ім'я функції для виклику
        args: Аргументи функції
        risk: Рівень ризику
        description: Людино-читабельний опис для UI
        requires_confirmation: Чи потребує явного підтвердження
    """
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    function_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    risk: RiskLevel = RiskLevel.SAFE
    description: str = ""
    requires_confirmation: bool = False

    def __post_init__(self) -> None:
        # Автоматично вимагати підтвердження для HIGH та DESTRUCTIVE
        if self.risk in (RiskLevel.HIGH, RiskLevel.DESTRUCTIVE) and not self.requires_confirmation:
            object.__setattr__(self, 'requires_confirmation', True)
    
    def to_human_readable(self) -> str:
        """Генерує людино-читабельний опис дії."""
        if self.description:
            return self.description
        return f"{self.tool_name}.{self.function_name}({self.args})"


@dataclass(frozen=True)
class ActionPlan:
    """
    План виконання, що складається з послідовності дій.
    
    Attributes:
        plan_id: Унікальний ідентифікатор плану
        intent: Оригінальний намір
        actions: Список дій для виконання (в порядку)
        requires_confirmation: Чи потребує план підтвердження
        max_risk: Максимальний рівень ризику серед дій
        dry_run: Чи це симуляція без реального виконання
        created_at: Час створення плану
    """
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent: Intent = field(default_factory=lambda: Intent(IntentType.UNKNOWN))
    actions: List[Action] = field(default_factory=list)
    requires_confirmation: bool = False
    dry_run: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def max_risk(self) -> RiskLevel:
        """Обчислює максимальний рівень ризику серед всіх дій."""
        if not self.actions:
            return RiskLevel.SAFE
        return max(action.risk for action in self.actions)

    @property
    def is_empty(self) -> bool:
        return len(self.actions) == 0

    def to_preview_text(self) -> str:
        """Генерує текст попереднього перегляду для UI."""
        if self.is_empty:
            return "No actions planned."
        
        lines = [f"Plan: {self.intent.intent_type.value}"]
        lines.append(f"Risk Level: {self.max_risk.name}")
        lines.append("")
        lines.append("Actions:")
        for i, action in enumerate(self.actions, 1):
            marker = "⚠️" if action.requires_confirmation else "✓"
            lines.append(f"  {i}. {marker} {action.to_human_readable()}")
        
        if self.requires_confirmation:
            lines.append("")
            lines.append("⚠️ This plan requires your confirmation before execution.")
        
        return "\n".join(lines)


@dataclass(frozen=True)
class ExecutionResult:
    """
    Результат виконання дії.
    
    Attributes:
        action: Виконана дія
        status: Статус виконання
        output: Вихідні дані (якщо є)
        error: Повідомлення про помилку (якщо є)
        started_at: Час початку виконання
        completed_at: Час завершення виконання
    """
    action: Action
    status: ExecutionStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS
    
    @property
    def duration_ms(self) -> Optional[float]:
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return None


@dataclass(frozen=True)
class AuditEvent:
    """
    Подія для журналу аудиту (append-only).
    
    Attributes:
        event_id: Унікальний ідентифікатор події
        timestamp: Час події
        event_type: Тип події (command, plan, confirmation, execution, error)
        actor: Хто ініціював (user, system, plugin:<name>)
        command_request: Оригінальний запит (якщо застосовно)
        plan: План дій (якщо застосовно)
        result: Результат виконання (якщо застосовно)
        metadata: Додаткові дані
        previous_hash: Хеш попередньої події (для hash chain)
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = "generic"
    actor: str = "system"
    command_request: Optional[CommandRequest] = None
    plan: Optional[ActionPlan] = None
    result: Optional[ExecutionResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""

    def compute_hash(self) -> str:
        """Обчислює SHA-256 хеш події для chain integrity."""
        content = f"{self.event_id}|{self.timestamp.isoformat()}|{self.event_type}|{self.actor}|{self.previous_hash}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


# ============================================
# Capability System Entities
# ============================================

class CapabilityScope(Enum):
    """Область застосування можливості (capability scope)."""
    # Filesystem
    FS_READ = "fs.read"
    FS_WRITE = "fs.write"
    FS_DELETE = "fs.delete"
    FS_CREATE = "fs.create"
    
    # Process
    PROCESS_LAUNCH = "process.launch"
    PROCESS_KILL = "process.kill"
    
    # Network (browser-only for MVP)
    NET_BROWSER = "net.browser"
    
    # System
    SYSTEM_INFO = "system.info"
    
    # UI
    UI_NOTIFY = "ui.notify"
    UI_DIALOG = "ui.dialog"


@dataclass(frozen=True)
class Capability:
    """
    Можливість, що надається навичці (skill).
    
    Attributes:
        scope: Область застосування
        constraints: Обмеження (allowed_paths, max_size, etc.)
        risk: Рівень ризику цієї можливості
    """
    scope: CapabilityScope
    constraints: Dict[str, Any] = field(default_factory=dict)
    risk: RiskLevel = RiskLevel.SAFE

    def allows_path(self, path: str) -> bool:
        """Перевіряє, чи дозволений шлях для filesystem операцій."""
        allowed_paths = self.constraints.get("allowed_paths", [])
        if not allowed_paths:
            return True  # Немає обмежень
        
        # Нормалізація та перевірка
        from pathlib import Path
        target = Path(path).resolve()
        for allowed in allowed_paths:
            allowed_path = Path(allowed).expanduser().resolve()
            try:
                target.relative_to(allowed_path)
                return True
            except ValueError:
                continue
        return False


@dataclass(frozen=True)
class CapabilityManifest:
    """
    Маніфест можливостей навички (plugin manifest).
    
    Attributes:
        skill_id: Унікальний ідентифікатор навички
        version: Версія навички
        publisher_id: Ідентифікатор видавця
        capabilities: Список запитуваних можливостей
        signature: Цифровий підпис маніфесту
    """
    skill_id: str
    version: str
    publisher_id: str
    capabilities: List[Capability] = field(default_factory=list)
    signature: str = ""

    def has_capability(self, scope: CapabilityScope) -> bool:
        """Перевіряє наявність можливості."""
        return any(cap.scope == scope for cap in self.capabilities)
    
    def get_capability(self, scope: CapabilityScope) -> Optional[Capability]:
        """Отримує можливість за scope."""
        for cap in self.capabilities:
            if cap.scope == scope:
                return cap
        return None
