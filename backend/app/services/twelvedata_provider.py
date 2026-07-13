"""
Provedor de dados de mercado real via TwelveData API (https://twelvedata.com).

Implementa `IMarketDataProvider` chamando os endpoints REST de séries
temporais e cotação da TwelveData, com:

    - Conversão automática de símbolo (EURUSD -> EUR/USD)
    - Rate limiting interno (respeita o plano gratuito: 8 req/min)
    - Cache em memória por (símbolo, timeframe) com TTL alinhado ao
      fechamento do candle, evitando estourar o limite de requisições

Plano gratuito da TwelveData: 8 requisições/minuto, 800/dia. Para monitorar
os 10 pares padrão em 4 timeframes com folga, recomenda-se reduzir SYMBOLS
e/ou TIMEFRAMES no .env, ou usar um plano pago para scan completo em tempo
real (veja README > "Conectando um Provedor de Dados Real").

Observação: a TwelveData não retorna volume real para pares de Forex/XAU
(mercado de balcão, sem volume centralizado). O campo `volume` é preenchido
com 0 nesses casos, o que reduz o peso efetivo do componente "Liquidez" do
IQS para esta fonte de dados — comportamento esperado e documentado.
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import httpx

from app.core.logging import get_logger
from app.interfaces.market_data_interface import IMarketDataProvider
from app.schemas.candle import CandleDTO

logger = get_logger(__name__)

TWELVEDATA_BASE_URL = "https://api.twelvedata.com"

_INTERVAL_MAP: Dict[str, str] = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "H1": "1h",
}

_TIMEFRAME_SECONDS: Dict[str, int] = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
}

MIN_SECONDS_BETWEEN_REQUESTS = 8.0  # ~7.5 req/min, com folga sobre o limite de 8/min


class TwelveDataMarketDataProvider(IMarketDataProvider):
    """Provedor real de dados de mercado usando a API da TwelveData."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError(
                "MARKET_DATA_API_KEY vazio. Defina sua chave da TwelveData no .env "
                "para usar DATA_PROVIDER=twelvedata."
            )
        self._api_key = api_key
        self._client = httpx.AsyncClient(base_url=TWELVEDATA_BASE_URL, timeout=15.0)

        self._rate_lock = asyncio.Lock()
        self._last_request_at: float = 0.0

        self._candle_cache: Dict[Tuple[str, str], Tuple[float, List[CandleDTO]]] = {}
        self._price_cache: Dict[str, Tuple[float, float]] = {}

    async def get_latest_candles(self, symbol: str, timeframe: str, limit: int) -> List[CandleDTO]:
        symbol = symbol.upper()
        cache_key = (symbol, timeframe)
        ttl = _TIMEFRAME_SECONDS.get(timeframe, 60)

        cached = self._candle_cache.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < ttl and len(cached[1]) >= limit:
            return cached[1][-limit:]

        interval = _INTERVAL_MAP.get(timeframe)
        if interval is None:
            raise ValueError(f"Timeframe não suportado pela TwelveData: {timeframe}")

        api_symbol = self._to_api_symbol(symbol)
        params = {
            "symbol": api_symbol,
            "interval": interval,
            "outputsize": min(limit, 5000),
            "apikey": self._api_key,
            "order": "ASC",
        }

        data = await self._request("/time_series", params)

        values = data.get("values")
        if not values:
            message = data.get("message", "resposta vazia da TwelveData")
            raise ValueError(f"Falha ao obter candles de {symbol} ({timeframe}): {message}")

        candles = [self._parse_candle(symbol, timeframe, v) for v in values]
        candles.sort(key=lambda c: c.open_time)

        self._candle_cache[cache_key] = (time.monotonic(), candles)
        return candles[-limit:]

    async def get_current_price(self, symbol: str) -> float:
        symbol = symbol.upper()
        cached = self._price_cache.get(symbol)
        if cached and (time.monotonic() - cached[0]) < 5:
            return cached[1]

        api_symbol = self._to_api_symbol(symbol)
        data = await self._request("/price", {"symbol": api_symbol, "apikey": self._api_key})

        if "price" not in data:
            message = data.get("message", "resposta inválida da TwelveData")
            raise ValueError(f"Falha ao obter preço de {symbol}: {message}")

        price = float(data["price"])
        self._price_cache[symbol] = (time.monotonic(), price)
        return price

    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> List[CandleDTO]:
        """
        Busca candles históricas num intervalo [start, end] para uso em
        backtest. Diferente de `get_latest_candles`, não usa o cache de TTL
        curto (o resultado é estável no tempo), mas ainda respeita o rate
        limiter interno. Para períodos longos, pode exigir múltiplas
        chamadas (a TwelveData limita a 5000 candles por requisição).
        """
        symbol = symbol.upper()
        interval = _INTERVAL_MAP.get(timeframe)
        if interval is None:
            raise ValueError(f"Timeframe não suportado pela TwelveData: {timeframe}")

        api_symbol = self._to_api_symbol(symbol)
        all_candles: List[CandleDTO] = []
        current_end = end

        # Pagina para trás em blocos de até 5000 candles até cobrir todo o
        # período solicitado ou até a API não retornar mais dados novos.
        for _ in range(10):  # limite de segurança: no máx. 50.000 candles
            params = {
                "symbol": api_symbol,
                "interval": interval,
                "outputsize": 5000,
                "apikey": self._api_key,
                "order": "DESC",
                "end_date": current_end.strftime("%Y-%m-%d %H:%M:%S"),
                "start_date": start.strftime("%Y-%m-%d %H:%M:%S"),
            }
            data = await self._request("/time_series", params)
            values = data.get("values")
            if not values:
                break

            batch = [self._parse_candle(symbol, timeframe, v) for v in values]
            all_candles.extend(batch)

            oldest_in_batch = min(c.open_time for c in batch)
            if oldest_in_batch <= start or len(batch) < 5000:
                break
            current_end = oldest_in_batch

        unique = {c.open_time: c for c in all_candles}
        candles = sorted(unique.values(), key=lambda c: c.open_time)
        return [c for c in candles if start <= c.open_time <= end]

    def is_market_open(self, symbol: str) -> bool:
        # Forex/XAU operam 24h entre domingo 22h UTC e sexta 22h UTC.
        now = datetime.now(timezone.utc)
        if now.weekday() == 5:
            return False
        if now.weekday() == 6 and now.hour < 22:
            return False
        if now.weekday() == 4 and now.hour >= 22:
            return False
        return True

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _request(self, path: str, params: dict) -> dict:
        async with self._rate_lock:
            elapsed = time.monotonic() - self._last_request_at
            wait = MIN_SECONDS_BETWEEN_REQUESTS - elapsed
            if wait > 0:
                await asyncio.sleep(wait)

            try:
                response = await self._client.get(path, params=params)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as exc:
                logger.error("Erro HTTP ao chamar TwelveData %s: %s", path, exc)
                raise
            finally:
                self._last_request_at = time.monotonic()

        if isinstance(data, dict) and data.get("status") == "error":
            raise ValueError(f"TwelveData retornou erro: {data.get('message')}")

        return data

    @staticmethod
    def _to_api_symbol(symbol: str) -> str:
        """Converte 'EURUSD' -> 'EUR/USD', 'XAUUSD' -> 'XAU/USD'."""
        if "/" in symbol:
            return symbol
        return f"{symbol[:-3]}/{symbol[-3:]}"

    @staticmethod
    def _parse_candle(symbol: str, timeframe: str, raw: dict) -> CandleDTO:
        open_time = datetime.strptime(raw["datetime"], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
        return CandleDTO(
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            open=float(raw["open"]),
            high=float(raw["high"]),
            low=float(raw["low"]),
            close=float(raw["close"]),
            volume=float(raw.get("volume") or 0),
        )
