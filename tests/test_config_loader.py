from hti.core.config import load_system_slice

def test_system_slice_loads_and_types_ok():
    cfg = load_system_slice()
    # Basic shape checks
    assert cfg.engine.startswith("mujoco-")
    assert cfg.physics.dt > 0
    assert cfg.bands.reflex_hz == 100
    # physics_hash should be filled (strict validator already enforces schema in CI)
    assert cfg.seeds.physics_hash and cfg.seeds.physics_hash != "<FILL_ME>"
    # Ranges parse
    lo, hi = cfg.bands.predict_range
    assert lo <= hi and lo > 0
    lo2, hi2 = cfg.bands.semantics_range
    assert lo2 <= hi2 and lo2 > 0

def test_config_is_cached():
    a = load_system_slice()
    b = load_system_slice()
    assert a is b  # lru_cache provides same object
