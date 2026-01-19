/**
 * Motor Control Implementation
 */

#include "motors.h"

MotorController::MotorController() {}

void MotorController::begin() {
    // Configure motor pins
    pinMode(MOTOR_LEFT_DIR1_PIN, OUTPUT);
    pinMode(MOTOR_LEFT_DIR2_PIN, OUTPUT);
    pinMode(MOTOR_RIGHT_DIR1_PIN, OUTPUT);
    pinMode(MOTOR_RIGHT_DIR2_PIN, OUTPUT);

    // Configure PWM channels
    ledcSetup(MOTOR_PWM_CHANNEL_LEFT, MOTOR_PWM_FREQ, MOTOR_PWM_RESOLUTION);
    ledcSetup(MOTOR_PWM_CHANNEL_RIGHT, MOTOR_PWM_FREQ, MOTOR_PWM_RESOLUTION);

    ledcAttachPin(MOTOR_LEFT_PWM_PIN, MOTOR_PWM_CHANNEL_LEFT);
    ledcAttachPin(MOTOR_RIGHT_PWM_PIN, MOTOR_PWM_CHANNEL_RIGHT);

    // Start stopped
    stop();

    DEBUG_PRINTLN("[MOTORS] Initialized");
}

void MotorController::stop() {
    _leftSpeed = 0;
    _rightSpeed = 0;

    ledcWrite(MOTOR_PWM_CHANNEL_LEFT, 0);
    ledcWrite(MOTOR_PWM_CHANNEL_RIGHT, 0);

    digitalWrite(MOTOR_LEFT_DIR1_PIN, LOW);
    digitalWrite(MOTOR_LEFT_DIR2_PIN, LOW);
    digitalWrite(MOTOR_RIGHT_DIR1_PIN, LOW);
    digitalWrite(MOTOR_RIGHT_DIR2_PIN, LOW);
}

void MotorController::setMotors(int16_t left, int16_t right) {
    if (!_enabled) {
        stop();
        return;
    }

    // Clamp values
    left = constrain(left, -MOTOR_MAX_PWM, MOTOR_MAX_PWM);
    right = constrain(right, -MOTOR_MAX_PWM, MOTOR_MAX_PWM);

    // Apply deadzone
    if (abs(left) < MOTOR_DEADZONE) left = 0;
    if (abs(right) < MOTOR_DEADZONE) right = 0;

    _leftSpeed = left;
    _rightSpeed = right;

    _applyMotor(MOTOR_PWM_CHANNEL_LEFT, MOTOR_LEFT_DIR1_PIN, MOTOR_LEFT_DIR2_PIN, left);
    _applyMotor(MOTOR_PWM_CHANNEL_RIGHT, MOTOR_RIGHT_DIR1_PIN, MOTOR_RIGHT_DIR2_PIN, right);
}

void MotorController::setVelocity(float linear, float angular) {
    // Clamp inputs
    linear = constrain(linear, -1.0f, 1.0f);
    angular = constrain(angular, -1.0f, 1.0f);

    // Differential drive mixing
    // linear: forward/backward (-1 to 1)
    // angular: turn rate (-1 = left, 1 = right)
    float left = linear - angular;
    float right = linear + angular;

    // Normalize if exceeding limits
    float maxVal = max(abs(left), abs(right));
    if (maxVal > 1.0f) {
        left /= maxVal;
        right /= maxVal;
    }

    // Convert to PWM
    int16_t leftPwm = (int16_t)(left * MOTOR_MAX_PWM);
    int16_t rightPwm = (int16_t)(right * MOTOR_MAX_PWM);

    setMotors(leftPwm, rightPwm);
}

void MotorController::emergencyStop() {
    _enabled = false;
    stop();
    DEBUG_PRINTLN("[MOTORS] EMERGENCY STOP");
}

void MotorController::setEnabled(bool enabled) {
    _enabled = enabled;
    if (!enabled) {
        stop();
    }
    DEBUG_PRINTF("[MOTORS] Enabled: %s\n", enabled ? "true" : "false");
}

void MotorController::_applyMotor(uint8_t pwmChannel, uint8_t dir1Pin, uint8_t dir2Pin, int16_t speed) {
    if (speed == 0) {
        // Brake mode
        digitalWrite(dir1Pin, LOW);
        digitalWrite(dir2Pin, LOW);
        ledcWrite(pwmChannel, 0);
    } else if (speed > 0) {
        // Forward
        digitalWrite(dir1Pin, HIGH);
        digitalWrite(dir2Pin, LOW);
        ledcWrite(pwmChannel, speed);
    } else {
        // Reverse
        digitalWrite(dir1Pin, LOW);
        digitalWrite(dir2Pin, HIGH);
        ledcWrite(pwmChannel, -speed);
    }
}
