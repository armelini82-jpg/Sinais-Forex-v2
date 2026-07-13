from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.operation import OperationResult
from app.models.signal import SignalDirection


class OperationCreateDTO(BaseModel):
    signal_id: int
    lot_size: float = Field(gt=0)
    entry_price: Optional[float] = Field(default=None, gt=0)


class OperationResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    signal_id: int
    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_price: Optional[float] = None
    lot_size: float
    risk_amount: float
    profit_loss: Optional[float] = None
    result: OperationResult
    opened_at: datetime
    closed_at: Optional[datetime] = None
