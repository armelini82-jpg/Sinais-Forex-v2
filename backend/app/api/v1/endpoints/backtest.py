from fastapi import APIRouter, Depends

from app.api.deps import get_backtest_engine
from app.core.exceptions import ForexRadarError
from app.schemas.backtest import BacktestRequestDTO, BacktestResultDTO
from app.services.backtest_engine import BacktestEngine

router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.post("/run", response_model=BacktestResultDTO)
async def run_backtest(
    request: BacktestRequestDTO,
    backtest_engine: BacktestEngine = Depends(get_backtest_engine),
):
    """
    Executa o motor de decisão (IQS + gestão de risco) sobre candles
    históricas reais de um par/timeframe, num período escolhido, e retorna
    as métricas de performance (Win Rate, Profit Factor, Drawdown, Curva de
    Capital) que teriam resultado de seguir todo sinal CONFIRMADO gerado.

    Sem lookahead bias: a cada ponto no tempo, o motor só enxerga candles já
    fechadas até aquele momento — igual ao comportamento em produção.
    """
    try:
        result = await backtest_engine.run(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start=request.start_date,
            end=request.end_date,
            initial_capital=request.initial_capital,
        )
    except ValueError as exc:
        raise ForexRadarError(str(exc), status_code=422)

    return result
