"""Shared test fixtures."""

import os

# Set test environment variables BEFORE any app imports so that
# the frozen Settings dataclass picks up the correct values.
os.environ.setdefault("DEV_ADMIN_PASSWORD", "admin123")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_daily_headlines.db")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.auth.service import seed_admin_user


@pytest.fixture()
def test_db():
    """Create a test database session and override the app dependency."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed admin user in test DB
    db = TestingSession()
    seed_admin_user(db)
    db.close()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSession
    app.dependency_overrides.clear()
