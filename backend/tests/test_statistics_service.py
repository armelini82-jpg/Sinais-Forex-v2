from datetime import datetime, timedelta, timezone

from app.models.operation import Operation, OperationResult
from app.models.signal import SignalDirection
from app.services.statistics_service import StatisticsService


def _make_operation(profit_loss: float, result: OperationResult, days_ago: int = 0) -> Operation:
    now = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return Operation(
        signal_id=1,
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.1000,
        stop_loss=1.0980,
        take_profit=1.1040,
        exit_price=1.1040 if result == OperationResult.WIN else 1.0980,
        lot_size=0.5,
        risk_amount=100.0,
        profit_loss=profit_loss,
        result=result,
        opened_at=now,
        closed_at=now,
    )


class TestStatisticsService:
    def setup_method(self):
        self.service = StatisticsService()

    def test_empty_operations_returns_zeroed_summary(self):
        summary = self.service.compute([])
        assert summary.total_operations == 0
        assert summary.win_rate == 0.0

    def test_win_rate_calculation(self):
        operations = [
            _make_operation(200, OperationResult.WIN),
            _make_operation(-100, OperationResult.LOSS),
            _make_operation(200, OperationResult.WIN),
            _make_operation(-100, OperationResult.LOSS),
        ]
        summary = self.service.compute(operations)
        assert summary.total_operations == 4
        assert summary.win_rate == 50.0

    def test_profit_factor_calculation(self):
        operations = [
            _make_operation(300, OperationResult.WIN),
            _make_operation(-100, OperationResult.LOSS),
        ]
        summary = self.service.compute(operations)
        assert summary.profit_factor == 3.0

    def test_net_result_is_sum_of_profit_loss(self):
        operations = [
            _make_operation(300, OperationResult.WIN),
            _make_operation(-100, OperationResult.LOSS),
            _make_operation(150, OperationResult.WIN),
        ]
        summary = self.service.compute(operations)
        assert summary.net_result == 350.0

    def test_max_drawdown_detects_peak_to_trough(self):
        operations = [
            _make_operation(500, OperationResult.WIN, days_ago=4),
            _make_operation(-200, OperationResult.LOSS, days_ago=3),
            _make_operation(-200, OperationResult.LOSS, days_ago=2),
            _make_operation(100, OperationResult.WIN, days_ago=1),
        ]
        summary = self.service.compute(operations)
        # Pico em 500, vale em 100 -> drawdown de 400
        assert summary.max_drawdown == 400.0
