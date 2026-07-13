"""
Interfaces (contratos) de repositório. Services dependem destas abstrações,
nunca das implementações concretas - princípio de Inversão de Dependência (SOLID).
"""
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional, Sequence

from app.models.candle import Candle
from app.models.operation import Operation
from app.models.signal import Signal, SignalStatus


class ICandleRepository(ABC):
    @abstractmethod
    async def get_recent(self, symbol: str, timeframe: str, limit: int) -> Sequence[Candle]:
        ...

    @abstractmethod
    async def bulk_upsert(self, candles: List[Candle]) -> None:
        ...


class ISignalRepository(ABC):
    @abstractmethod
    async def create(self, signal: Signal) -> Signal:
        ...

    @abstractmethod
    async def list_active(self, status: Optional[SignalStatus] = None) -> Sequence[Signal]:
        ...

    @abstractmethod
    async def get_by_id(self, signal_id: int) -> Optional[Signal]:
        ...

    @abstractmethod
    async def count_today_for_symbol(self, symbol: str) -> int:
        ...


class IOperationRepository(ABC):
    @abstractmethod
    async def create(self, operation: Operation) -> Operation:
        ...

    @abstractmethod
    async def list_recent(self, limit: int = 50) -> Sequence[Operation]:
        ...

    @abstractmethod
    async def list_between(self, start: date, end: date) -> Sequence[Operation]:
        ...

    @abstractmethod
    async def list_open(self) -> Sequence[Operation]:
        ...

    @abstractmethod
    async def update_result(self, operation_id: int, **kwargs) -> Optional[Operation]:
        ...
