"""
Unit tests for configuration system.
"""
import pytest
from pydantic import ValidationError

from sam_core.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.app_name == "Sam"
    assert settings.version == "0.1.0"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8765
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.ws_path == "/ws/ipc"
    assert settings.require_confirmation_for_tier3 is True
    assert settings.db_path.name == "sam.sqlite3"
    assert settings.logs_dir.name == "logs"


def test_settings_host_security_validation():
    # In Phase 1, host must be restricted to localhost
    with pytest.raises(ValidationError) as exc:
        Settings(host="0.0.0.0")
    assert "Security restriction" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        Settings(host="192.168.1.50")
    assert "Security restriction" in str(exc.value)


def test_settings_port_validation():
    with pytest.raises(ValidationError):
        Settings(port=0)

    with pytest.raises(ValidationError):
        Settings(port=70000)
