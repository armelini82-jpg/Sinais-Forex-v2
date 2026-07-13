import pytest

from app.core.exceptions import InsufficientDataError
from app.services.indicator_service import IndicatorService


class TestIndicatorService:
    def setup_method(self):
        self.service = IndicatorService()

    def test_calculates_all_indicators_for_trending_series(self, trending_candles):
        result = self.service.calculate("EURUSD", "M15", trending_candles)

        assert result.ema_9 is not None
        assert result.ema_21 is not None
        assert result.ema_200 is not None
        assert result.rsi_14 is not None
        assert result.atr_14 is not None
        assert result.adx_14 is not None
        assert result.macd is not None
        assert result.bb_upper is not None
        assert result.vwap is not None

    def test_uptrend_produces_ema9_above_ema21_above_ema200(self, trending_candles):
        result = self.service.calculate("EURUSD", "M15", trending_candles)
        assert result.ema_9 > result.ema_21 > result.ema_200

    def test_uptrend_rsi_above_neutral(self, trending_candles):
        result = self.service.calculate("EURUSD", "M15", trending_candles)
        assert result.rsi_14 > 50

    def test_raises_when_insufficient_candles(self, trending_candles):
        short_series = trending_candles[:50]
        with pytest.raises(InsufficientDataError):
            self.service.calculate("EURUSD", "M15", short_series)

    def test_flat_market_has_near_zero_atr(self, flat_candles):
        result = self.service.calculate("EURUSD", "M15", flat_candles)
        assert result.atr_14 < 0.0001
