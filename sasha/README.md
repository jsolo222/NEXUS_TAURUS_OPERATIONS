# SASHA - AI Mission Control Assistant

**Situational Awareness System for Hazard Assessment**

SASHA is the AI backbone of NEXUS TAURUS OPERATIONS, providing intelligent oversight, decision support, and autonomous coordination for vehicle operations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SASHA CORE                                    │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                   claude-flow (Hive Mind)                       │   │
│   │                                                                 │   │
│   │   ┌───────────┐                                                 │   │
│   │   │   QUEEN   │ ◄── Master Coordinator                          │   │
│   │   │  (Sasha)  │     Orchestrates all agents                     │   │
│   │   └─────┬─────┘                                                 │   │
│   │         │                                                       │   │
│   │   ┌─────┴─────────────────────────────────────────────────┐     │   │
│   │   │                                                       │     │   │
│   │   ▼              ▼              ▼              ▼          │     │   │
│   │ ┌──────┐     ┌──────┐     ┌──────┐     ┌──────────┐       │     │   │
│   │ │Safety│     │ Nav  │     │Telem │     │ Weather  │       │     │   │
│   │ │Agent │     │Agent │     │Agent │     │  Agent   │       │     │   │
│   │ └──────┘     └──────┘     └──────┘     └──────────┘       │     │   │
│   │                                                           │     │   │
│   └───────────────────────────────────────────────────────────┘     │   │
│                                                                     │   │
│   ┌─────────────────────────────────────────────────────────────┐   │   │
│   │                    Data Sources                             │   │   │
│   │                                                             │   │   │
│   │   ┌───────────┐  ┌───────────┐  ┌───────────────────────┐   │   │   │
│   │   │ NASA-MCP  │  │  Ollama   │  │ NEXUS TAURUS API      │   │   │   │
│   │   │ (Weather, │  │  (Local   │  │ (Telemetry, Commands) │   │   │   │
│   │   │  Imagery) │  │   LLM)    │  │                       │   │   │   │
│   │   └───────────┘  └───────────┘  └───────────────────────┘   │   │   │
│   │                                                             │   │   │
│   └─────────────────────────────────────────────────────────────┘   │   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agents

### Queen (Sasha Core)
- Master coordinator
- Receives operator instructions
- Delegates to specialized agents
- Synthesizes reports
- Makes high-level decisions

### Safety Agent
- Monitors telemetry for anomalies
- Tracks battery, connection, obstacles
- Triggers alerts and emergency procedures
- Recommends RTB when conditions deteriorate

### Navigation Agent
- Path planning assistance
- Waypoint management
- RTB route calculation
- GPS integration (future)

### Telemetry Agent
- Analyzes telemetry patterns
- Detects anomalies
- Tracks historical trends
- Reports system health

### Weather Agent
- Queries NASA weather data
- Assesses operational conditions
- Provides forecasts
- Recommends mission timing

---

## Data Sources

### NASA-MCP Server
Provides access to:
- Real-time weather data
- Satellite imagery
- Near-Earth object tracking
- Space weather (solar activity)

### Ollama (Local)
Local LLM inference for:
- Fast response times
- Privacy-sensitive operations
- Offline capability

### NEXUS TAURUS API
Direct access to:
- Vehicle telemetry
- Command dispatch
- Digital twin state
- Mission history

---

## Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- Ollama (optional, for local inference)
- NASA API key (free from api.nasa.gov)

### Installation

```bash
cd sasha

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Create `.env` file:
```bash
# NASA API (get free key at api.nasa.gov)
NASA_API_KEY=your_nasa_api_key

# Ollama (if using local inference)
OLLAMA_HOST=http://localhost:11434

# NEXUS TAURUS ground station
NTO_API_URL=http://localhost:8765

# Claude (if using cloud)
ANTHROPIC_API_KEY=your_anthropic_key
```

### Running Sasha

```bash
# Start Sasha assistant
npm run start

# Or with claude-flow swarm
npx claude-flow swarm "Monitor TAURUS-01 and report status"
```

---

## Example Interactions

### Status Check
```
Operator: "Sasha, status report"
Sasha: "TAURUS-01 Status:
- Mode: STANDBY
- Battery: 78%
- Connection: Strong (-45 dBm)
- Presence: Clear (no humans detected)
- Weather: Clear skies, winds 5 mph NW
Recommendation: Good conditions for operations."
```

### Weather Advisory
```
Sasha: "Weather Alert: Storm system approaching.
Expected arrival: 2 hours
Wind gusts up to 25 mph predicted.
Recommendation: Complete current mission within 90 minutes or initiate RTB."
```

### Anomaly Detection
```
Sasha: "Anomaly Detected: Battery discharge rate 40% above normal.
Possible causes:
1. Motor strain (check terrain)
2. Cold temperature effect
3. Battery degradation
Recommendation: Monitor closely, prepare for early RTB if trend continues."
```

---

## Integration with Ground Station

Sasha connects to the NEXUS TAURUS ground station via:

1. **WebSocket** - Real-time telemetry stream
2. **REST API** - Commands and queries
3. **Event hooks** - Triggered by telemetry conditions

The integration is bidirectional:
- Sasha receives all telemetry
- Sasha can issue commands (with operator approval)
- Sasha provides advisory overlays on Command Center UI

---

## Roadmap

### Phase 1 (Current)
- Basic status monitoring
- Weather integration via NASA-MCP
- Alert generation

### Phase 2
- Multi-agent coordination via claude-flow
- Predictive maintenance
- Mission planning assistance

### Phase 3
- Autonomous decision making (with operator oversight)
- Fleet coordination
- Advanced anomaly detection with ML
