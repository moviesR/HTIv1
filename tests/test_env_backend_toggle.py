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

