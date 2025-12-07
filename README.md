# Amadeus — Privacy-First Local PC Voice Assistant

> "Jarvis-inspired, privacy-first local PC voice assistant that executes structured commands safely."

## 🎯 Огляд проєкту

Amadeus — це голосовий асистент для ПК, що працює локально без потреби в хмарних сервісах. 
Проєкт орієнтований на приватність, безпеку та детерміновану поведінку.

## 🏗️ Архітектура

Проєкт побудований за принципами **Clean Architecture** з паттерном **Ports & Adapters**:

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer                              │
│                    (PyQt5 Desktop)                          │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                          │
│         (Orchestrator, Pipeline, Managers)                  │
├─────────────────────────────────────────────────────────────┤
│                     Domain Layer                             │
│    (Entities, Planner, PolicyEngine, StateMachine)         │
├─────────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                        │
│      (OS Adapters, Voice, Persistence, Sandbox)            │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Структура проєкту

```
amadeus/
├── core/                   # Чистий Python домен
│   ├── entities.py         # Доменні сутності
│   ├── ports.py            # Інтерфейси (Протоколи)
│   ├── planner.py          # Планувальник дій
│   ├── policy.py           # Двигун політик безпеки
│   └── state_machine.py    # Кінцевий автомат станів
├── adapters/               # Реалізація портів
│   ├── os/                 # OS-специфічні адаптери
│   ├── voice/              # ASR, Wake Word, TTS
│   └── persistence/        # Збереження даних
├── app/                    # Оркестрація
│   └── pipeline.py         # Головний пайплайн
├── ui/                     # PyQt5 інтерфейс
├── sandbox/                # Rust пісочниця
├── plugins/                # Зовнішні навички
└── tests/                  # Тести
```

## 🚀 Швидкий старт

### Передумови

- Python 3.10+
- Rust 1.70+ (для sandbox)
- Windows 10/11 або Ubuntu 22.04+

### Встановлення

```bash
# Клонування репозиторію
git clone https://github.com/yourusername/amadeus-voice-assistant.git
cd amadeus-voice-assistant

# Створення віртуального середовища
python -m venv env

# Активація (Windows)
.\env\Scripts\activate
# Активація (Linux/macOS)
source env/bin/activate

# Встановлення залежностей
pip install -r requirements.txt
```

### Запуск

```bash
python -m amadeus.app.main
```

## 🔒 Модель безпеки

- **Zero-Trust Skills**: Жодна навичка не має повного доступу за замовчуванням
- **Capability Manifests**: Явна декларація дозволів
- **Signed Plugins**: Верифікація підписів плагінів
- **Audit Logs**: Append-only логування всіх дій
- **Rust Sandbox**: Ізоляція небезпечних операцій

## 📋 Підтримувані команди (MVP)

| Команда | Рівень ризику | Потребує підтвердження |
|---------|---------------|------------------------|
| Open Application | SAFE | Ні |
| List Directory | SAFE | Ні |
| System Info | SAFE | Ні |
| Open URL | MEDIUM | Так (для non-HTTPS) |
| Web Search | MEDIUM | Ні |
| Create File | HIGH | Так |
| Write File | HIGH | Так |
| Delete File | DESTRUCTIVE | Так (typed confirmation) |

## 🎤 Голосовий режим

Amadeus використовує **Faster-Whisper** для розпізнавання мови — він працює офлайн та підтримує мультимовність (українська + англійські слова одночасно).

### Запуск голосового режиму

```bash
# Базовий запуск (модель small за замовчуванням)
python -m amadeus.app.main --voice

# З меншою моделлю (швидше, але гірша якість)
python -m amadeus.app.main --voice --whisper-model tiny

# З примусовою українською мовою
python -m amadeus.app.main --voice --language uk
```

### Доступні моделі Whisper

| Модель | Розмір | Швидкість | Якість |
|--------|--------|-----------|--------|
| tiny | 39MB | Швидко | Базова |
| base | 74MB | Швидко | Добра |
| **small** | 244MB | Середньо | Дуже добра ✅ |
| medium | 769MB | Повільно | Відмінна |
| large-v3 | 1.5GB | Дуже повільно | Найкраща |

### Приклади команд

```
"Amadeus, відкрий калькулятор"
"Amadeus, відкрий YouTube"
"Amadeus, пошук погода в Києві"
"Amadeus, покажи файли в завантаженнях"
```

## 🧪 Тестування

```bash
# Модульні тести
pytest tests/unit

# Інтеграційні тести
pytest tests/integration

# Тести безпеки
pytest tests/security
```

## 📚 Документація

- [Архітектурний огляд](docs/architecture.md)
- [Модель безпеки](docs/security.md)
- [API Reference](docs/api.md)
- [Дослідницький звіт](docs/research.md)

## 📄 Ліцензія

MIT License — див. [LICENSE](LICENSE)

## 🤝 Контрибуція

Див. [CONTRIBUTING.md](CONTRIBUTING.md) для деталей.