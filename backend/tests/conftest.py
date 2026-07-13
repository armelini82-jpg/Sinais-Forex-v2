import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.candle import CandleDTO  # noqa: E402


def build_trending_candles(
    n: int = 220, start_price: float = 1.1000, step: float = 0.00015, volume: float = 1000.0
) -> List[CandleDTO]:
    """Gera uma série de candles em tendência de alta consistente, útil para
    testar cenários onde o motor de sinais deve reconhecer um BUY forte."""
    now = datetime.now(timezone.utc)
    candles = []
    price = start_price
    for i in range(n):
        open_price = price
        close_price = open_price + step
        high_price = close_price + step * 0.3
        low_price = open_price - step * 0.2
        candles.append(
            CandleDTO(
                symbol="EURUSD",
                timeframe="M15",
                open_time=now - timedelta(minutes=15 * (n - i)),
                open=round(open_price, 5),
                high=round(high_price, 5),
                low=round(low_price, 5),
                close=round(close_price, 5),
                volume=volume,
            )
        )
        price = close_price
    return candles


def build_flat_candles(n: int = 220, price: float = 1.1000, volume: float = 1000.0) -> List[CandleDTO]:
    """Gera candles praticamente planas (mercado lateral / sem tendência)."""
    now = datetime.now(timezone.utc)
    candles = []
    for i in range(n):
        candles.append(
            CandleDTO(
                symbol="EURUSD",
                timeframe="M15",
                open_time=now - timedelta(minutes=15 * (n - i)),
                open=price,
                high=price + 0.00002,
                low=price - 0.00002,
                close=price,
                volume=volume,
            )
        )
    return candles


@pytest.fixture
def trending_candles() -> List[CandleDTO]:
    return build_trending_candles()


@pytest.fixture
def flat_candles() -> List[CandleDTO]:
    return build_flat_candles()
