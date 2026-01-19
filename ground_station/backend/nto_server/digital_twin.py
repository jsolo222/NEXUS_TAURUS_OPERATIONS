"""
Digital Twin State Manager

Maintains real-time synchronized state of all vehicles in the fleet.
The digital twin reflects ACTUAL vehicle state, not desired state.

Key principles:
- State is updated ONLY from validated telemetry
- All state changes are logged immutably
- State includes connection health and data freshness
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from collections import deque
import asyncio
import structlog

logger = structlog.get_logger()


@dataclass
class Position:
    """Vehicle position in local or global reference frame."""
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None


@dataclass
class Velocity:
    """Vehicle velocity state."""
    linear: float = 0.0
    angular: float = 0.0


@dataclass
class BatteryState:
    """Battery health."""
    voltage: float = 0.0
    current: float = 0.0
    percent: int = 0


@dataclass
class ConnectionState:
    """Connection health tracking."""
    connected: bool = False
    last_heartbeat: Optional[datetime] = None
    last_telemetry: Optional[datetime] = None
    latency_ms: float = 0.0
    missed_heartbeats: int = 0
    rssi: int = 0


@dataclass
class VehicleState:
    """
    Complete state representation of a single vehicle.

    This is the digital twin - an accurate real-time mirror
    of the physical vehicle's state.
    """
    vehicle_id: str
    position: Position = field(default_factory=Position)
    velocity: Velocity = field(default_factory=Velocity)
    battery: BatteryState = field(default_factory=BatteryState)
    connection: ConnectionState = field(default_factory=ConnectionState)

    # Operational state
    mode: str = "STANDBY"
    armed: bool = False

    # Motor outputs (for visualization)
    motor_left: int = 0
    motor_right: int = 0

    # Sensor readings
    ir_left: int = 1
    ir_right: int = 1
    ultrasonic_cm: float = 0.0

    # System health
    uptime_ms: int = 0
    free_heap: int = 0
    cpu_temp: float = 0.0

    # Telemetry tracking
    telemetry_sequence: int = 0
    telemetry_rate_hz: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert state to dictionary for JSON serialization."""
        return {
            "vehicle_id": self.vehicle_id,
            "position": {
                "x": self.position.x,
                "y": self.position.y,
                "heading": self.position.heading,
                "latitude": self.position.latitude,
                "longitude": self.position.longitude,
            },
            "velocity": {
                "linear": self.velocity.linear,
                "angular": self.velocity.angular,
            },
            "battery": {
                "voltage": self.battery.voltage,
                "current": self.battery.current,
                "percent": self.battery.percent,
            },
            "connection": {
                "connected": self.connection.connected,
                "latency_ms": self.connection.latency_ms,
                "rssi": self.connection.rssi,
            },
            "mode": self.mode,
            "armed": self.armed,
            "motors": {
                "left": self.motor_left,
                "right": self.motor_right,
            },
            "sensors": {
                "ir_left": self.ir_left,
                "ir_right": self.ir_right,
                "ultrasonic_cm": self.ultrasonic_cm,
            },
            "system": {
                "uptime_ms": self.uptime_ms,
                "free_heap": self.free_heap,
                "cpu_temp": self.cpu_temp,
            },
            "telemetry": {
                "sequence": self.telemetry_sequence,
                "rate_hz": self.telemetry_rate_hz,
            },
            "updated_at": self.updated_at.isoformat(),
        }


class DigitalTwinManager:
    """
    Manages digital twin state for all vehicles in the fleet.

    Thread-safe state management with event broadcasting.
    """

    def __init__(self, heartbeat_timeout_ms: int = 3000):
        self._vehicles: dict[str, VehicleState] = {}
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        self._heartbeat_timeout_ms = heartbeat_timeout_ms

        # Telemetry rate calculation
        self._telemetry_timestamps: dict[str, deque] = {}
        self._rate_window_size = 50

        logger.info("digital_twin_manager_initialized")

    async def register_vehicle(self, vehicle_id: str) -> VehicleState:
        """Register a new vehicle or return existing state."""
        async with self._lock:
            if vehicle_id not in self._vehicles:
                self._vehicles[vehicle_id] = VehicleState(vehicle_id=vehicle_id)
                self._telemetry_timestamps[vehicle_id] = deque(maxlen=self._rate_window_size)
                logger.info("vehicle_registered", vehicle_id=vehicle_id)
            return self._vehicles[vehicle_id]

    async def update_from_telemetry(self, vehicle_id: str, telemetry: dict) -> VehicleState:
        """
        Update vehicle state from incoming telemetry.

        This is the ONLY way state should be modified.
        """
        async with self._lock:
            if vehicle_id not in self._vehicles:
                self._vehicles[vehicle_id] = VehicleState(vehicle_id=vehicle_id)
                self._telemetry_timestamps[vehicle_id] = deque(maxlen=self._rate_window_size)

            state = self._vehicles[vehicle_id]
            payload = telemetry.get("payload", {})
            now = datetime.now(timezone.utc)

            # Update position
            if "position" in payload:
                pos = payload["position"]
                state.position.x = pos.get("x", state.position.x)
                state.position.y = pos.get("y", state.position.y)
                state.position.heading = pos.get("heading", state.position.heading)
                state.position.latitude = pos.get("latitude")
                state.position.longitude = pos.get("longitude")

            # Update velocity
            if "velocity" in payload:
                vel = payload["velocity"]
                state.velocity.linear = vel.get("linear", state.velocity.linear)
                state.velocity.angular = vel.get("angular", state.velocity.angular)

            # Update battery
            if "battery" in payload:
                bat = payload["battery"]
                state.battery.voltage = bat.get("voltage", state.battery.voltage)
                state.battery.current = bat.get("current", state.battery.current)
                state.battery.percent = bat.get("percent", state.battery.percent)

            # Update motors
            if "motors" in payload:
                motors = payload["motors"]
                state.motor_left = motors.get("left", state.motor_left)
                state.motor_right = motors.get("right", state.motor_right)

            # Update sensors
            if "sensors" in payload:
                sensors = payload["sensors"]
                state.ir_left = sensors.get("ir_left", state.ir_left)
                state.ir_right = sensors.get("ir_right", state.ir_right)
                state.ultrasonic_cm = sensors.get("ultrasonic_cm", state.ultrasonic_cm)

            # Update system state
            if "system" in payload:
                sys = payload["system"]
                state.mode = sys.get("mode", state.mode)
                state.armed = sys.get("armed", state.armed)
                state.uptime_ms = sys.get("uptime_ms", state.uptime_ms)
                state.free_heap = sys.get("free_heap", state.free_heap)
                state.cpu_temp = sys.get("cpu_temp", state.cpu_temp)
                state.connection.rssi = sys.get("wifi_rssi", state.connection.rssi)

            # Update telemetry tracking
            state.telemetry_sequence = telemetry.get("sequence", state.telemetry_sequence)
            state.connection.last_telemetry = now
            state.connection.connected = True
            state.updated_at = now

            # Calculate telemetry rate
            self._telemetry_timestamps[vehicle_id].append(now.timestamp())
            if len(self._telemetry_timestamps[vehicle_id]) >= 2:
                timestamps = list(self._telemetry_timestamps[vehicle_id])
                duration = timestamps[-1] - timestamps[0]
                if duration > 0:
                    state.telemetry_rate_hz = round((len(timestamps) - 1) / duration, 1)

            # Broadcast state update to subscribers
            await self._broadcast_state(vehicle_id, state)

            return state

    async def update_heartbeat(self, vehicle_id: str) -> None:
        """Update heartbeat timestamp for vehicle."""
        async with self._lock:
            if vehicle_id in self._vehicles:
                state = self._vehicles[vehicle_id]
                state.connection.last_heartbeat = datetime.now(timezone.utc)
                state.connection.missed_heartbeats = 0
                state.connection.connected = True

    async def check_connection_health(self) -> None:
        """Check connection health for all vehicles. Run periodically."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            for vehicle_id, state in self._vehicles.items():
                if state.connection.last_heartbeat:
                    elapsed_ms = (now - state.connection.last_heartbeat).total_seconds() * 1000
                    if elapsed_ms > self._heartbeat_timeout_ms:
                        state.connection.connected = False
                        state.connection.missed_heartbeats += 1
                        logger.warning(
                            "vehicle_connection_lost",
                            vehicle_id=vehicle_id,
                            elapsed_ms=elapsed_ms,
                        )

    async def get_state(self, vehicle_id: str) -> Optional[VehicleState]:
        """Get current state of a vehicle."""
        async with self._lock:
            return self._vehicles.get(vehicle_id)

    async def get_all_states(self) -> dict[str, VehicleState]:
        """Get states of all vehicles."""
        async with self._lock:
            return dict(self._vehicles)

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to state updates. Returns a queue that receives updates."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from state updates."""
        self._subscribers.discard(queue)

    async def _broadcast_state(self, vehicle_id: str, state: VehicleState) -> None:
        """Broadcast state update to all subscribers."""
        update = {
            "event": "state_update",
            "vehicle_id": vehicle_id,
            "state": state.to_dict(),
        }
        dead_queues = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(update)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        for queue in dead_queues:
            self._subscribers.discard(queue)


# Global singleton instance
_twin_manager: Optional[DigitalTwinManager] = None


def get_twin_manager() -> DigitalTwinManager:
    """Get the global digital twin manager instance."""
    global _twin_manager
    if _twin_manager is None:
        _twin_manager = DigitalTwinManager()
    return _twin_manager
