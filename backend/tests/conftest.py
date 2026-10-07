import os
import sys
import pytest
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Configure test environment variables before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test_sqlens.db"
os.environ["MAX_UPLOAD_SIZE_MB"] = "5"
os.environ["UPLOAD_DIRECTORY"] = str(backend_dir / "test_uploads")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db, engine as app_engine
import app.models  # Ensures all ORM models (Dataset, QueryHistory) are registered
from app.main import app

# Create test engine and session
test_engine = create_engine("sqlite:///./test_sqlens.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test database tables and cleanup after tests."""
    Base.metadata.create_all(bind=test_engine)
    os.makedirs(os.environ["UPLOAD_DIRECTORY"], exist_ok=True)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_sqlens.db"):
        try:
            os.remove("./test_sqlens.db")
        except Exception:
            pass

@pytest.fixture
def db_session():
    """Yield database session for direct model manipulation in tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db_session):
    """Yield FastAPI TestClient overriding get_db dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
