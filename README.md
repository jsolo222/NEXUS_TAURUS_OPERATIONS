# NEXUS TAURUS OPERATIONS

**Real-Time Robotic Operations Platform with Digital Twin Architecture**

> Professional ground control infrastructure for autonomous vehicle operations, telemetry management, and mission control.

---

## Overview

NEXUS TAURUS OPERATIONS (NTO) is a production-grade robotics operations platform designed for:

- **Real-time telemetry ingestion** from physical vehicles
- **Digital twin synchronization** mirroring actual vehicle state
- **Command and control** with verification and acknowledgment
- **Mission logging** with full telemetry persistence
- **AI-powered mission control** via SASHA (callsign: Ghost)
- **Extensible architecture** for multi-vehicle fleet operations

This is not a simulation. This is real hardware operations infrastructure.

---

## AI Mission Control: SASHA

**SASHA** (Situational Awareness System for Hazard Assessment), callsign **"Ghost"**, is the AI backbone of NEXUS TAURUS operations.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SASHA "Ghost" - AI Mission Control                   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                   claude-flow (Hive Mind)                       │   │
│   │   ┌───────────┐                                                 │   │
│   │   │   GHOST   │ ◄── Master Coordinator                          │   │
│   │   │  (Queen)  │                                                 │   │
│   │   └─────┬─────┘                                                 │   │
│   │   ┌─────┴─────────────────────────────────────────────────┐     │   │
│   │   ▼              ▼              ▼              ▼          │     │   │
│   │ ┌──────┐     ┌──────┐     ┌──────┐     ┌──────────┐       │     │   │
│   │ │Safety│     │ Nav  │     │Telem │     │ Weather  │       │     │   │
│   │ │Watch │     │Agent │     │Analyst│    │  Watch   │       │     │   │
│   │ └──────┘     └──────┘     └──────┘     └──────────┘       │     │   │
│   └───────────────────────────────────────────────────────────┘     │   │
│                                                                     │   │
│   Data Sources: NASA-MCP (weather/imagery) │ Ollama (local LLM)     │   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Capabilities
- **Real-time monitoring** of all vehicle telemetry
- **Anomaly detection** and predictive alerts
- **Weather integration** via NASA APIs
- **Multi-agent orchestration** via claude-flow
- **Natural language** status reports and commands

---

## Current Fleet

| Callsign | Platform | Controller | Comms | Status |
|----------|----------|------------|-------|--------|
| **TAURUS-01** | Yahboom G1 Tank | ESP32-S3 | WiFi/BLE | Active Development |

### Future Integrations
- Aerial platforms (multirotor)
- GPS/RTK positioning
- LoRa long-range telemetry
- LiDAR mapping with obstacle registration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      GROUND STATION (Windows 11)                    │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │   Command    │    │  Telemetry   │    │     Digital Twin      │  │
│  │   Center     │◄──►│   Server     │◄──►│   State Manager       │  │
│  │  (Frontend)  │    │  (FastAPI)   │    │                       │  │
│  └──────────────┘    └──────┬───────┘    └───────────────────────┘  │
│                             │                                       │
│                     ┌───────┴───────┐                               │
│                     │   Database    │                               │
│                     │  (Telemetry)  │                               │
│                     └───────────────┘                               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ WiFi (WebSocket)
                              │
┌─────────────────────────────┴───────────────────────────────────────┐
│                        VEHICLE: TAURUS-01                           │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │   Command    │    │   Sensor     │    │    Motion Control     │  │
│  │   Handler    │◄──►│   Manager    │◄──►│    (Motors/Encoders)  │  │
│  └──────────────┘    └──────────────┘    └───────────────────────┘  │
│                                                                     │
│                         ESP32-S3 @ 240MHz                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
NEXUS_TAURUS_OPERATIONS/
├── docs/                      # Technical documentation
│   ├── architecture/          # System design documents
│   ├── hardware/              # Wiring diagrams, specs
│   └── protocols/             # Communication protocol specs
│
├── firmware/                  # Vehicle firmware (ESP32-S3)
│   └── taurus_01/             # G1 Tank firmware
│       ├── src/               # Source code
│       ├── include/           # Headers
│       └── platformio.ini     # Build configuration
│
├── ground_station/            # Ground control software
│   ├── backend/               # Python telemetry server
│   │   ├── nto_server/        # Main package
│   │   ├── tests/             # Backend tests
│   │   └── pyproject.toml     # Python config
│   │
│   └── frontend/              # Command center UI
│       └── src/               # React/TypeScript
│
├── protocols/                 # Shared protocol definitions
│   └── messages.py            # Message schemas
│
├── tools/                     # Development utilities
│
└── .github/workflows/         # CI/CD pipelines
```

---

## Quick Start

### Prerequisites

- **Python 3.11+** (ground station)
- **Node.js 18+** (frontend)
- **PlatformIO** (firmware development)
- **Yahboom G1 Tank** with ESP32-S3

### Ground Station Setup

```bash
cd ground_station/backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e .
nto-server run
```

### Firmware Upload

```bash
cd firmware/taurus_01
pio run --target upload
```

### Frontend Development

```bash
cd ground_station/frontend
npm install
npm run dev
```

---

## Telemetry Protocol

All vehicle-to-ground communication uses a structured JSON protocol over WebSocket:

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
    "sensors": {"ir_left": 1, "ir_right": 1, "ultrasonic": 45.2}
  }
}
```

Commands follow the same structure with acknowledgment:

```json
{
  "msg_type": "command",
  "command_id": "cmd_001",
  "vehicle_id": "TAURUS-01",
  "command": "MOVE",
  "params": {"linear": 0.5, "angular": 0.0}
}
```

---

## Development Standards

- **All code** must include type hints (Python) or TypeScript
- **All functions** with business logic require unit tests
- **Telemetry** is immutable - append-only logging
- **Commands** require acknowledgment before state change
- **Git commits** follow conventional commit format

---

## License

MIT License - See LICENSE file

---

## Author:  TAURUS INDUSTRIES

Building real systems. No simulations. No shortcuts.
