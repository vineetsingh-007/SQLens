import os
import tempfile
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "SQLens"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/sqlens")
    
    # Upload limits & directories
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIRECTORY: str = os.getenv(
        "UPLOAD_DIRECTORY",
        str(Path(tempfile.gettempdir()) / "sqlens_uploads")
    )
    SAMPLE_DATA_DIRECTORY: str = str(BASE_DIR / "data" / "sample")
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # AI Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")



    GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))
    GEMINI_MAX_OUTPUT_TOKENS: int = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2048"))

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()

