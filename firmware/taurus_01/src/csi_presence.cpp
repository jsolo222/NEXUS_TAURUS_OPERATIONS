/**
 * ESP-CSI Presence Detection Implementation
 *
 * WiFi CSI allows detection of environmental changes through
 * analysis of signal amplitude and phase variations.
 */

#include "csi_presence.h"
#include "esp_wifi.h"
#include <cmath>

// Static instance for callback
CSIPresenceDetector* CSIPresenceDetector::_instance = nullptr;

// Latest CSI data (volatile for ISR access)
static volatile CSIData _latestCSI;
static volatile bool _newDataAvailable = false;

CSIPresenceDetector::CSIPresenceDetector() {
    _instance = this;
    memset(&_result, 0, sizeof(_result));
    memset(_varianceHistory, 0, sizeof(_varianceHistory));
}

bool CSIPresenceDetector::begin() {
    DEBUG_PRINTLN("[CSI] Initializing presence detection...");

    // Configure CSI
    wifi_csi_config_t csi_config = {
        .lltf_en = true,           // Enable LLTF (Legacy Long Training Field)
        .htltf_en = true,          // Enable HT-LTF
        .stbc_htltf2_en = true,    // Enable STBC HT-LTF2
        .ltf_merge_en = true,      // Merge LTF
        .channel_filter_en = false,
        .manu_scale = false,
        .shift = 0,
    };

    // Set CSI configuration
    esp_err_t err = esp_wifi_set_csi_config(&csi_config);
    if (err != ESP_OK) {
        DEBUG_PRINTF("[CSI] Config failed: %d\n", err);
        return false;
    }

    // Register callback
    err = esp_wifi_set_csi_rx_cb(_csiCallback, this);
    if (err != ESP_OK) {
        DEBUG_PRINTF("[CSI] Callback registration failed: %d\n", err);
        return false;
    }

    // Enable CSI
    err = esp_wifi_set_csi(true);
    if (err != ESP_OK) {
        DEBUG_PRINTF("[CSI] Enable failed: %d\n", err);
        return false;
    }

    DEBUG_PRINTLN("[CSI] Presence detection initialized");
    DEBUG_PRINTLN("[CSI] Calibrating baseline (keep area clear)...");

    // Auto-calibrate after short delay
    delay(2000);
    calibrate();

    return true;
}

void CSIPresenceDetector::stop() {
    esp_wifi_set_csi(false);
    esp_wifi_set_csi_rx_cb(nullptr, nullptr);
    DEBUG_PRINTLN("[CSI] Presence detection stopped");
}

void CSIPresenceDetector::_csiCallback(void* ctx, wifi_csi_info_t* info) {
    if (!info || !info->buf) return;

    // Copy amplitude data (even indices in buffer)
    size_t len = min((size_t)info->len / 2, (size_t)CSI_BUFFER_SIZE);
    for (size_t i = 0; i < len; i++) {
        _latestCSI.amplitude[i] = info->buf[i * 2];
        _latestCSI.phase[i] = info->buf[i * 2 + 1];
    }

    _latestCSI.rssi = info->rx_ctrl.rssi;
    _latestCSI.channel = info->rx_ctrl.channel;
    _latestCSI.timestamp = millis();
    _newDataAvailable = true;
}

void CSIPresenceDetector::update() {
    uint32_t now = millis();

    // Rate limit processing
    if (now - _lastSampleTime < CSI_SAMPLE_RATE_MS) {
        return;
    }
    _lastSampleTime = now;

    // Check for new data
    if (!_newDataAvailable) {
        return;
    }
    _newDataAvailable = false;

    // Calculate current variance
    float variance = _calculateVariance(_latestCSI.amplitude, CSI_BUFFER_SIZE);

    // Store in history
    _varianceHistory[_historyIndex] = variance;
    _historyIndex = (_historyIndex + 1) % CSI_WINDOW_SIZE;

    // Update presence state
    _updatePresenceState(variance);

    // Update duration if presence detected
    if (_result.state != PresenceState::CLEAR) {
        if (_presenceStartTime == 0) {
            _presenceStartTime = now;
        }
        _result.duration = now - _presenceStartTime;
        _result.lastDetection = now;
    } else {
        _presenceStartTime = 0;
        _result.duration = 0;
    }
}

float CSIPresenceDetector::_calculateVariance(const int8_t* data, size_t len) {
    if (len == 0) return 0.0f;

    // Calculate mean
    float sum = 0.0f;
    for (size_t i = 0; i < len; i++) {
        sum += data[i];
    }
    float mean = sum / len;

    // Calculate variance
    float varianceSum = 0.0f;
    for (size_t i = 0; i < len; i++) {
        float diff = data[i] - mean;
        varianceSum += diff * diff;
    }

    return varianceSum / len;
}

void CSIPresenceDetector::_updatePresenceState(float currentVariance) {
    if (!_calibrated) {
        _result.state = PresenceState::CLEAR;
        _result.confidence = 0.0f;
        return;
    }

    // Calculate delta from baseline
    float delta = currentVariance - _baselineVariance;
    _result.variance = currentVariance;

    // Calculate variance trend (for approach/retreat detection)
    float recentAvg = 0.0f;
    float olderAvg = 0.0f;
    int halfWindow = CSI_WINDOW_SIZE / 2;

    for (int i = 0; i < halfWindow; i++) {
        int recentIdx = (_historyIndex - 1 - i + CSI_WINDOW_SIZE) % CSI_WINDOW_SIZE;
        int olderIdx = (_historyIndex - 1 - halfWindow - i + CSI_WINDOW_SIZE) % CSI_WINDOW_SIZE;
        recentAvg += _varianceHistory[recentIdx];
        olderAvg += _varianceHistory[olderIdx];
    }
    recentAvg /= halfWindow;
    olderAvg /= halfWindow;

    _result.deltaVariance = recentAvg - olderAvg;

    // Determine state
    if (delta < CSI_DETECTION_THRESHOLD) {
        _result.state = PresenceState::CLEAR;
        _result.confidence = 1.0f - (delta / CSI_DETECTION_THRESHOLD);
    } else if (delta < CSI_MOVEMENT_THRESHOLD) {
        _result.state = PresenceState::PRESENCE;
        _result.confidence = (delta - CSI_DETECTION_THRESHOLD) /
                            (CSI_MOVEMENT_THRESHOLD - CSI_DETECTION_THRESHOLD);
    } else {
        // Active movement - check direction
        if (_result.deltaVariance > 5.0f) {
            _result.state = PresenceState::APPROACHING;
        } else if (_result.deltaVariance < -5.0f) {
            _result.state = PresenceState::RETREATING;
        } else {
            _result.state = PresenceState::MOVEMENT;
        }
        _result.confidence = min(1.0f, delta / (CSI_MOVEMENT_THRESHOLD * 2));
    }
}

void CSIPresenceDetector::calibrate() {
    DEBUG_PRINTLN("[CSI] Calibrating...");

    // Collect samples
    float sum = 0.0f;
    int samples = 0;
    uint32_t startTime = millis();

    while (millis() - startTime < 3000 && samples < 30) {
        if (_newDataAvailable) {
            _newDataAvailable = false;
            sum += _calculateVariance(_latestCSI.amplitude, CSI_BUFFER_SIZE);
            samples++;
            delay(100);
        }
    }

    if (samples > 0) {
        _baselineVariance = sum / samples;
        _calibrated = true;
        DEBUG_PRINTF("[CSI] Calibrated. Baseline variance: %.2f\n", _baselineVariance);
    } else {
        DEBUG_PRINTLN("[CSI] Calibration failed - no samples");
    }
}
