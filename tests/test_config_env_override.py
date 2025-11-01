"""
Test config environment variable overrides.

Verifies that ENV_BACKEND and ENV_FAIL_FAST override config values.
"""
import os
import pytest
from hti.core.config import load_system_slice


def test_env_backend_override(monkeypatch):
    """ENV_BACKEND should override cfg.env.backend."""
    # Clear cache
    load_system_slice.cache_clear()

    # Set environment variable
    monkeypatch.setenv("ENV_BACKEND", "DmControlEnv")

    cfg = load_system_slice("configs/system_slice.yaml")

    assert cfg.env.backend == "DmControlEnv"

    # Clean up for other tests
    load_system_slice.cache_clear()


def test_env_fail_fast_override_true(monkeypatch):
    """ENV_FAIL_FAST='true' should override cfg.env.fail_fast."""
    load_system_slice.cache_clear()

    monkeypatch.setenv("ENV_FAIL_FAST", "true")

    cfg = load_system_slice("configs/system_slice.yaml")

    assert cfg.env.fail_fast is True

    load_system_slice.cache_clear()


def test_env_fail_fast_override_false(monkeypatch):
    """ENV_FAIL_FAST='false' should override cfg.env.fail_fast."""
    load_system_slice.cache_clear()

    monkeypatch.setenv("ENV_FAIL_FAST", "false")

    cfg = load_system_slice("configs/system_slice.yaml")

    assert cfg.env.fail_fast is False

    load_system_slice.cache_clear()


def test_both_env_overrides(monkeypatch):
    """Both ENV_BACKEND and ENV_FAIL_FAST can be used together."""
    load_system_slice.cache_clear()

    monkeypatch.setenv("ENV_BACKEND", "NullEnv")
    monkeypatch.setenv("ENV_FAIL_FAST", "false")

    cfg = load_system_slice("configs/system_slice.yaml")

    assert cfg.env.backend == "NullEnv"
    assert cfg.env.fail_fast is False

    load_system_slice.cache_clear()


def test_no_env_override_uses_config_defaults():
    """Without env vars, use config file values."""
    load_system_slice.cache_clear()

    # Ensure no env vars are set
    if "ENV_BACKEND" in os.environ:
        del os.environ["ENV_BACKEND"]
    if "ENV_FAIL_FAST" in os.environ:
        del os.environ["ENV_FAIL_FAST"]

    cfg = load_system_slice("configs/system_slice.yaml")

    # Should use values from config file
    assert cfg.env.backend == "NullEnv"  # From config
    assert cfg.env.fail_fast is True      # From config

    load_system_slice.cache_clear()
