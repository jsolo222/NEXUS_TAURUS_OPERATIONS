"""
Telemetry Storage

Persistent storage for telemetry data using SQLite with async support.
Telemetry is append-only - historical data is never modified.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import aiosqlite
import structlog

logger = structlog.get_logger()

# Default database path
DEFAULT_DB_PATH = Path("./data/telemetry.db")


class TelemetryStore:
    """
    Async SQLite storage for telemetry data.

    Provides:
    - Append-only telemetry storage
    - Time-range queries
    - Vehicle-specific data retrieval
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._db: Optional[aiosqlite.Connection] = None
        self._initialized = False
        self._write_queue: asyncio.Queue = asyncio.Queue()
        self._writer_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize database connection and schema."""
        if self._initialized:
            return

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(str(self.db_path))
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA synchronous=NORMAL")

        # Create telemetry table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                sequence INTEGER NOT NULL,
                payload TEXT NOT NULL,
                received_at TEXT NOT NULL,
                UNIQUE(vehicle_id, sequence)
            )
        """)

        # Create indexes for common queries
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_time
            ON telemetry(vehicle_id, timestamp DESC)
        """)

        # Create commands table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_id TEXT UNIQUE NOT NULL,
                vehicle_id TEXT NOT NULL,
                command_type TEXT NOT NULL,
                params TEXT,
                status TEXT DEFAULT 'PENDING',
                sent_at TEXT NOT NULL,
                acked_at TEXT,
                completed_at TEXT
            )
        """)

        await self._db.commit()

        # Start background writer
        self._writer_task = asyncio.create_task(self._background_writer())

        self._initialized = True
        logger.info("telemetry_store_initialized", db_path=str(self.db_path))

    async def close(self) -> None:
        """Close database connection."""
        if self._writer_task:
            self._writer_task.cancel()
            try:
                await self._writer_task
            except asyncio.CancelledError:
                pass

        if self._db:
            await self._db.close()
            self._db = None
            self._initialized = False

    async def store_telemetry(self, vehicle_id: str, telemetry: dict) -> None:
        """Queue telemetry for storage."""
        await self._write_queue.put((vehicle_id, telemetry))

    async def _background_writer(self) -> None:
        """Background task that batches writes for efficiency."""
        batch = []
        batch_size = 50
        flush_interval = 1.0  # seconds

        while True:
            try:
                # Wait for data with timeout
                try:
                    item = await asyncio.wait_for(
                        self._write_queue.get(),
                        timeout=flush_interval
                    )
                    batch.append(item)
                except asyncio.TimeoutError:
                    pass

                # Flush if batch is full or timeout occurred
                if len(batch) >= batch_size or (batch and self._write_queue.empty()):
                    await self._flush_batch(batch)
                    batch = []

            except asyncio.CancelledError:
                # Flush remaining on shutdown
                if batch:
                    await self._flush_batch(batch)
                raise

    async def _flush_batch(self, batch: list) -> None:
        """Write a batch of telemetry records."""
        if not self._db or not batch:
            return

        now = datetime.now(timezone.utc).isoformat()

        try:
            await self._db.executemany(
                """
                INSERT OR IGNORE INTO telemetry
                (vehicle_id, timestamp, sequence, payload, received_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        vehicle_id,
                        telemetry.get("timestamp", 0),
                        telemetry.get("sequence", 0),
                        json.dumps(telemetry.get("payload", {})),
                        now,
                    )
                    for vehicle_id, telemetry in batch
                ]
            )
            await self._db.commit()
            logger.debug("telemetry_batch_written", count=len(batch))
        except Exception as e:
            logger.error("telemetry_write_error", error=str(e))

    async def get_telemetry(
        self,
        vehicle_id: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1000,
    ) -> list[dict]:
        """
        Retrieve telemetry records for a vehicle.

        Args:
            vehicle_id: Vehicle identifier
            start_time: Start timestamp (ms since epoch)
            end_time: End timestamp (ms since epoch)
            limit: Maximum records to return

        Returns:
            List of telemetry records, newest first
        """
        if not self._db:
            await self.initialize()

        query = "SELECT timestamp, sequence, payload FROM telemetry WHERE vehicle_id = ?"
        params: list = [vehicle_id]

        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "timestamp": row[0],
                "sequence": row[1],
                "payload": json.loads(row[2]),
            }
            for row in rows
        ]

    async def store_command(self, command: dict) -> None:
        """Store a command record."""
        if not self._db:
            await self.initialize()

        await self._db.execute(
            """
            INSERT INTO commands
            (command_id, vehicle_id, command_type, params, sent_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                command["command_id"],
                command["vehicle_id"],
                command["command"],
                json.dumps(command.get("params", {})),
                datetime.now(timezone.utc).isoformat(),
            )
        )
        await self._db.commit()

    async def update_command_status(
        self,
        command_id: str,
        status: str,
        completed: bool = False,
    ) -> None:
        """Update command status."""
        if not self._db:
            return

        now = datetime.now(timezone.utc).isoformat()

        if completed:
            await self._db.execute(
                "UPDATE commands SET status = ?, completed_at = ? WHERE command_id = ?",
                (status, now, command_id)
            )
        else:
            await self._db.execute(
                "UPDATE commands SET status = ?, acked_at = ? WHERE command_id = ?",
                (status, now, command_id)
            )
        await self._db.commit()

    async def get_statistics(self, vehicle_id: str) -> dict:
        """Get telemetry statistics for a vehicle."""
        if not self._db:
            await self.initialize()

        async with self._db.execute(
            """
            SELECT
                COUNT(*) as total_records,
                MIN(timestamp) as first_record,
                MAX(timestamp) as last_record
            FROM telemetry WHERE vehicle_id = ?
            """,
            (vehicle_id,)
        ) as cursor:
            row = await cursor.fetchone()

        return {
            "vehicle_id": vehicle_id,
            "total_records": row[0] if row else 0,
            "first_record_timestamp": row[1] if row else None,
            "last_record_timestamp": row[2] if row else None,
        }


# Global singleton
_telemetry_store: Optional[TelemetryStore] = None


def get_telemetry_store() -> TelemetryStore:
    """Get the global telemetry store instance."""
    global _telemetry_store
    if _telemetry_store is None:
        _telemetry_store = TelemetryStore()
    return _telemetry_store
