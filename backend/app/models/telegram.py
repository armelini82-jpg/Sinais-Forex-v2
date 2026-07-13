import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class TelegramMessageType(str, enum.Enum):
    NEW_SIGNAL = "NEW_SIGNAL"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    DAILY_SUMMARY = "DAILY_SUMMARY"
    WEEKLY_SUMMARY = "WEEKLY_SUMMARY"
    MONTHLY_SUMMARY = "MONTHLY_SUMMARY"


class TelegramMessage(TimestampMixin, Base):
    """Registro de mensagens enviadas ao Telegram."""

    __tablename__ = "telegram_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_type: Mapped[TelegramMessageType] = mapped_column(
        Enum(TelegramMessageType), nullable=False
    )
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), nullable=True)
    chat_id: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sent_successfully: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<TelegramMessage {self.message_type.value} sent={self.sent_successfully}>"
