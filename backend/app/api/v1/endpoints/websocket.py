from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.services.websocket_manager import connection_manager

logger = get_logger(__name__)
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """
    Canal WebSocket consumido pelo dashboard. Envia eventos em tempo real:
    `new_signal`, `operation_update`, `statistics_update`.
    O cliente não precisa enviar nada; a conexão é mantida aberta apenas
    para receber broadcasts do servidor.
    """
    await connection_manager.connect(websocket)
    try:
        while True:
            # Mantém a conexão viva; ignora mensagens recebidas do cliente.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("Conexão WebSocket encerrada com erro: %s", exc)
        await connection_manager.disconnect(websocket)
