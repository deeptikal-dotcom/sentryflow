"""Shared test fixtures for SentryFlow."""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base, get_session
from backend.main import create_app

TEST_DB_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def app(db_engine):
    _app = create_app()
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_session():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[get_session] = _override_session
    return _app


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create an admin user and return (user, password)."""
    from argon2 import PasswordHasher
    from backend.models.user import User

    ph = PasswordHasher()
    password = "test-admin-password-123"
    now = datetime.now(timezone.utc).isoformat()
    user = User(
        id=str(uuid.uuid4()),
        username="testadmin",
        password_hash=ph.hash(password),
        role="security_admin",
        display_name="Test Admin",
        active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    return user, password


@pytest_asyncio.fixture
async def admin_token(client, admin_user):
    """Get a valid JWT access token for the admin user."""
    user, password = admin_user
    resp = await client.post("/api/v1/auth/login", json={
        "username": user.username,
        "password": password,
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
