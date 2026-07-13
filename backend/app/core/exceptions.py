"""
Hierarquia de exceções de domínio e handlers globais de erro para a API.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class ForexRadarError(Exception):
    """Exceção base de domínio do Forex Radar AI."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SymbolNotSupportedError(ForexRadarError):
    def __init__(self, symbol: str):
        super().__init__(f"Símbolo não suportado: {symbol}", status.HTTP_422_UNPROCESSABLE_ENTITY)


class InsufficientDataError(ForexRadarError):
    def __init__(self, symbol: str, timeframe: str):
        super().__init__(
            f"Dados insuficientes para calcular indicadores em {symbol} ({timeframe})",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class RiskLimitExceededError(ForexRadarError):
    def __init__(self, symbol: str):
        super().__init__(
            f"Limite de operações diárias atingido para {symbol}",
            status.HTTP_409_CONFLICT,
        )


class EntityNotFoundError(ForexRadarError):
    def __init__(self, entity: str, identifier: str):
        super().__init__(f"{entity} não encontrado: {identifier}", status.HTTP_404_NOT_FOUND)


class AuthenticationError(ForexRadarError):
    def __init__(self, message: str = "Credenciais inválidas"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ForexRadarError)
    async def forex_radar_exception_handler(request: Request, exc: ForexRadarError):
        logger.warning("Erro de domínio: %s | path=%s", exc.message, request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.__class__.__name__, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Erro não tratado em %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "InternalServerError", "message": "Erro interno no servidor."},
        )
