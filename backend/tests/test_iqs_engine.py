from app.services.indicator_service import IndicatorService
from app.services.iqs_engine import (
    WEIGHT_ADX,
    WEIGHT_LIQUIDITY,
    WEIGHT_MOMENTUM,
    WEIGHT_PULLBACK,
    WEIGHT_SESSION,
    WEIGHT_TREND,
    WEIGHT_VOLATILITY,
    IQSEngine,
)


class TestIQSEngine:
    def setup_method(self):
        self.indicator_service = IndicatorService()
        self.iqs_engine = IQSEngine()

    def test_weights_sum_to_100(self):
        total_weight = (
            WEIGHT_TREND
            + WEIGHT_MOMENTUM
            + WEIGHT_PULLBACK
            + WEIGHT_VOLATILITY
            + WEIGHT_ADX
            + WEIGHT_LIQUIDITY
            + WEIGHT_SESSION
        )
        assert total_weight == 100

    def test_strong_uptrend_generates_buy_direction(self, trending_candles):
        indicators = self.indicator_service.calculate("EURUSD", "M15", trending_candles)
        result = self.iqs_engine.evaluate("EURUSD", trending_candles, indicators)
        assert result.direction == "BUY"

    def test_score_breakdown_never_exceeds_individual_weights(self, trending_candles):
        indicators = self.indicator_service.calculate("EURUSD", "M15", trending_candles)
        result = self.iqs_engine.evaluate("EURUSD", trending_candles, indicators)

        assert 0 <= result.breakdown.trend <= WEIGHT_TREND
        assert 0 <= result.breakdown.momentum <= WEIGHT_MOMENTUM
        assert 0 <= result.breakdown.pullback <= WEIGHT_PULLBACK
        assert 0 <= result.breakdown.volatility <= WEIGHT_VOLATILITY
        assert 0 <= result.breakdown.adx <= WEIGHT_ADX
        assert 0 <= result.breakdown.liquidity <= WEIGHT_LIQUIDITY
        assert 0 <= result.breakdown.session <= WEIGHT_SESSION

    def test_total_score_never_exceeds_100(self, trending_candles):
        indicators = self.indicator_service.calculate("EURUSD", "M15", trending_candles)
        result = self.iqs_engine.evaluate("EURUSD", trending_candles, indicators)
        assert 0 <= result.total_score <= 100

    def test_flat_market_yields_neutral_direction_and_low_score(self, flat_candles):
        indicators = self.indicator_service.calculate("EURUSD", "M15", flat_candles)
        result = self.iqs_engine.evaluate("EURUSD", flat_candles, indicators)
        assert result.direction == "NEUTRAL"
        assert result.status == "DESCARTADO"

    def test_classification_thresholds(self):
        assert self.iqs_engine._classify(95) == "CONFIRMADO"
        assert self.iqs_engine._classify(90) == "CONFIRMADO"
        assert self.iqs_engine._classify(85) == "PREPARANDO"
        assert self.iqs_engine._classify(80) == "PREPARANDO"
        assert self.iqs_engine._classify(79.9) == "DESCARTADO"

    def test_explain_neutral_direction(self):
        from app.services.iqs_engine import IQSBreakdownDTO

        breakdown = IQSBreakdownDTO(
            trend=0, momentum=0, pullback=0, volatility=0, adx=0, liquidity=0, session=0
        )
        reason = self.iqs_engine.explain("NEUTRAL", breakdown)
        assert "tendência" in reason.lower()

    def test_explain_identifies_weakest_component(self):
        from app.services.iqs_engine import IQSBreakdownDTO

        breakdown = IQSBreakdownDTO(
            trend=20, momentum=12, pullback=15, volatility=12, adx=1, liquidity=8, session=4
        )
        reason = self.iqs_engine.explain("BUY", breakdown)
        assert "adx" in reason.lower() or "lateral" in reason.lower()

    def test_explain_returns_nonempty_for_all_discard_scenarios(self, flat_candles):
        indicators = self.indicator_service.calculate("EURUSD", "M15", flat_candles)
        result = self.iqs_engine.evaluate("EURUSD", flat_candles, indicators)
        reason = self.iqs_engine.explain(result.direction, result.breakdown)
        assert isinstance(reason, str) and len(reason) > 0
