"""
Unit tests for structured logging and security masking.
"""
from sam_core.logger import (
    clear_correlation_id,
    get_correlation_id,
    mask_sensitive_data,
    set_correlation_id,
)


def test_correlation_id_context():
    assert get_correlation_id() is None
    set_correlation_id("req-12345")
    assert get_correlation_id() == "req-12345"
    clear_correlation_id()
    assert get_correlation_id() is None


def test_mask_sensitive_data():
    raw_log = "User provided api_key=sk-1234567890abcdef and secret: 'my_super_secret_token'"
    masked = mask_sensitive_data(raw_log)
    assert "sk-1234567890abcdef" not in masked
    assert "my_super_secret_token" not in masked
    assert "***MASKED***" in masked
