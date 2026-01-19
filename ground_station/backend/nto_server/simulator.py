"""
NEXUS TAURUS OPERATIONS - Telemetry Simulator

Generates realistic telemetry data for testing without hardware.
NOT for production use - development and testing only.
"""

import asyncio
import math
import random
import time
from dataclasses import dataclass
from typing import Callable, Optional

import structlog

from .digital_twin import get_twin_manager

logger = structlog.get_logger()


@dataclass
class SimulatorConfig:
    """Simulator configuration."""
    vehicle_id: str = "TAURUS-01"
    telemetry_rate_hz: float = 10.0
    battery_drain_rate: float = 0.01  # percent per second when moving
    initial_battery: float = 85.0
    noise_level: float = 0.1


class TelemetrySimulator:
    """
    Generates simulated telemetry for testing.

    Simulates:
    - Position updates based on velocity commands
    - Battery drain
    - Sensor readings
    - CSI presence detection events
    - System metrics
    """

    def __init__(self, config: Optional[SimulatorConfig] = None):
        self.config = config or SimulatorConfig()
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Simulated state
        self._x = 0.0
        self._y = 0.0
        self._heading = 0.0
        self._linear = 0.0
        self._angular = 0.0
        self._battery = self.config.initial_battery
        self._armed = False
        self._mode = "STANDBY"
        self._sequence = 0
        self._start_time = time.time()

        # CSI simulation
        self._csi_state = "CLEAR"
        self._csi_variance = 0.0
        self._csi_event_time = 0.0

        # Command callback
        self._command_callback: Optional[Callable] = None

    def set_command_callback(self, callback: Callable) -> None:
        """Set callback for receiving commands."""
        self._command_callback = callback

    async def start(self) -> None:
        """Start the simulator."""
        if self._running:
            return

        self._running = True
        self._start_time = time.time()
        self._task = asyncio.create_task(self._simulation_loop())
        logger.info("simulator_started", vehicle_id=self.config.vehicle_id)

    async def stop(self) -> None:
        """Stop the simulator."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("simulator_stopped", vehicle_id=self.config.vehicle_id)

    def handle_command(self, command: str, params: dict) -> None:
        """Handle incoming commands."""
        logger.debug("simulator_command", command=command, params=params)

        if command == "MOVE":
            if self._mode == "MANUAL" and self._armed:
                self._linear = params.get("linear", 0.0)
                self._angular = params.get("angular", 0.0)
        elif command == "STOP":
            self._linear = 0.0
            self._angular = 0.0
        elif command == "ARM":
            self._armed = True
        elif command == "DISARM":
            self._armed = False
            self._linear = 0.0
            self._angular = 0.0
        elif command == "SET_MODE":
            self._mode = params.get("mode", "STANDBY")
            if self._mode == "STANDBY" or self._mode == "E_STOP":
                self._armed = False
                self._linear = 0.0
                self._angular = 0.0

    async def _simulation_loop(self) -> None:
        """Main simulation loop."""
        twin = get_twin_manager()
        interval = 1.0 / self.config.telemetry_rate_hz

        while self._running:
            try:
                # Update physics
                self._update_physics(interval)

                # Update CSI (random events)
                self._update_csi()

                # Generate telemetry
                telemetry = self._generate_telemetry()

                # Send to digital twin
                await twin.update_from_telemetry(
                    self.config.vehicle_id,
                    telemetry
                )

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("simulator_error", error=str(e))
                await asyncio.sleep(1.0)

    def _update_physics(self, dt: float) -> None:
        """Update simulated position based on velocity."""
        if self._armed and self._mode == "MANUAL":
            # Simple differential drive model
            speed = self._linear * 0.5  # Max 0.5 m/s

            # Update heading
            self._heading += self._angular * 45 * dt  # degrees per second
            self._heading = self._heading % 360

            # Update position
            heading_rad = math.radians(self._heading)
            self._x += speed * math.cos(heading_rad) * dt
            self._y += speed * math.sin(heading_rad) * dt

            # Drain battery when moving
            if abs(self._linear) > 0 or abs(self._angular) > 0:
                self._battery -= self.config.battery_drain_rate * dt
                self._battery = max(0, self._battery)

    def _update_csi(self) -> None:
        """Simulate CSI presence detection events."""
        now = time.time()

        # Random presence events every 30-60 seconds
        if now - self._csi_event_time > random.uniform(30, 60):
            self._csi_event_time = now

            # 70% chance of CLEAR, 30% chance of detection
            if random.random() < 0.3:
                states = ["PRESENCE", "MOVEMENT", "APPROACHING", "RETREATING"]
                self._csi_state = random.choice(states)
                self._csi_variance = random.uniform(0.5, 2.0)
            else:
                self._csi_state = "CLEAR"
                self._csi_variance = random.uniform(0.0, 0.3)

        # Decay back to CLEAR after 5-10 seconds
        if self._csi_state != "CLEAR" and now - self._csi_event_time > random.uniform(5, 10):
            self._csi_state = "CLEAR"
            self._csi_variance = random.uniform(0.0, 0.3)

    def _generate_telemetry(self) -> dict:
        """Generate a telemetry message."""
        self._sequence += 1
        now = time.time()
        uptime = int((now - self._start_time) * 1000)

        # Add noise
        noise = self.config.noise_level

        # Simulate ultrasonic (random obstacles)
        ultrasonic = random.uniform(30, 200) if random.random() > 0.1 else random.uniform(5, 30)

        return {
            "msg_type": "telemetry",
            "vehicle_id": self.config.vehicle_id,
            "timestamp": int(now * 1000),
            "sequence": self._sequence,
            "payload": {
                "position": {
                    "x": self._x + random.gauss(0, noise * 0.01),
                    "y": self._y + random.gauss(0, noise * 0.01),
                    "heading": self._heading + random.gauss(0, noise * 2),
                },
                "velocity": {
                    "linear": self._linear,
                    "angular": self._angular,
                },
                "battery": {
                    "voltage": 7.4 * (self._battery / 100) + random.gauss(0, 0.1),
                    "current": abs(self._linear) * 1.5 + abs(self._angular) * 0.5 + random.gauss(0, 0.1),
                    "percent": self._battery,
                },
                "motors": {
                    "left": int((self._linear + self._angular) * 127),
                    "right": int((self._linear - self._angular) * 127),
                },
                "sensors": {
                    "ir_left": random.random() > 0.05,
                    "ir_right": random.random() > 0.05,
                    "ultrasonic_cm": ultrasonic,
                },
                "csi_presence": {
                    "state": self._csi_state,
                    "confidence": 0.95 if self._csi_state != "CLEAR" else 0.1,
                    "variance": self._csi_variance,
                    "duration_ms": int((now - self._csi_event_time) * 1000) if self._csi_state != "CLEAR" else 0,
                },
                "system": {
                    "mode": self._mode,
                    "armed": self._armed,
                    "uptime_ms": uptime,
                    "wifi_rssi": -50 + random.gauss(0, 5),
                    "free_heap": 200000 + random.randint(-10000, 10000),
                    "cpu_temp": 45 + random.gauss(0, 2),
                },
            },
        }


# Singleton
_simulator: Optional[TelemetrySimulator] = None


def get_simulator() -> TelemetrySimulator:
    """Get the simulator instance."""
    global _simulator
    if _simulator is None:
        _simulator = TelemetrySimulator()
    return _simulator
