from fastapi import APIRouter
from app.schemas.dataset import HealthResponse
from app.core.database import check_db_connection

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint verifying API service and PostgreSQL database status.
    """
    db_ok = check_db_connection()
    db_status = "connected" if db_ok else "disconnected"
    overall_status = "ok" if db_ok else "degraded"

    return HealthResponse(
        status=overall_status,
        service="SQLens backend",
        database=db_status
    )
