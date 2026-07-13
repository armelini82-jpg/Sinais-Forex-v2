from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_signal_engine, get_signal_repository
from app.core.config import settings
from app.core.exceptions import EntityNotFoundError
from app.models.signal import SignalStatus
from app.repositories.signal_repository import SignalRepository
from app.schemas.signal import SignalResponseDTO
from app.services.scan_state_service import scan_state_service
from app.services.signal_engine import SignalEngine

router = APIRouter(prefix="/signals", tags=["Sinais"])


@router.get("", response_model=List[SignalResponseDTO])
async def list_signals(
    status_filter: Optional[SignalStatus] = Query(default=None, alias="status"),
    signal_repo: SignalRepository = Depends(get_signal_repository),
):
    """Lista sinais ativos (PREPARANDO/CONFIRMADO) ou filtrados por status."""
    signals = await signal_repo.list_active(status=status_filter)
    return signals


@router.get("/latest-scan")
async def latest_scan():
    """
    Retorna a última leitura de IQS para CADA par/timeframe monitorado,
    inclusive os descartados (que nunca são persistidos como Signal no
    banco). Dá visibilidade total sobre o que o motor decidiu e por quê,
    em vez de silêncio quando nenhum sinal qualifica.
    """
    records = await scan_state_service.get_all()
    return records


@router.get("/{signal_id}", response_model=SignalResponseDTO)
async def get_signal(signal_id: int, signal_repo: SignalRepository = Depends(get_signal_repository)):
    """Retorna um sinal específico por ID."""
    signal = await signal_repo.get_by_id(signal_id)
    if not signal:
        raise EntityNotFoundError("Sinal", str(signal_id))
    return signal


@router.post("/scan", response_model=List[SignalResponseDTO])
async def trigger_scan(
    timeframe: str = Query(default="M15"),
    signal_engine: SignalEngine = Depends(get_signal_engine),
):
    """
    Dispara manualmente uma varredura (scan) de todos os pares monitorados
    no timeframe informado. Normalmente isto é feito automaticamente pelo
    scheduler, mas este endpoint permite acionar sob demanda (ex.: testes).
    """
    signals = await signal_engine.analyze_all(settings.symbols_list, timeframe)
    return signals
