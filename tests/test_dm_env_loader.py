from hti.core.config import load_system_slice
from hti.env.dm_env_loader import load_from_config, NullEnv

def test_env_loader_nullenv_basic():
    cfg = load_system_slice()
    env = load_from_config(cfg)
    assert isinstance(env, NullEnv)
    assert env.dt == cfg.physics.dt
    obs = env.reset(seed=cfg.seeds.sim_seed)
    assert "poseEE" in obs
    # advance a few steps with a small v_cap
    for _ in range(10):
        obs, done, info = env.step({"v_cap": 0.05})
    assert info["t"] > 0
