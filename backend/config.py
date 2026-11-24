from __future__ import annotations

import secrets
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Database
    database_url: str = "sqlite:///./sentryflow.db"

    # JWT
    jwt_secret_key: str = secrets.token_hex(32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_hours: int = 24

    # WebSocket tickets
    ws_ticket_lifetime_seconds: int = 30

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi4-mini:latest"

    # Cryptography
    pqc_mode: str = "optional"  # optional | required | disabled

    # HMAC key for bank-account fingerprints (hex)
    bank_fingerprint_key: str = secrets.token_hex(32)

    # AES-256-GCM key for field-level encryption (hex)
    field_encryption_key: str = secrets.token_hex(32)

    # Policy
    default_policy_file: str = "data/policies/default.yaml"

    # Logging
    log_level: str = "INFO"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent


settings = Settings()
