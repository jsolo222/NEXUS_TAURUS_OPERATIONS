# NEXUS TAURUS OPERATIONS - System Architecture

---

## Overview

NEXUS TAURUS OPERATIONS (NTO) is a ground control and telemetry system for autonomous vehicle operations. The architecture follows NASA-inspired patterns for reliability, traceability, and real-time operations.

---

## Design Principles

1. **Telemetry First**: All vehicle state changes are observable through telemetry
2. **Command Verification**: Every command requires acknowledgment
3. **Digital Twin**: Ground maintains synchronized state mirror
4. **Append-Only Logging**: Telemetry history is immutable
5. **Fail-Safe Defaults**: Connection loss triggers safe mode

---

## System Components

### 1. Vehicle (TAURUS-01)

```
┌─────────────────────────────────────────────────────────┐
│                    ESP32-S3 Firmware                    │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Command   │  │   Sensor    │  │     Motor       │  │
│  │   Handler   │  │   Manager   │  │    Controller   │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                  │           │
│         └────────┬───────┴──────────────────┘           │
│                  │                                      │
│         ┌────────┴────────┐                             │
│         │  Comms Manager  │                             │
│         │   (WebSocket)   │                             │
│         └────────┬────────┘                             │
└──────────────────┼──────────────────────────────────────┘
                   │
                WiFi
```

**Responsibilities**:
- Execute commands from ground station
- Collect and publish telemetry
- Perform safety checks (obstacle avoidance, battery)
- Maintain connection with heartbeats

### 2. Ground Station Backend

```
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Server                         │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Telemetry  │  │   Command   │  │   Digital Twin  │  │
│  │   Server    │  │  Dispatcher │  │    Manager      │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                  │           │
│         └────────┬───────┴──────────────────┘           │
│                  │                                      │
│         ┌────────┴────────┐                             │
│         │    Storage      │                             │
│         │   (SQLite)      │                             │
│         └─────────────────┘                             │
└─────────────────────────────────────────────────────────┘
```

**Responsibilities**:
- Accept vehicle WebSocket connections
- Parse and validate telemetry
- Update digital twin state
- Dispatch and track commands
- Persist telemetry history
- Stream state to frontend

### 3. Command Center Frontend

```
┌─────────────────────────────────────────────────────────┐
│                React Application                        │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Vehicle   │  │   Control   │  │   Digital Twin  │  │
│  │   Status    │  │    Panel    │  │  Visualization  │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │              WebSocket State Sync                   ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Responsibilities**:
- Display real-time vehicle state
- Provide control interface
- Visualize digital twin
- Show telemetry history

---

## Communication Protocol

### Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `telemetry` | Vehicle → Ground | Periodic state report |
| `command` | Ground → Vehicle | Control instruction |
| `ack` | Vehicle → Ground | Command acknowledgment |
| `heartbeat` | Bidirectional | Connection health |
| `error` | Vehicle → Ground | Error notification |

### Telemetry Message

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
    "system": {"mode": "MANUAL", "armed": true, "uptime_ms": 60000}
  }
}
```

### Command Message

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

### Command Lifecycle

```
Ground                          Vehicle
   │                               │
   │──── command ─────────────────>│
   │                               │ (validate)
   │<──── ack: RECEIVED ───────────│
   │                               │ (execute)
   │<──── ack: EXECUTING ──────────│
   │                               │ (complete)
   │<──── ack: COMPLETED ──────────│
   │                               │
```

---

## Data Flow

### Telemetry Pipeline

```
Vehicle Sensors
      │
      ▼
┌─────────────┐
│   Sample    │  (100 Hz internal)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Aggregate  │  (10 Hz telemetry)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Publish   │  (WebSocket)
└──────┬──────┘
       │
  ═══ WiFi ═══
       │
       ▼
┌─────────────┐
│   Ingest    │  (Telemetry Server)
└──────┬──────┘
       │
       ├──────────────────┐
       ▼                  ▼
┌─────────────┐    ┌─────────────┐
│ Digital Twin│    │   Storage   │
│   (Live)    │    │ (Persist)   │
└──────┬──────┘    └─────────────┘
       │
       ▼
┌─────────────┐
│  Broadcast  │  (WebSocket)
└──────┬──────┘
       │
       ▼
   Frontend
```

---

## Safety Systems

### Vehicle-Side Safety

1. **Obstacle Detection**
   - IR sensors: Side obstacle detection
   - Ultrasonic: Forward obstacle detection
   - Auto-stop when obstacle in path

2. **Connection Monitor**
   - Heartbeat timeout: 3 seconds
   - Action: Emergency stop on timeout

3. **Battery Protection**
   - Warning: < 20%
   - Critical stop: < 10%

### Ground-Side Safety

1. **Command Validation**
   - Parameter range checking
   - Mode-appropriate commands only

2. **Command Timeout**
   - Ack timeout: 5 seconds
   - Retry policy: configurable

3. **Connection Health**
   - Periodic heartbeat validation
   - Visual connection status

---

## Future Architecture

### Phase 2: Multi-Vehicle Support

```
                    ┌─────────────────┐
                    │  Fleet Manager  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
   │TAURUS-01│          │TAURUS-02│          │ DRONE-01│
   └─────────┘          └─────────┘          └─────────┘
```

### Phase 3: GPS + Mapping

```
┌─────────────────────────────────────────┐
│            Digital Twin Map             │
│                                         │
│   ┌─────┐                               │
│   │ GPS │──> Position overlay           │
│   └─────┘                               │
│                                         │
│   ┌───────┐                             │
│   │ LiDAR │──> Obstacle mapping         │
│   └───────┘                             │
│                                         │
│   Combined view with path history       │
└─────────────────────────────────────────┘
```

### Phase 4: Autonomous Missions

```
┌──────────────────┐
│  Mission Planner │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Waypoint Manager │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Path Executor  │
└────────┬─────────┘
         │
         ▼
    Vehicle RTB
```

---

## Development Guidelines

1. **Protocol Changes**: Update `protocols/messages.py` first
2. **New Sensors**: Add to firmware, update telemetry payload
3. **New Commands**: Add to `CommandType` enum, implement handler
4. **UI Changes**: Use existing component patterns
5. **Testing**: Backend requires unit tests, firmware requires HIL testing
