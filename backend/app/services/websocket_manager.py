"""
Gerenciador de conexões WebSocket. Responsável por manter a lista de clientes
conectados ao dashboard e fazer broadcast de sinais/operações/estatísticas em
tempo real, sem necessidade de refresh da página.
"""
import asyncio
import json
from typing import Any, Dict, List

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self):
        self._active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._active_connections.append(websocket)
        logger.info("Cliente WebSocket conectado. Total: %d", len(self._active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._active_connections:
                self._active_connections.remove(websocket)
        logger.info("Cliente WebSocket desconectado. Total: %d", len(self._active_connections))

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        message = json.dumps(
            {"event": event_type, "data": payload}, default=str, ensure_ascii=False
        )
        stale_connections: List[WebSocket] = []

        async with self._lock:
            connections = list(self._active_connections)

        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception:
                stale_connections.append(connection)

        if stale_connections:
            async with self._lock:
                for conn in stale_connections:
                    if conn in self._active_connections:
                        self._active_connections.remove(conn)


# Instância única compartilhada por toda a aplicação
connection_manager = ConnectionManager()
