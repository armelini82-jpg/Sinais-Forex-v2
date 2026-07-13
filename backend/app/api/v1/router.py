from fastapi import APIRouter

from app.api.v1.endpoints import auth, backtest, operations, pairs, signals, statistics, websocket

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(signals.router)
api_router.include_router(operations.router)
api_router.include_router(statistics.router)
api_router.include_router(pairs.router)
api_router.include_router(backtest.router)
api_router.include_router(websocket.router)
