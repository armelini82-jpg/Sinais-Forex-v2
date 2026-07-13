from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_operation_repository, get_statistics_service
from app.repositories.operation_repository import OperationRepository
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["Estatísticas"])


@router.get("")
async def get_statistics(
    days: int = Query(default=30, ge=1, le=365),
    operation_repo: OperationRepository = Depends(get_operation_repository),
    stats_service: StatisticsService = Depends(get_statistics_service),
):
    """
    Retorna Win Rate, Profit Factor, Payoff, Expectancy, Drawdown e Curva de
    Capital para os últimos N dias.
    """
    end = date.today()
    start = end - timedelta(days=days)
    operations = await operation_repo.list_between(start, end)
    summary = stats_service.compute(operations)
    return summary
