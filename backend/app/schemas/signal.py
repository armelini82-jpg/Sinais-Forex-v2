from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.signal import SignalDirection, SignalStatus


class IQSBreakdownDTO(BaseModel):
    trend: float
    momentum: float
    pullback: float
    volatility: float
    adx: float
    liquidity: float
    session: float

    @property
    def total(self) -> float:
        return round(
            self.trend
            + self.momentum
            + self.pullback
            + self.volatility
            + self.adx
            + self.liquidity
            + self.session,
            2,
        )


class SignalResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    timeframe: str
    direction: SignalDirection
    status: SignalStatus
    iqs_score: float
    probability: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    atr: float
    adx: float
    rsi: float
    expected_duration_minutes: int
    generated_at: datetime
