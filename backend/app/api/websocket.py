"""
WebSocket endpoint for real-time alert broadcasting.
Maintains a global registry of connected clients.
"""
import logging
import json
from typing import Set, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

# Global registry of connected WebSocket clients
_connected_clients: Set[WebSocket] = set()


def get_connected_clients() -> Set[WebSocket]:
    """Return the set of currently connected WebSocket clients."""
    return _connected_clients


async def broadcast(message: Dict[str, Any]) -> None:
    """
    Broadcast a message to all connected WebSocket clients.
    Automatically removes disconnected clients.
    """
    if not _connected_clients:
        return

    payload = json.dumps(message, default=str)
    disconnected = set()

    for ws in _connected_clients.copy():
        try:
            await ws.send_text(payload)
        except Exception as e:
            logger.debug(f"WS client disconnected during broadcast: {e}")
            disconnected.add(ws)

    for ws in disconnected:
        _connected_clients.discard(ws)


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time deforestation alerts.
    Clients connect here and receive JSON messages on:
    - New alerts (type: "alert")
    - Zone health updates (type: "health_update")
    - Scheduler heartbeats (type: "heartbeat")
    """
    await websocket.accept()
    _connected_clients.add(websocket)
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(f"WebSocket client connected: {client_host}. Total: {len(_connected_clients)}")

    try:
        # Send connection acknowledgement
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Foresence real-time alerts",
            "client_count": len(_connected_clients),
        })

        # Keep connection alive, handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Handle ping/keepalive from client
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_host}")
    except Exception as e:
        logger.error(f"WebSocket error for {client_host}: {e}")
    finally:
        _connected_clients.discard(websocket)
        logger.info(f"Active WebSocket clients: {len(_connected_clients)}")
