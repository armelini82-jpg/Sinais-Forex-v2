"""
Integração real com a Telegram Bot API (https://api.telegram.org).
Envia sinais, resultados de TP/SL e resumos diário/semanal/mensal.
"""
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.signal import Signal

logger = get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramService:
    """Envia notificações formatadas para o Telegram via Bot API."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self._bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self._chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self._enabled = settings.TELEGRAM_ENABLED and bool(self._bot_token) and bool(self._chat_id)

    async def send_new_signal(self, signal: Signal) -> bool:
        text = (
            f"🚨 <b>NOVO SINAL - {signal.symbol}</b>\n\n"
            f"Direção: <b>{signal.direction.value}</b>\n"
            f"IQS: <b>{signal.iqs_score}</b>\n"
            f"Probabilidade: <b>{signal.probability}%</b>\n\n"
            f"Entrada: <code>{signal.entry_price}</code>\n"
            f"Stop Loss: <code>{signal.stop_loss}</code>\n"
            f"Take Profit: <code>{signal.take_profit}</code>\n"
            f"RR: <b>{signal.risk_reward:.1f}:1</b>\n"
            f"Tempo esperado: {signal.expected_duration_minutes} min"
        )
        return await self._send(text)

    async def send_take_profit(self, signal: Signal, exit_price: float, profit: float) -> bool:
        text = (
            f"✅ <b>TAKE PROFIT ATINGIDO - {signal.symbol}</b>\n\n"
            f"Direção: {signal.direction.value}\n"
            f"Entrada: {signal.entry_price} → Saída: {exit_price}\n"
            f"Resultado: <b>+{profit:.2f}</b>"
        )
        return await self._send(text)

    async def send_stop_loss(self, signal: Signal, exit_price: float, loss: float) -> bool:
        text = (
            f"🔴 <b>STOP LOSS ATINGIDO - {signal.symbol}</b>\n\n"
            f"Direção: {signal.direction.value}\n"
            f"Entrada: {signal.entry_price} → Saída: {exit_price}\n"
            f"Resultado: <b>{loss:.2f}</b>"
        )
        return await self._send(text)

    async def send_summary(self, period_label: str, stats: dict) -> bool:
        text = (
            f"📊 <b>RESUMO {period_label.upper()}</b>\n\n"
            f"Operações: {stats.get('total_operations', 0)}\n"
            f"Win Rate: {stats.get('win_rate', 0):.1f}%\n"
            f"Profit Factor: {stats.get('profit_factor', 0):.2f}\n"
            f"Resultado líquido: {stats.get('net_result', 0):.2f}\n"
            f"Drawdown máximo: {stats.get('max_drawdown', 0):.2f}%"
        )
        return await self._send(text)

    async def _send(self, text: str) -> bool:
        if not self._enabled:
            logger.info("Telegram desabilitado (TELEGRAM_ENABLED=false) - mensagem não enviada.")
            return False

        url = TELEGRAM_API_BASE.format(token=self._bot_token)
        payload = {"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("Mensagem Telegram enviada com sucesso.")
                return True
        except httpx.HTTPError as exc:
            logger.error("Falha ao enviar mensagem Telegram: %s", exc)
            return False


telegram_service = TelegramService()
