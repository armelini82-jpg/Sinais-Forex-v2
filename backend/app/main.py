"""
Ponto de entrada da aplicação Forex Radar AI.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.scheduler.scheduler import shutdown_scheduler, start_scheduler

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando %s (env=%s)...", settings.APP_NAME, settings.APP_ENV)
    start_scheduler()
    yield
    logger.info("Encerrando %s...", settings.APP_NAME)
    shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    description="Scanner profissional de Day Trade em Forex com IQS (Intelligent Quality Score).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check simples para orquestração (Docker/Kubernetes)."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
