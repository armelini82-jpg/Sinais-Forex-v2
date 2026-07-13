from typing import Optional

from pydantic import BaseModel


class IndicatorSetDTO(BaseModel):
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    ema_200: Optional[float] = None
    rsi_14: Optional[float] = None
    atr_14: Optional[float] = None
    adx_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    vwap: Optional[float] = None
    momentum: Optional[float] = None
    volume: Optional[float] = None
