"""
Pytest configuration and shared fixtures for RecoverAI backend tests.
"""
import asyncio
import sys
import os
import pytest
import pytest_asyncio
from decimal import Decimal
from typing import AsyncGenerator

# Ensure backend module path is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Override DB to in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AI_PROVIDER"] = "rule_based"
os.environ["PAYMENT_PROVIDER"] = "simulation"
os.environ["AUTO_SEED_DEMO_DATA"] = "false"  # Tests manage their own fixtures

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from httpx import AsyncClient, ASGITransport

from app.core.database import Base
from app.main import app
from app.core.database import get_db


# ── In-memory test engine ─────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create fresh tables and return a test DB session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX async client wired to FastAPI with test DB."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def sample_transaction_data():
    return {
        "external_id": "TEST-001",
        "customer_ref": "CUST-0001",
        "amount": "5000.00",
        "currency": "INR",
        "transaction_type": "payment",
        "status": "failed",
        "failure_reason": "Gateway timeout",
        "failure_category": "temp_failure",
        "retry_count": "0",
    }


@pytest.fixture
def fraud_transaction_data():
    return {
        "external_id": "TEST-002",
        "customer_ref": "CUST-0002",
        "amount": "15000.00",
        "currency": "INR",
        "transaction_type": "payment",
        "status": "failed",
        "failure_reason": "Suspected fraud",
        "failure_category": "fraud",
        "retry_count": "0",
    }
