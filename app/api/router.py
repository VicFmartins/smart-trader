from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.api.routes import accounts, assets, clients, etl, health, ingestion_reports, llm_health, ollama_health, pdf_imports, positions, reports, taxes, trade_analytics, trades, upload
from app.api.routes import auth


api_router = APIRouter()
protected_dependencies = [Depends(get_current_user)]

api_router.include_router(health.router, tags=["health"])
api_router.include_router(ollama_health.router, tags=["health"])
api_router.include_router(llm_health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(upload.router, tags=["upload"], dependencies=protected_dependencies)
api_router.include_router(pdf_imports.router, tags=["pdf-imports"], dependencies=protected_dependencies)
api_router.include_router(ingestion_reports.router, tags=["ingestion-reports"], dependencies=protected_dependencies)
api_router.include_router(clients.router, prefix="/clients", tags=["clients"], dependencies=protected_dependencies)
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"], dependencies=protected_dependencies)
api_router.include_router(assets.router, prefix="/assets", tags=["assets"], dependencies=protected_dependencies)
api_router.include_router(positions.router, prefix="/positions", tags=["positions"], dependencies=protected_dependencies)
api_router.include_router(trade_analytics.router, tags=["trade-analytics"], dependencies=protected_dependencies)
api_router.include_router(taxes.router, tags=["taxes"], dependencies=protected_dependencies)
api_router.include_router(trades.router, tags=["trades"], dependencies=protected_dependencies)
api_router.include_router(etl.router, prefix="/etl", tags=["etl"], dependencies=protected_dependencies)
api_router.include_router(reports.router, tags=["reports"], dependencies=protected_dependencies)
