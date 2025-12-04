"""
Amadeus Core Domain Ports (Interfaces)

Цей модуль визначає всі порти (інтерфейси) системи.
Порти — це контракти, які реалізуються адаптерами в інфраструктурному шарі.

Принцип: Домен визначає, ЩО потрібно робити.
         Адаптери визначають, ЯК це робити.
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
    Порт для управління процесами.
    
    Реалізації:
        - WindowsProcessAdapter
        - LinuxProcessAdapter
    """

    @abstractmethod
    def open_app(self, app_name: str, args: Optional[List[str]] = None) -> bool:
        """
        Відкриває додаток за іменем.
        
        Args:
            app_name: Ім'я або шлях до додатку
            args: Аргументи командного рядка
            
        Returns:
            True якщо успішно запущено
            
        Raises:
            PermissionError: Якщо немає прав на запуск
            FileNotFoundError: Якщо додаток не знайдено
        """
        ...

    @abstractmethod
    def is_app_allowed(self, app_name: str) -> bool:
        """Перевіряє, чи додаток у білому списку."""
        ...

    @abstractmethod
    def get_app_path(self, app_name: str) -> Optional[Path]:
        """Отримує повний шлях до додатку."""
        ...


@runtime_checkable
class FileSystemPort(Protocol):
    """
    Порт для операцій з файловою системою.
    
    БЕЗПЕКА: Всі операції перевіряються на дозволені шляхи.
    """

    @abstractmethod
    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        """
        Повертає список файлів та папок.
        
        Args:
            path: Шлях до директорії
            
        Returns:
            Список словників з інформацією про файли:
            [{"name": "file.txt", "type": "file", "size": 1024}, ...]
        """
        ...

    @abstractmethod
    def read_file(self, path: str, max_bytes: int = 10240) -> str:
        """
        Читає вміст файлу (з обмеженням розміру).
        
        Args:
            path: Шлях до файлу
            max_bytes: Максимальний розмір для читання
            
        Returns:
            Вміст файлу як рядок
        """
        ...

    @abstractmethod
    def create_file(self, path: str, content: str = "") -> bool:
        """
        Створює новий файл.
        
        Args:
            path: Шлях до файлу
            content: Початковий вміст
            
        Returns:
            True якщо успішно створено
            
        Raises:
            FileExistsError: Якщо файл вже існує
            PermissionError: Якщо немає прав на створення
        """
        ...

    @abstractmethod
    def write_file(self, path: str, content: str, overwrite: bool = False) -> bool:
        """
        Записує вміст у файл.
        
        Args:
            path: Шлях до файлу
            content: Вміст для запису
            overwrite: Чи перезаписувати існуючий файл
            
        Returns:
            True якщо успішно записано
        """
        ...

    @abstractmethod
    def delete_path(self, path: str, recursive: bool = False) -> bool:
        """
        Видаляє файл або папку.
        
        УВАГА: Деструктивна операція! Потребує typed confirmation.
        
        Args:
            path: Шлях до файлу/папки
            recursive: Чи видаляти рекурсивно (для папок)
            
        Returns:
            True якщо успішно видалено
        """
        ...

    @abstractmethod
    def is_path_allowed(self, path: str, operation: str) -> bool:
        """
        Перевіряє, чи дозволена операція для шляху.
        
        Args:
            path: Шлях для перевірки
            operation: Тип операції (read, write, delete)
            
        Returns:
            True якщо дозволено
        """
        ...

    @abstractmethod
    def path_exists(self, path: str) -> bool:
        """Перевіряє, чи існує шлях."""
        ...


@runtime_checkable
class BrowserPort(Protocol):
    """
    Порт для операцій з браузером.
    
    БЕЗПЕКА: Тільки відкриття URL через системний браузер.
             Ніяких прихованих мережевих запитів.
    """

    @abstractmethod
    def open_url(self, url: str) -> bool:
        """
        Відкриває URL у браузері за замовчуванням.
        
        Args:
            url: URL для відкриття
            
        Returns:
            True якщо успішно відкрито
        """
        ...

    @abstractmethod
    def search_web(self, query: str, engine: str = "default") -> bool:
        """
        Виконує пошук у вебі.
        
        Args:
            query: Пошуковий запит
            engine: Пошукова система (default, google, duckduckgo)
            
        Returns:
            True якщо успішно відкрито пошук
        """
        ...

    @abstractmethod
    def is_url_safe(self, url: str) -> bool:
        """
        Перевіряє безпечність URL.
        
        Returns:
            True для HTTPS URL та дозволених доменів
        """
        ...


@runtime_checkable
class SystemInfoPort(Protocol):
    """Порт для отримання системної інформації."""

    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """
        Повертає загальну інформацію про систему.
        
        Returns:
            {"os": "Windows 11", "cpu": "...", "memory": {...}, ...}
        """
        ...

    @abstractmethod
    def get_memory_info(self) -> Dict[str, int]:
        """Повертає інформацію про пам'ять."""
        ...

    @abstractmethod
    def get_disk_info(self) -> List[Dict[str, Any]]:
        """Повертає інформацію про диски."""
        ...


# ============================================
# Voice Pipeline Ports
# ============================================

@runtime_checkable
class WakeWordPort(Protocol):
    """Порт для розпізнавання слова-активатора."""

    @abstractmethod
    def start_listening(self) -> None:
        """Починає прослуховування слова-активатора."""
        ...

    @abstractmethod
    def stop_listening(self) -> None:
        """Зупиняє прослуховування."""
        ...

    @abstractmethod
    def is_activated(self) -> bool:
        """Перевіряє, чи було розпізнано слово-активатор."""
        ...

    @abstractmethod
    def set_wake_word(self, word: str) -> bool:
        """Встановлює слово-активатор."""
        ...


@runtime_checkable
class ASRPort(Protocol):
    """Порт для розпізнавання мови (Automatic Speech Recognition)."""

    @abstractmethod
    def transcribe(self, audio_data: bytes) -> str:
        """
        Транскрибує аудіо в текст.
        
        Args:
            audio_data: Аудіо дані у форматі PCM
            
        Returns:
            Розпізнаний текст
        """
        ...

    @abstractmethod
    def start_stream(self) -> None:
        """Починає потокове розпізнавання."""
        ...

    @abstractmethod
    def stop_stream(self) -> str:
        """
        Зупиняє потокове розпізнавання.
        
        Returns:
            Фінальний розпізнаний текст
        """
        ...


@runtime_checkable
class NLUPort(Protocol):
    """Порт для розуміння природної мови (Natural Language Understanding)."""

    @abstractmethod
    def parse(self, text: str) -> "Intent":
        """
        Парсить текст у структурований намір.
        
        Args:
            text: Текст команди
            
        Returns:
            Розпізнаний намір зі слотами
        """
        ...


@runtime_checkable
class TTSPort(Protocol):
    """Порт для синтезу мови (Text-to-Speech)."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """
        Озвучує текст.
        
        Args:
            text: Текст для озвучування
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """Зупиняє поточне озвучування."""
        ...


# ============================================
# Persistence Ports
# ============================================

@runtime_checkable
class AuditPort(Protocol):
    """
    Порт для журналу аудиту.
    
    ВАЖЛИВО: Журнал є append-only для забезпечення integrity.
    """

    @abstractmethod
    def append_event(self, event: "AuditEvent") -> str:
        """
        Додає подію до журналу.
        
        Args:
            event: Подія для логування
            
        Returns:
            ID створеної події
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
        Отримує події з журналу.
        
        Args:
            start_time: Початок періоду (ISO format)
            end_time: Кінець періоду (ISO format)
            event_type: Фільтр за типом події
            limit: Максимальна кількість подій
            
        Returns:
            Список подій
        """
        ...

    @abstractmethod
    def verify_integrity(self) -> bool:
        """
        Перевіряє цілісність журналу (hash chain).
        
        Returns:
            True якщо журнал не було модифіковано
        """
        ...

    @abstractmethod
    def get_last_hash(self) -> str:
        """Повертає хеш останньої події."""
        ...


@runtime_checkable
class ConfigPort(Protocol):
    """Порт для зберігання конфігурації."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Отримує значення конфігурації."""
        ...

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Встановлює значення конфігурації."""
        ...

    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """Повертає всю конфігурацію."""
        ...


# ============================================
# Security Ports
# ============================================

@runtime_checkable
class PolicyPort(Protocol):
    """
    Порт для двигуна політик безпеки.
    
    Перевіряє ActionPlan проти capabilities та правил ризику.
    """

    @abstractmethod
    def evaluate(
        self,
        plan: "ActionPlan",
        capabilities: List["Capability"]
    ) -> "PolicyDecision":
        """
        Оцінює план дій.
        
        Args:
            plan: План для оцінки
            capabilities: Доступні можливості
            
        Returns:
            Рішення політики (allowed/denied + причина)
        """
        ...

    @abstractmethod
    def get_required_confirmations(self, plan: "ActionPlan") -> List[str]:
        """
        Визначає, які підтвердження потрібні для плану.
        
        Returns:
            Список описів підтверджень
        """
        ...


@runtime_checkable
class SignaturePort(Protocol):
    """Порт для перевірки підписів плагінів."""

    @abstractmethod
    def verify_manifest(self, manifest: "CapabilityManifest") -> bool:
        """
        Перевіряє підпис маніфесту.
        
        Returns:
            True якщо підпис валідний
        """
        ...

    @abstractmethod
    def sign_manifest(self, manifest: "CapabilityManifest", private_key: bytes) -> str:
        """
        Підписує маніфест.
        
        Returns:
            Підпис у форматі Base64
        """
        ...

    @abstractmethod
    def add_trusted_publisher(self, publisher_id: str, public_key: bytes) -> None:
        """Додає довіреного видавця."""
        ...


# ============================================
# UI Ports
# ============================================

@runtime_checkable
class DialogPort(Protocol):
    """Порт для діалогу з користувачем."""

    @abstractmethod
    def show_message(self, message: str, title: str = "Amadeus") -> None:
        """Показує інформаційне повідомлення."""
        ...

    @abstractmethod
    def show_error(self, message: str, title: str = "Error") -> None:
        """Показує повідомлення про помилку."""
        ...

    @abstractmethod
    def show_confirmation(
        self,
        plan: "ActionPlan",
        timeout_seconds: int = 30
    ) -> bool:
        """
        Показує діалог підтвердження для плану.
        
        Args:
            plan: План для підтвердження
            timeout_seconds: Таймаут очікування
            
        Returns:
            True якщо користувач підтвердив
        """
        ...

    @abstractmethod
    def show_typed_confirmation(
        self,
        plan: "ActionPlan",
        confirmation_phrase: str
    ) -> bool:
        """
        Показує діалог з typed confirmation для деструктивних операцій.
        
        Args:
            plan: План для підтвердження
            confirmation_phrase: Фраза, яку користувач повинен ввести
            
        Returns:
            True якщо користувач ввів правильну фразу
        """
        ...


# ============================================
# Supporting Types
# ============================================

@runtime_checkable
class PolicyDecision(Protocol):
    """Результат оцінки політики."""
    
    @property
    def allowed(self) -> bool:
        """Чи дозволено виконання."""
        ...
    
    @property
    def reason(self) -> str:
        """Причина рішення."""
        ...
    
    @property
    def requires_confirmation(self) -> bool:
        """Чи потрібне підтвердження."""
        ...
    
    @property
    def confirmation_type(self) -> str:
        """Тип підтвердження (simple, typed, passcode)."""
        ...
