"""
Serviço de gestão de risco.

Calcula Stop Loss e Take Profit com base no ATR (fallback: último fundo/topo),
garante relação risco/retorno mínima de 2:1 e calcula o tamanho de posição de
acordo com o risco máximo por operação (1% do capital, configurável).
"""
from dataclasses import dataclass
from typing import List, Literal

from app.core.config import settings
from app.schemas.candle import CandleDTO

Direction = Literal["BUY", "SELL"]

ATR_STOP_MULTIPLIER = 1.5


@dataclass
class TradePlan:
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    lot_size: float
    risk_amount: float


class RiskManagementService:
    """Calcula entrada, stop, alvo e tamanho de posição para um sinal."""

    def build_trade_plan(
        self,
        direction: Direction,
        candles: List[CandleDTO],
        atr: float,
        account_balance: float = 10_000.0,
    ) -> TradePlan:
        entry_price = candles[-1].close
        stop_loss = self._calculate_stop_loss(direction, candles, entry_price, atr)
        stop_distance = abs(entry_price - stop_loss)

        take_profit = self._calculate_take_profit(direction, entry_price, stop_distance)
        risk_reward = self._risk_reward(entry_price, stop_loss, take_profit)

        risk_amount = account_balance * (settings.RISK_PER_TRADE_PERCENT / 100)
        lot_size = self._position_size(risk_amount, stop_distance, entry_price)

        return TradePlan(
            entry_price=round(entry_price, 5),
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            risk_reward=round(risk_reward, 2),
            lot_size=round(lot_size, 4),
            risk_amount=round(risk_amount, 2),
        )

    @staticmethod
    def _calculate_stop_loss(
        direction: Direction, candles: List[CandleDTO], entry_price: float, atr: float
    ) -> float:
        atr_stop_distance = atr * ATR_STOP_MULTIPLIER

        lookback = candles[-10:]
        swing_low = min(c.low for c in lookback)
        swing_high = max(c.high for c in lookback)

        if direction == "BUY":
            atr_based = entry_price - atr_stop_distance
            # usa o mais conservador (mais distante) entre ATR e último fundo
            return min(atr_based, swing_low) if atr_stop_distance > 0 else swing_low
        else:
            atr_based = entry_price + atr_stop_distance
            return max(atr_based, swing_high) if atr_stop_distance > 0 else swing_high

    @staticmethod
    def _calculate_take_profit(direction: Direction, entry_price: float, stop_distance: float) -> float:
        target_distance = stop_distance * max(settings.MIN_RISK_REWARD, 2.0)
        if direction == "BUY":
            return entry_price + target_distance
        return entry_price - target_distance

    @staticmethod
    def _risk_reward(entry_price: float, stop_loss: float, take_profit: float) -> float:
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        if risk == 0:
            return 0.0
        return reward / risk

    @staticmethod
    def _position_size(risk_amount: float, stop_distance: float, entry_price: float) -> float:
        """
        Tamanho de posição simplificado em lotes-padrão (100.000 unidades),
        assumindo conta denominada em USD e pip value proporcional ao preço.
        """
        if stop_distance <= 0:
            return 0.0
        pip_value_per_lot = 100_000 * stop_distance
        if pip_value_per_lot == 0:
            return 0.0
        return risk_amount / pip_value_per_lot
