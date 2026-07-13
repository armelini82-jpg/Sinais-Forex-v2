from fastapi import APIRouter, Depends

from app.api.deps import get_market_data_provider
from app.core.config import settings
from app.interfaces.market_data_interface import IMarketDataProvider

router = APIRouter(prefix="/pairs", tags=["Pares / Mercado"])


@router.get("")
async def list_pairs():
    """Lista os pares monitorados e timeframes disponíveis."""
    return {"symbols": settings.symbols_list, "timeframes": settings.timeframes_list}


@router.get("/{symbol}/status")
async def get_symbol_status(
    symbol: str, provider: IMarketDataProvider = Depends(get_market_data_provider)
):
    """Retorna preço atual e se o mercado do símbolo está aberto."""
    symbol = symbol.upper()
    price = await provider.get_current_price(symbol)
    is_open = provider.is_market_open(symbol)
    return {"symbol": symbol, "current_price": price, "market_open": is_open}
