"""
Test strict fail-fast enforcement for DmControlEnv backend.

Verifies that the system raises exceptions when DmControlEnv is requested
but dm_control or assets are unavailable (no fallback exists).
"""
import pytest
from pathlib import Path
from unittest.mock import patch
from hti.core.config import load_system_slice
from hti.env.dm_env_loader import load_from_config, _DM_CONTROL_AVAILABLE


def test_raises_when_dm_control_missing():
    """When DmControlEnv requested but dm_control missing, should raise RuntimeError."""
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"

    # Mock dm_control as unavailable
    with patch('hti.env.dm_env_loader._DM_CONTROL_AVAILABLE', False):
        with pytest.raises(RuntimeError, match="dm_control not installed"):
            load_from_config(cfg)


def test_raises_when_asset_missing():
    """When DmControlEnv requested but assets missing, should raise FileNotFoundError."""
    if not _DM_CONTROL_AVAILABLE:
        pytest.skip("dm_control not available")

    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"

    # Mock the asset path existence check
    with patch('hti.env.dm_env_loader.Path.exists', return_value=False):
        with pytest.raises(FileNotFoundError, match="asset not found"):
            load_from_config(cfg)


def test_nullenv_backend_always_works():
    """NullEnv backend should always work (no dependencies)."""
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "NullEnv"

    env = load_from_config(cfg)
    assert type(env).__name__ == "NullEnv"
