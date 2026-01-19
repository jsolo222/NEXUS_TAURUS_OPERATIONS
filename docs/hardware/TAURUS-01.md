# TAURUS-01 Hardware Configuration

**Platform**: Yahboom G1 Tank
**Controller**: ESP32-S3
**Callsign**: TAURUS-01

---

## Overview

TAURUS-01 is the first vehicle in the NEXUS fleet. It serves as the development platform for:
- Telemetry protocol validation
- Digital twin synchronization
- Command/control testing
- Sensor integration patterns

---

## Hardware Specifications

### Chassis: Yahboom G1 Tank

| Specification | Value |
|--------------|-------|
| Chassis Type | Tracked tank |
| Material | Aluminum alloy |
| Drive Type | Differential (2 motors) |
| Motor Type | DC gear motors |
| Gear Ratio | TBD |
| Max Speed | ~0.5 m/s |
| Turning | Zero-radius capable |

### Controller: ESP32-S3

| Specification | Value |
|--------------|-------|
| MCU | ESP32-S3 |
| Clock | 240 MHz dual-core |
| Flash | 8 MB |
| PSRAM | 8 MB |
| WiFi | 802.11 b/g/n |
| Bluetooth | BLE 5.0 |
| ADC | 12-bit |
| GPIO | 45 pins |

### Power System

| Component | Specification |
|-----------|--------------|
| Battery | 2S LiPo (7.4V nominal) |
| Capacity | 2200-3000 mAh recommended |
| Voltage Range | 6.4V - 8.4V |
| Monitoring | ADC with voltage divider |

---

## Pin Configuration

### Motor Driver Pins

```
Left Motor:
  - PWM:  GPIO 12
  - DIR1: GPIO 13
  - DIR2: GPIO 14

Right Motor:
  - PWM:  GPIO 27
  - DIR1: GPIO 26
  - DIR2: GPIO 25
```

### Sensor Pins

```
Infrared Obstacle Sensors:
  - Left:  GPIO 34 (input only)
  - Right: GPIO 35 (input only)

Ultrasonic (HC-SR04):
  - Trigger: GPIO 32
  - Echo:    GPIO 33

Battery Monitoring:
  - ADC: GPIO 36 (input only)
```

---

## Wiring Diagram

```
                    ┌─────────────────────┐
                    │      ESP32-S3       │
                    │                     │
    ┌───────────────┼─ GPIO 12 (PWM_L)    │
    │  ┌────────────┼─ GPIO 13 (DIR1_L)   │
    │  │  ┌─────────┼─ GPIO 14 (DIR2_L)   │
    │  │  │         │                     │
    │  │  │    ┌────┼─ GPIO 27 (PWM_R)    │
    │  │  │    │ ┌──┼─ GPIO 26 (DIR1_R)   │
    │  │  │    │ │ ┌┼─ GPIO 25 (DIR2_R)   │
    │  │  │    │ │ ││                     │
    │  │  │    │ │ ││  GPIO 34 ─┐ IR_L    │
    │  │  │    │ │ ││  GPIO 35 ─┤ IR_R    │
    │  │  │    │ │ ││  GPIO 32 ─┤ US_TRIG │
    │  │  │    │ │ ││  GPIO 33 ─┤ US_ECHO │
    │  │  │    │ │ ││  GPIO 36 ─┘ VBAT    │
    │  │  │    │ │ ││                     │
    └──┴──┴────┴─┴─┴┴─────────────────────┘
         │           │
    ┌────┴───┐  ┌────┴───┐
    │  L298N │  │  L298N │
    │  or    │  │  or    │
    │  TB6612│  │  TB6612│
    └────┬───┘  └────┬───┘
         │           │
    ┌────┴───┐  ┌────┴───┐
    │ Motor  │  │ Motor  │
    │ Left   │  │ Right  │
    └────────┘  └────────┘
```

---

## Sensor Details

### Infrared Obstacle Sensors

- **Type**: Active IR with comparator
- **Output**: Digital (0 = obstacle detected, 1 = clear)
- **Range**: 2-30 cm typical
- **Usage**: Side obstacle detection

### Ultrasonic Sensor (HC-SR04)

- **Type**: Time-of-flight ultrasonic
- **Range**: 2-400 cm
- **Resolution**: ~3mm
- **Beam Angle**: ~15°
- **Usage**: Forward distance measurement

### Battery Monitor

- **Method**: Voltage divider to ADC
- **Divider Ratio**: 2:1 (adjust based on actual resistors)
- **ADC Resolution**: 12-bit (0-4095)
- **Reference**: 3.3V with 11dB attenuation

---

## Calibration Notes

### Motor Calibration

1. Verify both motors spin in correct direction
2. If reversed, swap DIR1 and DIR2 pins in config
3. Adjust `MOTOR_MIN_PWM` if motors stall at low speeds
4. Test differential drive: forward, reverse, spin left, spin right

### Sensor Calibration

1. **Ultrasonic**: Verify readings against tape measure
2. **IR Sensors**: Test detection threshold with hand
3. **Battery**: Measure actual voltage, adjust divider ratio

---

## Future Upgrades

### Phase 2: GPS Integration
- Module: u-blox NEO-M8N or similar
- Interface: UART
- Purpose: Absolute positioning for digital twin

### Phase 3: LiDAR Integration
- Module: RPLIDAR A1 or similar
- Interface: UART
- Purpose: 2D mapping, obstacle detection

### Phase 4: LoRa Communication
- Module: SX1276/SX1278
- Interface: SPI
- Purpose: Long-range telemetry backup

---

## Maintenance

### Pre-Operation Checklist

- [ ] Battery voltage > 7.0V
- [ ] All connections secure
- [ ] Tracks properly tensioned
- [ ] Sensors unobstructed
- [ ] WiFi network available

### Post-Operation

- [ ] Power off vehicle
- [ ] Disconnect battery if storing
- [ ] Clean tracks if dirty
- [ ] Log any issues observed
