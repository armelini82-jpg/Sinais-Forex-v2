from datetime import datetime, timedelta, timezone

import pytest

from app.services.backtest_engine import BacktestEngine
from app.services.market_data_service import SimulatedMarketDataProvider


class TestBacktestEngine:
    def setup_method(self):
        self.provider = SimulatedMarketDataProvider()
        self.engine = BacktestEngine(market_data_provider=self.provider)

    @pytest.mark.asyncio
    async def test_run_returns_result_with_expected_shape(self):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=10)

        result = await self.engine.run("EURUSD", "M15", start, end, initial_capital=10_000)

        assert result.symbol == "EURUSD"
        assert result.timeframe == "M15"
        assert result.initial_capital == 10_000
        assert result.signals_evaluated >= 0
        assert result.total_operations == len(result.trades)
        assert result.capital_curve[0] == pytest.approx(10_000, abs=0.01)

    @pytest.mark.asyncio
    async def test_run_is_deterministic_for_same_period(self):
        end = datetime(2026, 1, 10, tzinfo=timezone.utc)
        start = end - timedelta(days=5)

        result_a = await self.engine.run("EURUSD", "M15", start, end)
        result_b = await self.engine.run("EURUSD", "M15", start, end)

        assert result_a.signals_evaluated == result_b.signals_evaluated
        assert result_a.total_operations == result_b.total_operations
        assert result_a.net_result == result_b.net_result

    @pytest.mark.asyncio
    async def test_trades_do_not_overlap_in_time(self):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=15)

        result = await self.engine.run("GBPUSD", "M15", start, end)

        for prev, curr in zip(result.trades, result.trades[1:]):
            assert curr.opened_at >= prev.closed_at

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_empty_result(self):
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=1)  # período curto demais para 220 candles

        result = await self.engine.run("EURUSD", "M15", start, end)

        assert result.total_operations == 0
        assert result.final_capital == result.initial_capital

    @pytest.mark.asyncio
    async def test_unsupported_symbol_raises(self):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=5)

        with pytest.raises(ValueError):
            await self.engine.run("BTCUSD", "M15", start, end)
