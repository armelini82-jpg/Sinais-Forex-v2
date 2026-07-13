import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SignalDirection(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalStatus(str, enum.Enum):
    DESCARTADO = "DESCARTADO"
    PREPARANDO = "PREPARANDO"
    CONFIRMADO = "CONFIRMADO"
    EXPIRADO = "EXPIRADO"


class Signal(TimestampMixin, Base):
    """Sinal de trading gerado pelo motor de decisão (SignalEngine)."""

    __tablename__ = "signals"
    __table_args__ = (Index("ix_signal_symbol_status_time", "symbol", "status", "generated_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)
    direction: Mapped[SignalDirection] = mapped_column(Enum(SignalDirection), nullable=False)
    status: Mapped[SignalStatus] = mapped_column(
        Enum(SignalStatus), nullable=False, default=SignalStatus.PREPARANDO
    )

    iqs_score: Mapped[float] = mapped_column(Float, nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)

    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    take_profit: Mapped[float] = mapped_column(Float, nullable=False)
    risk_reward: Mapped[float] = mapped_column(Float, nullable=False)

    atr: Mapped[float] = mapped_column(Float, nullable=False)
    adx: Mapped[float] = mapped_column(Float, nullable=False)
    rsi: Mapped[float] = mapped_column(Float, nullable=False)

    expected_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Breakdown do IQS para auditoria/transparência
    score_trend: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_momentum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_pullback: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_volatility: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_adx: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_liquidity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_session: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    def __repr__(self) -> str:
        return f"<Signal {self.symbol} {self.direction.value} IQS={self.iqs_score}>"
