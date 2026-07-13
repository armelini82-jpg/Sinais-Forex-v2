"""
Interface abstrata para provedores de dados de mercado.
Permite trocar a fonte de dados (simulada, OANDA, MT5, TwelveData, etc.)
sem alterar nenhuma linha do motor de indicadores/sinais - princípio Open/Closed.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from app.schemas.candle import CandleDTO


class IMarketDataProvider(ABC):
    @abstractmethod
    async def get_latest_candles(self, symbol: str, timeframe: str, limit: int) -> List[CandleDTO]:
        """Retorna as últimas `limit` candles fechadas para symbol/timeframe."""
        ...

    @abstractmethod
    async def get_current_price(self, symbol: str) -> float:
        """Retorna o preço (bid/mid) atual do símbolo."""
        ...

    @abstractmethod
    def is_market_open(self, symbol: str) -> bool:
        """Indica se o mercado do símbolo está aberto no momento."""
        ...

    @abstractmethod
    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> List[CandleDTO]:
        """Retorna candles históricas de symbol/timeframe entre start e end
        (ambos inclusive), em ordem cronológica ascendente. Usado pelo motor
        de backtest."""
        ...
