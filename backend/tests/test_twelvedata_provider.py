from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.twelvedata_provider import TwelveDataMarketDataProvider


def _mock_response(json_data: dict, status_ok: bool = True) -> MagicMock:
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status = MagicMock() if status_ok else MagicMock(side_effect=Exception("HTTP error"))
    return response


class TestTwelveDataMarketDataProvider:
    def setup_method(self):
        self.provider = TwelveDataMarketDataProvider(api_key="fake-key")

    def teardown_method(self):
        pass

    def test_requires_api_key(self):
        with pytest.raises(ValueError):
            TwelveDataMarketDataProvider(api_key="")

    @pytest.mark.parametrize(
        "symbol,expected",
        [
            ("EURUSD", "EUR/USD"),
            ("XAUUSD", "XAU/USD"),
            ("GBPJPY", "GBP/JPY"),
            ("EUR/USD", "EUR/USD"),
        ],
    )
    def test_symbol_conversion(self, symbol, expected):
        assert self.provider._to_api_symbol(symbol) == expected

    @pytest.mark.asyncio
    async def test_get_latest_candles_parses_and_orders_ascending(self, monkeypatch):
        payload = {
            "status": "ok",
            "values": [
                {"datetime": "2026-01-01 10:00:00", "open": "1.10", "high": "1.11", "low": "1.09", "close": "1.105", "volume": "0"},
                {"datetime": "2026-01-01 11:00:00", "open": "1.105", "high": "1.12", "low": "1.10", "close": "1.115", "volume": "0"},
            ],
        }
        self.provider._client.get = AsyncMock(return_value=_mock_response(payload))

        candles = await self.provider.get_latest_candles("EURUSD", "H1", 10)

        assert len(candles) == 2
        assert candles[0].open_time < candles[1].open_time
        assert candles[-1].close == 1.115

    @pytest.mark.asyncio
    async def test_get_current_price_parses_float(self, monkeypatch):
        self.provider._client.get = AsyncMock(return_value=_mock_response({"price": "1.08765"}))
        price = await self.provider.get_current_price("EURUSD")
        assert price == 1.08765

    @pytest.mark.asyncio
    async def test_error_status_raises_value_error(self, monkeypatch):
        self.provider._client.get = AsyncMock(
            return_value=_mock_response({"status": "error", "message": "invalid symbol"})
        )
        with pytest.raises(ValueError):
            await self.provider.get_latest_candles("EURUSD", "H1", 10)

    def test_is_market_open_uses_weekend_heuristic(self):
        # Apenas garante que o método executa e retorna um bool, sem
        # depender do dia da semana em que os testes rodam.
        result = self.provider.is_market_open("EURUSD")
        assert isinstance(result, bool)
