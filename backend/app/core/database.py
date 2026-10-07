import logging
from typing import Generator
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger("sqlens.database")

def format_database_url(url_str: str) -> str:
    """Format and normalize database URL for PostgreSQL/Supabase compatibility."""
    if not url_str:
        return "sqlite:///./sqlens.db"

    url_str = url_str.strip()

    # Convert legacy postgres:// prefix to postgresql://
    if url_str.startswith("postgres://"):
        url_str = "postgresql://" + url_str[len("postgres://"):]

    if url_str.startswith("sqlite"):
        return url_str

    # Ensure sslmode=require for remote PostgreSQL / Supabase
    if "postgresql" in url_str and "localhost" not in url_str and "127.0.0.1" not in url_str and "sslmode=" not in url_str:
        delimiter = "&" if "?" in url_str else "?"
        url_str = f"{url_str}{delimiter}sslmode=require"

    return url_str

def create_app_engine(raw_url: str):
    """Initialize database engine with fallback to local SQLite if PostgreSQL is unavailable."""
    db_url = format_database_url(raw_url)
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    
    try:
        eng = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args=connect_args
        )
        # Test connection
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Database connected using dialect: {eng.name}")
        return eng
    except Exception as e:
        if not db_url.startswith("sqlite"):
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database.")
            fallback_url = "sqlite:///./sqlens.db"
            return create_engine(fallback_url, pool_pre_ping=True, connect_args={"check_same_thread": False})
        else:
            raise e

engine = create_app_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator:
    """FastAPI dependency yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection() -> bool:
    """Verify application database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def create_dataset_schema(schema_name: str) -> None:
    """
    Create an isolated PostgreSQL schema for a dataset.
    If sqlite is used, schema creation is a no-op as tables will use schema_name prefix.
    """
    if engine.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            conn.commit()

def drop_dataset_schema(schema_name: str) -> None:
    """
    Safely drop an isolated dataset schema and all its tables (CASCADE).
    """
    if engine.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
            conn.commit()
    elif engine.name == "sqlite":
        inspector = inspect(engine)
        with engine.connect() as conn:
            for table_name in inspector.get_table_names():
                if table_name.startswith(f"{schema_name}__"):
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
            conn.commit()
