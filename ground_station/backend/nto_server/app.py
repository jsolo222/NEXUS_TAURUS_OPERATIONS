"""
NEXUS TAURUS OPERATIONS - Ground Station API

FastAPI application providing:
- WebSocket endpoints for vehicle telemetry
- REST API for command dispatch
- Digital twin state queries
- Real-time state streaming for frontend
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

from .digital_twin import get_twin_manager
from .telemetry import get_telemetry_server
from .commands import get_command_dispatcher, CommandType
from .storage import get_telemetry_store
from .simulator import get_simulator

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


# =============================================================================
# Lifecycle Management
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Manage application lifecycle."""
    logger.info("nto_server_starting")

    # Initialize storage
    store = get_telemetry_store()
    await store.initialize()

    # Start health check loop
    health_task = asyncio.create_task(connection_health_loop())

    # Start simulator if enabled
    sim = None
    if os.environ.get("NTO_SIMULATE") == "1":
        sim = get_simulator()
        await sim.start()
        logger.info("simulator_auto_started")

    yield

    # Cleanup
    if sim:
        await sim.stop()

    health_task.cancel()
    try:
        await health_task
    except asyncio.CancelledError:
        pass

    await store.close()
    logger.info("nto_server_stopped")


async def connection_health_loop() -> None:
    """Periodically check connection health."""
    twin = get_twin_manager()
    while True:
        await asyncio.sleep(1.0)
        await twin.check_connection_health()


# =============================================================================
# Application Setup
# =============================================================================

app = FastAPI(
    title="NEXUS TAURUS OPERATIONS",
    description="Ground Station Control Server",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request/Response Models
# =============================================================================

class CommandRequest(BaseModel):
    """Command request body."""
    command: str = Field(..., description="Command type (MOVE, STOP, ARM, etc.)")
    params: dict = Field(default_factory=dict, description="Command parameters")


class CommandResponse(BaseModel):
    """Command response."""
    command_id: str
    vehicle_id: str
    command: str
    status: str


class VehicleStateResponse(BaseModel):
    """Vehicle state response."""
    vehicle_id: str
    connected: bool
    state: dict


# =============================================================================
# REST API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Server status."""
    return {
        "service": "NEXUS TAURUS OPERATIONS",
        "version": "0.1.0",
        "status": "operational"
    }


@app.get("/api/vehicles")
async def list_vehicles():
    """List all known vehicles and their connection status."""
    twin = get_twin_manager()
    telemetry = get_telemetry_server()

    states = await twin.get_all_states()
    connected = await telemetry.get_connected_vehicles()

    return {
        "vehicles": [
            {
                "vehicle_id": vid,
                "connected": vid in connected,
                "mode": state.mode,
                "armed": state.armed,
                "battery_percent": state.battery.percent,
            }
            for vid, state in states.items()
        ]
    }


@app.get("/api/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str):
    """Get current state of a vehicle."""
    twin = get_twin_manager()
    state = await twin.get_state(vehicle_id)

    if state is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")

    return VehicleStateResponse(
        vehicle_id=vehicle_id,
        connected=state.connection.connected,
        state=state.to_dict()
    )


@app.post("/api/vehicles/{vehicle_id}/command")
async def send_command(vehicle_id: str, request: CommandRequest):
    """Send a command to a vehicle."""
    dispatcher = get_command_dispatcher()

    try:
        command_type = CommandType(request.command)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid command type: {request.command}"
        )

    # If simulator is running and this is the simulated vehicle, send to simulator
    sim = get_simulator()
    if sim._running and vehicle_id == sim.config.vehicle_id:
        sim.handle_command(request.command, request.params)
        return CommandResponse(
            command_id=f"sim_{vehicle_id}",
            vehicle_id=vehicle_id,
            command=request.command,
            status="SENT",
        )

    try:
        record = await dispatcher.dispatch(
            vehicle_id=vehicle_id,
            command_type=command_type,
            params=request.params,
        )
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CommandResponse(
        command_id=record.command_id,
        vehicle_id=vehicle_id,
        command=record.command_type.value,
        status=record.status.value,
    )


@app.post("/api/vehicles/{vehicle_id}/stop")
async def emergency_stop(vehicle_id: str):
    """Emergency stop a vehicle."""
    # If simulator is running, send E_STOP to it
    sim = get_simulator()
    if sim._running and vehicle_id == sim.config.vehicle_id:
        sim.handle_command("SET_MODE", {"mode": "E_STOP"})
        return CommandResponse(
            command_id=f"sim_estop_{vehicle_id}",
            vehicle_id=vehicle_id,
            command="E_STOP",
            status="SENT",
        )

    dispatcher = get_command_dispatcher()

    try:
        record = await dispatcher.emergency_stop(vehicle_id)
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return CommandResponse(
        command_id=record.command_id,
        vehicle_id=vehicle_id,
        command="E_STOP",
        status=record.status.value,
    )


@app.get("/api/vehicles/{vehicle_id}/telemetry")
async def get_telemetry(
    vehicle_id: str,
    start_time: int | None = None,
    end_time: int | None = None,
    limit: int = 100,
):
    """Get historical telemetry for a vehicle."""
    store = get_telemetry_store()
    records = await store.get_telemetry(
        vehicle_id=vehicle_id,
        start_time=start_time,
        end_time=end_time,
        limit=min(limit, 1000),
    )
    return {"vehicle_id": vehicle_id, "records": records}


@app.get("/api/vehicles/{vehicle_id}/stats")
async def get_vehicle_stats(vehicle_id: str):
    """Get telemetry statistics for a vehicle."""
    store = get_telemetry_store()
    stats = await store.get_statistics(vehicle_id)
    return stats


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@app.websocket("/ws/vehicle/{vehicle_id}")
async def vehicle_websocket(websocket: WebSocket, vehicle_id: str):
    """
    WebSocket endpoint for vehicle connections.

    Vehicles connect here to send telemetry and receive commands.
    """
    telemetry = get_telemetry_server()
    await telemetry.handle_connection(websocket, vehicle_id)


@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard/frontend connections.

    Streams real-time state updates for all vehicles.
    """
    await websocket.accept()
    twin = get_twin_manager()
    queue = await twin.subscribe()

    logger.info("dashboard_connected", client=str(websocket.client))

    try:
        # Send initial state
        states = await twin.get_all_states()
        await websocket.send_json({
            "event": "initial_state",
            "vehicles": {vid: state.to_dict() for vid, state in states.items()}
        })

        # Stream updates
        while True:
            update = await queue.get()
            await websocket.send_json(update)

    except WebSocketDisconnect:
        logger.info("dashboard_disconnected", client=str(websocket.client))
    finally:
        await twin.unsubscribe(queue)


# =============================================================================
# Health Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


@app.get("/health/detailed")
async def detailed_health():
    """Detailed health information."""
    telemetry = get_telemetry_server()
    twin = get_twin_manager()

    connected = await telemetry.get_connected_vehicles()
    states = await twin.get_all_states()
    stats = await telemetry.get_connection_stats()

    return {
        "status": "healthy",
        "connected_vehicles": len(connected),
        "known_vehicles": len(states),
        "connection_stats": stats,
    }


# =============================================================================
# Simulator Endpoints (Development Only)
# =============================================================================

@app.post("/api/simulator/start")
async def start_simulator():
    """Start the telemetry simulator for testing without hardware."""
    sim = get_simulator()
    await sim.start()
    return {"status": "started", "vehicle_id": sim.config.vehicle_id}


@app.post("/api/simulator/stop")
async def stop_simulator():
    """Stop the telemetry simulator."""
    sim = get_simulator()
    await sim.stop()
    return {"status": "stopped"}


@app.post("/api/simulator/command")
async def simulator_command(request: CommandRequest):
    """Send a command to the simulator."""
    sim = get_simulator()
    sim.handle_command(request.command, request.params)
    return {"status": "ok", "command": request.command}
