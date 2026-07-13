from typing import List, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.repository_interfaces import ICandleRepository
from app.models.candle import Candle


class CandleRepository(ICandleRepository):
    """Implementação concreta do repositório de candles usando SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_recent(self, symbol: str, timeframe: str, limit: int) -> Sequence[Candle]:
        stmt = (
            select(Candle)
            .where(Candle.symbol == symbol, Candle.timeframe == timeframe)
            .order_by(Candle.open_time.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        candles = list(result.scalars().all())
        candles.reverse()  # ordem cronológica ascendente
        return candles

    async def bulk_upsert(self, candles: List[Candle]) -> None:
        if not candles:
            return
        values = [
            {
                "symbol": c.symbol,
                "timeframe": c.timeframe,
                "open_time": c.open_time,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        stmt = insert(Candle).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "open_time"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
