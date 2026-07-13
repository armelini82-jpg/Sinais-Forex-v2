"""
Motor de estatísticas. Calcula Win Rate, Profit Factor, Payoff, Expectancy,
Drawdown e Curva de Capital a partir do histórico de operações fechadas.
"""
from dataclasses import dataclass, field
from typing import List, Sequence

from app.models.operation import Operation, OperationResult


@dataclass
class StatisticsSummary:
    total_operations: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    payoff: float = 0.0
    expectancy: float = 0.0
    max_drawdown: float = 0.0
    net_result: float = 0.0
    capital_curve: List[float] = field(default_factory=list)


class StatisticsService:
    """Calcula métricas de performance a partir de operações fechadas."""

    def compute(self, operations: Sequence[Operation]) -> StatisticsSummary:
        closed = [
            op
            for op in operations
            if op.result in (OperationResult.WIN, OperationResult.LOSS, OperationResult.BREAKEVEN)
            and op.profit_loss is not None
        ]

        if not closed:
            return StatisticsSummary()

        closed = sorted(closed, key=lambda o: o.opened_at)

        wins = [op for op in closed if op.result == OperationResult.WIN]
        losses = [op for op in closed if op.result == OperationResult.LOSS]

        total = len(closed)
        win_count = len(wins)
        loss_count = len(losses)

        gross_profit = sum(op.profit_loss for op in wins)
        gross_loss = abs(sum(op.profit_loss for op in losses))

        win_rate = (win_count / total * 100) if total else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float(gross_profit > 0)

        avg_win = (gross_profit / win_count) if win_count else 0.0
        avg_loss = (gross_loss / loss_count) if loss_count else 0.0
        payoff = (avg_win / avg_loss) if avg_loss > 0 else float(avg_win > 0)

        win_probability = win_count / total if total else 0.0
        loss_probability = loss_count / total if total else 0.0
        expectancy = (win_probability * avg_win) - (loss_probability * avg_loss)

        net_result = sum(op.profit_loss for op in closed)

        capital_curve = self._build_capital_curve(closed)
        max_drawdown = self._max_drawdown(capital_curve)

        return StatisticsSummary(
            total_operations=total,
            wins=win_count,
            losses=loss_count,
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            payoff=round(payoff, 2),
            expectancy=round(expectancy, 2),
            max_drawdown=round(max_drawdown, 2),
            net_result=round(net_result, 2),
            capital_curve=capital_curve,
        )

    @staticmethod
    def _build_capital_curve(closed_operations: Sequence[Operation]) -> List[float]:
        curve = [0.0]
        cumulative = 0.0
        for op in closed_operations:
            cumulative += op.profit_loss or 0.0
            curve.append(round(cumulative, 2))
        return curve

    @staticmethod
    def _max_drawdown(capital_curve: List[float]) -> float:
        if not capital_curve:
            return 0.0
        peak = capital_curve[0]
        max_dd = 0.0
        for value in capital_curve:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_dd:
                max_dd = drawdown
        return max_dd
