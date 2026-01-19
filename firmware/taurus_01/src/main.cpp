/**
 * NEXUS TAURUS OPERATIONS - TAURUS-01 Main Application
 *
 * Vehicle: Yahboom G1 Tank
 * Controller: ESP32-S3
 *
 * This is the main entry point for the vehicle firmware.
 * Handles initialization, main loop, and coordinates all subsystems.
 */

#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"
#include "motors.h"
#include "sensors.h"
#include "comms.h"
#include "csi_presence.h"

// =============================================================================
// Global Objects
// =============================================================================

MotorController motors;
SensorManager sensors;
CommsManager comms;
CSIPresenceDetector csiDetector;

// =============================================================================
// State
// =============================================================================

enum class VehicleMode {
    STANDBY,
    MANUAL,
    AUTONOMOUS,
    RETURN_TO_BASE,
    EMERGENCY_STOP
};

struct VehicleState {
    VehicleMode mode = VehicleMode::STANDBY;
    bool armed = false;
    float targetLinear = 0.0f;
    float targetAngular = 0.0f;
    uint32_t lastCommandTime = 0;
    uint32_t uptimeMs = 0;
};

VehicleState state;

// Timing
uint32_t lastTelemetryTime = 0;
const uint32_t TELEMETRY_INTERVAL_MS = 1000 / TELEMETRY_RATE_HZ;

// =============================================================================
// Command Handler
// =============================================================================

void handleCommand(const char* command, JsonObject& params) {
    DEBUG_PRINTF("[MAIN] Handling command: %s\n", command);

    state.lastCommandTime = millis();

    if (strcmp(command, "MOVE") == 0) {
        if (state.mode != VehicleMode::MANUAL || !state.armed) {
            DEBUG_PRINTLN("[MAIN] MOVE rejected - not in MANUAL mode or not armed");
            return;
        }
        state.targetLinear = params["linear"] | 0.0f;
        state.targetAngular = params["angular"] | 0.0f;

    } else if (strcmp(command, "STOP") == 0) {
        state.targetLinear = 0.0f;
        state.targetAngular = 0.0f;
        motors.stop();

    } else if (strcmp(command, "ARM") == 0) {
        state.armed = true;
        motors.setEnabled(true);
        DEBUG_PRINTLN("[MAIN] Vehicle ARMED");

    } else if (strcmp(command, "DISARM") == 0) {
        state.armed = false;
        state.targetLinear = 0.0f;
        state.targetAngular = 0.0f;
        motors.setEnabled(false);
        DEBUG_PRINTLN("[MAIN] Vehicle DISARMED");

    } else if (strcmp(command, "SET_MODE") == 0) {
        const char* modeStr = params["mode"] | "STANDBY";

        if (strcmp(modeStr, "STANDBY") == 0) {
            state.mode = VehicleMode::STANDBY;
            state.armed = false;
            motors.setEnabled(false);
        } else if (strcmp(modeStr, "MANUAL") == 0) {
            state.mode = VehicleMode::MANUAL;
        } else if (strcmp(modeStr, "AUTONOMOUS") == 0) {
            state.mode = VehicleMode::AUTONOMOUS;
        } else if (strcmp(modeStr, "RTB") == 0) {
            state.mode = VehicleMode::RETURN_TO_BASE;
        } else if (strcmp(modeStr, "E_STOP") == 0) {
            state.mode = VehicleMode::EMERGENCY_STOP;
            state.armed = false;
            motors.emergencyStop();
        }

        DEBUG_PRINTF("[MAIN] Mode set to: %s\n", modeStr);

    } else if (strcmp(command, "REBOOT") == 0) {
        DEBUG_PRINTLN("[MAIN] Rebooting...");
        delay(100);
        ESP.restart();

    } else {
        DEBUG_PRINTF("[MAIN] Unknown command: %s\n", command);
    }
}

// =============================================================================
// Telemetry
// =============================================================================

void sendTelemetry() {
    const SensorData& sensorData = sensors.getData();

    JsonDocument doc;
    JsonObject payload = doc["payload"].to<JsonObject>();

    // Position (placeholder - will use encoders/GPS later)
    JsonObject position = payload["position"].to<JsonObject>();
    position["x"] = 0.0f;
    position["y"] = 0.0f;
    position["heading"] = 0.0f;

    // Velocity
    JsonObject velocity = payload["velocity"].to<JsonObject>();
    velocity["linear"] = state.targetLinear;
    velocity["angular"] = state.targetAngular;

    // Battery
    JsonObject battery = payload["battery"].to<JsonObject>();
    battery["voltage"] = sensorData.batteryVoltage;
    battery["current"] = sensorData.batteryCurrent;
    battery["percent"] = sensorData.batteryPercent;

    // Motors
    JsonObject motorsObj = payload["motors"].to<JsonObject>();
    motorsObj["left"] = motors.getLeftSpeed();
    motorsObj["right"] = motors.getRightSpeed();

    // Sensors
    JsonObject sensorsObj = payload["sensors"].to<JsonObject>();
    sensorsObj["ir_left"] = sensorData.irLeft;
    sensorsObj["ir_right"] = sensorData.irRight;
    sensorsObj["ultrasonic_cm"] = sensorData.ultrasonicCm;

    // CSI Presence Detection
    PresenceResult presence = csiDetector.getPresence();
    JsonObject csiObj = payload["csi_presence"].to<JsonObject>();
    const char* presenceState = "CLEAR";
    switch (presence.state) {
        case PresenceState::CLEAR: presenceState = "CLEAR"; break;
        case PresenceState::PRESENCE: presenceState = "PRESENCE"; break;
        case PresenceState::MOVEMENT: presenceState = "MOVEMENT"; break;
        case PresenceState::APPROACHING: presenceState = "APPROACHING"; break;
        case PresenceState::RETREATING: presenceState = "RETREATING"; break;
    }
    csiObj["state"] = presenceState;
    csiObj["confidence"] = presence.confidence;
    csiObj["variance"] = presence.variance;
    csiObj["duration_ms"] = presence.duration;

    // System
    JsonObject system = payload["system"].to<JsonObject>();

    const char* modeStr = "STANDBY";
    switch (state.mode) {
        case VehicleMode::STANDBY: modeStr = "STANDBY"; break;
        case VehicleMode::MANUAL: modeStr = "MANUAL"; break;
        case VehicleMode::AUTONOMOUS: modeStr = "AUTONOMOUS"; break;
        case VehicleMode::RETURN_TO_BASE: modeStr = "RTB"; break;
        case VehicleMode::EMERGENCY_STOP: modeStr = "E_STOP"; break;
    }

    system["mode"] = modeStr;
    system["armed"] = state.armed;
    system["uptime_ms"] = millis();
    system["wifi_rssi"] = comms.getWifiRssi();
    system["free_heap"] = ESP.getFreeHeap();
    system["cpu_temp"] = temperatureRead();

    comms.sendTelemetry(doc);
}

// =============================================================================
// Safety Checks
// =============================================================================

void performSafetyChecks() {
    // Check for connection loss
    if (!comms.isConnected() && state.armed) {
        uint32_t elapsed = millis() - state.lastCommandTime;
        if (elapsed > CONNECTION_LOST_TIMEOUT_MS) {
            DEBUG_PRINTLN("[SAFETY] Connection lost - emergency stop");
            state.mode = VehicleMode::EMERGENCY_STOP;
            state.armed = false;
            motors.emergencyStop();
            return;
        }
    }

    // Check for obstacles in MANUAL mode
    if (state.mode == VehicleMode::MANUAL && state.armed) {
        if (sensors.isObstacleFront() && state.targetLinear > 0) {
            DEBUG_PRINTLN("[SAFETY] Obstacle detected - stopping forward motion");
            state.targetLinear = 0;
            motors.stop();
            comms.sendError(100, "Obstacle detected - forward motion blocked", "WARNING");
        }
    }

    // CSI Presence Detection alerts
    static PresenceState lastPresenceState = PresenceState::CLEAR;
    PresenceResult presence = csiDetector.getPresence();

    if (presence.state != lastPresenceState) {
        lastPresenceState = presence.state;

        if (presence.state == PresenceState::APPROACHING) {
            DEBUG_PRINTLN("[CSI] Human approaching detected!");
            comms.sendError(200, "Human approaching - CSI detection", "WARNING");
        } else if (presence.state == PresenceState::MOVEMENT) {
            DEBUG_PRINTLN("[CSI] Movement detected nearby");
            comms.sendError(201, "Movement detected nearby - CSI", "INFO");
        }
    }

    // Low battery warning
    const SensorData& data = sensors.getData();
    if (data.batteryPercent < 20 && data.batteryPercent > 0) {
        static uint32_t lastWarning = 0;
        if (millis() - lastWarning > 30000) {  // Warn every 30s
            lastWarning = millis();
            comms.sendError(101, "Low battery", "WARNING");
        }
    }

    // Critical battery - emergency stop
    if (data.batteryPercent < 10 && data.batteryPercent > 0) {
        DEBUG_PRINTLN("[SAFETY] Critical battery - emergency stop");
        state.mode = VehicleMode::EMERGENCY_STOP;
        state.armed = false;
        motors.emergencyStop();
        comms.sendError(102, "Critical battery - emergency stop", "CRITICAL");
    }
}

// =============================================================================
// Main Setup and Loop
// =============================================================================

void setup() {
    // Initialize serial
    Serial.begin(DEBUG_SERIAL_BAUD);
    delay(1000);

    DEBUG_PRINTLN("");
    DEBUG_PRINTLN("╔═══════════════════════════════════════════════════════╗");
    DEBUG_PRINTLN("║     NEXUS TAURUS OPERATIONS - TAURUS-01               ║");
    DEBUG_PRINTLN("║     Vehicle Firmware v0.1.0                           ║");
    DEBUG_PRINTLN("╚═══════════════════════════════════════════════════════╝");
    DEBUG_PRINTLN("");

    // Initialize subsystems
    motors.begin();
    sensors.begin();

    // Set command callback before comms.begin()
    comms.setCommandCallback(handleCommand);
    comms.begin();

    // Initialize CSI presence detection (after WiFi is connected)
    DEBUG_PRINTLN("[MAIN] Initializing CSI presence detection...");
    if (csiDetector.begin()) {
        DEBUG_PRINTLN("[MAIN] CSI presence detection active");
    } else {
        DEBUG_PRINTLN("[MAIN] CSI presence detection failed - continuing without");
    }

    // Initial state
    state.mode = VehicleMode::STANDBY;
    state.armed = false;
    state.lastCommandTime = millis();

    DEBUG_PRINTLN("[MAIN] Initialization complete");
    DEBUG_PRINTLN("[MAIN] Waiting for ground station connection...");
}

void loop() {
    uint32_t now = millis();

    // Update communications
    comms.loop();

    // Update sensors
    sensors.update();

    // Update CSI presence detection
    csiDetector.update();

    // Safety checks
    performSafetyChecks();

    // Apply motor commands (only if in correct mode and armed)
    if (state.mode == VehicleMode::MANUAL && state.armed) {
        motors.setVelocity(state.targetLinear, state.targetAngular);
    }

    // Send telemetry at configured rate
    if (now - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
        lastTelemetryTime = now;
        if (comms.isConnected()) {
            sendTelemetry();
        }
    }

    // Small delay to prevent watchdog issues
    delay(1);
}
