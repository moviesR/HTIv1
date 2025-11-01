import pytest
from hti.core.config import load_system_slice
from hti.env.dm_env_loader import load_from_config, _DM_CONTROL_AVAILABLE

@pytest.mark.skipif(not _DM_CONTROL_AVAILABLE, reason="dm_control not installed")
def test_dm_env_velocity_integration():
    """
    Verify that poseEE z increases by approximately v*dt with proper units (MKS).
    """
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"

    env = load_from_config(cfg)

    if type(env).__name__ != "DmControlEnv":
        pytest.skip("DmControlEnv not available (asset missing or load failed)")

    obs0 = env.reset(seed=42)
    z0 = obs0["poseEE"][2]

    # Command upward velocity: 0.05 m/s
    v_cap = 0.05
    dt = env.dt

    # Step for 10 cycles
    n_steps = 10
    for _ in range(n_steps):
        obs, done, info = env.step({"v_cap": v_cap})

    z1 = obs["poseEE"][2]
    dz = z1 - z0

    # Expected displacement: v * dt * n_steps = 0.05 * 0.02 * 10 = 0.01 m
    expected_dz = v_cap * dt * n_steps

    # Allow 5e-4 m tolerance (0.5mm) due to physics settling
    assert abs(dz - expected_dz) < 5e-4, f"Expected dz≈{expected_dz}, got {dz}"


@pytest.mark.skipif(not _DM_CONTROL_AVAILABLE, reason="dm_control not installed")
def test_dm_env_forces_non_negative():
    """
    Verify that Fn, Ft are non-negative and finite (proper units: Newtons).
    """
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"

    env = load_from_config(cfg)

    if type(env).__name__ != "DmControlEnv":
        pytest.skip("DmControlEnv not available (asset missing or load failed)")

    obs = env.reset(seed=42)

    # Run a few steps
    for _ in range(20):
        obs, done, info = env.step({"v_cap": 0.02})

        # Forces must be non-negative and finite
        assert obs["Fn"] >= 0.0, f"Fn={obs['Fn']} must be non-negative"
        assert obs["Ft"] >= 0.0, f"Ft={obs['Ft']} must be non-negative"
        assert abs(obs["Fn"]) < 1e6, f"Fn={obs['Fn']} unreasonably large"
        assert abs(obs["Ft"]) < 1e6, f"Ft={obs['Ft']} unreasonably large"


@pytest.mark.skipif(not _DM_CONTROL_AVAILABLE, reason="dm_control not installed")
def test_dm_env_contact_flags():
    """
    Verify that contact_flags is 0 or 1 (binary flag).
    """
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"

    env = load_from_config(cfg)

    if type(env).__name__ != "DmControlEnv":
        pytest.skip("DmControlEnv not available (asset missing or load failed)")

    obs = env.reset(seed=42)

    # Run a few steps
    for _ in range(20):
        obs, done, info = env.step({"v_cap": 0.01})
        assert obs["contact_flags"] in (0, 1), f"contact_flags={obs['contact_flags']} must be 0 or 1"
