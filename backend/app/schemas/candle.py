from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CandleDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    timeframe: str
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
