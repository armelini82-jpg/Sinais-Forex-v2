from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class IndicatorSnapshot(TimestampMixin, Base):
    """
    Snapshot dos indicadores calculados para um par/timeframe em um instante.
    Esta tabela também serve como base de features para o futuro pipeline de ML
    (probabilidade de sucesso do sinal).
    """

    __tablename__ = "indicators"
    __table_args__ = (
        Index("ix_indicator_symbol_tf_time", "symbol", "timeframe", "reference_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)
    reference_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    ema_9: Mapped[float] = mapped_column(Float, nullable=True)
    ema_21: Mapped[float] = mapped_column(Float, nullable=True)
    ema_200: Mapped[float] = mapped_column(Float, nullable=True)
    rsi_14: Mapped[float] = mapped_column(Float, nullable=True)
    atr_14: Mapped[float] = mapped_column(Float, nullable=True)
    adx_14: Mapped[float] = mapped_column(Float, nullable=True)
    macd: Mapped[float] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float] = mapped_column(Float, nullable=True)
    macd_hist: Mapped[float] = mapped_column(Float, nullable=True)
    bb_upper: Mapped[float] = mapped_column(Float, nullable=True)
    bb_middle: Mapped[float] = mapped_column(Float, nullable=True)
    bb_lower: Mapped[float] = mapped_column(Float, nullable=True)
    vwap: Mapped[float] = mapped_column(Float, nullable=True)
    momentum: Mapped[float] = mapped_column(Float, nullable=True)
    volume: Mapped[float] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<IndicatorSnapshot {self.symbol} {self.timeframe} {self.reference_time}>"
