"""
Deterministic NLU (Natural Language Understanding)

Детерміноване розуміння природної мови на основі регулярних виразів та правил.
Це базова реалізація для MVP — надійна та передбачувана.

Переваги:
- Детерміновані результати (один вхід → один вихід)
- Низька затримка (<10ms)
- Немає залежностей від ML моделей
- Легко тестувати та налагоджувати

Обмеження:
- Не розуміє перефразування
- Потребує явних шаблонів для кожного варіанту
- Не масштабується на велику кількість намірів

Для порівняння див. LLM-based NLU у дослідницькому модулі.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

from amadeus.core.entities import CommandRequest, Intent, IntentType


@dataclass
class NLUPattern:
    """
    Шаблон для розпізнавання наміру.
    
    Attributes:
        intent_type: Тип наміру для цього шаблону
        patterns: Список регулярних виразів
        slot_extractors: Функції для витягування слотів
        priority: Пріоритет (вищий = перевіряється першим)
        examples: Приклади команд (для документації/тестів)
    """
    intent_type: IntentType
    patterns: List[str]
    slot_extractors: Dict[str, str] = field(default_factory=dict)
    priority: int = 0
    examples: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Компілюємо регулярні вирази
        self._compiled: List[Pattern[str]] = []
        for pattern in self.patterns:
            try:
                self._compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")


# ============================================
# Шаблони для MVP команд
# ============================================

DEFAULT_PATTERNS: List[NLUPattern] = [
    # OPEN_APP
    NLUPattern(
        intent_type=IntentType.OPEN_APP,
        patterns=[
            r"^open\s+(?P<app_name>[\w\s]+?)(?:\s+app)?$",
            r"^launch\s+(?P<app_name>[\w\s]+)$",
            r"^start\s+(?P<app_name>[\w\s]+)$",
            r"^run\s+(?P<app_name>[\w\s]+)$",
            r"^відкрий\s+(?P<app_name>[\w\s]+)$",  # Ukrainian
            r"^запусти\s+(?P<app_name>[\w\s]+)$",  # Ukrainian
        ],
        priority=10,
        examples=[
            "open calculator",
            "launch notepad",
            "start browser",
            "відкрий калькулятор",
        ],
    ),
    
    # OPEN_URL
    NLUPattern(
        intent_type=IntentType.OPEN_URL,
        patterns=[
            r"^(?:go\s+to|open|visit)\s+(?P<url>https?://\S+)$",
            r"^(?:go\s+to|open|visit)\s+(?P<url>www\.\S+)$",
            r"^(?:go\s+to|open|visit)\s+(?P<url>[\w\.-]+\.\w{2,})$",
            r"^open\s+url\s+(?P<url>\S+)$",
            r"^navigate\s+to\s+(?P<url>\S+)$",
        ],
        priority=15,  # Higher priority than OPEN_APP to catch URLs
        examples=[
            "go to https://github.com",
            "open www.google.com",
            "visit github.com",
        ],
    ),
    
    # WEB_SEARCH
    NLUPattern(
        intent_type=IntentType.WEB_SEARCH,
        patterns=[
            r"^search\s+(?:for\s+)?(?P<query>.+)$",
            r"^google\s+(?P<query>.+)$",
            r"^look\s+up\s+(?P<query>.+)$",
            r"^find\s+(?:information\s+(?:about|on)\s+)?(?P<query>.+)$",
            r"^what\s+is\s+(?P<query>.+)$",
            r"^who\s+is\s+(?P<query>.+)$",
            r"^пошук\s+(?P<query>.+)$",  # Ukrainian
            r"^знайди\s+(?P<query>.+)$",  # Ukrainian
        ],
        priority=5,
        examples=[
            "search for python tutorials",
            "google machine learning",
            "what is clean architecture",
            "пошук рецепти борщу",
        ],
    ),
    
    # LIST_DIR
    NLUPattern(
        intent_type=IntentType.LIST_DIR,
        patterns=[
            r"^list\s+(?:files\s+in\s+)?(?P<path>.+)$",
            r"^show\s+(?:files\s+in\s+)?(?P<path>.+)$",
            r"^what(?:'s|\s+is)\s+in\s+(?P<path>.+)$",
            r"^ls\s+(?P<path>.+)$",
            r"^dir\s+(?P<path>.+)$",
            r"^list\s+(?:the\s+)?directory(?:\s+(?P<path>.+))?$",
            r"^show\s+(?:the\s+)?directory(?:\s+(?P<path>.+))?$",
            r"^покажи\s+файли\s+(?:в\s+)?(?P<path>.+)$",  # Ukrainian
        ],
        priority=10,  # Higher priority than WEB_SEARCH to catch "what's in" first
        examples=[
            "list files in ~/Documents",
            "show ~/Downloads",
            "what's in my documents",
            "ls .",
        ],
    ),
    
    # READ_FILE
    NLUPattern(
        intent_type=IntentType.READ_FILE,
        patterns=[
            r"^read\s+(?:file\s+)?(?P<path>.+)$",
            r"^show\s+(?:contents\s+of\s+)?(?:file\s+)?(?P<path>.+)$",
            r"^cat\s+(?P<path>.+)$",
            r"^view\s+(?:file\s+)?(?P<path>.+)$",
            r"^прочитай\s+(?:файл\s+)?(?P<path>.+)$",  # Ukrainian
        ],
        priority=5,
        examples=[
            "read file ~/Documents/notes.txt",
            "show contents of readme.md",
            "cat config.json",
        ],
    ),
    
    # CREATE_FILE
    NLUPattern(
        intent_type=IntentType.CREATE_FILE,
        patterns=[
            r"^create\s+(?:a\s+)?(?:new\s+)?file\s+(?P<path>.+?)(?:\s+with\s+(?:content\s+)?(?P<content>.+))?$",
            r"^make\s+(?:a\s+)?(?:new\s+)?file\s+(?P<path>.+)$",
            r"^touch\s+(?P<path>.+)$",
            r"^new\s+file\s+(?P<path>.+)$",
            r"^створи\s+файл\s+(?P<path>.+)$",  # Ukrainian
        ],
        priority=5,
        examples=[
            "create file ~/Documents/notes.txt",
            "make a new file test.py",
            "touch readme.md",
            "create file hello.txt with content Hello World",
        ],
    ),
    
    # WRITE_FILE
    NLUPattern(
        intent_type=IntentType.WRITE_FILE,
        patterns=[
            r"^write\s+(?P<content>.+?)\s+to\s+(?:file\s+)?(?P<path>.+)$",
            r"^save\s+(?P<content>.+?)\s+to\s+(?:file\s+)?(?P<path>.+)$",
            r"^append\s+(?P<content>.+?)\s+to\s+(?:file\s+)?(?P<path>.+)$",
            r"^запиши\s+(?P<content>.+?)\s+(?:в|до)\s+(?:файл\s+)?(?P<path>.+)$",  # Ukrainian
        ],
        priority=5,
        examples=[
            "write Hello World to ~/Documents/test.txt",
            "save my notes to notes.txt",
        ],
    ),
    
    # DELETE_FILE
    NLUPattern(
        intent_type=IntentType.DELETE_FILE,
        patterns=[
            r"^delete\s+(?:file\s+)?(?P<path>.+)$",
            r"^remove\s+(?:file\s+)?(?P<path>.+)$",
            r"^rm\s+(?:-r\s+)?(?P<path>.+)$",
            r"^erase\s+(?:file\s+)?(?P<path>.+)$",
            r"^видали\s+(?:файл\s+)?(?P<path>.+)$",  # Ukrainian
        ],
        priority=5,
        examples=[
            "delete file ~/Documents/old.txt",
            "remove temp.log",
            "rm -r ~/old_folder",
        ],
    ),
    
    # SYSTEM_INFO
    NLUPattern(
        intent_type=IntentType.SYSTEM_INFO,
        patterns=[
            r"^(?:show\s+)?system\s+info(?:rmation)?$",
            r"^what(?:'s|\s+is)\s+my\s+system$",
            r"^system\s+status$",
            r"^computer\s+info(?:rmation)?$",
            r"^about\s+(?:this\s+)?computer$",
            r"^інформація\s+про\s+систему$",  # Ukrainian
            r"^інфо\s+системи$",  # Ukrainian
        ],
        priority=5,
        examples=[
            "show system info",
            "what's my system",
            "system status",
        ],
    ),
]


class DeterministicNLU:
    """
    Детерміноване розуміння природної мови.
    
    Використовує регулярні вирази для розпізнавання намірів та витягування слотів.
    
    Приклад використання:
        nlu = DeterministicNLU()
        intent = nlu.parse("open calculator")
        # Intent(intent_type=IntentType.OPEN_APP, slots={"app_name": "calculator"}, ...)
    """

    def __init__(self, patterns: Optional[List[NLUPattern]] = None) -> None:
        self.patterns = patterns or DEFAULT_PATTERNS.copy()
        # Сортуємо за пріоритетом (вищий → перевіряється першим)
        self.patterns.sort(key=lambda p: -p.priority)
        
        # Preprocessors для нормалізації тексту
        self._preprocessors: List[Callable[[str], str]] = [
            self._normalize_whitespace,
            self._expand_contractions,
        ]
        
        # Postprocessors для слотів
        self._slot_processors: Dict[str, Callable[[str], str]] = {
            "path": self._process_path,
            "url": self._process_url,
            "app_name": self._process_app_name,
        }

    def parse(self, text: str) -> Intent:
        """
        Парсить текст команди в структурований намір.
        
        Args:
            text: Текст команди (після ASR)
            
        Returns:
            Розпізнаний Intent
        """
        # Preprocessing
        normalized = self._preprocess(text)
        
        # Намагаємось знайти відповідний шаблон
        for pattern_def in self.patterns:
            for compiled in pattern_def._compiled:
                match = compiled.match(normalized)
                if match:
                    # Витягуємо слоти
                    slots = self._extract_slots(match, pattern_def)
                    
                    return Intent(
                        intent_type=pattern_def.intent_type,
                        slots=slots,
                        confidence=1.0,  # Regex = детерміновано
                        original_request=CommandRequest(raw_text=text),
                    )
        
        # Нічого не знайдено
        return Intent(
            intent_type=IntentType.UNKNOWN,
            slots={},
            confidence=0.0,
            original_request=CommandRequest(raw_text=text),
        )

    def _preprocess(self, text: str) -> str:
        """Нормалізує текст перед парсингом."""
        result = text.strip()
        for processor in self._preprocessors:
            result = processor(result)
        return result

    def _normalize_whitespace(self, text: str) -> str:
        """Нормалізує пробіли."""
        return " ".join(text.split())

    def _expand_contractions(self, text: str) -> str:
        """Розгортає скорочення."""
        contractions = {
            "what's": "what is",
            "it's": "it is",
            "let's": "let us",
            "i'm": "i am",
            "don't": "do not",
            "doesn't": "does not",
            "can't": "cannot",
            "won't": "will not",
        }
        result = text.lower()
        for contraction, expansion in contractions.items():
            result = result.replace(contraction, expansion)
        return result

    def _extract_slots(
        self,
        match: re.Match,
        pattern_def: NLUPattern
    ) -> Dict[str, Any]:
        """Витягує слоти з match об'єкта."""
        slots = {}
        
        for name, value in match.groupdict().items():
            if value is not None:
                # Застосовуємо postprocessor якщо є
                processor = self._slot_processors.get(name)
                if processor:
                    value = processor(value)
                slots[name] = value
        
        return slots

    def _process_path(self, path: str) -> str:
        """Обробляє шлях до файлу."""
        path = path.strip()
        # Розгортаємо ~ до home directory
        if path.startswith("~"):
            from pathlib import Path
            path = str(Path(path).expanduser())
        # Нормалізуємо шлях
        path = path.replace("\\", "/")
        return path

    def _process_url(self, url: str) -> str:
        """Обробляє URL."""
        url = url.strip()
        # Додаємо https:// якщо немає протоколу
        if not url.startswith(("http://", "https://")):
            if url.startswith("www."):
                url = "https://" + url
            else:
                url = "https://" + url
        return url

    def _process_app_name(self, name: str) -> str:
        """Обробляє назву додатку."""
        return name.strip().lower()

    def add_pattern(self, pattern: NLUPattern) -> None:
        """Додає новий шаблон."""
        self.patterns.append(pattern)
        self.patterns.sort(key=lambda p: -p.priority)

    def get_supported_intents(self) -> List[IntentType]:
        """Повертає список підтримуваних намірів."""
        return list(set(p.intent_type for p in self.patterns))

    def get_examples(self, intent_type: IntentType) -> List[str]:
        """Повертає приклади команд для наміру."""
        examples = []
        for pattern in self.patterns:
            if pattern.intent_type == intent_type:
                examples.extend(pattern.examples)
        return examples


# ============================================
# Testing Utilities
# ============================================

def test_nlu_patterns() -> None:
    """Тестує всі шаблони NLU."""
    nlu = DeterministicNLU()
    
    test_cases = [
        # (input, expected_intent, expected_slots)
        ("open calculator", IntentType.OPEN_APP, {"app_name": "calculator"}),
        ("launch notepad", IntentType.OPEN_APP, {"app_name": "notepad"}),
        ("go to https://github.com", IntentType.OPEN_URL, {"url": "https://github.com"}),
        ("search for python tutorials", IntentType.WEB_SEARCH, {"query": "python tutorials"}),
        ("list files in ~/Documents", IntentType.LIST_DIR, {}),  # path буде оброблено
        ("system info", IntentType.SYSTEM_INFO, {}),
        ("create file test.txt", IntentType.CREATE_FILE, {}),
        ("delete file old.log", IntentType.DELETE_FILE, {}),
        ("random gibberish", IntentType.UNKNOWN, {}),
    ]
    
    print("Testing NLU patterns...")
    passed = 0
    failed = 0
    
    for text, expected_intent, expected_slots in test_cases:
        intent = nlu.parse(text)
        
        if intent.intent_type == expected_intent:
            print(f"  ✓ '{text}' → {intent.intent_type.value}")
            passed += 1
        else:
            print(f"  ✗ '{text}' → {intent.intent_type.value} (expected {expected_intent.value})")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")


if __name__ == "__main__":
    test_nlu_patterns()
