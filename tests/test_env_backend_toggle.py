from hti.core.config import SystemSlice, load_system_slice
from hti.env.dm_env_loader import load_from_config, NullEnv, _DM_CONTROL_AVAILABLE

def test_backend_flag_nullenv():
    """Verify that backend='NullEnv' returns NullEnv."""
    cfg = load_system_slice("configs/system_slice.yaml")
    assert cfg.env.backend == "NullEnv"

    env = load_from_config(cfg)
    assert isinstance(env, NullEnv)
    assert env.dt == cfg.physics.dt
    assert env.substeps == cfg.physics.substeps

def test_backend_flag_dmcontrol_fallback():
    """
    Verify that backend='DmControlEnv' falls back to NullEnv if dm_control unavailable.
    If dm_control IS available, we get DmControlEnv and can reset/step.
    """
    cfg = load_system_slice("configs/system_slice.yaml")

    # Temporarily override backend
    cfg.env.backend = "DmControlEnv"

    env = load_from_config(cfg)

    if not _DM_CONTROL_AVAILABLE:
        # Should fall back to NullEnv
        assert isinstance(env, NullEnv)
    else:
        # dm_control available: should get DmControlEnv
        # But we can't import it directly (conditional definition), so check by type name
        assert type(env).__name__ == "DmControlEnv"
        assert env.dt == cfg.physics.dt
        assert env.substeps == cfg.physics.substeps

        # Test reset returns correct keys
        obs = env.reset(seed=42)
        assert "poseEE" in obs
        assert "Fn" in obs
        assert "Ft" in obs
        assert "contact_flags" in obs
        assert len(obs["poseEE"]) == 3
        assert isinstance(obs["Fn"], (int, float))
        assert isinstance(obs["Ft"], (int, float))
        assert obs["contact_flags"] in (0, 1)

        # Test step returns correct structure
        action = {"v_cap": 0.01}
        obs, done, info = env.step(action)
        assert "poseEE" in obs
        assert "Fn" in obs
        assert "Ft" in obs
        assert "contact_flags" in obs
        assert isinstance(done, bool)
        assert "t" in info
