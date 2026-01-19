/**
 * Communications Module Implementation
 */

#include "comms.h"

// Static instance for callback
CommsManager* CommsManager::_instance = nullptr;

CommsManager::CommsManager() {
    _instance = this;
}

void CommsManager::begin() {
    DEBUG_PRINTLN("[COMMS] Initializing...");

    _connectWifi();
    _connectWebSocket();

    DEBUG_PRINTLN("[COMMS] Initialized");
}

void CommsManager::loop() {
    // Handle WiFi reconnection
    if (!isWifiConnected()) {
        _wsConnected = false;
        uint32_t now = millis();
        if (now - _lastReconnectAttempt > 5000) {
            _lastReconnectAttempt = now;
            DEBUG_PRINTLN("[COMMS] WiFi disconnected, reconnecting...");
            _connectWifi();
        }
        return;
    }

    // Handle WebSocket
    _ws.loop();

    // Check heartbeat timeout
    if (_wsConnected && _lastHeartbeatReceived > 0) {
        uint32_t elapsed = millis() - _lastHeartbeatReceived;
        if (elapsed > HEARTBEAT_TIMEOUT_MS) {
            DEBUG_PRINTLN("[COMMS] Heartbeat timeout, connection lost");
            _wsConnected = false;
        }
    }

    // Send periodic heartbeat
    if (_wsConnected) {
        uint32_t now = millis();
        if (now - _lastHeartbeatSent >= HEARTBEAT_INTERVAL_MS) {
            sendHeartbeat();
            _lastHeartbeatSent = now;
        }
    }
}

void CommsManager::_connectWifi() {
    DEBUG_PRINTF("[COMMS] Connecting to WiFi: %s\n", WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    uint32_t startTime = millis();
    while (WiFi.status() != WL_CONNECTED) {
        if (millis() - startTime > WIFI_CONNECT_TIMEOUT_MS) {
            DEBUG_PRINTLN("[COMMS] WiFi connection timeout");
            return;
        }
        delay(500);
        DEBUG_PRINT(".");
    }

    DEBUG_PRINTLN("");
    DEBUG_PRINTF("[COMMS] WiFi connected. IP: %s\n", WiFi.localIP().toString().c_str());
    DEBUG_PRINTF("[COMMS] RSSI: %d dBm\n", WiFi.RSSI());
}

void CommsManager::_connectWebSocket() {
    DEBUG_PRINTF("[COMMS] Connecting to WebSocket: ws://%s:%d%s\n",
                 GROUND_STATION_HOST, GROUND_STATION_PORT, GROUND_STATION_PATH);

    _ws.begin(GROUND_STATION_HOST, GROUND_STATION_PORT, GROUND_STATION_PATH);
    _ws.onEvent(_wsEventHandler);
    _ws.setReconnectInterval(WEBSOCKET_RECONNECT_INTERVAL_MS);
}

void CommsManager::_wsEventHandler(WStype_t type, uint8_t* payload, size_t length) {
    if (_instance) {
        _instance->_onWebSocketEvent(type, payload, length);
    }
}

void CommsManager::_onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            DEBUG_PRINTLN("[COMMS] WebSocket disconnected");
            _wsConnected = false;
            break;

        case WStype_CONNECTED:
            DEBUG_PRINTF("[COMMS] WebSocket connected to: %s\n", payload);
            _wsConnected = true;
            _lastHeartbeatReceived = millis();
            break;

        case WStype_TEXT:
            _handleMessage(payload, length);
            break;

        case WStype_ERROR:
            DEBUG_PRINTLN("[COMMS] WebSocket error");
            break;

        default:
            break;
    }
}

void CommsManager::_handleMessage(uint8_t* payload, size_t length) {
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, payload, length);

    if (error) {
        DEBUG_PRINTF("[COMMS] JSON parse error: %s\n", error.c_str());
        return;
    }

    const char* msgType = doc["msg_type"];

    if (strcmp(msgType, "command") == 0) {
        const char* commandId = doc["command_id"];
        const char* command = doc["command"];
        JsonObject params = doc["params"].as<JsonObject>();

        DEBUG_PRINTF("[COMMS] Command received: %s (id: %s)\n", command, commandId);

        // Send acknowledgment
        sendAck(commandId, "RECEIVED");

        // Invoke callback
        if (_commandCallback) {
            _commandCallback(command, params);
            sendAck(commandId, "COMPLETED");
        }

    } else if (strcmp(msgType, "heartbeat") == 0) {
        _lastHeartbeatReceived = millis();

    } else {
        DEBUG_PRINTF("[COMMS] Unknown message type: %s\n", msgType);
    }
}

void CommsManager::sendTelemetry(JsonDocument& doc) {
    if (!_wsConnected) return;

    doc["msg_type"] = "telemetry";
    doc["vehicle_id"] = VEHICLE_ID;
    doc["timestamp"] = millis();  // TODO: Use proper timestamp
    doc["sequence"] = _sequence++;

    String output;
    serializeJson(doc, output);
    _ws.sendTXT(output);
}

void CommsManager::sendHeartbeat() {
    if (!_wsConnected) return;

    JsonDocument doc;
    doc["msg_type"] = "heartbeat";
    doc["vehicle_id"] = VEHICLE_ID;
    doc["timestamp"] = millis();

    String output;
    serializeJson(doc, output);
    _ws.sendTXT(output);
}

void CommsManager::sendAck(const char* commandId, const char* status, const char* message) {
    if (!_wsConnected) return;

    JsonDocument doc;
    doc["msg_type"] = "ack";
    doc["command_id"] = commandId;
    doc["vehicle_id"] = VEHICLE_ID;
    doc["status"] = status;
    doc["timestamp"] = millis();

    if (message) {
        doc["message"] = message;
    }

    String output;
    serializeJson(doc, output);
    _ws.sendTXT(output);
}

void CommsManager::sendError(int code, const char* message, const char* severity) {
    if (!_wsConnected) return;

    JsonDocument doc;
    doc["msg_type"] = "error";
    doc["vehicle_id"] = VEHICLE_ID;
    doc["error_code"] = code;
    doc["error_message"] = message;
    doc["severity"] = severity;
    doc["timestamp"] = millis();

    String output;
    serializeJson(doc, output);
    _ws.sendTXT(output);
}
