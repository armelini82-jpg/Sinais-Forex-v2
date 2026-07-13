"""
Serviço de operações "semi-manuais": o usuário confirma que entrou em um
sinal (informando lote e, opcionalmente, preço de entrada real) — a partir
daí, o sistema monitora o preço real via o MarketDataProvider e fecha a
operação sozinho quando o preço atinge o Take Profit ou o Stop Loss.

Isto evita duas armadilhas:
  - Não requer acesso à conta/corretora do usuário (diferente de uma
    integração real via API MT4/MT5).
  - Não é uma simulação cega de "todo sinal seria operado" — só entra no
    cálculo de estatísticas o que o usuário de fato confirmou ter operado.
"""
from datetime import datetime, timezone
from typing import Optional

from app.core.exceptions import EntityNotFoundError
from app.core.logging import get_logger
from app.interfaces.market_data_interface import IMarketDataProvider
from app.interfaces.repository_interfaces import IOperationRepository, ISignalRepository
from app.models.operation import Operation, OperationResult
from app.models.signal import SignalDirection
from app.schemas.operation import OperationCreateDTO

logger = get_logger(__name__)

LOT_SIZE_UNITS = 100_000  # 1.0 lote padrão = 100.000 unidades da moeda base


class OperationService:
    """Abre operações a partir de sinais confirmados pelo usuário."""

    def __init__(self, operation_repo: IOperationRepository, signal_repo: ISignalRepository):
        self._operation_repo = operation_repo
        self._signal_repo = signal_repo

    async def open_from_signal(self, data: OperationCreateDTO) -> Operation:
        signal = await self._signal_repo.get_by_id(data.signal_id)
        if signal is None:
            raise EntityNotFoundError("Sinal", str(data.signal_id))

        entry_price = data.entry_price or signal.entry_price
        stop_distance = abs(entry_price - signal.stop_loss)
        risk_amount = round(data.lot_size * LOT_SIZE_UNITS * stop_distance, 2)

        operation = Operation(
            signal_id=signal.id,
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            lot_size=data.lot_size,
            risk_amount=risk_amount,
            result=OperationResult.OPEN,
            opened_at=datetime.now(timezone.utc),
        )
        return await self._operation_repo.create(operation)


class OperationMonitorService:
    """
    Roda periodicamente (via scheduler) verificando operações OPEN contra o
    preço real de mercado, fechando-as automaticamente quando o preço
    atinge o Take Profit ou o Stop Loss.
    """

    def __init__(self, market_data_provider: IMarketDataProvider, operation_repo: IOperationRepository):
        self._market_data = market_data_provider
        self._operation_repo = operation_repo

    async def check_open_operations(self) -> int:
        """Retorna quantas operações foram fechadas nesta checagem."""
        open_operations = await self._operation_repo.list_open()
        closed_count = 0

        for operation in open_operations:
            try:
                current_price = await self._market_data.get_current_price(operation.symbol)
            except Exception:
                logger.exception("Falha ao buscar preço atual de %s para monitorar operação #%s",
                                  operation.symbol, operation.id)
                continue

            outcome = self._evaluate(operation, current_price)
            if outcome is None:
                continue

            result, exit_price = outcome
            profit_loss = self._calculate_profit_loss(operation, exit_price)

            await self._operation_repo.update_result(
                operation.id,
                result=result,
                exit_price=exit_price,
                profit_loss=profit_loss,
                closed_at=datetime.now(timezone.utc),
            )
            closed_count += 1
            logger.info(
                "Operação #%s (%s) fechada automaticamente: %s @ %.5f (P/L=%.2f)",
                operation.id, operation.symbol, result.value, exit_price, profit_loss,
            )

        return closed_count

    @staticmethod
    def _evaluate(operation: Operation, current_price: float) -> Optional[tuple]:
        if operation.direction == SignalDirection.BUY:
            if current_price >= operation.take_profit:
                return OperationResult.WIN, operation.take_profit
            if current_price <= operation.stop_loss:
                return OperationResult.LOSS, operation.stop_loss
        else:
            if current_price <= operation.take_profit:
                return OperationResult.WIN, operation.take_profit
            if current_price >= operation.stop_loss:
                return OperationResult.LOSS, operation.stop_loss
        return None

    @staticmethod
    def _calculate_profit_loss(operation: Operation, exit_price: float) -> float:
        distance = exit_price - operation.entry_price
        if operation.direction == SignalDirection.SELL:
            distance = -distance
        return round(distance * operation.lot_size * LOT_SIZE_UNITS, 2)
