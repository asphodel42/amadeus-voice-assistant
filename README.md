# Amadeus — Privacy-First Local PC Voice Assistant

> "Jarvis-inspired, privacy-first local PC voice assistant that executes structured commands safely."

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Project Overview

Amadeus is a local PC voice assistant that works entirely offline without cloud services. 
The project focuses on **privacy**, **security**, and **deterministic behavior**.

### ✨ Key Features

- 🎙️ **Offline Voice Recognition** — Faster-Whisper (multilingual support)
- 🔐 **Risk-Based Confirmation** — Two-step approval for dangerous commands
- 🗣️ **Emotional TTS** — Female voice with 8 emotion types and SSML markup
- 📊 **Comprehensive Audit Logging** — SQLite database with hash chain integrity
- 🧠 **Intelligent NLU** — Deterministic intent recognition with ASR error correction
- 🛡️ **Policy Engine** — Zero-trust security with capability-based permissions
- 🔄 **State Machine** — Deterministic transitions between assistant states

## 🏗️ Architecture

The project is built using **Clean Architecture** principles with **Ports & Adapters** pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer                             │
│                 (CLI / Future: PyQt5)                       │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                         │
│           VoicePipeline • ActionExecutor                    │
│         State Machine • Event System • Audit                │
├─────────────────────────────────────────────────────────────┤
│                     Domain Layer                            │
│    Entities • Planner • PolicyEngine • StateMachine         │
│              Intent • ActionPlan • RiskLevel                │
├─────────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                       │
│   OS Adapters • Voice (ASR/TTS/WakeWord) • Persistence      │
│      Windows/Linux • Whisper • Piper • SQLite               │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

- **VoicePipeline** — Main orchestrator coordinating all stages
- **DeterministicNLU** — Regex-based intent recognition with file extension normalization
- **Planner** — Converts intents to executable action plans
- **PolicyEngine** — Risk assessment and permission enforcement
- **StateMachine** — Manages assistant states (IDLE → LISTENING → PROCESSING → REVIEWING → EXECUTING)
- **ActionExecutor** — Executes action plans with proper error handling
- **EmotionalTTS** — Natural speech with 8 emotion profiles and pause markup

## 📁 Project Structure

```
amadeus/
├── core/                   # Pure Python domain layer
│   ├── entities.py         # Domain entities (Intent, ActionPlan, RiskLevel)
│   ├── ports.py            # Interfaces (Protocols)
│   ├── planner.py          # Action planner (Intent → ActionPlan)
│   ├── policy.py           # Security policy engine
│   └── state_machine.py    # Finite state machine (FSM)
├── adapters/               # Infrastructure implementations
│   ├── os/                 # OS-specific adapters (Windows/Linux)
│   │   ├── windows.py      # Windows operations
│   │   └── linux.py        # Linux operations
│   ├── voice/              # Voice processing
│   │   ├── asr.py          # Automatic Speech Recognition (Whisper)
│   │   ├── tts.py          # Text-to-Speech (Piper) with emotions
│   │   ├── nlu.py          # Natural Language Understanding (Regex)
│   │   ├── wake_word.py    # Wake word detection (Porcupine)
│   │   └── audio_input.py  # Microphone input (PyAudio)
│   └── persistence/        # Data storage
│       └── audit.py        # Audit logging (SQLite with hash chain)
├── app/                    # Application orchestration
│   ├── pipeline.py         # Main voice pipeline
│   ├── executor.py         # Action executor
│   └── main.py             # Entry point
├── ui/                     # User interface (future PyQt5)
├── sandbox/                # Rust sandbox (future isolation)
├── plugins/                # External skills (future extensibility)
└── tests/                  # Test suite
    ├── unit/               # Unit tests
    ├── integration/        # Integration tests
    └── security/           # Security tests
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Windows 10/11 or Ubuntu 22.04+ 
- Microphone (for voice mode)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/amadeus-voice-assistant.git
cd amadeus-voice-assistant

# Create virtual environment
python -m venv env

# Activate (Windows)
.\env\Scripts\activate
# Activate (Linux/macOS)
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

```

### Running

#### Text Mode (Testing)

```bash
# Interactive CLI mode
python -m amadeus.app.main

# Single command
python -m amadeus.app.main --text "open calculator"

# Dry run (simulation without execution)
python -m amadeus.app.main --dry-run
```

#### Voice Mode

```bash
# Basic voice mode (default: small Whisper model)
python -m amadeus.app.main --voice

# With specific Whisper model
python -m amadeus.app.main --voice --whisper-model tiny

# With specific language
python -m amadeus.app.main --voice --language uk

# Skip wake word (for testing)
python -m amadeus.app.main --voice --skip-wake
```

## 🔒 Security Model

- **Zero-Trust Skills**: No skill has full access by default
- **Capability Manifests**: Explicit permission declarations
- **Signed Plugins**: Plugin signature verification
- **Audit Logs**: Append-only logging of all actions
- **Rust Sandbox**: Isolation of dangerous operations

## 📋 Supported Commands (MVP)

| Command | Risk Level | Requires Confirmation |
|---------|------------|----------------------|
| Open Application | SAFE | No |
| List Directory | SAFE | No |
| System Info | SAFE | No |
| Open URL | MEDIUM | Yes (for non-HTTPS) |
| Web Search | MEDIUM | No |
| Create File | HIGH | Yes |
| Write File | HIGH | Yes |
| Delete File | DESTRUCTIVE | Yes (typed confirmation) |

## 🎤 Voice Mode

Amadeus uses **Faster-Whisper** for speech recognition — it works offline and supports multilingual input (Ukrainian + English simultaneously).

### Voice Pipeline Features

- 🎙️ **Wake Word Detection** — Custom "Amadeus" keyword using Porcupine
- 🗣️ **Speech Recognition** — Faster-Whisper with VAD (Voice Activity Detection)
- 🧠 **Intent Recognition** — ASR error correction + file extension normalization
- 🎭 **Emotional TTS** — Female voice with 8 emotion types
- ⏸️ **SSML Markup** — Natural pauses (`<pause>`, `<break>`)
- 🔐 **Confirmation Dialogs** — Voice-based confirmation for risky commands

### Running Voice Mode

```bash
# Basic voice mode (default: small Whisper model)
python -m amadeus.app.main --voice

# With smaller model (faster, lower quality)
python -m amadeus.app.main --voice --whisper-model tiny

# With forced Ukrainian language
python -m amadeus.app.main --voice --language uk

# Skip wake word (for testing)
python -m amadeus.app.main --voice --skip-wake
```

### Available Whisper Models

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| tiny | 39MB | Fast | Basic |
| base | 74MB | Fast | Good |
| **small** | 244MB | Medium | Very Good ✅ |
| medium | 769MB | Slow | Excellent |
| large-v3 | 1.5GB | Very Slow | Best |

### Voice Command Examples

```
# English
"Amadeus, open calculator"
"Amadeus, open YouTube"
"Amadeus, search weather in Kyiv"
"Amadeus, show files in downloads"

# Ukrainian
"Amadeus, відкрий калькулятор"
"Amadeus, відкрий YouTube"
"Amadeus, пошук погода в Києві"
"Amadeus, покажи файли в завантаженнях"

# Mixed (works automatically)
"Amadeus, open file звіт.txt"
"Amadeus, відкрий notepad"
```

### Emotional TTS

Amadeus responds with different emotions based on context:

| Situation | Emotion | Example Response |
|-----------|---------|------------------|
| Greeting | `friendly` | "Hello! I am Amadeus. <pause> Ready to help." |
| Command received | `confident` | "Got it. <pause> Done" |
| Error | `concerned` | "Sorry, I couldn't execute that command" |
| Apology | `apologetic` | "Sorry, I didn't catch that. <pause> Could you repeat?" |
| Warning | `alert` | "Warning! <break> This command is dangerous. Confirm?" |
| Success | `happy` | "Okay. Done" |


## 🛣️ Roadmap

### ✅ Phase 1: Foundation (Complete)
- Core architecture with Clean Architecture principles
- Domain entities and ports
- State machine implementation

### ✅ Phase 2: Infrastructure (Complete)
- OS adapters (Windows/Linux)
- SQLite audit logging
- Regex-based NLU

### ✅ Phase 3: Voice Interface (Complete)
- Wake word detection (Porcupine)
- Speech recognition (Faster-Whisper)
- Emotional TTS (Piper)
- Confirmation dialogs
- Comprehensive audit logging
- File operation improvements

### 🔄 Phase 4: Advanced Features (In Planning)
- PyQt5 GUI interface
- ML-based NLU (BERT/spaCy)
- Plugin system
- Rust sandbox for isolation
- Cloud sync (optional, encrypted)

## 📄 License

MIT License — see [LICENSE](LICENSE)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 🙏 Acknowledgments

- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) — Offline speech recognition
- [Piper TTS](https://github.com/rhasspy/piper) — High-quality text-to-speech
- [Porcupine](https://picovoice.ai/platform/porcupine/) — Wake word detection
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) — Audio I/O