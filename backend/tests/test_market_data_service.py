import pytest

from app.services.market_data_service import SimulatedMarketDataProvider


class TestSimulatedMarketDataProvider:
    def setup_method(self):
        self.provider = SimulatedMarketDataProvider()

    @pytest.mark.asyncio
    async def test_returns_requested_number_of_candles(self):
        candles = await self.provider.get_latest_candles("EURUSD", "M15", 220)
        assert len(candles) == 220

    @pytest.mark.asyncio
    async def test_candles_are_chronologically_ordered(self):
        candles = await self.provider.get_latest_candles("EURUSD", "M15", 50)
        times = [c.open_time for c in candles]
        assert times == sorted(times)

    @pytest.mark.asyncio
    async def test_unsupported_symbol_raises(self):
        with pytest.raises(ValueError):
            await self.provider.get_latest_candles("BTCUSD", "M15", 50)

    @pytest.mark.asyncio
    async def test_current_price_is_positive(self):
        price = await self.provider.get_current_price("EURUSD")
        assert price > 0
