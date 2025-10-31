"""
Test fail-fast behavior for DmControlEnv backend.

Verifies that when fail_fast=true, the system raises exceptions instead of
silently falling back to NullEnv.
"""
import pytest
from pathlib import Path
from unittest.mock import patch
from hti.core.config import load_system_slice
from hti.env.dm_env_loader import load_from_config, _DM_CONTROL_AVAILABLE


def test_fail_fast_true_raises_when_dm_control_missing():
    """When fail_fast=true and dm_control missing, should raise RuntimeError."""
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"
    cfg.env.fail_fast = True

    # Mock dm_control as unavailable
    with patch('hti.env.dm_env_loader._DM_CONTROL_AVAILABLE', False):
        with pytest.raises(RuntimeError, match="dm_control not installed"):
            load_from_config(cfg)


def test_fail_fast_true_raises_when_asset_missing():
    """When fail_fast=true and asset missing, should raise FileNotFoundError."""
    if not _DM_CONTROL_AVAILABLE:
        pytest.skip("dm_control not available")

    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"
    cfg.env.fail_fast = True

    # Mock asset path to non-existent file
    with patch('hti.env.dm_env_loader.Path') as mock_path:
        mock_path.return_value.parent = Path("/fake")
        mock_path.return_value.parent.__truediv__ = lambda self, x: Path("/fake/assets")

        fake_assets = Path("/fake/assets")
        fake_mjcf = fake_assets / "minimal_world.xml"

        with patch.object(Path, 'exists', return_value=False):
            with pytest.raises(FileNotFoundError, match="asset not found"):
                load_from_config(cfg)


def test_fail_fast_false_falls_back_to_nullenv():
    """When fail_fast=false and dm_control missing, should fallback to NullEnv."""
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"
    cfg.env.fail_fast = False

    # Mock dm_control as unavailable
    with patch('hti.env.dm_env_loader._DM_CONTROL_AVAILABLE', False):
        env = load_from_config(cfg)
        assert type(env).__name__ == "NullEnv"


def test_nullenv_backend_always_works():
    """NullEnv backend should always work regardless of fail_fast."""
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "NullEnv"
    cfg.env.fail_fast = True  # Even with fail_fast, NullEnv works

    env = load_from_config(cfg)
    assert type(env).__name__ == "NullEnv"
