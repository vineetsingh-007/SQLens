import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.router import api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sqlens")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SQLens metadata database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("SQLens metadata tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing metadata database tables: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS dynamically for local ports and Vercel domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["http://localhost:5173"],
    allow_origin_regex=r"(https?://.*\.vercel\.app)|(http://(localhost|127\.0\.0\.1)(:\d+)?)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
@app.get("/api")
@app.get("/api/")
def root():
    return {
        "status": "healthy",
        "service": "SQLens API",
        "health_check": "/api/health",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
