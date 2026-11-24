from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_session
from backend.models.user import User

router = APIRouter()
ph = PasswordHasher()
security = HTTPBearer()

VALID_ROLES = {
    "security_admin",
    "procurement_operator",
    "finance_approver",
    "security_analyst",
    "auditor",
}

# In-memory store for single-use WebSocket tickets
_ws_tickets: dict[str, dict] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class WSTicketResponse(BaseModel):
    ticket: str
    expires_in: int


def _create_token(user_id: str, role: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "role": role,
        "token_type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("token_type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def require_role(*roles: str):
    async def _check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not authorized. Required: {roles}",
            )
        return user
    return _check


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: Annotated[AsyncSession, Depends(get_session)]):
    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    try:
        ph.verify(user.password_hash, body.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if ph.check_needs_rehash(user.password_hash):
        user.password_hash = ph.hash(body.password)
        await session.commit()

    access_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    refresh_expires = timedelta(hours=settings.jwt_refresh_token_expire_hours)

    return TokenResponse(
        access_token=_create_token(user.id, user.role, "access", access_expires),
        refresh_token=_create_token(user.id, user.role, "refresh", refresh_expires),
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/ws-ticket", response_model=WSTicketResponse)
async def create_ws_ticket(user: Annotated[User, Depends(get_current_user)]):
    ticket = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.ws_ticket_lifetime_seconds)
    _ws_tickets[ticket] = {
        "user_id": user.id,
        "role": user.role,
        "expires_at": expires_at,
    }
    return WSTicketResponse(ticket=ticket, expires_in=settings.ws_ticket_lifetime_seconds)


def validate_ws_ticket(ticket: str) -> dict | None:
    data = _ws_tickets.pop(ticket, None)  # single-use: remove on retrieval
    if data is None:
        return None
    if datetime.now(UTC) > data["expires_at"]:
        return None
    return data


@router.get("/me")
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name,
        "active": user.active,
    }
