from fastapi import APIRouter
from app.api.routes import health, datasets, ai, query, export

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(export.router, prefix="/export", tags=["export"])



