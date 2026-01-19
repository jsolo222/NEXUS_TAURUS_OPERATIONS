/**
 * Sensor Module
 *
 * Handles all sensor reading and processing.
 */

#ifndef SENSORS_H
#define SENSORS_H

#include <Arduino.h>
#include "config.h"

struct SensorData {
    // Infrared obstacle detection (0 = obstacle, 1 = clear)
    uint8_t irLeft;
    uint8_t irRight;

    // Ultrasonic distance (cm)
    float ultrasonicCm;

    // Battery
    float batteryVoltage;
    float batteryCurrent;  // Placeholder for future current sensor
    uint8_t batteryPercent;

    // Timestamps
    uint32_t lastUpdateMs;
};

class SensorManager {
public:
    SensorManager();

    void begin();
    void update();

    const SensorData& getData() const { return _data; }

    // Individual sensor reads
    float readUltrasonicCm();
    float readBatteryVoltage();
    uint8_t readBatteryPercent();

    // Obstacle detection
    bool isObstacleLeft() const { return _data.irLeft == 0; }
    bool isObstacleRight() const { return _data.irRight == 0; }
    bool isObstacleFront() const { return _data.ultrasonicCm < EMERGENCY_STOP_DISTANCE_CM; }
    bool hasObstacle() const { return isObstacleLeft() || isObstacleRight() || isObstacleFront(); }

private:
    SensorData _data;
    uint32_t _lastUltrasonicReadMs = 0;
    static const uint32_t ULTRASONIC_READ_INTERVAL_MS = 50;  // 20Hz max
};

#endif // SENSORS_H
