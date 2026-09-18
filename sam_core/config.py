"""
Configuration and settings management for Project Sam.
Uses pydantic-settings for robust environment variable validation.
"""
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Sam Core."""

    # Application Information
    app_name: str = Field(default="Sam", description="Application display name")
    version: str = Field(default="0.1.0", description="Sam Core version")
    environment: Literal["development", "production", "test"] = Field(
        default="development", description="Runtime environment"
    )
    debug: bool = Field(default=False, description="Enable development debug mode")

    # Networking & IPC
    host: str = Field(
        default="127.0.0.1",
        description="Local host binding for IPC server (restricted to localhost in Phase 1)",
    )
    port: int = Field(default=8765, description="Port for IPC server")
    ws_path: str = Field(default="/ws/ipc", description="WebSocket IPC endpoint path")
    ws_ping_interval: int = Field(default=20, description="WebSocket ping keepalive interval in seconds")
    ws_ping_timeout: int = Field(default=20, description="WebSocket ping timeout in seconds")
    ws_max_message_size: int = Field(
        default=1048576, description="Max incoming WebSocket message size in bytes (1MB default)"
    )
    auth_token: str | None = Field(
        default=None,
        description="Optional shared secret token for authenticating IPC clients",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging verbosity (DEBUG, INFO, WARNING, ERROR)")

    # Data & Storage Directories
    data_dir: Path = Field(
        default=Path.home() / ".sam",
        description="Base storage directory for local persistent data",
    )

    # AI / LLM Providers
    default_provider: str = Field(
        default="gemini",
        validation_alias=AliasChoices("default_provider", "DEFAULT_PROVIDER"),
        description="Default AI provider (gemini, openai, groq, ollama, mock)",
    )
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("gemini_api_key", "GEMINI_API_KEY", "google_api_key", "GOOGLE_API_KEY"),
        description="Gemini API key (GEMINI_API_KEY or GOOGLE_API_KEY)",
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        validation_alias=AliasChoices("gemini_model", "GEMINI_MODEL"),
        description="Gemini model name",
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("openai_api_key", "OPENAI_API_KEY"),
        description="OpenAI API key",
    )
    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("groq_api_key", "GROQ_API_KEY"),
        description="Groq API key",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("anthropic_api_key", "ANTHROPIC_API_KEY"),
        description="Anthropic API key",
    )

    # Placeholders for future Safety & Permissions settings (Phase 2+)
    require_confirmation_for_tier3: bool = Field(
        default=True,
        description="Whether Tier 3 critical operations require explicit confirmation",
    )
    confirmation_timeout_seconds: int = Field(
        default=60, description="Seconds before an unconfirmed action expires"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @field_validator("host")
    @classmethod
    def validate_host_security(cls, v: str) -> str:
        # Phase 1 safety rule: bind to localhost only
        allowed_hosts = {"127.0.0.1", "localhost", "::1"}
        if v.strip() not in allowed_hosts:
            raise ValueError(
                f"Security restriction: Phase 1 IPC server must bind to localhost ({allowed_hosts}), got '{v}'"
            )
        return v.strip()

    @property
    def db_path(self) -> Path:
        """Path to persistent SQLite database."""
        path = self.data_dir / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path / "sam.sqlite3"

    @property
    def logs_dir(self) -> Path:
        """Path to persistent logs directory."""
        path = self.data_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path


# Factory to create settings or retrieve singleton
def get_settings() -> Settings:
    """Return validated application settings."""
    return Settings()


# Default singleton instance
settings = get_settings()
