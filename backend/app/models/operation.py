import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.signal import SignalDirection


class OperationResult(str, enum.Enum):
    OPEN = "OPEN"
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    CANCELLED = "CANCELLED"


class Operation(TimestampMixin, Base):
    """Operação executada (ou simulada em paper trading) a partir de um sinal."""

    __tablename__ = "operations"
    __table_args__ = (Index("ix_operation_symbol_result", "symbol", "result"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[SignalDirection] = mapped_column(Enum(SignalDirection), nullable=False)

    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    take_profit: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)

    lot_size: Mapped[float] = mapped_column(Float, nullable=False)
    risk_amount: Mapped[float] = mapped_column(Float, nullable=False)
    profit_loss: Mapped[float] = mapped_column(Float, nullable=True)
    result: Mapped[OperationResult] = mapped_column(
        Enum(OperationResult), nullable=False, default=OperationResult.OPEN
    )

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Operation {self.symbol} {self.direction.value} result={self.result.value}>"
