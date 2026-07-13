"""
Provedor de dados de mercado.

Implementa `IMarketDataProvider` com um gerador determinístico-estocástico
(random walk com volatilidade calibrada por símbolo), permitindo rodar o
sistema completo (indicadores, IQS, sinais, dashboard) sem depender de uma
conta paga de corretora.

Para produção, basta implementar outra classe (ex.: `OandaMarketDataProvider`,
`MT5MarketDataProvider`, `TwelveDataMarketDataProvider`) que satisfaça a mesma
interface e trocar o binding em `market_data_factory.py` — nenhum outro
módulo do sistema precisa ser alterado (Open/Closed Principle).
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from app.interfaces.market_data_interface import IMarketDataProvider
from app.schemas.candle import CandleDTO

_BASE_PRICES: Dict[str, float] = {
    "EURUSD": 1.0850,
    "GBPUSD": 1.2650,
    "USDJPY": 157.20,
    "AUDUSD": 0.6650,
    "NZDUSD": 0.6120,
    "USDCAD": 1.3680,
    "USDCHF": 0.8950,
    "EURJPY": 170.60,
    "GBPJPY": 198.90,
    "XAUUSD": 2350.00,
}

_PIP_VOLATILITY: Dict[str, float] = {
    "EURUSD": 0.00012,
    "GBPUSD": 0.00015,
    "USDJPY": 0.020,
    "AUDUSD": 0.00013,
    "NZDUSD": 0.00013,
    "USDCAD": 0.00013,
    "USDCHF": 0.00012,
    "EURJPY": 0.022,
    "GBPJPY": 0.028,
    "XAUUSD": 1.50,
}

_TIMEFRAME_MINUTES: Dict[str, int] = {"M1": 1, "M5": 5, "M15": 15, "H1": 60}


class SimulatedMarketDataProvider(IMarketDataProvider):
    """Gerador de candles via random walk com leve viés de tendência por símbolo."""

    def __init__(self):
        self._price_state: Dict[str, float] = dict(_BASE_PRICES)
        self._trend_bias: Dict[str, float] = {s: random.uniform(-1, 1) for s in _BASE_PRICES}

    async def get_latest_candles(self, symbol: str, timeframe: str, limit: int) -> List[CandleDTO]:
        symbol = symbol.upper()
        if symbol not in _BASE_PRICES:
            raise ValueError(f"Símbolo não suportado pelo provider simulado: {symbol}")

        volatility = _PIP_VOLATILITY[symbol]
        minutes = _TIMEFRAME_MINUTES.get(timeframe, 5)
        bias = self._trend_bias[symbol]

        price = self._price_state[symbol]
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        candles: List[CandleDTO] = []

        for i in range(limit, 0, -1):
            open_time = now - timedelta(minutes=minutes * i)
            open_price = price
            drift = bias * volatility * 0.3
            steps = [random.gauss(drift, volatility) for _ in range(4)]
            close_price = open_price + sum(steps)
            high_price = max(open_price, close_price) + abs(random.gauss(0, volatility * 0.5))
            low_price = min(open_price, close_price) - abs(random.gauss(0, volatility * 0.5))
            volume = abs(random.gauss(1200, 400))

            candles.append(
                CandleDTO(
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=open_time,
                    open=round(open_price, 5),
                    high=round(high_price, 5),
                    low=round(low_price, 5),
                    close=round(close_price, 5),
                    volume=round(volume, 2),
                )
            )
            price = close_price

        self._price_state[symbol] = price
        return candles

    async def get_current_price(self, symbol: str) -> float:
        symbol = symbol.upper()
        if symbol not in self._price_state:
            raise ValueError(f"Símbolo não suportado pelo provider simulado: {symbol}")
        return round(self._price_state[symbol], 5)

    def is_market_open(self, symbol: str) -> bool:
        now = datetime.now(timezone.utc)
        # Forex fecha de sexta 22h UTC a domingo 22h UTC
        if now.weekday() == 5:
            return False
        if now.weekday() == 6 and now.hour < 22:
            return False
        if now.weekday() == 4 and now.hour >= 22:
            return False
        return True

    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> List[CandleDTO]:
        """
        Gera candles sintéticas cobrindo [start, end] via random walk, com
        seed determinística por símbolo+período para que o mesmo backtest
        rodado duas vezes produza sempre o mesmo resultado.
        """
        symbol = symbol.upper()
        if symbol not in _BASE_PRICES:
            raise ValueError(f"Símbolo não suportado pelo provider simulado: {symbol}")

        minutes = _TIMEFRAME_MINUTES.get(timeframe, 5)
        total_minutes = max(int((end - start).total_seconds() // 60), minutes)
        n_candles = min(total_minutes // minutes, 20000)

        rng = random.Random(f"{symbol}-{timeframe}-{start.isoformat()}-{end.isoformat()}")
        volatility = _PIP_VOLATILITY[symbol]
        bias = rng.uniform(-1, 1)
        price = _BASE_PRICES[symbol]

        candles: List[CandleDTO] = []
        for i in range(n_candles):
            open_time = start + timedelta(minutes=minutes * i)
            open_price = price
            drift = bias * volatility * 0.3
            steps = [rng.gauss(drift, volatility) for _ in range(4)]
            close_price = open_price + sum(steps)
            high_price = max(open_price, close_price) + abs(rng.gauss(0, volatility * 0.5))
            low_price = min(open_price, close_price) - abs(rng.gauss(0, volatility * 0.5))
            volume = abs(rng.gauss(1200, 400))

            candles.append(
                CandleDTO(
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=open_time,
                    open=round(open_price, 5),
                    high=round(high_price, 5),
                    low=round(low_price, 5),
                    close=round(close_price, 5),
                    volume=round(volume, 2),
                )
            )
            price = close_price

        return candles


# Instância singleton compartilhada por toda a aplicação, garantindo que os
# preços evoluam de forma consistente entre chamadas do scheduler.
simulated_market_data_provider = SimulatedMarketDataProvider()
