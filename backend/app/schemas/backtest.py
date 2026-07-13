from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator


class BacktestRequestDTO(BaseModel):
    symbol: str
    timeframe: str = "M15"
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=10_000.0, gt=0)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()

    @field_validator("timeframe")
    @classmethod
    def uppercase_timeframe(cls, v: str) -> str:
        return v.upper()

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: datetime, info):
        start = info.data.get("start_date")
        if start and v <= start:
            raise ValueError("end_date deve ser posterior a start_date")
        return v


class BacktestTradeDTO(BaseModel):
    symbol: str
    timeframe: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_price: float
    lot_size: float
    profit_loss: float
    result: str
    iqs_score: float
    opened_at: datetime
    closed_at: datetime


class BacktestResultDTO(BaseModel):
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
    capital_curve: List[float]
    trades: List[BacktestTradeDTO]
