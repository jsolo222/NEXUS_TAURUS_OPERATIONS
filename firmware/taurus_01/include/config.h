/**
 * NEXUS TAURUS OPERATIONS - TAURUS-01 Configuration
 *
 * Hardware: Yahboom G1 Tank with ESP32-S3
 * Vehicle ID: TAURUS-01
 */

#ifndef CONFIG_H
#define CONFIG_H

// =============================================================================
// Vehicle Identity
// =============================================================================

#ifndef VEHICLE_ID
#define VEHICLE_ID "TAURUS-01"
#endif

// =============================================================================
// Network Configuration
// =============================================================================

// WiFi credentials - UPDATE THESE
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Ground station address - UPDATE THIS
#define GROUND_STATION_HOST "192.168.1.100"
#define GROUND_STATION_PORT 8765
#define GROUND_STATION_PATH "/ws/vehicle/" VEHICLE_ID

// Connection settings
#define WIFI_CONNECT_TIMEOUT_MS 30000
#define WEBSOCKET_RECONNECT_INTERVAL_MS 5000

// =============================================================================
// Telemetry Configuration
// =============================================================================

#define TELEMETRY_RATE_HZ 10           // Telemetry send rate
#define HEARTBEAT_INTERVAL_MS 1000     // Heartbeat interval
#define HEARTBEAT_TIMEOUT_MS 3000      // Connection lost threshold

// =============================================================================
// Motor Configuration (Yahboom G1)
// =============================================================================

// Motor driver pins (L298N or similar)
#define MOTOR_LEFT_PWM_PIN 12
#define MOTOR_LEFT_DIR1_PIN 13
#define MOTOR_LEFT_DIR2_PIN 14

#define MOTOR_RIGHT_PWM_PIN 27
#define MOTOR_RIGHT_DIR1_PIN 26
#define MOTOR_RIGHT_DIR2_PIN 25

// PWM configuration
#define MOTOR_PWM_FREQ 5000
#define MOTOR_PWM_RESOLUTION 8         // 0-255
#define MOTOR_PWM_CHANNEL_LEFT 0
#define MOTOR_PWM_CHANNEL_RIGHT 1

// Motor limits
#define MOTOR_MAX_PWM 255
#define MOTOR_MIN_PWM 30               // Minimum to overcome static friction
#define MOTOR_DEADZONE 10              // Input deadzone

// =============================================================================
// Sensor Configuration
// =============================================================================

// Infrared obstacle sensors
#define IR_LEFT_PIN 34
#define IR_RIGHT_PIN 35

// Ultrasonic sensor (HC-SR04)
#define ULTRASONIC_TRIG_PIN 32
#define ULTRASONIC_ECHO_PIN 33
#define ULTRASONIC_MAX_DISTANCE_CM 400
#define ULTRASONIC_TIMEOUT_US 25000

// Battery monitoring
#define BATTERY_ADC_PIN 36
#define BATTERY_VOLTAGE_DIVIDER 2.0    // Resistor divider ratio
#define BATTERY_CELLS 2                // 2S LiPo
#define BATTERY_FULL_VOLTAGE 8.4       // 4.2V per cell
#define BATTERY_EMPTY_VOLTAGE 6.4      // 3.2V per cell

// =============================================================================
// Safety Configuration
// =============================================================================

#define EMERGENCY_STOP_DISTANCE_CM 15  // Auto-stop if obstacle closer
#define CONNECTION_LOST_TIMEOUT_MS 3000 // Stop if connection lost
#define WATCHDOG_TIMEOUT_MS 5000       // System watchdog

// =============================================================================
// Debug Configuration
// =============================================================================

#define DEBUG_SERIAL_BAUD 115200
#define DEBUG_ENABLED true

#if DEBUG_ENABLED
#define DEBUG_PRINT(x) Serial.print(x)
#define DEBUG_PRINTLN(x) Serial.println(x)
#define DEBUG_PRINTF(...) Serial.printf(__VA_ARGS__)
#else
#define DEBUG_PRINT(x)
#define DEBUG_PRINTLN(x)
#define DEBUG_PRINTF(...)
#endif

#endif // CONFIG_H
