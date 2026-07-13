"""
Motor de sinais (SignalEngine) - orquestra todo o pipeline de decisão:

    1. Busca candles recentes (MarketDataProvider)
    2. Calcula indicadores técnicos (IndicatorService)
    3. Avalia o IQS e a direção (IQSEngine)
    4. Se IQS >= 80, monta o plano de trade (RiskManagementService)
    5. Aplica limites de risco (máx. operações/dia por símbolo)
    6. Persiste o sinal (SignalRepository)
    7. Notifica via WebSocket e Telegram

Este service depende apenas de abstrações (interfaces), nunca de detalhes de
implementação concretos - respeitando o Dependency Inversion Principle.
"""
from datetime import datetime, timezone
from typing import List, Optional

from app.core.config import settings
from app.core.exceptions import RiskLimitExceededError
from app.core.logging import get_logger
from app.interfaces.market_data_interface import IMarketDataProvider
from app.interfaces.repository_interfaces import ISignalRepository
from app.models.signal import Signal, SignalDirection, SignalStatus
from app.services.indicator_service import IndicatorService
from app.services.iqs_engine import IQSEngine
from app.services.risk_management_service import RiskManagementService
from app.services.scan_state_service import ScanRecord, scan_state_service
from app.services.telegram_service import TelegramService
from app.services.websocket_manager import ConnectionManager

logger = get_logger(__name__)

CANDLES_LOOKBACK = 220


class SignalEngine:
    """Orquestra a geração de sinais de trading ponta a ponta."""

    def __init__(
        self,
        market_data_provider: IMarketDataProvider,
        signal_repository: ISignalRepository,
        indicator_service: Optional[IndicatorService] = None,
        iqs_engine: Optional[IQSEngine] = None,
        risk_service: Optional[RiskManagementService] = None,
        telegram_service: Optional[TelegramService] = None,
        connection_manager: Optional[ConnectionManager] = None,
    ):
        self._market_data = market_data_provider
        self._signal_repo = signal_repository
        self._indicator_service = indicator_service or IndicatorService()
        self._iqs_engine = iqs_engine or IQSEngine()
        self._risk_service = risk_service or RiskManagementService()
        self._telegram_service = telegram_service
        self._connection_manager = connection_manager

    async def analyze_symbol(self, symbol: str, timeframe: str) -> Optional[Signal]:
        """Executa o pipeline completo para um símbolo/timeframe. Retorna o
        sinal persistido, ou None se não houver oportunidade qualificada.

        Independentemente do resultado, sempre registra a leitura em
        `scan_state_service` — inclusive quando o par é descartado — para
        que o dashboard possa mostrar o que o motor decidiu, e por quê.
        """

        candles = await self._market_data.get_latest_candles(symbol, timeframe, CANDLES_LOOKBACK)
        if len(candles) < CANDLES_LOOKBACK:
            logger.debug("Candles insuficientes para %s %s", symbol, timeframe)
            await self._record_scan(
                symbol, timeframe, "NEUTRAL", "SEM_DADOS", 0.0,
                f"Candles insuficientes ({len(candles)}/{CANDLES_LOOKBACK})",
            )
            return None

        indicators = self._indicator_service.calculate(symbol, timeframe, candles)
        iqs_result = self._iqs_engine.evaluate(symbol, candles, indicators)
        reason = self._iqs_engine.explain(iqs_result.direction, iqs_result.breakdown)
        current_price = candles[-1].close

        await self._record_scan(
            symbol, timeframe, iqs_result.direction, iqs_result.status,
            iqs_result.total_score, reason, current_price, iqs_result.breakdown,
        )

        if iqs_result.direction == "NEUTRAL" or iqs_result.status == "DESCARTADO":
            return None

        operations_today = await self._signal_repo.count_today_for_symbol(symbol)
        if (
            iqs_result.status == "CONFIRMADO"
            and operations_today >= settings.MAX_OPERATIONS_PER_SYMBOL_PER_DAY
        ):
            logger.info("Limite diário de operações atingido para %s", symbol)
            await self._record_scan(
                symbol, timeframe, iqs_result.direction, "LIMITE_ATINGIDO",
                iqs_result.total_score, "Limite diário de operações atingido para este par",
                current_price, iqs_result.breakdown,
            )
            raise RiskLimitExceededError(symbol)

        trade_plan = self._risk_service.build_trade_plan(
            direction=iqs_result.direction,
            candles=candles,
            atr=indicators.atr_14 or 0.0001,
        )

        if trade_plan.risk_reward < settings.MIN_RISK_REWARD:
            logger.debug("RR abaixo do mínimo para %s: %.2f", symbol, trade_plan.risk_reward)
            await self._record_scan(
                symbol, timeframe, iqs_result.direction, "DESCARTADO",
                iqs_result.total_score,
                f"RR abaixo do mínimo ({trade_plan.risk_reward:.1f} < {settings.MIN_RISK_REWARD})",
                current_price, iqs_result.breakdown,
            )
            return None

        probability = self._estimate_probability(iqs_result.total_score)
        expected_duration = self._estimate_duration(timeframe)

        signal = Signal(
            symbol=symbol,
            timeframe=timeframe,
            direction=SignalDirection(iqs_result.direction),
            status=SignalStatus(iqs_result.status),
            iqs_score=iqs_result.total_score,
            probability=probability,
            entry_price=trade_plan.entry_price,
            stop_loss=trade_plan.stop_loss,
            take_profit=trade_plan.take_profit,
            risk_reward=trade_plan.risk_reward,
            atr=indicators.atr_14 or 0.0,
            adx=indicators.adx_14 or 0.0,
            rsi=indicators.rsi_14 or 0.0,
            expected_duration_minutes=expected_duration,
            generated_at=datetime.now(timezone.utc),
            score_trend=iqs_result.breakdown.trend,
            score_momentum=iqs_result.breakdown.momentum,
            score_pullback=iqs_result.breakdown.pullback,
            score_volatility=iqs_result.breakdown.volatility,
            score_adx=iqs_result.breakdown.adx,
            score_liquidity=iqs_result.breakdown.liquidity,
            score_session=iqs_result.breakdown.session,
        )

        persisted = await self._signal_repo.create(signal)

        await self._notify(persisted)
        return persisted

    async def analyze_all(self, symbols: List[str], timeframe: str) -> List[Signal]:
        results: List[Signal] = []
        for symbol in symbols:
            try:
                signal = await self.analyze_symbol(symbol, timeframe)
                if signal:
                    results.append(signal)
            except RiskLimitExceededError as exc:
                logger.info(str(exc))
            except Exception as exc:
                logger.exception("Erro ao analisar %s (%s)", symbol, timeframe)
                await self._record_scan(
                    symbol, timeframe, "NEUTRAL", "ERRO", 0.0,
                    f"Falha ao obter/processar dados: {exc}",
                )
        return results

    async def _record_scan(
        self,
        symbol: str,
        timeframe: str,
        direction: str,
        status: str,
        iqs_score: float,
        reason: str,
        current_price: Optional[float] = None,
        breakdown=None,
    ) -> None:
        record = ScanRecord(
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            status=status,
            iqs_score=iqs_score,
            reason=reason,
            scanned_at=datetime.now(timezone.utc),
            current_price=current_price,
            breakdown=breakdown.model_dump() if breakdown is not None else None,
        )
        await scan_state_service.record(record)

    async def _notify(self, signal: Signal) -> None:
        if self._connection_manager:
            await self._connection_manager.broadcast(
                "new_signal",
                {
                    "id": signal.id,
                    "symbol": signal.symbol,
                    "timeframe": signal.timeframe,
                    "direction": signal.direction.value,
                    "status": signal.status.value,
                    "iqs_score": signal.iqs_score,
                    "probability": signal.probability,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "risk_reward": signal.risk_reward,
                    "expected_duration_minutes": signal.expected_duration_minutes,
                    "generated_at": signal.generated_at.isoformat(),
                },
            )

        if self._telegram_service and signal.status == SignalStatus.CONFIRMADO:
            await self._telegram_service.send_new_signal(signal)

    @staticmethod
    def _estimate_probability(iqs_score: float) -> float:
        """
        Probabilidade estimada da operação como função monotônica do IQS.
        Serve como heurística inicial; será substituída por um modelo de
        classificação treinado (ver tabela `indicators` como feature store)
        na Fase de Machine Learning.
        """
        probability = 50 + (iqs_score - 50) * 0.8
        return round(max(50.0, min(97.0, probability)), 1)

    @staticmethod
    def _estimate_duration(timeframe: str) -> int:
        mapping = {"M1": 15, "M5": 35, "M15": 90, "H1": 240}
        return mapping.get(timeframe, 60)
