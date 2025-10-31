"""
Test force bounds and signals_quality flag.

Fn/Ft must be non-negative and finite.
signals_quality.contacts must be "placeholder" or "measured".
"""
import pytest
from hti.core.config import load_system_slice
from hti.env.dm_env_loader import load_from_config, _DM_CONTROL_AVAILABLE


@pytest.mark.skipif(not _DM_CONTROL_AVAILABLE, reason="dm_control not installed")
def test_forces_non_negative_and_finite():
    """DmControlEnv forces must be non-negative and finite."""
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"
    cfg.env.fail_fast = False  # Allow fallback for test

    env = load_from_config(cfg)

    if type(env).__name__ != "DmControlEnv":
        pytest.skip("DmControlEnv not available (asset missing or load failed)")

    obs = env.reset(seed=42)

    # Check initial observation
    assert obs["Fn"] >= 0.0, f"Fn must be non-negative, got {obs['Fn']}"
    assert obs["Ft"] >= 0.0, f"Ft must be non-negative, got {obs['Ft']}"
    assert abs(obs["Fn"]) < float('inf'), f"Fn must be finite, got {obs['Fn']}"
    assert abs(obs["Ft"]) < float('inf'), f"Ft must be finite, got {obs['Ft']}"

    # Step a few times and verify bounds
    for _ in range(10):
        obs, done, info = env.step({"v_cap": 0.02})

        assert obs["Fn"] >= 0.0, f"Fn must be non-negative, got {obs['Fn']}"
        assert obs["Ft"] >= 0.0, f"Ft must be non-negative, got {obs['Ft']}"
        assert abs(obs["Fn"]) < float('inf'), f"Fn must be finite, got {obs['Fn']}"
        assert abs(obs["Ft"]) < float('inf'), f"Ft must be finite, got {obs['Ft']}"


def test_signals_quality_contacts_flag():
    """signals_quality.contacts must be 'placeholder' or 'measured'."""
    from hti.io.eventpack import RingBuffer, EventPackAssembler

    ring = RingBuffer(maxlen=512)

    def meta_provider():
        return {
            "config_hash": "test",
            "signals_quality": {
                "contacts": "placeholder"  # Until UR5 contacts are real
            }
        }

    ep_asm = EventPackAssembler(ring, lambda: 0.0)
    ep_asm._meta_provider = meta_provider

    # Add some samples
    ring.add(0.0, {"poseEE": [0, 0, 0.02], "Fn": 0.0, "Ft": 0.0})
    ring.add(0.01, {"poseEE": [0, 0, 0.03], "Fn": 0.5, "Ft": 0.1})

    # Assemble EventPack
    ep = ep_asm.assemble(trigger_t=0.01)

    assert "signals_quality" in ep.meta, "EventPack must include signals_quality"
    assert "contacts" in ep.meta["signals_quality"], "signals_quality must include contacts flag"

    contacts_quality = ep.meta["signals_quality"]["contacts"]
    assert contacts_quality in ("placeholder", "measured"), \
        f"contacts must be 'placeholder' or 'measured', got {contacts_quality}"


@pytest.mark.skipif(not _DM_CONTROL_AVAILABLE, reason="dm_control not installed")
def test_forces_are_zero_in_free_space():
    """When EE is in free space (not touching table), forces should be ~0."""
    cfg = load_system_slice("configs/system_slice.yaml")
    cfg.env.backend = "DmControlEnv"
    cfg.env.fail_fast = False

    env = load_from_config(cfg)

    if type(env).__name__ != "DmControlEnv":
        pytest.skip("DmControlEnv not available")

    obs = env.reset(seed=42)

    # EE starts at z=0.72 (above table at 0.7), so no contact
    # Forces should be very small (computational noise ok)
    assert obs["Fn"] < 0.1, f"Fn should be near zero in free space, got {obs['Fn']}"
    assert obs["Ft"] < 0.1, f"Ft should be near zero in free space, got {obs['Ft']}"

    # Lift upward - still no contact
    for _ in range(5):
        obs, done, info = env.step({"v_cap": 0.05})

    assert obs["Fn"] < 0.1, f"Fn should remain near zero when lifting, got {obs['Fn']}"
    assert obs["Ft"] < 0.1, f"Ft should remain near zero when lifting, got {obs['Ft']}"
