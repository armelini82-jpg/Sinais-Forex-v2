"""
Dependências compartilhadas do FastAPI (Dependency Injection).
Compõe repositórios e services a partir da sessão de banco por requisição.
"""
from typing import AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.factories.market_data_factory import MarketDataProviderFactory
from app.interfaces.market_data_interface import IMarketDataProvider
from app.models.user import User
from app.repositories.candle_repository import CandleRepository
from app.repositories.operation_repository import OperationRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.backtest_engine import BacktestEngine
from app.services.operation_service import OperationService
from app.services.signal_engine import SignalEngine
from app.services.statistics_service import StatisticsService
from app.services.telegram_service import telegram_service
from app.services.websocket_manager import connection_manager


def get_market_data_provider() -> IMarketDataProvider:
    return MarketDataProviderFactory.create()


def get_signal_repository(session: AsyncSession = Depends(get_db)) -> SignalRepository:
    return SignalRepository(session)


def get_candle_repository(session: AsyncSession = Depends(get_db)) -> CandleRepository:
    return CandleRepository(session)


def get_operation_repository(session: AsyncSession = Depends(get_db)) -> OperationRepository:
    return OperationRepository(session)


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_signal_engine(
    market_data: IMarketDataProvider = Depends(get_market_data_provider),
    signal_repo: SignalRepository = Depends(get_signal_repository),
) -> SignalEngine:
    return SignalEngine(
        market_data_provider=market_data,
        signal_repository=signal_repo,
        telegram_service=telegram_service,
        connection_manager=connection_manager,
    )


def get_statistics_service() -> StatisticsService:
    return StatisticsService()


def get_auth_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(user_repo)


def get_operation_service(
    operation_repo: OperationRepository = Depends(get_operation_repository),
    signal_repo: SignalRepository = Depends(get_signal_repository),
) -> OperationService:
    return OperationService(operation_repo, signal_repo)


def get_backtest_engine(
    market_data: IMarketDataProvider = Depends(get_market_data_provider),
) -> BacktestEngine:
    return BacktestEngine(market_data_provider=market_data)


async def get_current_user(
    authorization: str = Header(default=""),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Token de autenticação ausente.")

    token = authorization.removeprefix("Bearer ").strip()
    username = decode_access_token(token)
    if not username:
        raise AuthenticationError("Token inválido ou expirado.")

    user = await user_repo.get_by_username(username)
    if not user:
        raise AuthenticationError("Usuário do token não encontrado.")
    return user
