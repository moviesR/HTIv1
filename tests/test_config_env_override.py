"""
Test config environment variable overrides.

Verifies that ENV_BACKEND overrides config values.
"""
import os
import pytest
from hti.core.config import load_system_slice


def test_env_backend_override(monkeypatch):
    """ENV_BACKEND should override cfg.env.backend."""
    load_system_slice.cache_clear()

    monkeypatch.setenv("ENV_BACKEND", "DmControlEnv")

    cfg = load_system_slice("configs/system_slice.yaml")

    assert cfg.env.backend == "DmControlEnv"

    load_system_slice.cache_clear()


def test_no_env_override_uses_config_defaults():
    """Without env vars, use config file values."""
    load_system_slice.cache_clear()

    # Ensure no env vars are set
    if "ENV_BACKEND" in os.environ:
        del os.environ["ENV_BACKEND"]

    cfg = load_system_slice("configs/system_slice.yaml")

    # Should use values from config file
    assert cfg.env.backend == "NullEnv"  # From config

    load_system_slice.cache_clear()
