"""Basic health check and auth tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "sentryflow-gateway"


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    user, password = admin_user
    resp = await client.post("/api/v1/auth/login", json={
        "username": user.username,
        "password": password,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    user, _ = admin_user
    resp = await client.post("/api/v1/auth/login", json={
        "username": user.username,
        "password": "wrong-password",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    resp = await client.post("/api/v1/auth/login", json={
        "username": "nonexistent",
        "password": "whatever",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client, admin_token):
    resp = await client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "security_admin"


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)  # no bearer token


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    resp = await client.get("/api/v1/auth/me", headers={
        "Authorization": "Bearer invalid-token-here",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ws_ticket_creation(client, admin_token):
    resp = await client.post("/api/v1/auth/ws-ticket", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "ticket" in data
    assert data["expires_in"] > 0
