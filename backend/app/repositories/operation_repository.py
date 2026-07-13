from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.repository_interfaces import IOperationRepository
from app.models.operation import Operation, OperationResult


class OperationRepository(IOperationRepository):
    """Implementação concreta do repositório de operações usando SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, operation: Operation) -> Operation:
        self._session.add(operation)
        await self._session.flush()
        await self._session.refresh(operation)
        return operation

    async def list_recent(self, limit: int = 50) -> Sequence[Operation]:
        stmt = select(Operation).order_by(Operation.opened_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_between(self, start: date, end: date) -> Sequence[Operation]:
        stmt = select(Operation).where(
            Operation.opened_at >= start, Operation.opened_at <= end
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_open(self) -> Sequence[Operation]:
        stmt = select(Operation).where(Operation.result == OperationResult.OPEN)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_result(self, operation_id: int, **kwargs) -> Optional[Operation]:
        operation = await self._session.get(Operation, operation_id)
        if operation is None:
            return None
        for key, value in kwargs.items():
            setattr(operation, key, value)
        await self._session.flush()
        await self._session.refresh(operation)
        return operation
