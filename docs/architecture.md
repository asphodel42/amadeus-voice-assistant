# Архітектура Amadeus

## Огляд

Amadeus побудований за принципами **Clean Architecture** (Чиста Архітектура) з паттерном **Ports & Adapters** (Порти та Адаптери / Hexagonal Architecture).

## Ключові принципи

### 1. Залежності спрямовані всередину

```
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
│   (OS Adapters, Voice, Database, UI)                        │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│   (Pipeline, Orchestrator, Managers)                        │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                            │
│   (Entities, Planner, Policy, StateMachine)                 │
└─────────────────────────────────────────────────────────────┘
```

Зовнішні шари залежать від внутрішніх, але не навпаки.

### 2. Детермінована поведінка

- Core Domain не має side effects
- Один вхід → один вихід
- Всі дії явно заплановані та підтверджені

### 3. Ports & Adapters

- **Порти** (Interfaces) визначаються в Domain
- **Адаптери** (Implementations) в Infrastructure
- Легко замінити реалізацію без зміни бізнес-логіки

## Компоненти

### Core Domain (`amadeus/core/`)

#### Entities (`entities.py`)
Доменні сутності — незмінні data classes:
- `Intent` — розпізнаний намір
- `Action` — атомарна дія
- `ActionPlan` — план виконання
- `AuditEvent` — подія аудиту
- `Capability` — можливість навички

#### State Machine (`state_machine.py`)
Кінцевий автомат станів асистента:
```
IDLE → LISTENING → PROCESSING → REVIEWING → EXECUTING → IDLE
                                    ↓
                                  DENY → IDLE
```

#### Planner (`planner.py`)
Перетворює Intent → ActionPlan:
- Визначає необхідні дії
- Призначає рівні ризику
- Генерує людино-читабельні описи

#### Policy Engine (`policy.py`)
Двигун політик безпеки:
- Перевіряє capabilities
- Оцінює ризики
- Визначає тип підтвердження

### Application Layer (`amadeus/app/`)

#### Pipeline (`pipeline.py`)
Головний оркестратор:
```
Wake → ASR → NLU → Plan → Policy → Confirm → Execute → Respond
```

#### Executor (`executor.py`)
Виконує затверджені плани:
- Pre-execution validation
- Виклик адаптерів
- Логування результатів

### Infrastructure Layer (`amadeus/adapters/`)

#### OS Adapters (`os/`)
- `WindowsAdapter` — Windows 10/11
- `LinuxAdapter` — Ubuntu/Debian
- `BaseOSAdapter` — спільна логіка

#### Voice Adapters (`voice/`)
- `DeterministicNLU` — regex-based NLU
- (Планується) `VoskASR` — ASR адаптер
- (Планується) `PorcupineWakeWord`

#### Persistence (`persistence/`)
- `SQLiteAuditAdapter` — append-only аудит

## Потік даних

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Voice Input │────►│     ASR     │────►│     NLU      │
└──────────────┘     └─────────────┘     └──────────────┘
                                                │
                                                ▼
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Response   │◄────│  Executor   │◄────│   Planner    │
└──────────────┘     └─────────────┘     └──────────────┘
                           │                    │
                           ▼                    ▼
                     ┌─────────────┐     ┌──────────────┐
                     │ OS Adapter  │     │Policy Engine │
                     └─────────────┘     └──────────────┘
```

## Безпека

### Zero-Trust Model
1. Всі дії перевіряються двічі (planning + execution)
2. Capabilities явно декларуються
3. Деструктивні операції потребують typed confirmation

### Audit Log
- Append-only
- Hash chain integrity
- Локальне зберігання

## Розширюваність

### Додавання нової команди
1. Додати `IntentType` в `entities.py`
2. Додати шаблон в `nlu.py`
3. Додати handler в `Planner`
4. (Опціонально) Додати метод в OS Adapter

### Додавання нової платформи
1. Створити адаптер в `adapters/os/`
2. Розширити `BaseOSAdapter`
3. Оновити `factory.py`
