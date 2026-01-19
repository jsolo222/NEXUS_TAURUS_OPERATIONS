/**
 * Motor Control Module
 *
 * Handles low-level motor control for differential drive.
 */

#ifndef MOTORS_H
#define MOTORS_H

#include <Arduino.h>
#include "config.h"

class MotorController {
public:
    MotorController();

    void begin();
    void stop();

    // Set motor speeds (-255 to 255)
    void setMotors(int16_t left, int16_t right);

    // Set normalized velocity (-1.0 to 1.0)
    void setVelocity(float linear, float angular);

    // Get current motor states
    int16_t getLeftSpeed() const { return _leftSpeed; }
    int16_t getRightSpeed() const { return _rightSpeed; }

    // Emergency stop
    void emergencyStop();

    // Enable/disable motors
    void setEnabled(bool enabled);
    bool isEnabled() const { return _enabled; }

private:
    int16_t _leftSpeed = 0;
    int16_t _rightSpeed = 0;
    bool _enabled = false;

    void _applyMotor(uint8_t pwmChannel, uint8_t dir1Pin, uint8_t dir2Pin, int16_t speed);
};

#endif // MOTORS_H
