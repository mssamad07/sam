# Sam — Personal AI Assistant

> **Current Status: Phase 1 (Foundation, Core IPC, Event Bus, Logging & Testing)**

Sam is a modular, cross-platform personal AI assistant designed for Windows and Android, with planned support for natural voice interaction, deep OS automation, persistent memory, and safe action execution.

---

## Current Phase: Phase 1 (Foundation)

In **Phase 1**, we have established the foundational infrastructure of Sam. Real AI providers, voice engines, Windows automation, and Android clients are **deliberately deferred** to subsequent phases to ensure a rock-solid, decoupled base.

### Current Capabilities (Implemented in Phase 1)
- **Centralized Typed Configuration**: Built with `pydantic-settings` to validate environment variables, port/host constraints, and storage paths. Phase 1 strictly binds development IPC to `127.0.0.1` (localhost).
- **Structured Centralized Logging**: Built on Python standard logging with custom formatters, secret masking (preventing credentials from leaking into logs), and `correlation_id` request tracing across asynchronous contexts.
- **Asynchronous Event Bus**: Decoupled pub-sub message broker supporting typed events, multiple concurrent subscribers, and handler exception isolation.
- **Typed JSON-RPC 2.0 Protocol**: Strongly typed Pydantic models for requests, notifications, success responses, and error objects with standard error codes (`-32700`, `-32600`, `-32601`, `-32602`, `-32603`).
- **FastAPI WebSocket IPC Gateway**: Asynchronous server with health check (`/health`), truthful status reporting, and `/ws/ipc` WebSocket endpoint for real-time client communication.
- **Skill Foundation**: Extensible `BaseSkill` interface and `SkillRegistry` with duplicate registration protection, skill listing, and dynamic querying.
- **Permission Foundation**: Three-tier risk classification model (`TIER_1_SAFE`, `TIER_2_REVIEW`, `TIER_3_CRITICAL`) and cryptographic token generation with expiry (TTL).
- **Automated Test Suite**: Comprehensive unit and integration test suite using `pytest` and `pytest-asyncio` covering all Phase 1 components.

### Capabilities NOT Implemented Yet (Planned for Future Phases)
- ❌ **Real AI / LLM Providers** (Google Gemini, OpenAI, Groq, Ollama) — *Phase 2*
- ❌ **Conversation Manager & Multilingual Personality** (Hindi, Hinglish, English) — *Phase 2*
- ❌ **Windows OS Automation & UI Control** (pywin32, UIA, app launching, safe files) — *Phase 3*
- ❌ **Web Search & Browser Automation** (Playwright) — *Phase 3*
- ❌ **Voice Pipeline** (Wake-word, Silero VAD, STT, neural TTS) — *Phase 4*
- ❌ **Windows Client UI** (PySide6 floating HUD, system tray, global hotkeys) — *Phase 4*
- ❌ **Android Client & LAN Networking** (Kotlin / Jetpack Compose) — *Phase 5*
- ❌ **Persistent Memory** (SQLite entity store + vector semantic search) — *Phase 5*

---

## Project Architecture Overview

```
sam/
├── pyproject.toml                     # Modern PEP 621 package specification
├── README.md                          # Project documentation
├── .gitignore                         # Comprehensive ignore rules
├── .env.example                       # Documented environment template
├── sam_core/                          # Backend Brain & Daemon
│   ├── __init__.py
│   ├── main.py                        # Core daemon entrypoint
│   ├── config.py                      # Pydantic-settings configuration
│   ├── logger.py                      # Structured logging & correlation tracking
│   ├── events/                        # Asynchronous Event Bus
│   │   ├── __init__.py
│   │   ├── bus.py                     # EventBus implementation
│   │   └── types.py                   # Typed event models
│   ├── api/                           # IPC & Gateway Server
│   │   ├── __init__.py
│   │   ├── server.py                  # FastAPI + WebSocket server
│   │   ├── rpc_handler.py             # JSON-RPC 2.0 dispatcher
│   │   └── ipc_models.py              # Pydantic IPC message models
│   ├── conversation/                  # Multi-turn context (future phase)
│   ├── ai/                            # LLM abstraction (future phase)
│   ├── memory/                        # Memory subsystems (future phase)
│   └── permissions/                   # Safety & permission foundation
│       ├── __init__.py
│       ├── policy.py                  # Risk tiers & policy models
│       └── manager.py                 # Token lifecycle & guardrails
├── sam_capabilities/                  # Modular Skills System
│   ├── __init__.py
│   ├── base.py                        # BaseSkill & Tool interfaces
│   └── registry.py                    # SkillRegistry
└── tests/                             # Automated Test Suite
    ├── unit/                          # Unit tests (config, events, IPC, skills, permissions)
    └── integration/                   # Integration tests (server endpoints, WebSocket)
```

---

## Requirements
- **Python**: `3.13` (or `3.11+`)
- **OS**: Windows 10/11 (with future support for Android and Linux)

---

## Installation & Setup

1. **Clone the repository and navigate to the project directory**:
   ```powershell
   cd sam
   ```

2. **Create and activate a virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies in editable mode**:
   ```powershell
   pip install -e .
   ```
   Or install core requirements:
   ```powershell
   pip install pydantic pydantic-settings fastapi uvicorn[standard] websockets httpx loguru rich python-dotenv psutil pytest pytest-asyncio ruff
   ```

4. **Environment Configuration**:
   ```powershell
   Copy-Item .env.example .env
   ```
   *(Note: .env contains optional local overrides. In Phase 1, defaults run immediately out-of-the-box on `127.0.0.1:8765`).*

---

## Development Commands

### Run Tests
To run all unit and integration tests:
```powershell
pytest -v tests/
```

### Run Linter
To run code linting and formatting checks:
```powershell
ruff check .
```

### Start Sam Core
To launch the Sam Core daemon:
```powershell
python -m sam_core.main
```
Or directly with Uvicorn:
```powershell
uvicorn sam_core.api.server:app --host 127.0.0.1 --port 8765
```

---

## Verifying IPC Endpoints

### 1. HTTP Health & Status Check
```powershell
curl http://127.0.0.1:8765/health
```
**Response**:
```json
{
  "app_name": "Sam",
  "version": "0.1.0",
  "environment": "development",
  "status": "operational",
  "subsystems": {
    "core": "ready",
    "ipc": "ready",
    "event_bus": "ready",
    "skill_registry": "ready",
    "ai_engine": "not_implemented",
    "voice_engine": "not_implemented",
    "memory_system": "not_implemented",
    "windows_automation": "not_implemented",
    "android_client": "not_implemented"
  },
  "registered_skills_count": 0
}
```

### 2. WebSocket JSON-RPC 2.0 Ping
Send:
```json
{"jsonrpc": "2.0", "method": "sam.ping", "params": {}, "id": "req-1"}
```
Receive:
```json
{"jsonrpc": "2.0", "id": "req-1", "result": {"pong": true, "app": "Sam"}, "error": null}
```
