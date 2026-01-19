# AI Assistant Briefing Document

> **READ THIS FIRST** if you are an AI assistant (Claude, Cursor, Copilot, Gemini, etc.) working on this codebase.

---

## Mission Statement

**NEXUS TAURUS OPERATIONS** is a real-world robotics operations platform. Not a simulation. Not a demo. Real hardware, real telemetry, real commands.

**Your job:** Help build, maintain, and extend professional-grade ground control infrastructure for autonomous vehicles.

---

## The Assignment

### What We're Building

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NEXUS TAURUS OPERATIONS                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    SASHA "Ghost" (AI Mission Control)               │    │
│  │         Multi-agent orchestration, monitoring, alerts               │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                           │
│  ┌──────────────────────────────┴──────────────────────────────────────┐    │
│  │                      GROUND STATION                                 │    │
│  │   ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐    │    │
│  │   │   Backend    │  │ Digital Twin │  │   Command Center UI    │    │    │
│  │   │  (FastAPI)   │  │   (State)    │  │   (React/TypeScript)   │    │    │
│  │   └──────────────┘  └──────────────┘  └────────────────────────┘    │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │ WiFi/WebSocket                            │
│  ┌──────────────────────────────┴──────────────────────────────────────┐    │
│  │                         VEHICLE FLEET                               │    │
│  │   ┌────────────────────────────────────────────────────────────┐    │    │
│  │   │  TAURUS-01 (Yahboom G1 Tank + ESP32-S3)                    │    │    │
│  │   │  - Motors, sensors, CSI presence detection                 │    │    │
│  │   │  - Real hardware, not simulation                           │    │    │
│  │   └────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Hardware

| Callsign | Platform | Controller | Status |
|----------|----------|------------|--------|
| TAURUS-01 | Yahboom G1 Tank | ESP32-S3 | Primary development vehicle |

### Future Hardware (planned)
- Aerial drones (multirotor)
- GPS/RTK modules
- LiDAR sensors
- LoRa long-range communication

---

## Project Structure

```
NEXUS_TAURUS_OPERATIONS/
│
├── firmware/                      # VEHICLE CODE (ESP32-S3)
│   └── taurus_01/
│       ├── src/
│       │   ├── main.cpp           # Main application loop
│       │   ├── motors.cpp/h       # Motor control
│       │   ├── sensors.cpp/h      # Sensor management
│       │   ├── comms.cpp/h        # WebSocket communication
│       │   └── csi_presence.cpp/h # WiFi presence detection
│       ├── include/
│       │   └── config.h           # Hardware configuration
│       └── platformio.ini         # Build configuration
│
├── ground_station/                # GROUND CONTROL SOFTWARE
│   ├── backend/                   # Python/FastAPI server
│   │   ├── nto_server/
│   │   │   ├── app.py             # Main FastAPI application
│   │   │   ├── digital_twin.py    # Real-time state management
│   │   │   ├── telemetry.py       # WebSocket telemetry server
│   │   │   ├── commands.py        # Command dispatch
│   │   │   ├── storage.py         # Telemetry persistence
│   │   │   └── cli.py             # CLI entry point
│   │   └── pyproject.toml
│   │
│   └── frontend/                  # React/TypeScript UI
│       ├── src/
│       │   ├── App.tsx            # Main application
│       │   ├── main.tsx           # Entry point
│       │   └── index.css          # Styles
│       ├── package.json
│       └── vite.config.ts
│
├── sasha/                         # AI MISSION CONTROL
│   ├── src/
│   │   ├── index.js               # Entry point
│   │   ├── sasha-core.js          # Core orchestration
│   │   ├── telemetry-monitor.js   # Alert system
│   │   └── agents/                # Specialized agents
│   │       ├── safety-agent.js
│   │       └── weather-agent.js
│   ├── mcp-servers/
│   │   └── nto-server.js          # MCP server for AI access
│   ├── claude-flow.config.js      # Multi-agent config
│   ├── mcp.json                   # MCP configuration
│   └── package.json
│
├── protocols/                     # SHARED DEFINITIONS
│   ├── __init__.py
│   └── messages.py                # Telemetry/command schemas
│
├── docs/                          # DOCUMENTATION
│   ├── architecture/
│   ├── hardware/
│   └── QUICKSTART.md
│
└── .github/workflows/             # CI/CD
    └── ci.yml
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Vehicle Firmware | C++ / Arduino / PlatformIO | ESP32-S3 control |
| Ground Backend | Python 3.11+ / FastAPI | Telemetry server, API |
| Ground Frontend | React / TypeScript / Vite | Command center UI |
| AI Assistant | Node.js / claude-flow | SASHA orchestration |
| Database | SQLite | Telemetry persistence |
| Communication | WebSocket / JSON | Real-time telemetry |

---

## Communication Protocol

### Telemetry (Vehicle → Ground)

```json
{
  "msg_type": "telemetry",
  "vehicle_id": "TAURUS-01",
  "timestamp": 1705632000000,
  "sequence": 12345,
  "payload": {
    "position": {"x": 0.0, "y": 0.0, "heading": 90.0},
    "velocity": {"linear": 0.5, "angular": 0.0},
    "battery": {"voltage": 7.4, "current": 1.2, "percent": 85},
    "motors": {"left": 128, "right": 128},
    "sensors": {"ir_left": 1, "ir_right": 1, "ultrasonic_cm": 45.2},
    "csi_presence": {"state": "CLEAR", "confidence": 0.95},
    "system": {"mode": "MANUAL", "armed": true, "uptime_ms": 60000}
  }
}
```

### Commands (Ground → Vehicle)

```json
{
  "msg_type": "command",
  "command_id": "cmd_a1b2c3d4",
  "vehicle_id": "TAURUS-01",
  "command": "MOVE",
  "params": {"linear": 0.5, "angular": 0.0},
  "timestamp": 1705632000000
}
```

### Available Commands

| Command | Params | Description |
|---------|--------|-------------|
| `MOVE` | `{linear, angular}` | Set velocity (-1.0 to 1.0) |
| `STOP` | none | Immediate stop |
| `ARM` | none | Enable motors |
| `DISARM` | none | Disable motors |
| `SET_MODE` | `{mode}` | STANDBY, MANUAL, AUTONOMOUS, RTB, E_STOP |
| `REBOOT` | none | Restart vehicle |

---

## Key Principles

### 1. Real Hardware Only
- No simulations, no mocks
- If code changes vehicle behavior, it affects real motors
- Test carefully

### 2. Telemetry First
- Everything the vehicle does generates telemetry
- Digital twin reflects actual state, not desired state
- All telemetry is logged immutably

### 3. Commands Require Acknowledgment
- Every command gets ACK from vehicle
- No "fire and forget" - verify execution
- Timeout handling for lost commands

### 4. Safety is Non-Negotiable
- Connection loss → automatic stop
- Low battery → alert and RTB recommendation
- Obstacle detection → prevent collision
- Human presence (CSI) → alert operator

### 5. Professional Standards
- Type hints everywhere (Python/TypeScript)
- Tests for business logic
- Clean commit messages
- No secrets in code

---

## Development Workflow

### Running Locally

**1. Ground Station Backend:**
```bash
cd ground_station/backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
nto-server run
```

**2. Frontend:**
```bash
cd ground_station/frontend
npm install
npm run dev
```

**3. Firmware (requires hardware):**
```bash
cd firmware/taurus_01
# Edit include/config.h with WiFi credentials
pio run --target upload
pio device monitor
```

**4. SASHA:**
```bash
cd sasha
npm install
cp .env.example .env
# Edit .env with API keys
npm start
```

---

## Configuration Required

### Firmware (`firmware/taurus_01/include/config.h`)
```cpp
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define GROUND_STATION_HOST "YOUR_PC_IP_ADDRESS"
```

### SASHA (`sasha/.env`)
```bash
NASA_API_KEY=your_nasa_api_key      # Get free at api.nasa.gov
OLLAMA_HOST=http://localhost:11434  # If using local LLM
NTO_API_URL=http://localhost:8765   # Ground station
```

---

## What NOT To Do

1. **Don't commit API keys or passwords**
2. **Don't send ARM or MOVE commands without user confirmation**
3. **Don't modify telemetry history** (append-only)
4. **Don't skip safety checks** in firmware
5. **Don't assume WiFi is always connected**

---

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Backend API | ✅ Ready | Needs testing |
| Digital Twin | ✅ Ready | Needs testing |
| Frontend UI | ✅ Ready | Needs `npm install` |
| Firmware | ✅ Ready | Needs WiFi config + flash |
| CSI Presence | ✅ Ready | Integrated in firmware |
| SASHA Core | ✅ Ready | Needs API keys |
| NASA-MCP | ✅ Configured | Needs NASA API key |
| CI/CD | ✅ Ready | GitHub Actions |

---

## Questions?

If you're an AI assistant and something is unclear:
1. Read the relevant source file
2. Check `docs/` for architecture details
3. Check `protocols/messages.py` for data schemas
4. Ask the human operator for clarification

---

**Remember: This controls real hardware. Be careful. Be professional.**
