"""
Armazena em memória a última leitura de IQS para cada símbolo/timeframe
monitorado — inclusive as descartadas, que hoje não deixam nenhum rastro no
banco de dados (só sinais PREPARANDO/CONFIRMADO são persistidos).

Isso dá visibilidade total ao usuário: "o motor rodou e decidiu não
confirmar" é uma informação tão importante quanto um sinal confirmado.

É um singleton em memória (não em banco) porque é informação transitória de
diagnóstico — não precisa sobreviver a um restart do container, e evita
poluir o schema/migrations do banco com uma tabela só para isso.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


@dataclass
class ScanRecord:
    symbol: str
    timeframe: str
    direction: str  # BUY | SELL | NEUTRAL
    status: str  # CONFIRMADO | PREPARANDO | DESCARTADO | SEM_DADOS | LIMITE_ATINGIDO
    iqs_score: float
    reason: str
    scanned_at: datetime
    current_price: Optional[float] = None
    breakdown: Optional[dict] = None


class ScanStateService:
    """Guarda a última leitura de cada (symbol, timeframe) já escaneado."""

    def __init__(self):
        self._records: Dict[Tuple[str, str], ScanRecord] = {}
        self._lock = asyncio.Lock()

    async def record(self, record: ScanRecord) -> None:
        async with self._lock:
            self._records[(record.symbol, record.timeframe)] = record

    async def get_all(self) -> List[ScanRecord]:
        async with self._lock:
            records = list(self._records.values())
        records.sort(key=lambda r: r.iqs_score, reverse=True)
        return records

    async def get(self, symbol: str, timeframe: str) -> Optional[ScanRecord]:
        async with self._lock:
            return self._records.get((symbol, timeframe))


scan_state_service = ScanStateService()
