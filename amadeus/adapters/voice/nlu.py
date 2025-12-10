"""
Deterministic NLU (Natural Language Understanding)

Deterministic understanding of natural language based on regular expressions and rules.
This is a basic implementation for MVP - reliable and predictable.

Advantages:
- Deterministic results (one input -> one output)
- Low latency (<10ms)
- No dependencies on ML models
- Easy to test and debug
- Full Ukrainian language support
- Natural speech patterns (e.g., "відкрий ютуб" -> opens youtube.com)

Limitations:
- Does not understand paraphrasing
- Requires explicit patterns for each variant
- Does not scale to a large number of intents
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

from amadeus.core.entities import CommandRequest, Intent, IntentType


# ============================================
# Popular Sites/Apps Mapping
# ============================================

# Mapping of natural names to URLs (for "open youtube" -> youtube.com)
SITE_SHORTCUTS: Dict[str, str] = {
    # Video & Streaming
    "youtube": "https://youtube.com",
    "ютуб": "https://youtube.com",
    "ютюб": "https://youtube.com",
    "youtube music": "https://music.youtube.com",
    "youtube-music": "https://music.youtube.com",
    "youtube-музик": "https://music.youtube.com",
    "ютуб музик": "https://music.youtube.com",
    "ютуб-музик": "https://music.youtube.com",
    "ютуб музика": "https://music.youtube.com",
    "ютуб музік": "https://music.youtube.com",
    "netflix": "https://netflix.com",
    "нетфлікс": "https://netflix.com",
    "неться": "https://netflix.com",  # ASR variation
    "twitch": "https://twitch.tv",
    "твіч": "https://twitch.tv",
    "tiktok": "https://tiktok.com",
    "тікток": "https://tiktok.com",
    "тік ток": "https://tiktok.com",
    
    # Music
    "spotify": "https://open.spotify.com",
    "спотіфай": "https://open.spotify.com",
    "спотифай": "https://open.spotify.com",
    "soundcloud": "https://soundcloud.com",
    "саундклауд": "https://soundcloud.com",
    "саундклаут": "https://soundcloud.com",  # ASR variation
    "саунд клауд": "https://soundcloud.com",  # ASR variation
    "саунд клаут": "https://soundcloud.com",  # ASR variation
    
    # Social Media
    "facebook": "https://facebook.com",
    "фейсбук": "https://facebook.com",
    "instagram": "https://instagram.com",
    "інстаграм": "https://instagram.com",
    "інста": "https://instagram.com",
    "twitter": "https://twitter.com",
    "твіттер": "https://twitter.com",
    "твітер": "https://twitter.com",  # ASR variation (one т)
    "x": "https://x.com",
    "reddit": "https://reddit.com",
    "редіт": "https://reddit.com",
    "linkedin": "https://linkedin.com",
    "лінкедін": "https://linkedin.com",
    
    # Messengers
    "telegram": "https://web.telegram.org",
    "телеграм": "https://web.telegram.org",
    "whatsapp": "https://web.whatsapp.com",
    "вотсап": "https://web.whatsapp.com",
    "viber": "https://viber.com",
    "вайбер": "https://viber.com",
    "discord": "https://discord.com",
    "діскорд": "https://discord.com",
    "slack": "https://slack.com",
    "слак": "https://slack.com",
    
    # Development
    "github": "https://github.com",
    "гітхаб": "https://github.com",
    "гіт хаб": "https://github.com",
    "gitlab": "https://gitlab.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    
    # Search & Knowledge
    "google": "https://google.com",
    "гугл": "https://google.com",
    "угол": "https://google.com",  # ASR variation
    "wikipedia": "https://wikipedia.org",
    "вікіпедія": "https://wikipedia.org",
    "вікіпедію": "https://wikipedia.org",
    "википедія": "https://wikipedia.org",  # ASR variation
    "википедію": "https://wikipedia.org",  # ASR variation
    "вікі": "https://wikipedia.org",
    "вики": "https://wikipedia.org",
    
    # Shopping
    "amazon": "https://amazon.com",
    "амазон": "https://amazon.com",
    "rozetka": "https://rozetka.com.ua",
    "розетка": "https://rozetka.com.ua",
    "aliexpress": "https://aliexpress.com",
    "алі": "https://aliexpress.com",
    "аліекспрес": "https://aliexpress.com",
    "olx": "https://olx.ua",
    "олх": "https://olx.ua",
    
    # AI & Tools
    "chatgpt": "https://chat.openai.com",
    "чат гпт": "https://chat.openai.com",
    "чатгпт": "https://chat.openai.com",
    "чат-гпт": "https://chat.openai.com",
    "чад-гпт": "https://chat.openai.com",  # ASR variation
    "чад-гптн": "https://chat.openai.com",  # ASR variation
    "чотгпт": "https://chat.openai.com",  # ASR variation
    "claude": "https://claude.ai",
    "клод": "https://claude.ai",
    "notion": "https://notion.so",
    "ноушн": "https://notion.so",
    
    # Email
    "gmail": "https://mail.google.com",
    "гмейл": "https://mail.google.com",
    "джмейл": "https://mail.google.com",
    "джмаєл": "https://mail.google.com",  # ASR variation
    "гміл": "https://mail.google.com",  # ASR variation
    "пошта": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "outlook": "https://outlook.com",
    "аутлук": "https://outlook.com",
    
    # Maps & Travel
    "maps": "https://maps.google.com",
    "карти": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "гугл карти": "https://maps.google.com",
    
    # Entertainment
    "spotify": "https://open.spotify.com",
    "спотіфай": "https://open.spotify.com",
    "youtube music": "https://music.youtube.com",
    "ютуб музика": "https://music.youtube.com",
    "ютюб мюзік": "https://music.youtube.com",
    "ютюб музика": "https://music.youtube.com",
    
    # News
    "news": "https://news.google.com",
    "новини": "https://news.google.com",
}

# Mapping of Ukrainian app names to English (with ASR variations)
APP_NAME_ALIASES: Dict[str, str] = {
    # System apps (with Whisper ASR variations)
    "калькулятор": "calculator",
    "калькулятору": "calculator",  # ASR variation
    "калікулятор": "calculator",   # ASR variation
    "калікулятору": "calculator",  # ASR variation
    "блокнот": "notepad",
    "блокноту": "notepad",
    "провідник": "explorer",
    "файловий менеджер": "explorer",
    "термінал": "terminal",
    "командний рядок": "cmd",
    "консоль": "terminal",
    "налаштування": "settings",
    "панель керування": "control panel",
    "диспетчер завдань": "task manager",
    
    # Browsers
    "браузер": "browser",
    "хром": "chrome",
    "файрфокс": "firefox",
    "едж": "edge",
    
    # Office
    "ворд": "word",
    "ексель": "excel",
    "повер поінт": "powerpoint",
    "презентація": "powerpoint",
    
    # Media
    "музика": "spotify",
    "відео": "vlc",
    "плеєр": "vlc",
    
    # Development
    "код": "vscode",
    "редактор коду": "vscode",
    "студія": "vscode",
    "vs code": "vscode",
    "єс-код": "vscode",  # ASR variation
    "єс код": "vscode",  # ASR variation
    "ios-код": "vscode",  # ASR variation
    "іос-код": "vscode",  # ASR variation
    "вс код": "vscode",
    
    # Communication
    "діскорд": "discord",
    "телеграм": "telegram",
    "слак": "slack",
    "зум": "zoom",
    "тімс": "teams",
    
    # Other
    "стім": "steam",
    "ігри": "steam",
}

# Directory shortcuts
DIRECTORY_SHORTCUTS: Dict[str, str] = {
    # English
    "downloads": "~/Downloads",
    "download": "~/Downloads",
    "documents": "~/Documents",
    "document": "~/Documents",
    "desktop": "~/Desktop",
    "pictures": "~/Pictures",
    "picture": "~/Pictures",
    "music": "~/Music",
    "videos": "~/Videos",
    "video": "~/Videos",
    "home": "~",
    
    # Завантаження (Downloads)
    "завантаження": "~/Downloads",
    "завантаженнях": "~/Downloads",
    "завантаженні": "~/Downloads",
    "завантажень": "~/Downloads",
    "загрузки": "~/Downloads",
    "загрузках": "~/Downloads",
    
    # Документи (Documents)
    "документи": "~/Documents",
    "документах": "~/Documents",
    "документів": "~/Documents",
    "доки": "~/Documents",
    "доках": "~/Documents",
    
    # Робочий стіл (Desktop)
    "робочий стіл": "~/Desktop",
    "робочому столі": "~/Desktop",
    "робочого столу": "~/Desktop",
    "десктоп": "~/Desktop",
    "десктопі": "~/Desktop",
    
    # Зображення (Pictures)
    "фото": "~/Pictures",
    "фотках": "~/Pictures",
    "фотки": "~/Pictures",
    "зображення": "~/Pictures",
    "зображеннях": "~/Pictures",
    "картинки": "~/Pictures",
    "картинках": "~/Pictures",
    
    # Музика (Music)
    "музика": "~/Music",
    "музиці": "~/Music",
    "музики": "~/Music",
    
    # Відео (Videos)
    "відео": "~/Videos",
    "відеозаписи": "~/Videos",
    "відеозаписах": "~/Videos",
    
    # Домашня папка (Home)
    "домашня папка": "~",
    "домашній папці": "~",
    "дім": "~",
    "домівка": "~",
}


@dataclass
class NLUPattern:
    """
    Template for intent recognition.

    Attributes:
        intent_type: Type of intent for this pattern
        patterns: List of regular expressions
        slot_extractors: Functions for extracting slots
        priority: Priority (higher = checked first)
        examples: Examples of commands (for documentation/testing)
    """
    intent_type: IntentType
    patterns: List[str]
    slot_extractors: Dict[str, str] = field(default_factory=dict)
    priority: int = 0
    examples: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Compile regular expressions
        self._compiled: List[Pattern[str]] = []
        for pattern in self.patterns:
            try:
                self._compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")


# ============================================
# Templates for MVP commands
# ============================================

DEFAULT_PATTERNS: List[NLUPattern] = [
    # ============================================
    # CONFIRM - підтвердження команд (HIGHEST PRIORITY!)
    # ============================================
    NLUPattern(
        intent_type=IntentType.CONFIRM,
        patterns=[
            # Ukrainian
            r"^(?:так|ага|угу|авжеж|звісно|звичайно)\.?!?$",
            r"^(?:згоден|згодна|згідний|згідна|погоджуюсь)\.?!?$",
            r"^(?:підтверджую|підтверджуй|виконай|виконати|давай|роби)\.?!?$",
            # English
            r"^(?:yes|yeah|yep|sure|ok|okay|fine|confirm|do it|go ahead)\.?!?$",
            # Short forms
            r"^(?:y|k)$",
        ],
        priority=100,  # Highest priority to catch confirmations first
        examples=[
            "так",
            "yes",
            "окей",
            "підтверджую",
            "виконай",
            "давай",
        ],
    ),
    
    # ============================================
    # DENY - відмова від команд (HIGHEST PRIORITY!)
    # ============================================
    NLUPattern(
        intent_type=IntentType.DENY,
        patterns=[
            # Ukrainian
            r"^(?:ні|не|ніт|нє|неа|нічого|нізащо)\.?!?$",
            r"^(?:скасуй|скасувати|відміна|відмінити|стоп|зупини)\.?!?$",
            r"^(?:не треба|не потрібно|не роби|не виконуй)\.?!?$",
            # English
            r"^(?:no|nope|nah|cancel|stop|abort|never mind|forget it)\.?!?$",
            # Short forms
            r"^(?:n)$",
        ],
        priority=100,  # Highest priority to catch denials first
        examples=[
            "ні",
            "no",
            "скасуй",
            "відміна",
            "стоп",
            "не треба",
        ],
    ),
    
    # ============================================
    # OPEN_FILE - відкриття файлів (з розширенням)
    # ============================================
    NLUPattern(
        intent_type=IntentType.OPEN_FILE,
        patterns=[
            # Explicit "open file X"
            r"^(?:open|відкрий|відкри|відкрив)\s+файл\s+(?P<path>[\w\s\-а-яіїєґ\.]+)$",
            # "open X.ext" - must have file extension
            r"^(?:open|відкрий|відкри|відкрив)\s+(?P<path>[\w\s\-а-яіїєґ]+\.\w{2,4})$",
            # Ukrainian with extension
            r"^(?:покажи|відкрити)\s+(?P<path>[\w\s\-а-яіїєґ]+\.\w{2,4})$",
        ],
        priority=20,  # Higher than OPEN_APP to catch files first
        examples=[
            "відкрий файл test.txt",
            "відкрий notes.pdf",
            "open document.docx",
            "покажи readme.md",
        ],
    ),
    
    # ============================================
    # OPEN_APP - відкриття програм
    # ============================================
    NLUPattern(
        intent_type=IntentType.OPEN_APP,
        patterns=[
            # English
            r"^open\s+(?P<app_name>[\w\s\-]+?)(?:\s+app)?$",
            r"^launch\s+(?P<app_name>[\w\s\-]+)$",
            r"^start\s+(?P<app_name>[\w\s\-]+)$",
            r"^run\s+(?P<app_name>[\w\s\-]+)$",
            # Ukrainian (with ASR variations)
            r"^(?:відкрий|відкрій|відкри|відкрив|відкрай|відкрой|підкрай|відкрити|відкрию|відкрить)\s+(?P<app_name>[\w\s\-а-яіїєґ]+?)\.?$",
            r"^(?:запусти|запустити|запустіть|запустив)\s+(?P<app_name>[\w\s\-а-яіїєґ]+?)\.?$",
            r"^покажи\s+(?P<app_name>[\w\s\-а-яіїєґ]+)$",
        ],
        priority=10,
        examples=[
            "open calculator",
            "launch notepad",
            "start browser",
            "відкрий калькулятор",
            "відкри калькулятор",
            "відкрив калькулятор",
            "запусти браузер",
            "відкрий ютуб",
        ],
    ),
    
    # ============================================
    # OPEN_URL - відкриття веб-сайтів
    # ============================================
    NLUPattern(
        intent_type=IntentType.OPEN_URL,
        patterns=[
            # Explicit URLs
            r"^(?:go\s+to|open|visit|navigate\s+to)\s+(?P<url>https?://\S+)$",
            r"^(?:go\s+to|open|visit)\s+(?P<url>www\.\S+)$",
            r"^(?:go\s+to|open|visit)\s+(?P<url>[\w\.-]+\.(?:com|org|net|io|ua|tv|ai|co|dev|edu|gov))(?:/\S*)?$",
            r"^open\s+url\s+(?P<url>\S+)$",
            # Ukrainian
            r"^(?:відкрий|перейди\s+на|зайди\s+на|покажи)\s+(?P<url>https?://\S+)$",
            r"^(?:відкрий|перейди\s+на|зайди\s+на|покажи)\s+(?P<url>www\.\S+)$",
            r"^(?:відкрий|перейди\s+на|зайди\s+на|покажи)\s+(?P<url>[\w\.-]+\.(?:com|org|net|io|ua|tv|ai|co|dev|edu|gov))(?:/\S*)?$",
        ],
        priority=15,  # Higher priority than OPEN_APP to catch URLs
        examples=[
            "go to https://github.com",
            "open www.google.com",
            "visit github.com",
            "відкрий youtube.com",
            "перейди на google.com",
        ],
    ),
    
    # ============================================
    # WEB_SEARCH - пошук в інтернеті
    # ============================================
    NLUPattern(
        intent_type=IntentType.WEB_SEARCH,
        patterns=[
            # English
            r"^search\s+(?:for\s+)?(?P<query>.+)$",
            r"^google\s+(?P<query>.+)$",
            r"^look\s+up\s+(?P<query>.+)$",
            r"^find\s+(?:information\s+(?:about|on)\s+)?(?P<query>.+)$",
            r"^what\s+is\s+(?P<query>.+)$",
            r"^who\s+is\s+(?P<query>.+)$",
            r"^how\s+to\s+(?P<query>.+)$",
            # Ukrainian
            r"^пошук\s+(?P<query>.+)$",
            r"^знайди\s+(?P<query>.+)$",
            r"^знайти\s+(?P<query>.+)$",
            r"^шукай\s+(?P<query>.+)$",
            r"^шукати\s+(?P<query>.+)$",
            r"^що\s+таке\s+(?P<query>.+)$",
            r"^хто\s+такий\s+(?P<query>.+)$",
            r"^хто\s+така\s+(?P<query>.+)$",
            r"^як\s+(?P<query>.+)$",
            r"^загугли\s+(?P<query>.+)$",
            r"^погугли\s+(?P<query>.+)$",
        ],
        priority=5,
        examples=[
            "search for python tutorials",
            "google machine learning",
            "what is clean architecture",
            "пошук рецепти борщу",
            "знайди погоду в Києві",
            "що таке машинне навчання",
        ],
    ),
    
    # ============================================
    # LIST_DIR - перегляд вмісту папки
    # ============================================
    NLUPattern(
        intent_type=IntentType.LIST_DIR,
        patterns=[
            # English
            r"^list\s+(?:files\s+in\s+)?(?P<path>.+)$",
            r"^show\s+files\s+(?:in\s+)?(?P<path>.+)$",
            r"^show\s+(?P<path>~/?\w+)$",  # "show ~/Downloads" or "show downloads"
            r"^what(?:'s|\s+is)\s+in\s+(?P<path>.+)$",
            r"^ls\s+(?P<path>.+)$",
            r"^dir\s+(?P<path>.+)$",
            r"^list\s+directory(?:\s+(?P<path>.+))?$",
            r"^show\s+directory(?:\s+(?P<path>.+))?$",
            # Ukrainian - specific patterns for file listing
            r"^покажи\s+файли\s+(?:в\s+)?(?:папці\s+)?(?P<path>.+)$",
            r"^покажи\s+вміст\s+(?:папки\s+)?(?P<path>.+)$",
            r"^що\s+(?:є\s+)?в\s+(?:папці\s+)?(?P<path>.+)$",
            r"^список\s+(?:файлів\s+)?(?:в\s+)?(?P<path>.+)$",
            r"^вміст\s+(?:папки\s+)?(?P<path>.+)$",
            r"^відкрий\s+папку\s+(?P<path>.+)$",
        ],
        priority=12,  # Higher than OPEN_APP to match "покажи файли" first
        examples=[
            "list files in ~/Documents",
            "show ~/Downloads",
            "what's in my documents",
            "ls .",
            "покажи файли в завантаженнях",
            "що в документах",
            "вміст папки downloads",
        ],
    ),
    
    # ============================================
    # READ_FILE - читання файлу
    # ============================================
    NLUPattern(
        intent_type=IntentType.READ_FILE,
        patterns=[
            # English
            r"^read\s+(?:file\s+)?(?P<path>.+)$",
            r"^show\s+(?:contents?\s+of\s+)?(?:file\s+)?(?P<path>[\w\./\\\-]+\.\w+)$",
            r"^cat\s+(?P<path>.+)$",
            r"^view\s+(?:file\s+)?(?P<path>.+)$",
            r"^display\s+(?:file\s+)?(?P<path>.+)$",
            # Ukrainian
            r"^прочитай\s+(?:файл\s+)?(?P<path>.+)$",
            r"^прочитати\s+(?:файл\s+)?(?P<path>.+)$",
            r"^покажи\s+(?:вміст\s+)?(?:файлу?\s+)?(?P<path>[\w\./\\\-]+\.\w+)$",
            r"^відкрий\s+файл\s+(?P<path>.+)$",
        ],
        priority=7,
        examples=[
            "read file ~/Documents/notes.txt",
            "show contents of readme.md",
            "cat config.json",
            "прочитай файл readme.md",
            "покажи вміст config.json",
        ],
    ),
    
    # ============================================
    # CREATE_FILE - створення файлу
    # ============================================
    NLUPattern(
        intent_type=IntentType.CREATE_FILE,
        patterns=[
            # English
            r"^create\s+(?:a\s+)?(?:new\s+)?file\s+(?P<path>.+?)(?:\s+with\s+(?:content\s+)?(?P<content>.+))?$",
            r"^make\s+(?:a\s+)?(?:new\s+)?file\s+(?P<path>.+)$",
            r"^touch\s+(?P<path>.+)$",
            r"^new\s+file\s+(?P<path>.+)$",
            # Ukrainian
            r"^створи\s+(?:новий\s+)?файл\s+(?P<path>.+?)(?:\s+(?:з\s+)?(?:текстом|вмістом)\s+(?P<content>.+))?$",
            r"^створити\s+(?:новий\s+)?файл\s+(?P<path>.+)$",
            r"^новий\s+файл\s+(?P<path>.+)$",
        ],
        priority=5,
        examples=[
            "create file ~/Documents/notes.txt",
            "make a new file test.py",
            "touch readme.md",
            "create file hello.txt with content Hello World",
            "створи файл test.txt",
            "створи файл notes.txt з текстом Привіт",
        ],
    ),
    
    # ============================================
    # WRITE_FILE - запис у файл
    # ============================================
    NLUPattern(
        intent_type=IntentType.WRITE_FILE,
        patterns=[
            # English
            r"^write\s+(?P<content>.+?)\s+to\s+(?:file\s+)?(?P<path>.+)$",
            r"^save\s+(?P<content>.+?)\s+to\s+(?:file\s+)?(?P<path>.+)$",
            r"^append\s+(?P<content>.+?)\s+to\s+(?:file\s+)?(?P<path>.+)$",
            # Ukrainian
            r"^запиши\s+(?P<content>.+?)\s+(?:в|до|у)\s+(?:файл\s+)?(?P<path>.+)$",
            r"^збережи\s+(?P<content>.+?)\s+(?:в|до|у)\s+(?:файл\s+)?(?P<path>.+)$",
            r"^додай\s+(?P<content>.+?)\s+(?:в|до|у)\s+(?:файл\s+)?(?P<path>.+)$",
        ],
        priority=5,
        examples=[
            "write Hello World to ~/Documents/test.txt",
            "save my notes to notes.txt",
            "запиши привіт у файл test.txt",
            "збережи замітку в notes.txt",
        ],
    ),
    
    # ============================================
    # DELETE_FILE - видалення файлу
    # ============================================
    NLUPattern(
        intent_type=IntentType.DELETE_FILE,
        patterns=[
            # English
            r"^delete\s+(?:file\s+)?(?P<path>.+)$",
            r"^remove\s+(?:file\s+)?(?P<path>.+)$",
            r"^rm\s+(?:-r\s+)?(?P<path>.+)$",
            r"^erase\s+(?:file\s+)?(?P<path>.+)$",
            # Ukrainian
            r"^видали\s+(?:файл\s+)?(?P<path>.+)$",
            r"^видалити\s+(?:файл\s+)?(?P<path>.+)$",
            r"^вилучи\s+(?:файл\s+)?(?P<path>.+)$",
            r"^вилучити\s+(?:файл\s+)?(?P<path>.+)$",
            r"^зітри\s+(?:файл\s+)?(?P<path>.+)$",
            # ASR variations (Whisper outputs)
            r"^відали\s+(?:файл\s+)?(?P<path>.+)$",
            r"^ви\s+дали\s+файл\s+(?P<path>.+)$", 
            r"^видаль\s+(?:файл\s+)?(?P<path>.+)$", 
        ],
        priority=5,
        examples=[
            "delete file ~/Documents/old.txt",
            "remove temp.log",
            "rm -r ~/old_folder",
            "видали файл test.txt",
            "вилучи temp.log",
        ],
    ),
    
    # ============================================
    # SYSTEM_INFO - інформація про систему
    # ============================================
    NLUPattern(
        intent_type=IntentType.SYSTEM_INFO,
        patterns=[
            # English
            r"^(?:show\s+)?system\s*[-\s]?\s*info(?:rmation)?$",
            r"^systeminfo$",
            r"^what(?:'s|\s+is)\s+my\s+system$",
            r"^system\s+status$",
            r"^computer\s+info(?:rmation)?$",
            r"^about\s+(?:this\s+)?computer$",
            r"^my\s+computer\s+specs?$",
            # Ukrainian
            r"^інформація\s+про\s+систему$",
            r"^інфо\s+(?:про\s+)?систем[иу]$",
            r"^статус\s+систем[иу]$",
            r"^(?:покажи\s+)?систем(?:ну)?\s+інформацію$",
            r"^системна\s+інформація$",  # exact match
            r"^про\s+комп'?ютер$",
            r"^характеристики\s+(?:комп'?ютера)?$",
            r"^що\s+за\s+система$",
            # ASR variations
            r"^систем[-\s]?інф[оа]\.?$",
            r"^інфо[-\s]?систем[иу]\.?$",
            r"^систем[-\s]?инфо\.?$",  
            # Time/Date commands (mapped to SYSTEM_INFO for now)
            r"^котр[аоу][-\s]?година\.?$",
            r"^(?:який\s+)?час[\.!]?$", 
            r"^(?:яка\s+)?дата[\.!]?$", 
            r"^(?:який\s+)?(?:сьогодні\s+)?день[\.!]?$",
            r"^скільки\s+(?:зараз\s+)?час[ау]?[\.!]?$",
        ],
        priority=5,
        examples=[
            "show system info",
            "what's my system",
            "system status",
            "інформація про систему",
            "інфо системи",
            "характеристики комп'ютера",
            "котра година",
            "час",
        ],
    ),
]


class DeterministicNLU:
    """
    Deterministic natural language understanding.

    Uses regular expressions to recognize intents and extract slots.
    Supports both English and Ukrainian languages.
    Handles natural speech patterns like "відкрий ютуб" -> opens youtube.com

    Example:
    ```
    nlu = DeterministicNLU()
    intent = nlu.parse("open calculator")
    # Intent(intent_type=IntentType.OPEN_APP, slots={"app_name": "calculator"}, ...)
    
    intent = nlu.parse("відкрий ютуб")
    # Intent(intent_type=IntentType.OPEN_URL, slots={"url": "https://youtube.com"}, ...)
    ```
    """

    def __init__(self, patterns: Optional[List[NLUPattern]] = None) -> None:
        self.patterns = patterns or DEFAULT_PATTERNS.copy()
        # Sort by priority (higher -> checked first)
        self.patterns.sort(key=lambda p: -p.priority)

        # Preprocessors for text normalization
        self._preprocessors: List[Callable[[str], str]] = [
            self._normalize_whitespace,
            self._expand_contractions,
        ]

        # Postprocessors for slots
        self._slot_processors: Dict[str, Callable[[str], str]] = {
            "path": self._process_path,
            "url": self._process_url,
            "app_name": self._process_app_name,
        }

    def parse(self, text: str) -> Intent:
        """
        Parse command text into structured intent.

        Args:
            text: Command text (after ASR)

        Returns:
            Recognized Intent
        """
        # Preprocessing
        normalized = self._preprocess(text)
        
        # First, check if this is a site shortcut (e.g., "відкрий ютуб")
        site_intent = self._check_site_shortcut(normalized, text)
        if site_intent:
            return site_intent

        # Try to find a matching pattern
        for pattern_def in self.patterns:
            for compiled in pattern_def._compiled:
                match = compiled.match(normalized)
                if match:
                    # Extract slots
                    slots = self._extract_slots(match, pattern_def)
                    
                    # Special handling: check if app_name is actually a site
                    if pattern_def.intent_type == IntentType.OPEN_APP:
                        app_name = slots.get("app_name", "").lower()
                        if app_name in SITE_SHORTCUTS:
                            return Intent(
                                intent_type=IntentType.OPEN_URL,
                                slots={"url": SITE_SHORTCUTS[app_name]},
                                confidence=1.0,
                                original_request=CommandRequest(raw_text=text),
                            )
                    
                    return Intent(
                        intent_type=pattern_def.intent_type,
                        slots=slots,
                        confidence=1.0,  # Regex = high confidence
                        original_request=CommandRequest(raw_text=text),
                    )

        # Nothing found
        return Intent(
            intent_type=IntentType.UNKNOWN,
            slots={},
            confidence=0.0,
            original_request=CommandRequest(raw_text=text),
        )
    
    def _check_site_shortcut(self, normalized: str, original: str) -> Optional[Intent]:
        """
        Check if the command is trying to open a known site.
        
        Handles patterns like:
        - "відкрий ютуб" -> youtube.com
        - "відкри ютуб" -> youtube.com (ASR variation)
        - "open youtube" -> youtube.com
        """
        # Check for "open/відкрий <site>" pattern (with ASR variations)
        open_patterns = [
            r"^(?:open|launch|start|відкрий|відкри|відкрив|відкрай|відкрити|запусти|запустити|покажи)\s+(.+?)\.?$"
        ]
        
        for pattern in open_patterns:
            match = re.match(pattern, normalized, re.IGNORECASE)
            if match:
                target = match.group(1).strip().lower()
                
                # Remove trailing punctuation that Whisper might add
                target = target.rstrip('.')
                
                # Check if it's a known site shortcut
                if target in SITE_SHORTCUTS:
                    return Intent(
                        intent_type=IntentType.OPEN_URL,
                        slots={"url": SITE_SHORTCUTS[target]},
                        confidence=1.0,
                        original_request=CommandRequest(raw_text=original),
                    )
        
        return None

    def _preprocess(self, text: str) -> str:
        """Normalize text before parsing."""
        result = text.strip()
        for processor in self._preprocessors:
            result = processor(result)
        return result

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        return " ".join(text.split())

    def _expand_contractions(self, text: str) -> str:
        """Expand contractions."""
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
        """Extract slots from match object."""
        slots = {}
        
        for name, value in match.groupdict().items():
            if value is not None:
                # Apply postprocessor if exists
                processor = self._slot_processors.get(name)
                if processor:
                    value = processor(value)
                slots[name] = value
        
        return slots

    def _process_path(self, path: str) -> str:
        """Process file path."""
        from pathlib import Path as PathLib
        
        path = path.strip()
        
        # Fix ASR errors: "крапка txt" -> ".txt"
        path = self._fix_file_extension(path)
        
        # Remove trailing period (from ASR output)
        if path.endswith(".") and not path.endswith(".."):
            path = path[:-1].strip()
        
        # Remove quotes «» (from ASR output)
        path = path.replace("«", "").replace("»", "")
        
        # Check for directory shortcuts (e.g., "downloads" -> "~/Downloads")
        path_lower = path.lower().strip()
        if path_lower in DIRECTORY_SHORTCUTS:
            path = DIRECTORY_SHORTCUTS[path_lower]
        
        # If path is just a filename (no directory), put it in ~/Documents
        # This ensures files are created in an allowed directory
        if not path.startswith(("~", "/", "C:", "D:", "E:")) and "/" not in path and "\\" not in path:
            # Check if it looks like a file (has extension)
            if "." in path:
                path = f"~/Documents/{path}"
            # If no extension at all, add .txt and put in Documents
            else:
                path = f"~/Documents/{path}.txt"
        
        # Expand ~ to home directory
        if path.startswith("~"):
            path = str(PathLib(path).expanduser())
        
        # Normalize path separators
        path = path.replace("\\", "/")
        return path
    
    def _fix_file_extension(self, path: str) -> str:
        """
        Fix file extension from ASR output.
        
        ASR often transcribes "file.txt" as "file крапка txt"
        This function corrects such errors.
        
        Examples:
            "test крапка txt" -> "test.txt"
            "notes крапка doc" -> "notes.docx"
            "файл крапка текст" -> "файл.txt"
        """
        # Replace "крапка <extension>" with ".<extension>"
        path = re.sub(r"\s+крапка\s+(\w+)", r".\1", path, flags=re.IGNORECASE)
        
        # Map common ASR variations to proper extensions
        extension_map = {
            ".doc": ".docx",
            ".текст": ".txt",
            ".текста": ".txt",
            ".тексті": ".txt",
            ".доці": ".docx",
            ".док": ".docx",
            ".пдф": ".pdf",
            ".піді еф": ".pdf",
            ".ексель": ".xlsx",
            ".ексел": ".xlsx",
            ".повер поінт": ".pptx",
            ".джейсон": ".json",
            ".сієс віі": ".csv",
        }
        
        for wrong_ext, correct_ext in extension_map.items():
            if path.lower().endswith(wrong_ext):
                path = path[:-len(wrong_ext)] + correct_ext
                break
        
        return path

    def _process_url(self, url: str) -> str:
        """Process URL."""
        url = url.strip()
        # Add https:// if no protocol is present
        if not url.startswith(("http://", "https://")):
            if url.startswith("www."):
                url = "https://" + url
            else:
                url = "https://" + url
        return url

    def _process_app_name(self, name: str) -> str:
        """Process app name, including Ukrainian aliases."""
        name = name.strip().lower()
        
        # Check for Ukrainian app name aliases
        if name in APP_NAME_ALIASES:
            name = APP_NAME_ALIASES[name]
        
        return name

    def add_pattern(self, pattern: NLUPattern) -> None:
        """Add new pattern."""
        self.patterns.append(pattern)
        self.patterns.sort(key=lambda p: -p.priority)

    def get_supported_intents(self) -> List[IntentType]:
        """Returns a list of supported intents."""
        return list(set(p.intent_type for p in self.patterns))

    def get_examples(self, intent_type: IntentType) -> List[str]:
        """Returns example commands for the intent."""
        examples = []
        for pattern in self.patterns:
            if pattern.intent_type == intent_type:
                examples.extend(pattern.examples)
        return examples


# ============================================
# Testing Utilities
# ============================================

def test_nlu_patterns() -> None:
    """Tests all NLU patterns including Ukrainian."""
    nlu = DeterministicNLU()
    
    test_cases = [
        # Confirmation commands
        ("так", IntentType.CONFIRM, {}),
        ("yes", IntentType.CONFIRM, {}),
        ("підтверджую", IntentType.CONFIRM, {}),
        ("давай", IntentType.CONFIRM, {}),
        ("ok", IntentType.CONFIRM, {}),
        
        # Denial commands
        ("ні", IntentType.DENY, {}),
        ("no", IntentType.DENY, {}),
        ("скасуй", IntentType.DENY, {}),
        ("стоп", IntentType.DENY, {}),
        ("не треба", IntentType.DENY, {}),
        
        # English commands
        ("open calculator", IntentType.OPEN_APP, {"app_name": "calculator"}),
        ("launch notepad", IntentType.OPEN_APP, {"app_name": "notepad"}),
        ("go to https://github.com", IntentType.OPEN_URL, {"url": "https://github.com"}),
        ("search for python tutorials", IntentType.WEB_SEARCH, {"query": "python tutorials"}),
        ("system info", IntentType.SYSTEM_INFO, {}),
        
        # Site shortcuts (English)
        ("open youtube", IntentType.OPEN_URL, {"url": "https://youtube.com"}),
        ("open github", IntentType.OPEN_URL, {"url": "https://github.com"}),
        ("open telegram", IntentType.OPEN_URL, {"url": "https://web.telegram.org"}),
        
        # Open files (with extension)
        ("open test.txt", IntentType.OPEN_FILE, {}),
        ("відкрий файл notes.pdf", IntentType.OPEN_FILE, {}),
        ("відкрий readme.md", IntentType.OPEN_FILE, {}),
        
        # Ukrainian commands
        ("відкрий калькулятор", IntentType.OPEN_APP, {"app_name": "calculator"}),
        ("запусти браузер", IntentType.OPEN_APP, {"app_name": "browser"}),
        
        # Ukrainian site shortcuts
        ("відкрий ютуб", IntentType.OPEN_URL, {"url": "https://youtube.com"}),
        ("відкрий телеграм", IntentType.OPEN_URL, {"url": "https://web.telegram.org"}),
        ("запусти гітхаб", IntentType.OPEN_URL, {"url": "https://github.com"}),
        ("відкрий інстаграм", IntentType.OPEN_URL, {"url": "https://instagram.com"}),
        
        # Ukrainian search
        ("пошук рецепти борщу", IntentType.WEB_SEARCH, {"query": "рецепти борщу"}),
        ("знайди погоду в києві", IntentType.WEB_SEARCH, {}),
        ("що таке машинне навчання", IntentType.WEB_SEARCH, {}),
        
        # Ukrainian file operations
        ("покажи файли в завантаженнях", IntentType.LIST_DIR, {}),
        ("створи файл test.txt", IntentType.CREATE_FILE, {}),
        ("видали файл old.log", IntentType.DELETE_FILE, {}),
        
        # Ukrainian system
        ("інформація про систему", IntentType.SYSTEM_INFO, {}),
        ("інфо системи", IntentType.SYSTEM_INFO, {}),
        
        # Unknown
        ("random gibberish", IntentType.UNKNOWN, {}),
        ("абракадабра", IntentType.UNKNOWN, {}),
    ]
    
    print("Testing NLU patterns (English + Ukrainian)...")
    print("=" * 60)
    passed = 0
    failed = 0
    
    for text, expected_intent, expected_slots in test_cases:
        intent = nlu.parse(text)
        
        intent_match = intent.intent_type == expected_intent
        
        if intent_match:
            print(f"  ✓ '{text}'")
            print(f"      -> {intent.intent_type.value}", end="")
            if intent.slots:
                print(f" {intent.slots}")
            else:
                print()
            passed += 1
        else:
            print(f"  ✗ '{text}'")
            print(f"      -> {intent.intent_type.value} (expected {expected_intent.value})")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")


if __name__ == "__main__":
    test_nlu_patterns()
