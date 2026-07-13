"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-07 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    signal_direction = sa.Enum("BUY", "SELL", name="signaldirection")
    signal_status = sa.Enum("DESCARTADO", "PREPARANDO", "CONFIRMADO", "EXPIRADO", name="signalstatus")
    operation_result = sa.Enum(
        "OPEN", "WIN", "LOSS", "BREAKEVEN", "CANCELLED", name="operationresult"
    )
    telegram_message_type = sa.Enum(
        "NEW_SIGNAL",
        "TAKE_PROFIT",
        "STOP_LOSS",
        "DAILY_SUMMARY",
        "WEEKLY_SUMMARY",
        "MONTHLY_SUMMARY",
        name="telegrammessagetype",
    )
    log_level = sa.Enum("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", name="loglevel")

    op.create_table(
        "candles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("symbol", "timeframe", "open_time", name="uq_candle_symbol_tf_time"),
    )
    op.create_index("ix_candle_symbol_tf_time", "candles", ["symbol", "timeframe", "open_time"])

    op.create_table(
        "indicators",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=False),
        sa.Column("reference_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ema_9", sa.Float(), nullable=True),
        sa.Column("ema_21", sa.Float(), nullable=True),
        sa.Column("ema_200", sa.Float(), nullable=True),
        sa.Column("rsi_14", sa.Float(), nullable=True),
        sa.Column("atr_14", sa.Float(), nullable=True),
        sa.Column("adx_14", sa.Float(), nullable=True),
        sa.Column("macd", sa.Float(), nullable=True),
        sa.Column("macd_signal", sa.Float(), nullable=True),
        sa.Column("macd_hist", sa.Float(), nullable=True),
        sa.Column("bb_upper", sa.Float(), nullable=True),
        sa.Column("bb_middle", sa.Float(), nullable=True),
        sa.Column("bb_lower", sa.Float(), nullable=True),
        sa.Column("vwap", sa.Float(), nullable=True),
        sa.Column("momentum", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_indicator_symbol_tf_time", "indicators", ["symbol", "timeframe", "reference_time"])

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=False),
        sa.Column("direction", signal_direction, nullable=False),
        sa.Column("status", signal_status, nullable=False, server_default="PREPARANDO"),
        sa.Column("iqs_score", sa.Float(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("stop_loss", sa.Float(), nullable=False),
        sa.Column("take_profit", sa.Float(), nullable=False),
        sa.Column("risk_reward", sa.Float(), nullable=False),
        sa.Column("atr", sa.Float(), nullable=False),
        sa.Column("adx", sa.Float(), nullable=False),
        sa.Column("rsi", sa.Float(), nullable=False),
        sa.Column("expected_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score_trend", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_momentum", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_pullback", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_volatility", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_adx", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_liquidity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_session", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_signal_symbol_status_time", "signals", ["symbol", "status", "generated_at"])

    op.create_table(
        "operations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("signal_id", sa.Integer(), sa.ForeignKey("signals.id"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("direction", signal_direction, nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("stop_loss", sa.Float(), nullable=False),
        sa.Column("take_profit", sa.Float(), nullable=False),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("lot_size", sa.Float(), nullable=False),
        sa.Column("risk_amount", sa.Float(), nullable=False),
        sa.Column("profit_loss", sa.Float(), nullable=True),
        sa.Column("result", operation_result, nullable=False, server_default="OPEN"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_operation_symbol_result", "operations", ["symbol", "result"])

    op.create_table(
        "statistics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False, server_default="ALL"),
        sa.Column("total_operations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("profit_factor", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payoff", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expectancy", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_drawdown", sa.Float(), nullable=False, server_default="0"),
        sa.Column("net_result", sa.Float(), nullable=False, server_default="0"),
        sa.Column("capital_curve_point", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("reference_date", "symbol", name="uq_stats_date_symbol"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("email", sa.String(120), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "telegram_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("message_type", telegram_message_type, nullable=False),
        sa.Column("signal_id", sa.Integer(), sa.ForeignKey("signals.id"), nullable=True),
        sa.Column("chat_id", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sent_successfully", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("level", log_level, nullable=False, server_default="INFO"),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_logs")
    op.drop_table("telegram_messages")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.drop_table("statistics")
    op.drop_index("ix_operation_symbol_result", table_name="operations")
    op.drop_table("operations")
    op.drop_index("ix_signal_symbol_status_time", table_name="signals")
    op.drop_table("signals")
    op.drop_index("ix_indicator_symbol_tf_time", table_name="indicators")
    op.drop_table("indicators")
    op.drop_index("ix_candle_symbol_tf_time", table_name="candles")
    op.drop_table("candles")

    sa.Enum(name="loglevel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="telegrammessagetype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="operationresult").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="signalstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="signaldirection").drop(op.get_bind(), checkfirst=True)
