from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.repository_interfaces import ISignalRepository
from app.models.signal import Signal, SignalStatus


class SignalRepository(ISignalRepository):
    """Implementação concreta do repositório de sinais usando SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, signal: Signal) -> Signal:
        self._session.add(signal)
        await self._session.flush()
        await self._session.refresh(signal)
        return signal

    async def list_active(self, status: Optional[SignalStatus] = None) -> Sequence[Signal]:
        stmt = select(Signal)
        if status is not None:
            stmt = stmt.where(Signal.status == status)
        else:
            stmt = stmt.where(
                Signal.status.in_([SignalStatus.CONFIRMADO, SignalStatus.PREPARANDO])
            )
        stmt = stmt.order_by(Signal.generated_at.desc()).limit(200)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, signal_id: int) -> Optional[Signal]:
        return await self._session.get(Signal, signal_id)

    async def count_today_for_symbol(self, symbol: str) -> int:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count(Signal.id)).where(
            Signal.symbol == symbol,
            Signal.generated_at >= today_start,
            Signal.status == SignalStatus.CONFIRMADO,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
