"""WebSocket real-time event streaming.

Auth uses short-lived single-use tickets (not long-lived JWTs in query params).
Tickets are obtained via POST /api/v1/auth/ws-ticket, valid for 30 seconds.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.api.auth import _ws_tickets

router = APIRouter()
logger = logging.getLogger("sentryflow.ws")

_connected: set[WebSocket] = set()


async def authenticate_ws(ws: WebSocket) -> str | None:
    ticket = ws.query_params.get("ticket")
    if not ticket:
        return None

    import time
    ticket_data = _ws_tickets.pop(ticket, None)
    if not ticket_data:
        return None
    if time.time() > ticket_data["expires_at"]:
        return None

    return ticket_data["user_id"]


@router.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    user_id = await authenticate_ws(ws)
    if not user_id:
        await ws.close(code=4001, reason="Invalid or expired ticket")
        return

    await ws.accept()
    _connected.add(ws)
    logger.info(f"WebSocket connected: user={user_id}")

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        _connected.discard(ws)
        logger.info(f"WebSocket disconnected: user={user_id}")


async def broadcast_event(event: dict[str, Any]) -> None:
    if not _connected:
        return
    message = json.dumps(event)
    disconnected = set()
    for ws in _connected:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    _connected.difference_update(disconnected)
