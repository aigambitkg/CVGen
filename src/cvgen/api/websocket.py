"""CVGen WebSocket Server — Real-time event broadcasting"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class EventBroadcaster:
    """Manages WebSocket connections and broadcasts events to all connected clients."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.event_queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, websocket: WebSocket) -> None:
        """Register a new client connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a client connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"WebSocket client disconnected. Total clients: {len(self.active_connections)}"
            )

    async def publish(self, event_type: str, data: Any) -> None:
        """Publish an event to all connected clients."""
        message = {
            "type": event_type,
            "data": data,
        }
        await self.event_queue.put(message)

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

    async def broadcast_job_status(self, job_id: str, status: str, progress: int = 0) -> None:
        """Broadcast job status change."""
        await self.publish(
            "job_status_change",
            {
                "job_id": job_id,
                "status": status,
                "progress": progress,
            },
        )

    async def broadcast_backend_status(self, backend_name: str, available: bool) -> None:
        """Broadcast backend availability change."""
        await self.publish(
            "backend_status_change",
            {
                "backend": backend_name,
                "available": available,
            },
        )

    async def broadcast_agent_progress(self, agent_id: str, progress: str) -> None:
        """Broadcast agent execution progress."""
        await self.publish(
            "agent_progress",
            {
                "agent_id": agent_id,
                "progress": progress,
            },
        )

    async def broadcast_system_metrics(self, metrics: dict) -> None:
        """Broadcast system metrics."""
        await self.publish("system_metrics", metrics)

    async def event_loop(self) -> None:
        """Process events from queue and broadcast to all clients."""
        while True:
            try:
                message = await asyncio.wait_for(self.event_queue.get(), timeout=10)
                await self.broadcast(message)
            except asyncio.TimeoutError:
                # Send heartbeat
                if self.active_connections:
                    await self.broadcast({"type": "heartbeat"})
            except Exception as e:
                logger.error(f"Error in event loop: {e}")


# Global broadcaster instance
broadcaster = EventBroadcaster()


@router.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time event streaming."""
    await broadcaster.connect(websocket)

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Could handle client messages here if needed
                logger.debug(f"Received from client: {message}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
    except WebSocketDisconnect:
        await broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await broadcaster.disconnect(websocket)
        except Exception:
            pass
