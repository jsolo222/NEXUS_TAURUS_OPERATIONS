/**
 * Communications Module
 *
 * Handles WiFi connection and WebSocket communication
 * with ground station.
 */

#ifndef COMMS_H
#define COMMS_H

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "config.h"

// Command callback type
typedef void (*CommandCallback)(const char* command, JsonObject& params);

class CommsManager {
public:
    CommsManager();

    void begin();
    void loop();

    // Connection state
    bool isWifiConnected() const { return WiFi.status() == WL_CONNECTED; }
    bool isWebSocketConnected() const { return _wsConnected; }
    bool isConnected() const { return isWifiConnected() && isWebSocketConnected(); }

    int32_t getWifiRssi() const { return WiFi.RSSI(); }

    // Send telemetry
    void sendTelemetry(JsonDocument& doc);

    // Send heartbeat
    void sendHeartbeat();

    // Send command acknowledgment
    void sendAck(const char* commandId, const char* status, const char* message = nullptr);

    // Send error
    void sendError(int code, const char* message, const char* severity = "WARNING");

    // Register command callback
    void setCommandCallback(CommandCallback callback) { _commandCallback = callback; }

    // Get telemetry sequence number
    uint32_t getSequence() const { return _sequence; }

private:
    WebSocketsClient _ws;
    bool _wsConnected = false;
    uint32_t _sequence = 0;
    uint32_t _lastReconnectAttempt = 0;
    uint32_t _lastHeartbeatSent = 0;
    uint32_t _lastHeartbeatReceived = 0;

    CommandCallback _commandCallback = nullptr;

    void _connectWifi();
    void _connectWebSocket();
    void _onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length);
    void _handleMessage(uint8_t* payload, size_t length);

    static void _wsEventHandler(WStype_t type, uint8_t* payload, size_t length);
    static CommsManager* _instance;
};

#endif // COMMS_H
