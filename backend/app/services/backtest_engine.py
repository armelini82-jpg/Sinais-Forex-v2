"""
Motor de Backtest.

Roda o MESMO pipeline de decisão do sistema ao vivo (IndicatorService +
IQSEngine + RiskManagementService) sobre candles históricas, com uma janela
deslizante — a cada candle, o motor só "enxerga" os dados até aquele ponto
(sem lookahead bias). Quando um sinal CONFIRMADO surge, o motor avança pelas
candles seguintes para descobrir se o Take Profit ou o Stop Loss seria
atingido primeiro, com base em high/low reais.

Isto permite responder: "se eu tivesse seguido todo sinal confirmado do
Forex Radar AI no par X, no timeframe Y, entre as datas A e B, qual teria
sido o resultado?" — sem depender de operações ao vivo acontecerem.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.interfaces.market_data_interface import IMarketDataProvider
from app.models.operation import Operation, OperationResult
from app.models.signal import SignalDirection
from app.schemas.candle import CandleDTO
from app.services.indicator_service import IndicatorService
from app.services.iqs_engine import IQSEngine
from app.services.risk_management_service import RiskManagementService
from app.services.statistics_service import StatisticsService

CANDLES_LOOKBACK = 220
LOT_SIZE_UNITS = 100_000
MAX_HOLD_CANDLES = 500  # evita operações "presas" abertas indefinidamente no backtest


@dataclass
class BacktestTrade:
    symbol: str
    timeframe: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_price: float
    lot_size: float
    profit_loss: float
    result: str  # WIN | LOSS
    iqs_score: float
    opened_at: datetime
    closed_at: datetime


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    signals_evaluated: int
    total_operations: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    payoff: float
    expectancy: float
    max_drawdown: float
    net_result: float
    capital_curve: List[float] = field(default_factory=list)
    trades: List[BacktestTrade] = field(default_factory=list)


class BacktestEngine:
    """Motor de backtest orientado a eventos, reaproveitando os services de produção."""

    def __init__(
        self,
        market_data_provider: IMarketDataProvider,
        indicator_service: Optional[IndicatorService] = None,
        iqs_engine: Optional[IQSEngine] = None,
        risk_service: Optional[RiskManagementService] = None,
        statistics_service: Optional[StatisticsService] = None,
    ):
        self._market_data = market_data_provider
        self._indicator_service = indicator_service or IndicatorService()
        self._iqs_engine = iqs_engine or IQSEngine()
        self._risk_service = risk_service or RiskManagementService()
        self._statistics_service = statistics_service or StatisticsService()

    async def run(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        initial_capital: float = 10_000.0,
        min_iqs_signal: int = 90,
    ) -> BacktestResult:
        buffer_minutes = self._lookback_buffer_minutes(timeframe)
        fetch_start = start - timedelta(minutes=buffer_minutes)

        candles = await self._market_data.get_historical_candles(symbol, timeframe, fetch_start, end)

        if len(candles) < CANDLES_LOOKBACK + 1:
            return BacktestResult(
                symbol=symbol, timeframe=timeframe, start_date=start, end_date=end,
                initial_capital=initial_capital, final_capital=initial_capital,
                signals_evaluated=0, total_operations=0, wins=0, losses=0,
                win_rate=0.0, profit_factor=0.0, payoff=0.0, expectancy=0.0,
                max_drawdown=0.0, net_result=0.0,
            )

        running_capital = initial_capital
        trades: List[BacktestTrade] = []
        signals_evaluated = 0

        i = CANDLES_LOOKBACK
        while i < len(candles) - 1:
            window = candles[i - CANDLES_LOOKBACK : i + 1]
            current_candle = window[-1]

            if current_candle.open_time < start:
                i += 1
                continue

            try:
                indicators = self._indicator_service.calculate(symbol, timeframe, window)
            except Exception:
                i += 1
                continue

            iqs_result = self._iqs_engine.evaluate(symbol, window, indicators)
            signals_evaluated += 1

            if iqs_result.direction == "NEUTRAL" or iqs_result.total_score < min_iqs_signal:
                i += 1
                continue

            trade_plan = self._risk_service.build_trade_plan(
                direction=iqs_result.direction,
                candles=window,
                atr=indicators.atr_14 or 0.0001,
                account_balance=running_capital,
            )

            outcome = self._simulate_forward(candles, i + 1, iqs_result.direction, trade_plan)
            if outcome is None:
                i += 1
                continue

            exit_price, exit_index, result = outcome
            profit_loss = self._profit_loss(
                iqs_result.direction, trade_plan.entry_price, exit_price, trade_plan.lot_size
            )
            running_capital += profit_loss

            trades.append(
                BacktestTrade(
                    symbol=symbol,
                    timeframe=timeframe,
                    direction=iqs_result.direction,
                    entry_price=trade_plan.entry_price,
                    stop_loss=trade_plan.stop_loss,
                    take_profit=trade_plan.take_profit,
                    exit_price=exit_price,
                    lot_size=trade_plan.lot_size,
                    profit_loss=profit_loss,
                    result=result,
                    iqs_score=iqs_result.total_score,
                    opened_at=current_candle.open_time,
                    closed_at=candles[exit_index].open_time,
                )
            )

            i = exit_index + 1  # não sobrepõe operações no mesmo par/timeframe

        return self._build_result(
            symbol, timeframe, start, end, initial_capital, running_capital,
            signals_evaluated, trades,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _lookback_buffer_minutes(timeframe: str) -> int:
        per_candle = {"M1": 1, "M5": 5, "M15": 15, "H1": 60}.get(timeframe, 15)
        # +30% de folga para cobrir fins de semana/feriados sem candle
        return int(per_candle * (CANDLES_LOOKBACK + 20) * 1.3)

    @staticmethod
    def _simulate_forward(
        candles: List[CandleDTO], start_index: int, direction: str, trade_plan
    ) -> Optional[tuple]:
        """Varre candles futuras (dados reais de high/low) para achar se o
        TP ou o SL seria atingido primeiro. Retorna (exit_price, exit_index,
        'WIN'|'LOSS') ou None se nenhum dos dois for atingido dentro da
        janela de espera máxima."""
        end_index = min(start_index + MAX_HOLD_CANDLES, len(candles))

        for j in range(start_index, end_index):
            candle = candles[j]
            if direction == "BUY":
                if candle.low <= trade_plan.stop_loss:
                    return trade_plan.stop_loss, j, "LOSS"
                if candle.high >= trade_plan.take_profit:
                    return trade_plan.take_profit, j, "WIN"
            else:
                if candle.high >= trade_plan.stop_loss:
                    return trade_plan.stop_loss, j, "LOSS"
                if candle.low <= trade_plan.take_profit:
                    return trade_plan.take_profit, j, "WIN"
        return None

    @staticmethod
    def _profit_loss(direction: str, entry: float, exit_price: float, lot_size: float) -> float:
        distance = exit_price - entry
        if direction == "SELL":
            distance = -distance
        return round(distance * lot_size * LOT_SIZE_UNITS, 2)

    def _build_result(
        self, symbol, timeframe, start, end, initial_capital, final_capital,
        signals_evaluated, trades: List[BacktestTrade],
    ) -> BacktestResult:
        pseudo_operations = [
            Operation(
                signal_id=0,
                symbol=t.symbol,
                direction=SignalDirection(t.direction),
                entry_price=t.entry_price,
                stop_loss=t.stop_loss,
                take_profit=t.take_profit,
                exit_price=t.exit_price,
                lot_size=t.lot_size,
                risk_amount=0.0,
                profit_loss=t.profit_loss,
                result=OperationResult(t.result),
                opened_at=t.opened_at,
                closed_at=t.closed_at,
            )
            for t in trades
        ]

        summary = self._statistics_service.compute(pseudo_operations)
        capital_curve = [round(initial_capital + x, 2) for x in summary.capital_curve]

        return BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start,
            end_date=end,
            initial_capital=initial_capital,
            final_capital=round(final_capital, 2),
            signals_evaluated=signals_evaluated,
            total_operations=summary.total_operations,
            wins=summary.wins,
            losses=summary.losses,
            win_rate=summary.win_rate,
            profit_factor=summary.profit_factor,
            payoff=summary.payoff,
            expectancy=summary.expectancy,
            max_drawdown=summary.max_drawdown,
            net_result=summary.net_result,
            capital_curve=capital_curve or [initial_capital],
            trades=trades,
        )
