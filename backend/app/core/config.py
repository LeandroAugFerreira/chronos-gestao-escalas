"""Chronos 1.0: configuração tipada; nenhuma chave insegura de reserva."""

import os
import sys
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3]
PRODUCT_NAME = "Chronos"
PRODUCT_VERSION = "1.0"
PRODUCT_TITLE = "Chronos 1.0 — Gestão Inteligente de Jornadas e Escalas"
DEMO_FILE = PROJECT_ROOT / "data" / "synthetic" / "hospital_horizonte.json"
ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv("CHRONOS_ALLOWED_ORIGINS", "http://127.0.0.1:5187,http://localhost:5187").split(",")
    if origin.strip()
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHRONOS_", env_file=None if getattr(sys, "frozen", False) else PROJECT_ROOT / ".env", extra="ignore", populate_by_name=True, hide_input_in_errors=True)

    database_url: SecretStr = Field(default=SecretStr(""), validation_alias=AliasChoices("CHRONOS_DATABASE_URL", "DATABASE_URL"))
    jwt_secret: SecretStr = Field(default=SecretStr(""), validation_alias=AliasChoices("CHRONOS_JWT_SECRET", "JWT_SECRET"))
    environment: str = "development"
    allow_sqlite: bool = False
    allowed_origins: str = ",".join(ALLOWED_ORIGINS)
    access_minutes: int = Field(default=15, ge=1, le=60)
    refresh_days: int = Field(default=7, ge=1, le=30)
    login_limit: int = Field(default=8, ge=1, le=100)
    login_window_seconds: int = Field(default=300, ge=1, le=3600)
    cookie_secure: bool = False
    max_request_bytes: int = Field(default=1048576, ge=1024, le=8388608)
    request_body_seconds: int = Field(default=10, ge=1, le=60)
    n8n_webhook_base_url: str = ""
    n8n_outbound_token: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def secure_settings(self):
        if self.environment not in {"development", "test", "production"}:
            raise ValueError("Ambiente inválido")
        secret = self.jwt_secret.get_secret_value()
        if secret and len(secret) < 32:
            raise ValueError("JWT_SECRET deve possuir pelo menos 32 caracteres")
        if self.environment == "production" and (not secret or not self.database_url.get_secret_value()):
            raise ValueError("Produção exige banco e segredo JWT configurados")
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("Produção exige cookies Secure e acesso HTTPS")
        from urllib.parse import urlsplit
        normalized = []
        for value in self.allowed_origins.split(","):
            value = value.strip().rstrip("/")
            if not value:
                continue
            origin = urlsplit(value)
            if (origin.scheme not in {"http", "https"} or not origin.hostname or origin.username or origin.password or
                    origin.path or origin.query or origin.fragment or "*" in value):
                raise ValueError("Informe origens HTTP(S) explícitas, sem caminhos ou credenciais")
            origin.port  # Validate port without logging a potentially sensitive URL.
            if self.environment == "production" and origin.scheme != "https":
                raise ValueError("Produção exige origens HTTPS")
            normalized.append(value)
        if not normalized:
            raise ValueError("Configure ao menos uma origem explícita")
        self.allowed_origins = ",".join(normalized)
        if self.n8n_webhook_base_url:
            from urllib.parse import urlsplit
            endpoint = urlsplit(self.n8n_webhook_base_url)
            if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "::1"} or endpoint.path.rstrip("/") != "/webhook/chronos" or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
                raise ValueError("Esta fase permite somente webhook n8n em loopback, caminho /webhook/chronos")
            if self.environment == "production" or len(self.n8n_outbound_token.get_secret_value()) < 32:
                raise ValueError("Integração local n8n exige ambiente development/test e token com ao menos 32 caracteres")
            if self.environment == "development":
                import json
                policy = json.loads((PROJECT_ROOT / "automation/n8n/security-status.json").read_text(encoding="utf-8"))
                if policy.get("execution_allowed") is not True:
                    raise ValueError("Partida n8n bloqueada pela auditoria da Fase 9; use automações locais até corrigir e revisar as dependências")
        return self
