import logging
import os
import re
from typing import Generator
from urllib.parse import quote_plus, unquote
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger("sqlens.database")

def format_database_url(url_str: str) -> str:
    """Format, normalize, add sslmode=require if missing, and encode credentials safely."""
    if not url_str:
        return "sqlite:///./sqlens.db"

    url_str = url_str.strip()

    # Convert legacy postgres:// prefix to postgresql://
    if url_str.startswith("postgres://"):
        url_str = "postgresql://" + url_str[len("postgres://"):]

    if url_str.startswith("sqlite"):
        return url_str

    # Ensure sslmode=require for PostgreSQL if not specified
    if "postgresql" in url_str and "sslmode=" not in url_str:
        delimiter = "&" if "?" in url_str else "?"
        url_str = f"{url_str}{delimiter}sslmode=require"

    try:
        url_obj = make_url(url_str)
        return str(url_obj)
    except Exception:
        # Fallback regex parser for passwords containing raw unencoded special characters
        try:
            pattern = r"^(postgresql(?:\+[a-z0-9]+)?):\/\/([^:]+):(.*)@([^:\/\?]+)(?::(\d+))?\/(.+)$"
            match = re.match(pattern, url_str)
            if match:
                scheme, user, password, host, port, rest = match.groups()
                encoded_user = quote_plus(unquote(user))
                encoded_pass = quote_plus(unquote(password))
                port_str = f":{port}" if port else ""
                return f"{scheme}://{encoded_user}:{encoded_pass}@{host}{port_str}/{rest}"
        except Exception as parse_err:
            logger.warning(f"Unable to parse custom database URL: {parse_err}")
        return url_str

def create_app_engine(raw_url: str):
    """Initialize database engine with safe pooling and sslmode=require for Supabase PostgreSQL."""
    db_url = format_database_url(raw_url)
    is_sqlite = db_url.startswith("sqlite")

    connect_args = {"check_same_thread": False} if is_sqlite else {}
    
    if not is_sqlite and "sslmode" not in db_url:
        connect_args["sslmode"] = "require"

    engine_kwargs = {
        "pool_pre_ping": True,
        "connect_args": connect_args
    }

    if not is_sqlite:
        engine_kwargs["pool_recycle"] = 300
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10

    try:
        eng = create_engine(db_url, **engine_kwargs)
        # Test initial connection
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Database connected successfully using dialect: {eng.name}")
        return eng
    except Exception as e:
        logger.error(f"Database connection attempt failed: {e}")
        # If DATABASE_URL was explicitly provided as PostgreSQL, keep PostgreSQL engine so connection retries or detailed errors surface!
        if not is_sqlite and raw_url and ("postgresql" in raw_url or "postgres" in raw_url):
            logger.warning("Retaining PostgreSQL engine for connection retries on serverless invocations.")
            return create_engine(db_url, **engine_kwargs)
        else:
            fallback_url = "sqlite:///./sqlens.db"
            return create_engine(fallback_url, pool_pre_ping=True, connect_args={"check_same_thread": False})

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
    """Verify application database connectivity without exposing connection details."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connectivity check failed: {e}")
        return False

def create_dataset_schema(schema_name: str) -> None:
    """
    Create an isolated PostgreSQL schema for a dataset.
    If sqlite is used, schema creation is a no-op as tables use schema_name prefix.
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
