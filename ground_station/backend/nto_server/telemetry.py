"""
Telemetry Server

WebSocket server for receiving real-time telemetry from vehicles.
Handles connection management, message parsing, and state updates.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
import structlog
from fastapi import WebSocket, WebSocketDisconnect

from .digital_twin import get_twin_manager
from .storage import get_telemetry_store

logger = structlog.get_logger()


class VehicleConnection:
    """Represents an active connection to a vehicle."""

    def __init__(self, websocket: WebSocket, vehicle_id: str):
        self.websocket = websocket
        self.vehicle_id = vehicle_id
        self.connected_at = datetime.now(timezone.utc)
        self.last_message_at: Optional[datetime] = None
        self.message_count = 0
        self.error_count = 0

    async def send_command(self, command: dict) -> bool:
        """Send a command to the vehicle."""
        try:
            await self.websocket.send_json(command)
            logger.debug("command_sent", vehicle_id=self.vehicle_id, command=command)
            return True
        except Exception as e:
            logger.error("command_send_failed", vehicle_id=self.vehicle_id, error=str(e))
            self.error_count += 1
            return False


class TelemetryServer:
    """
    Manages WebSocket connections and telemetry ingestion from vehicles.
    """

    def __init__(self):
        self._connections: dict[str, VehicleConnection] = {}
        self._twin_manager = get_twin_manager()
        self._store = get_telemetry_store()
        self._lock = asyncio.Lock()
        logger.info("telemetry_server_initialized")

    async def handle_connection(self, websocket: WebSocket, vehicle_id: str) -> None:
        """
        Handle a new WebSocket connection from a vehicle.

        This is the main connection handler that processes all incoming messages.
        """
        await websocket.accept()
        connection = VehicleConnection(websocket, vehicle_id)

        async with self._lock:
            # Close existing connection if any
            if vehicle_id in self._connections:
                old_conn = self._connections[vehicle_id]
                try:
                    await old_conn.websocket.close()
                except Exception:
                    pass
                logger.warning("replaced_existing_connection", vehicle_id=vehicle_id)

            self._connections[vehicle_id] = connection

        # Register vehicle with digital twin
        await self._twin_manager.register_vehicle(vehicle_id)

        logger.info(
            "vehicle_connected",
            vehicle_id=vehicle_id,
            remote=str(websocket.client),
        )

        try:
            await self._message_loop(connection)
        except WebSocketDisconnect:
            logger.info("vehicle_disconnected", vehicle_id=vehicle_id)
        except Exception as e:
            logger.error("connection_error", vehicle_id=vehicle_id, error=str(e))
        finally:
            async with self._lock:
                if self._connections.get(vehicle_id) == connection:
                    del self._connections[vehicle_id]

    async def _message_loop(self, connection: VehicleConnection) -> None:
        """Process messages from a vehicle connection."""
        while True:
            try:
                data = await connection.websocket.receive_text()
                connection.last_message_at = datetime.now(timezone.utc)
                connection.message_count += 1

                message = json.loads(data)
                await self._process_message(connection, message)

            except json.JSONDecodeError as e:
                logger.warning(
                    "invalid_json",
                    vehicle_id=connection.vehicle_id,
                    error=str(e),
                )
                connection.error_count += 1

    async def _process_message(self, connection: VehicleConnection, message: dict) -> None:
        """Route and process a message based on type."""
        msg_type = message.get("msg_type", "unknown")

        if msg_type == "telemetry":
            await self._handle_telemetry(connection, message)
        elif msg_type == "heartbeat":
            await self._handle_heartbeat(connection, message)
        elif msg_type == "ack":
            await self._handle_ack(connection, message)
        elif msg_type == "error":
            await self._handle_error(connection, message)
        else:
            logger.warning(
                "unknown_message_type",
                vehicle_id=connection.vehicle_id,
                msg_type=msg_type,
            )

    async def _handle_telemetry(self, connection: VehicleConnection, message: dict) -> None:
        """Process incoming telemetry message."""
        vehicle_id = connection.vehicle_id

        # Update digital twin
        await self._twin_manager.update_from_telemetry(vehicle_id, message)

        # Persist telemetry (async, non-blocking)
        asyncio.create_task(self._store.store_telemetry(vehicle_id, message))

        logger.debug(
            "telemetry_received",
            vehicle_id=vehicle_id,
            sequence=message.get("sequence"),
        )

    async def _handle_heartbeat(self, connection: VehicleConnection, message: dict) -> None:
        """Process heartbeat message."""
        await self._twin_manager.update_heartbeat(connection.vehicle_id)

        # Send heartbeat response
        response = {
            "msg_type": "heartbeat",
            "vehicle_id": connection.vehicle_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        }
        await connection.websocket.send_json(response)

    async def _handle_ack(self, connection: VehicleConnection, message: dict) -> None:
        """Process command acknowledgment."""
        command_id = message.get("command_id")
        status = message.get("status")

        logger.info(
            "command_ack_received",
            vehicle_id=connection.vehicle_id,
            command_id=command_id,
            status=status,
        )

        # TODO: Notify command dispatcher of acknowledgment

    async def _handle_error(self, connection: VehicleConnection, message: dict) -> None:
        """Process error message from vehicle."""
        logger.error(
            "vehicle_error",
            vehicle_id=connection.vehicle_id,
            error_code=message.get("error_code"),
            error_message=message.get("error_message"),
            severity=message.get("severity"),
        )

    async def send_command(self, vehicle_id: str, command: dict) -> bool:
        """Send a command to a specific vehicle."""
        async with self._lock:
            connection = self._connections.get(vehicle_id)

        if connection is None:
            logger.warning("command_failed_not_connected", vehicle_id=vehicle_id)
            return False

        return await connection.send_command(command)

    async def get_connected_vehicles(self) -> list[str]:
        """Get list of currently connected vehicle IDs."""
        async with self._lock:
            return list(self._connections.keys())

    async def get_connection_stats(self) -> dict:
        """Get connection statistics for all vehicles."""
        async with self._lock:
            stats = {}
            for vehicle_id, conn in self._connections.items():
                stats[vehicle_id] = {
                    "connected_at": conn.connected_at.isoformat(),
                    "last_message_at": conn.last_message_at.isoformat() if conn.last_message_at else None,
                    "message_count": conn.message_count,
                    "error_count": conn.error_count,
                }
            return stats


# Global singleton
_telemetry_server: Optional[TelemetryServer] = None


def get_telemetry_server() -> TelemetryServer:
    """Get the global telemetry server instance."""
    global _telemetry_server
    if _telemetry_server is None:
        _telemetry_server = TelemetryServer()
    return _telemetry_server
