from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import EntityNotFoundError
from app.models.operation import Operation, OperationResult
from app.models.signal import Signal, SignalDirection, SignalStatus
from app.schemas.operation import OperationCreateDTO
from app.services.operation_service import OperationMonitorService, OperationService


def _make_signal(**overrides) -> Signal:
    defaults = dict(
        id=1,
        symbol="EURUSD",
        timeframe="M15",
        direction=SignalDirection.BUY,
        status=SignalStatus.CONFIRMADO,
        iqs_score=92.0,
        probability=88.0,
        entry_price=1.1000,
        stop_loss=1.0980,
        take_profit=1.1040,
        risk_reward=2.0,
        atr=0.0006,
        adx=28.0,
        rsi=65.0,
        expected_duration_minutes=90,
        generated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Signal(**defaults)


def _make_operation(**overrides) -> Operation:
    defaults = dict(
        id=1,
        signal_id=1,
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.1000,
        stop_loss=1.0980,
        take_profit=1.1040,
        lot_size=0.1,
        risk_amount=20.0,
        result=OperationResult.OPEN,
        opened_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Operation(**defaults)


class TestOperationService:
    @pytest.mark.asyncio
    async def test_opens_operation_using_signal_defaults(self):
        signal_repo = AsyncMock()
        signal_repo.get_by_id.return_value = _make_signal()
        operation_repo = AsyncMock()
        operation_repo.create.side_effect = lambda op: op

        service = OperationService(operation_repo, signal_repo)
        result = await service.open_from_signal(
            OperationCreateDTO(signal_id=1, lot_size=0.1)
        )

        assert result.entry_price == 1.1000
        assert result.stop_loss == 1.0980
        assert result.take_profit == 1.1040
        assert result.result == OperationResult.OPEN

    @pytest.mark.asyncio
    async def test_uses_custom_entry_price_when_provided(self):
        signal_repo = AsyncMock()
        signal_repo.get_by_id.return_value = _make_signal()
        operation_repo = AsyncMock()
        operation_repo.create.side_effect = lambda op: op

        service = OperationService(operation_repo, signal_repo)
        result = await service.open_from_signal(
            OperationCreateDTO(signal_id=1, lot_size=0.1, entry_price=1.1005)
        )

        assert result.entry_price == 1.1005

    @pytest.mark.asyncio
    async def test_raises_when_signal_not_found(self):
        signal_repo = AsyncMock()
        signal_repo.get_by_id.return_value = None
        operation_repo = AsyncMock()

        service = OperationService(operation_repo, signal_repo)
        with pytest.raises(EntityNotFoundError):
            await service.open_from_signal(OperationCreateDTO(signal_id=999, lot_size=0.1))


class TestOperationMonitorService:
    @pytest.mark.asyncio
    async def test_closes_buy_operation_on_take_profit(self):
        operation_repo = AsyncMock()
        operation_repo.list_open.return_value = [_make_operation()]
        market_data = AsyncMock()
        market_data.get_current_price.return_value = 1.1050  # acima do TP

        monitor = OperationMonitorService(market_data, operation_repo)
        closed = await monitor.check_open_operations()

        assert closed == 1
        call_kwargs = operation_repo.update_result.call_args.kwargs
        assert call_kwargs["result"] == OperationResult.WIN
        assert call_kwargs["exit_price"] == 1.1040

    @pytest.mark.asyncio
    async def test_closes_buy_operation_on_stop_loss(self):
        operation_repo = AsyncMock()
        operation_repo.list_open.return_value = [_make_operation()]
        market_data = AsyncMock()
        market_data.get_current_price.return_value = 1.0970  # abaixo do SL

        monitor = OperationMonitorService(market_data, operation_repo)
        closed = await monitor.check_open_operations()

        assert closed == 1
        call_kwargs = operation_repo.update_result.call_args.kwargs
        assert call_kwargs["result"] == OperationResult.LOSS
        assert call_kwargs["exit_price"] == 1.0980

    @pytest.mark.asyncio
    async def test_leaves_operation_open_when_price_between_sl_and_tp(self):
        operation_repo = AsyncMock()
        operation_repo.list_open.return_value = [_make_operation()]
        market_data = AsyncMock()
        market_data.get_current_price.return_value = 1.1010  # dentro da faixa

        monitor = OperationMonitorService(market_data, operation_repo)
        closed = await monitor.check_open_operations()

        assert closed == 0
        operation_repo.update_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_sell_operation_closes_on_take_profit(self):
        sell_op = _make_operation(
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1020,
            take_profit=1.0960,
        )
        operation_repo = AsyncMock()
        operation_repo.list_open.return_value = [sell_op]
        market_data = AsyncMock()
        market_data.get_current_price.return_value = 1.0950  # abaixo do TP de venda

        monitor = OperationMonitorService(market_data, operation_repo)
        closed = await monitor.check_open_operations()

        assert closed == 1
        call_kwargs = operation_repo.update_result.call_args.kwargs
        assert call_kwargs["result"] == OperationResult.WIN

    @pytest.mark.asyncio
    async def test_profit_loss_calculation_for_buy_win(self):
        operation = _make_operation(lot_size=1.0)
        pl = OperationMonitorService._calculate_profit_loss(operation, 1.1040)
        # (1.1040 - 1.1000) * 1.0 * 100_000 = 400.0
        assert pl == pytest.approx(400.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_continues_after_price_fetch_failure(self):
        operation_repo = AsyncMock()
        operation_repo.list_open.return_value = [_make_operation()]
        market_data = AsyncMock()
        market_data.get_current_price.side_effect = Exception("API indisponível")

        monitor = OperationMonitorService(market_data, operation_repo)
        closed = await monitor.check_open_operations()

        assert closed == 0
