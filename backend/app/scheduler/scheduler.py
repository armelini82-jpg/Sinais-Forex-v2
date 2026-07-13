"""
Scheduler (APScheduler) responsável por rodar o scan de mercado continuamente
em background, um job por timeframe monitorado.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.factories.market_data_factory import MarketDataProviderFactory
from app.repositories.operation_repository import OperationRepository
from app.repositories.signal_repository import SignalRepository
from app.services.operation_service import OperationMonitorService
from app.services.signal_engine import SignalEngine
from app.services.telegram_service import telegram_service
from app.services.websocket_manager import connection_manager

logger = get_logger(__name__)

_TIMEFRAME_SCAN_SECONDS = {"M1": 60, "M5": 120, "M15": 300, "H1": 600}

_OPERATION_MONITOR_SECONDS = 60

scheduler = AsyncIOScheduler()


async def _scan_timeframe(timeframe: str) -> None:
    market_data_provider = MarketDataProviderFactory.create()

    async with AsyncSessionLocal() as session:
        try:
            signal_repo = SignalRepository(session)
            engine = SignalEngine(
                market_data_provider=market_data_provider,
                signal_repository=signal_repo,
                telegram_service=telegram_service,
                connection_manager=connection_manager,
            )
            signals = await engine.analyze_all(settings.symbols_list, timeframe)
            await session.commit()
            if signals:
                logger.info("Scan %s: %d sinal(is) gerado(s)", timeframe, len(signals))
        except Exception:
            await session.rollback()
            logger.exception("Erro durante o scan de %s", timeframe)


a sync def _monitor_open_operations() -> None:
    """
    Verifica as operações que o usuário confirmou ter aberto e fecha
    automaticamente as que já bateram Take Profit ou Stop Loss, com base no
    preço real de mercado — sem exigir acesso à conta/corretora.
    """
    market_data_provider = MarketDataProviderFactory.create()

    async with AsyncSessionLocal() as session:
        try:
            operation_repo = OperationRepository(session)
            monitor = OperationMonitorService(market_data_provider, operation_repo)
            closed = await monitor.check_open_operations()
            await session.commit()
            if closed:
                logger.info("%d operação(ões) fechada(s) automaticamente", closed)
                await connection_manager.broadcast("operation_update", {"closed": closed})
                await connection_manager.broadcast("statistics_update", {})
        except Exception:
            await session.rollback()
            logger.exception("Erro ao monitorar operações abertas")


def start_scheduler() -> None:
    if scheduler.running:
        return

    for timeframe in settings.timeframes_list:
        interval_seconds = _TIMEFRAME_SCAN_SECONDS.get(timeframe, 60)
        scheduler.add_job(
            _scan_timeframe,
            trigger=IntervalTrigger(seconds=interval_seconds),
            args=[timeframe],
            id=f"scan_{timeframe}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info("Job de scan agendado: %s a cada %ds", timeframe, interval_seconds)

    scheduler.add_job(
        _monitor_open_operations,
        trigger=IntervalTrigger(seconds=_OPERATION_MONITOR_SECONDS),
        id="monitor_operations",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("Job de monitoramento de operações agendado a cada %ds", _OPERATION_MONITOR_SECONDS)

    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
