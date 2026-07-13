"""
Configuração central do Forex Radar AI.
Todo o sistema lê parâmetros exclusivamente através desta classe,
que carrega valores do arquivo .env (ou variáveis de ambiente do container).
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Forex Radar AI"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key-in-production"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://forexradar:forexradar_secret@db:5432/forex_radar_ai"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Market
    SYMBOLS: str = "EURUSD,GBPUSD,USDJPY,AUDUSD,NZDUSD,USDCAD,USDCHF,EURJPY,GBPJPY,XAUUSD"
    TIMEFRAMES: str = "M1,M5,M15,H1"
    DATA_PROVIDER: str = "simulated"
    MARKET_DATA_API_KEY: str = ""

    # Strategy / Risk Management
    RISK_PER_TRADE_PERCENT: float = 1.0
    MIN_RISK_REWARD: float = 2.0
    MAX_OPERATIONS_PER_SYMBOL_PER_DAY: int = 3
    IQS_MIN_SIGNAL: int = 90
    IQS_MIN_PREPARING: int = 80

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_ENABLED: bool = False

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    @property
    def symbols_list(self) -> List[str]:
        return [s.strip().upper() for s in self.SYMBOLS.split(",") if s.strip()]

    @property
    def timeframes_list(self) -> List[str]:
        return [t.strip().upper() for t in self.TIMEFRAMES.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
