from datetime import date

from pydantic import BaseModel, ConfigDict


class StatisticsResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference_date: date
    symbol: str
    total_operations: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    payoff: float
    expectancy: float
    max_drawdown: float
    net_result: float
    capital_curve_point: float
