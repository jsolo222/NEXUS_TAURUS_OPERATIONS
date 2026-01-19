/**
 * ESP-CSI Presence Detection Module
 *
 * Uses WiFi Channel State Information to detect:
 * - Human presence (without cameras)
 * - Movement (walking, running)
 * - Subtle motion (breathing in static environments)
 *
 * This provides situational awareness without additional sensors.
 */

#ifndef CSI_PRESENCE_H
#define CSI_PRESENCE_H

#include <Arduino.h>
#include "esp_wifi.h"
#include "config.h"

// CSI Configuration
#define CSI_BUFFER_SIZE 128
#define CSI_DETECTION_THRESHOLD 15.0f  // Variance threshold for presence
#define CSI_MOVEMENT_THRESHOLD 30.0f   // Variance threshold for movement
#define CSI_SAMPLE_RATE_MS 100         // Sample every 100ms
#define CSI_WINDOW_SIZE 50             // Samples for variance calculation

// Presence states
enum class PresenceState {
    CLEAR,          // No presence detected
    PRESENCE,       // Someone nearby (subtle)
    MOVEMENT,       // Active movement detected
    APPROACHING,    // Movement toward vehicle
    RETREATING      // Movement away from vehicle
};

// CSI data structure
struct CSIData {
    int8_t amplitude[CSI_BUFFER_SIZE];
    int8_t phase[CSI_BUFFER_SIZE];
    uint32_t timestamp;
    int rssi;
    uint8_t channel;
};

// Presence detection result
struct PresenceResult {
    PresenceState state;
    float confidence;       // 0.0 - 1.0
    float variance;         // Signal variance
    float deltaVariance;    // Change in variance (approach/retreat)
    uint32_t lastDetection; // Timestamp of last presence
    uint32_t duration;      // How long presence detected
};

class CSIPresenceDetector {
public:
    CSIPresenceDetector();

    // Initialize CSI capture
    bool begin();

    // Stop CSI capture
    void stop();

    // Process CSI data (call in loop)
    void update();

    // Get current presence state
    PresenceResult getPresence() const { return _result; }

    // Check states
    bool isPresenceDetected() const { return _result.state != PresenceState::CLEAR; }
    bool isMovementDetected() const { return _result.state == PresenceState::MOVEMENT; }
    bool isApproaching() const { return _result.state == PresenceState::APPROACHING; }

    // Get raw variance for telemetry
    float getVariance() const { return _result.variance; }

    // Calibrate for current environment
    void calibrate();

private:
    PresenceResult _result;
    float _varianceHistory[CSI_WINDOW_SIZE];
    int _historyIndex = 0;
    float _baselineVariance = 0.0f;
    bool _calibrated = false;
    uint32_t _lastSampleTime = 0;
    uint32_t _presenceStartTime = 0;

    // CSI callback (static for ESP-IDF)
    static void _csiCallback(void* ctx, wifi_csi_info_t* info);
    static CSIPresenceDetector* _instance;

    // Signal processing
    float _calculateVariance(const int8_t* data, size_t len);
    void _updatePresenceState(float currentVariance);
};

#endif // CSI_PRESENCE_H
