from datetime import date

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DailyStatistics(TimestampMixin, Base):
    """Estatísticas agregadas por dia (e opcionalmente por símbolo)."""

    __tablename__ = "statistics"
    __table_args__ = (UniqueConstraint("reference_date", "symbol", name="uq_stats_date_symbol"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, default="ALL")

    total_operations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    win_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payoff: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expectancy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    net_result: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    capital_curve_point: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    def __repr__(self) -> str:
        return f"<DailyStatistics {self.reference_date} {self.symbol} win_rate={self.win_rate}>"
