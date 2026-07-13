from app.core.config import settings
from app.services.risk_management_service import RiskManagementService


class TestRiskManagementService:
    def setup_method(self):
        self.service = RiskManagementService()

    def test_buy_trade_plan_has_stop_below_entry_and_target_above(self, trending_candles):
        plan = self.service.build_trade_plan(direction="BUY", candles=trending_candles, atr=0.0006)
        assert plan.stop_loss < plan.entry_price < plan.take_profit

    def test_sell_trade_plan_has_stop_above_entry_and_target_below(self, trending_candles):
        plan = self.service.build_trade_plan(direction="SELL", candles=trending_candles, atr=0.0006)
        assert plan.take_profit < plan.entry_price < plan.stop_loss

    def test_risk_reward_meets_minimum(self, trending_candles):
        plan = self.service.build_trade_plan(direction="BUY", candles=trending_candles, atr=0.0006)
        assert plan.risk_reward >= settings.MIN_RISK_REWARD - 0.01

    def test_position_size_respects_risk_amount(self, trending_candles):
        plan = self.service.build_trade_plan(
            direction="BUY", candles=trending_candles, atr=0.0006, account_balance=10_000
        )
        expected_risk = 10_000 * (settings.RISK_PER_TRADE_PERCENT / 100)
        assert abs(plan.risk_amount - expected_risk) < 0.01

    def test_lot_size_is_positive(self, trending_candles):
        plan = self.service.build_trade_plan(direction="BUY", candles=trending_candles, atr=0.0006)
        assert plan.lot_size > 0
