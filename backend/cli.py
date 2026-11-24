"""SentryFlow CLI — initialization and management commands."""
from __future__ import annotations

import asyncio
import secrets
import sys
import uuid
from datetime import UTC, datetime

from argon2 import PasswordHasher

ph = PasswordHasher()


async def _init_admin():
    from sqlalchemy import select

    from backend.database import async_session_factory, init_db
    from backend.models.user import User

    await init_db()

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.role == "security_admin").limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Security admin already exists: {existing.username}")
            return

        password = secrets.token_urlsafe(16)
        now = datetime.now(UTC).isoformat()
        user = User(
            id=str(uuid.uuid4()),
            username="admin",
            password_hash=ph.hash(password),
            role="security_admin",
            display_name="System Administrator",
            active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        await session.commit()

        print("=" * 50)
        print("SentryFlow — Initial Admin Created")
        print("=" * 50)
        print("Username: admin")
        print(f"Password: {password}")
        print("Role:     security_admin")
        print("=" * 50)
        print("SAVE THIS PASSWORD. It will not be shown again.")
        print("=" * 50)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m backend.cli <command>")
        print("Commands: init, generate-data")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        asyncio.run(_init_admin())
    elif command == "generate-data":
        from backend.simulation.data_generator import generate_all
        asyncio.run(generate_all())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
