# Quick Start Guide

Get NEXUS TAURUS OPERATIONS running in 10 minutes.

---

## Prerequisites

- **Windows 11** (or Linux/macOS)
- **Python 3.11+**
- **Node.js 18+**
- **PlatformIO** (for firmware)
- **Yahboom G1 Tank** with ESP32-S3

---

## Step 1: Clone and Setup

```bash
git clone https://github.com/jsolo222/NEXUS_TAURUS_OPERATIONS.git
cd NEXUS_TAURUS_OPERATIONS
```

---

## Step 2: Configure Firmware

Edit WiFi credentials in `firmware/taurus_01/include/config.h`:

```cpp
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define GROUND_STATION_HOST "YOUR_PC_IP_ADDRESS"
```

Find your PC's IP address:
- Windows: `ipconfig` → Look for IPv4 Address
- Linux/Mac: `ip addr` or `ifconfig`

---

## Step 3: Flash Firmware

```bash
cd firmware/taurus_01

# Install PlatformIO if needed
pip install platformio

# Build and upload
pio run --target upload

# Monitor serial output
pio device monitor
```

You should see:
```
╔═══════════════════════════════════════════════════════╗
║     NEXUS TAURUS OPERATIONS - TAURUS-01               ║
║     Vehicle Firmware v0.1.0                           ║
╚═══════════════════════════════════════════════════════╝

[MOTORS] Initialized
[SENSORS] Initialized
[COMMS] Connecting to WiFi: YOUR_SSID
[COMMS] WiFi connected. IP: 192.168.1.xxx
[COMMS] Connecting to WebSocket...
```

---

## Step 4: Start Ground Station Backend

```bash
cd ground_station/backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install
pip install -e .

# Run server
nto-server run
```

You should see:
```
╔═══════════════════════════════════════════════════════════════╗
║           NEXUS TAURUS OPERATIONS - Ground Station            ║
╠═══════════════════════════════════════════════════════════════╣
║  Server starting on http://0.0.0.0:8765                       ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Step 5: Start Command Center Frontend

```bash
cd ground_station/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open http://localhost:3000 in your browser.

---

## Step 6: Verify Connection

1. Check the Command Center shows "Connected"
2. Check TAURUS-01 appears with telemetry
3. Battery, sensors, and system info should display

---

## Step 7: First Commands

1. Set mode to **MANUAL**
2. Click **ARM** to enable motors
3. Use directional buttons to move
4. Click **STOP** or **DISARM** when done

---

## Troubleshooting

### Vehicle not connecting?

1. Check WiFi credentials in firmware
2. Verify ground station IP in firmware
3. Ensure both on same network
4. Check firewall allows port 8765

### No telemetry?

1. Check serial monitor on vehicle
2. Verify WebSocket connection in browser console
3. Restart ground station

### Motors not moving?

1. Ensure vehicle is ARMED
2. Ensure mode is MANUAL
3. Check battery level
4. Verify no obstacles detected

---

## Next Steps

- Read the [System Architecture](architecture/SYSTEM_ARCHITECTURE.md)
- Review [TAURUS-01 Hardware](hardware/TAURUS-01.md)
- Explore the API at http://localhost:8765/docs
