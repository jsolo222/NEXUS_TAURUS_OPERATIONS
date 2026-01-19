"""
NEXUS TAURUS OPERATIONS - Message Protocol Definitions

This module defines the canonical message formats for all vehicle-ground
communication. These schemas are the source of truth for telemetry and
command structures.

Protocol version: 1.0.0
"""

from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Optional
import time
import json
import uuid


class MessageType(Enum):
    """Top-level message classification."""
    TELEMETRY = "telemetry"
    COMMAND = "command"
    ACK = "ack"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class CommandType(Enum):
    """Available command types for vehicle control."""
    # Motion commands
    MOVE = "MOVE"
    STOP = "STOP"
    ROTATE = "ROTATE"

    # Mode commands
    SET_MODE = "SET_MODE"
    ARM = "ARM"
    DISARM = "DISARM"

    # System commands
    REBOOT = "REBOOT"
    CALIBRATE = "CALIBRATE"
    SET_CONFIG = "SET_CONFIG"

    # Mission commands
    RETURN_TO_BASE = "RTB"
    HOLD_POSITION = "HOLD"
    WAYPOINT = "WAYPOINT"


class VehicleMode(Enum):
    """Operational modes for vehicles."""
    STANDBY = "STANDBY"
    MANUAL = "MANUAL"
    AUTONOMOUS = "AUTONOMOUS"
    RETURN_TO_BASE = "RTB"
    EMERGENCY_STOP = "E_STOP"


class AckStatus(Enum):
    """Command acknowledgment status codes."""
    RECEIVED = "RECEIVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


# =============================================================================
# Telemetry Payload Components
# =============================================================================

@dataclass
class Position:
    """Vehicle position in local reference frame."""
    x: float = 0.0           # meters from origin
    y: float = 0.0           # meters from origin
    heading: float = 0.0     # degrees, 0 = North, clockwise positive

    # Future GPS integration
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None


@dataclass
class Velocity:
    """Vehicle velocity state."""
    linear: float = 0.0      # m/s forward velocity
    angular: float = 0.0     # rad/s yaw rate


@dataclass
class BatteryState:
    """Battery telemetry."""
    voltage: float = 0.0     # Volts
    current: float = 0.0     # Amps (positive = discharging)
    percent: int = 0         # State of charge 0-100


@dataclass
class MotorState:
    """Motor PWM states."""
    left: int = 0            # -255 to 255
    right: int = 0           # -255 to 255


@dataclass
class SensorState:
    """Sensor readings from vehicle."""
    ir_left: int = 0         # IR obstacle sensor (0 = obstacle, 1 = clear)
    ir_right: int = 0        # IR obstacle sensor
    ultrasonic_cm: float = 0.0  # Ultrasonic distance in cm

    # Future sensor integrations
    lidar_points: Optional[list] = None  # LiDAR point cloud
    imu_accel: Optional[list] = None     # [ax, ay, az] m/s^2
    imu_gyro: Optional[list] = None      # [gx, gy, gz] rad/s


@dataclass
class SystemState:
    """Vehicle system health."""
    mode: str = "STANDBY"
    armed: bool = False
    uptime_ms: int = 0
    wifi_rssi: int = 0       # dBm
    free_heap: int = 0       # bytes
    cpu_temp: float = 0.0    # Celsius


# =============================================================================
# Top-Level Message Types
# =============================================================================

@dataclass
class TelemetryPayload:
    """Complete telemetry payload from vehicle."""
    position: Position = field(default_factory=Position)
    velocity: Velocity = field(default_factory=Velocity)
    battery: BatteryState = field(default_factory=BatteryState)
    motors: MotorState = field(default_factory=MotorState)
    sensors: SensorState = field(default_factory=SensorState)
    system: SystemState = field(default_factory=SystemState)


@dataclass
class TelemetryMessage:
    """
    Vehicle-to-Ground telemetry message.

    Sent periodically by vehicle to report current state.
    Rate: 10-50 Hz depending on mode.
    """
    vehicle_id: str
    payload: TelemetryPayload
    msg_type: str = MessageType.TELEMETRY.value
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    sequence: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, data: str) -> "TelemetryMessage":
        d = json.loads(data)
        d["payload"] = TelemetryPayload(
            position=Position(**d["payload"]["position"]),
            velocity=Velocity(**d["payload"]["velocity"]),
            battery=BatteryState(**d["payload"]["battery"]),
            motors=MotorState(**d["payload"]["motors"]),
            sensors=SensorState(**d["payload"]["sensors"]),
            system=SystemState(**d["payload"]["system"]),
        )
        return cls(**d)


@dataclass
class CommandMessage:
    """
    Ground-to-Vehicle command message.

    All commands require acknowledgment from vehicle.
    """
    vehicle_id: str
    command: str
    params: dict = field(default_factory=dict)
    msg_type: str = MessageType.COMMAND.value
    command_id: str = field(default_factory=lambda: f"cmd_{uuid.uuid4().hex[:8]}")
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "CommandMessage":
        return cls(**json.loads(data))


@dataclass
class AckMessage:
    """
    Vehicle-to-Ground command acknowledgment.

    Sent in response to every command received.
    """
    command_id: str
    vehicle_id: str
    status: str
    message: str = ""
    msg_type: str = MessageType.ACK.value
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "AckMessage":
        return cls(**json.loads(data))


@dataclass
class HeartbeatMessage:
    """
    Bidirectional heartbeat for connection health monitoring.

    Sent every 1 second by both ground and vehicle.
    Connection considered lost after 3 missed heartbeats.
    """
    vehicle_id: str
    msg_type: str = MessageType.HEARTBEAT.value
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class ErrorMessage:
    """
    Error notification from vehicle.

    Used for non-fatal errors that don't require immediate action.
    """
    vehicle_id: str
    error_code: int
    error_message: str
    severity: str = "WARNING"  # WARNING, ERROR, CRITICAL
    msg_type: str = MessageType.ERROR.value
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_json(self) -> str:
        return json.dumps(asdict(self))


# =============================================================================
# Protocol Constants
# =============================================================================

PROTOCOL_VERSION = "1.0.0"
TELEMETRY_PORT = 8765
COMMAND_PORT = 8766

# Timing constants (milliseconds)
HEARTBEAT_INTERVAL_MS = 1000
HEARTBEAT_TIMEOUT_MS = 3000
TELEMETRY_INTERVAL_MS = 100  # 10 Hz default
COMMAND_TIMEOUT_MS = 5000


if __name__ == "__main__":
    # Example usage
    telem = TelemetryMessage(
        vehicle_id="TAURUS-01",
        sequence=1,
        payload=TelemetryPayload(
            position=Position(x=1.5, y=2.3, heading=45.0),
            velocity=Velocity(linear=0.5, angular=0.1),
            battery=BatteryState(voltage=7.4, current=1.2, percent=85),
            motors=MotorState(left=128, right=128),
            sensors=SensorState(ir_left=1, ir_right=1, ultrasonic_cm=45.2),
            system=SystemState(mode="MANUAL", armed=True, uptime_ms=60000),
        )
    )
    print("Telemetry Message:")
    print(telem.to_json())
    print()

    cmd = CommandMessage(
        vehicle_id="TAURUS-01",
        command=CommandType.MOVE.value,
        params={"linear": 0.5, "angular": 0.0}
    )
    print("Command Message:")
    print(cmd.to_json())
