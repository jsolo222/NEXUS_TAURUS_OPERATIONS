/**
 * Sensor Module Implementation
 */

#include "sensors.h"

SensorManager::SensorManager() {
    memset(&_data, 0, sizeof(_data));
    _data.irLeft = 1;
    _data.irRight = 1;
}

void SensorManager::begin() {
    // Configure IR sensor pins
    pinMode(IR_LEFT_PIN, INPUT);
    pinMode(IR_RIGHT_PIN, INPUT);

    // Configure ultrasonic pins
    pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
    pinMode(ULTRASONIC_ECHO_PIN, INPUT);
    digitalWrite(ULTRASONIC_TRIG_PIN, LOW);

    // Configure battery ADC
    pinMode(BATTERY_ADC_PIN, INPUT);
    analogSetAttenuation(ADC_11db);  // Full range for 3.3V

    DEBUG_PRINTLN("[SENSORS] Initialized");
}

void SensorManager::update() {
    uint32_t now = millis();

    // Read IR sensors (fast, no rate limiting needed)
    _data.irLeft = digitalRead(IR_LEFT_PIN);
    _data.irRight = digitalRead(IR_RIGHT_PIN);

    // Read ultrasonic at limited rate
    if (now - _lastUltrasonicReadMs >= ULTRASONIC_READ_INTERVAL_MS) {
        _data.ultrasonicCm = readUltrasonicCm();
        _lastUltrasonicReadMs = now;
    }

    // Read battery
    _data.batteryVoltage = readBatteryVoltage();
    _data.batteryPercent = readBatteryPercent();
    _data.batteryCurrent = 0.0f;  // Placeholder

    _data.lastUpdateMs = now;
}

float SensorManager::readUltrasonicCm() {
    // Trigger pulse
    digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(ULTRASONIC_TRIG_PIN, LOW);

    // Read echo with timeout
    uint32_t duration = pulseIn(ULTRASONIC_ECHO_PIN, HIGH, ULTRASONIC_TIMEOUT_US);

    if (duration == 0) {
        // Timeout - return max distance
        return ULTRASONIC_MAX_DISTANCE_CM;
    }

    // Convert to cm (speed of sound = 343 m/s at 20°C)
    // distance = duration * 0.0343 / 2
    float distance = duration * 0.0171f;

    return constrain(distance, 0.0f, (float)ULTRASONIC_MAX_DISTANCE_CM);
}

float SensorManager::readBatteryVoltage() {
    // Read ADC with averaging
    uint32_t sum = 0;
    const int samples = 10;

    for (int i = 0; i < samples; i++) {
        sum += analogRead(BATTERY_ADC_PIN);
    }

    float adcValue = sum / (float)samples;

    // Convert to voltage
    // ESP32-S3 ADC: 12-bit (0-4095), 3.3V reference with 11dB attenuation
    float voltage = (adcValue / 4095.0f) * 3.3f * BATTERY_VOLTAGE_DIVIDER;

    return voltage;
}

uint8_t SensorManager::readBatteryPercent() {
    float voltage = _data.batteryVoltage;

    // Linear interpolation between empty and full
    float percent = (voltage - BATTERY_EMPTY_VOLTAGE) /
                    (BATTERY_FULL_VOLTAGE - BATTERY_EMPTY_VOLTAGE) * 100.0f;

    return constrain((uint8_t)percent, 0, 100);
}
