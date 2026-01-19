"""
Command Dispatcher

Handles command creation, validation, dispatch, and acknowledgment tracking.
Commands are the ONLY way to modify vehicle state from ground station.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable, Awaitable
import structlog

from .telemetry import get_telemetry_server
from .storage import get_telemetry_store

logger = structlog.get_logger()


class CommandStatus(Enum):
    """Command lifecycle states."""
    PENDING = "PENDING"
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class CommandType(Enum):
    """Available command types."""
    # Motion
    MOVE = "MOVE"
    STOP = "STOP"
    ROTATE = "ROTATE"

    # Mode
    SET_MODE = "SET_MODE"
    ARM = "ARM"
    DISARM = "DISARM"

    # System
    REBOOT = "REBOOT"
    CALIBRATE = "CALIBRATE"

    # Mission
    RETURN_TO_BASE = "RTB"
    HOLD = "HOLD"


@dataclass
class CommandRecord:
    """Tracks a command through its lifecycle."""
    command_id: str
    vehicle_id: str
    command_type: CommandType
    params: dict = field(default_factory=dict)
    status: CommandStatus = CommandStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    acked_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_message(self) -> dict:
        """Convert to wire format."""
        return {
            "msg_type": "command",
            "command_id": self.command_id,
            "vehicle_id": self.vehicle_id,
            "command": self.command_type.value,
            "params": self.params,
            "timestamp": int(self.created_at.timestamp() * 1000),
        }


class CommandDispatcher:
    """
    Manages command creation, dispatch, and tracking.

    Features:
    - Command validation before dispatch
    - Acknowledgment tracking with timeout
    - Command history
    """

    def __init__(self, default_timeout_ms: int = 5000):
        self._pending_commands: dict[str, CommandRecord] = {}
        self._command_history: dict[str, list[CommandRecord]] = {}
        self._telemetry_server = get_telemetry_server()
        self._store = get_telemetry_store()
        self._default_timeout_ms = default_timeout_ms
        self._ack_callbacks: dict[str, Callable[[CommandRecord], Awaitable[None]]] = {}
        self._lock = asyncio.Lock()

        logger.info("command_dispatcher_initialized")

    async def dispatch(
        self,
        vehicle_id: str,
        command_type: CommandType,
        params: Optional[dict] = None,
        timeout_ms: Optional[int] = None,
    ) -> CommandRecord:
        """
        Create and dispatch a command to a vehicle.

        Args:
            vehicle_id: Target vehicle
            command_type: Type of command
            params: Command parameters
            timeout_ms: Acknowledgment timeout

        Returns:
            CommandRecord for tracking

        Raises:
            ValueError: If command validation fails
            ConnectionError: If vehicle not connected
        """
        # Validate command
        if params is None:
            params = {}

        self._validate_command(command_type, params)

        # Create command record
        command = CommandRecord(
            command_id=f"cmd_{uuid.uuid4().hex[:8]}",
            vehicle_id=vehicle_id,
            command_type=command_type,
            params=params,
        )

        # Store in pending
        async with self._lock:
            self._pending_commands[command.command_id] = command

            if vehicle_id not in self._command_history:
                self._command_history[vehicle_id] = []
            self._command_history[vehicle_id].append(command)

        # Persist command
        await self._store.store_command(command.to_message())

        # Dispatch via telemetry server
        success = await self._telemetry_server.send_command(
            vehicle_id,
            command.to_message()
        )

        if not success:
            command.status = CommandStatus.FAILED
            command.error_message = "Vehicle not connected"
            raise ConnectionError(f"Vehicle {vehicle_id} not connected")

        command.status = CommandStatus.SENT
        command.sent_at = datetime.now(timezone.utc)

        logger.info(
            "command_dispatched",
            command_id=command.command_id,
            vehicle_id=vehicle_id,
            command_type=command_type.value,
        )

        # Start timeout watcher
        timeout = timeout_ms or self._default_timeout_ms
        asyncio.create_task(self._timeout_watcher(command.command_id, timeout))

        return command

    def _validate_command(self, command_type: CommandType, params: dict) -> None:
        """Validate command parameters."""
        if command_type == CommandType.MOVE:
            linear = params.get("linear", 0)
            angular = params.get("angular", 0)
            if not (-1.0 <= linear <= 1.0):
                raise ValueError(f"linear velocity must be between -1.0 and 1.0, got {linear}")
            if not (-1.0 <= angular <= 1.0):
                raise ValueError(f"angular velocity must be between -1.0 and 1.0, got {angular}")

        elif command_type == CommandType.ROTATE:
            angle = params.get("angle")
            if angle is None:
                raise ValueError("ROTATE command requires 'angle' parameter")

        elif command_type == CommandType.SET_MODE:
            mode = params.get("mode")
            valid_modes = ["STANDBY", "MANUAL", "AUTONOMOUS", "RTB", "E_STOP"]
            if mode not in valid_modes:
                raise ValueError(f"Invalid mode '{mode}', must be one of {valid_modes}")

    async def _timeout_watcher(self, command_id: str, timeout_ms: int) -> None:
        """Watch for command timeout."""
        await asyncio.sleep(timeout_ms / 1000)

        async with self._lock:
            command = self._pending_commands.get(command_id)
            if command and command.status == CommandStatus.SENT:
                command.status = CommandStatus.TIMEOUT
                command.error_message = f"No acknowledgment within {timeout_ms}ms"
                del self._pending_commands[command_id]

                logger.warning(
                    "command_timeout",
                    command_id=command_id,
                    timeout_ms=timeout_ms,
                )

    async def handle_ack(self, ack_message: dict) -> None:
        """Process command acknowledgment from vehicle."""
        command_id = ack_message.get("command_id")
        status = ack_message.get("status")

        async with self._lock:
            command = self._pending_commands.get(command_id)
            if not command:
                logger.warning("ack_for_unknown_command", command_id=command_id)
                return

            command.acked_at = datetime.now(timezone.utc)

            if status == "RECEIVED":
                command.status = CommandStatus.RECEIVED
            elif status == "EXECUTING":
                command.status = CommandStatus.EXECUTING
            elif status == "COMPLETED":
                command.status = CommandStatus.COMPLETED
                command.completed_at = datetime.now(timezone.utc)
                del self._pending_commands[command_id]
            elif status in ("FAILED", "REJECTED"):
                command.status = CommandStatus.FAILED
                command.error_message = ack_message.get("message", "Unknown error")
                del self._pending_commands[command_id]

        # Update persistent storage
        await self._store.update_command_status(
            command_id,
            command.status.value,
            completed=(command.status in (CommandStatus.COMPLETED, CommandStatus.FAILED))
        )

        logger.info(
            "command_ack_processed",
            command_id=command_id,
            status=command.status.value,
        )

    async def get_pending_commands(self, vehicle_id: Optional[str] = None) -> list[CommandRecord]:
        """Get all pending commands, optionally filtered by vehicle."""
        async with self._lock:
            commands = list(self._pending_commands.values())
            if vehicle_id:
                commands = [c for c in commands if c.vehicle_id == vehicle_id]
            return commands

    async def get_command_history(
        self,
        vehicle_id: str,
        limit: int = 100,
    ) -> list[CommandRecord]:
        """Get command history for a vehicle."""
        async with self._lock:
            history = self._command_history.get(vehicle_id, [])
            return history[-limit:]

    # Convenience methods for common commands

    async def move(
        self,
        vehicle_id: str,
        linear: float = 0.0,
        angular: float = 0.0,
    ) -> CommandRecord:
        """Send MOVE command."""
        return await self.dispatch(
            vehicle_id,
            CommandType.MOVE,
            {"linear": linear, "angular": angular}
        )

    async def stop(self, vehicle_id: str) -> CommandRecord:
        """Send STOP command."""
        return await self.dispatch(vehicle_id, CommandType.STOP)

    async def arm(self, vehicle_id: str) -> CommandRecord:
        """ARM the vehicle for operation."""
        return await self.dispatch(vehicle_id, CommandType.ARM)

    async def disarm(self, vehicle_id: str) -> CommandRecord:
        """DISARM the vehicle."""
        return await self.dispatch(vehicle_id, CommandType.DISARM)

    async def emergency_stop(self, vehicle_id: str) -> CommandRecord:
        """Emergency stop - immediate halt."""
        return await self.dispatch(
            vehicle_id,
            CommandType.SET_MODE,
            {"mode": "E_STOP"}
        )

    async def return_to_base(self, vehicle_id: str) -> CommandRecord:
        """Initiate return to base."""
        return await self.dispatch(vehicle_id, CommandType.RETURN_TO_BASE)


# Global singleton
_command_dispatcher: Optional[CommandDispatcher] = None


def get_command_dispatcher() -> CommandDispatcher:
    """Get the global command dispatcher instance."""
    global _command_dispatcher
    if _command_dispatcher is None:
        _command_dispatcher = CommandDispatcher()
    return _command_dispatcher
