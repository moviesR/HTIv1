from hti.io.eventpack import RingBuffer, EventPackAssembler

def _fake_meta():
    return {
        "config_hash": "deadbeef",
        "physics_hash": "0099d6b12134",
        "sim_seed": 1337,
        "band_clocks": {},
        "caps": {},
        "loop_stats": {},
        "missed_cycles": {},
    }

def test_eventpack_counters_and_env_meta():
    """
    Simulate one abstain + one veto + one TTL expiry; assert counters in EventPack.
    """
    ring = RingBuffer(maxlen=256)
    # Add a few samples
    for i in range(10):
        ring.add(i * 0.01, {"poseEE": [0, 0, 0.02 + i * 0.001]})

    asm = EventPackAssembler(ring, _fake_meta)

    counters = {"abstain": 1, "veto": 1, "ttl_expired": 1}
    env_meta = {"backend": "NullEnv", "dt": 0.005, "substeps": 1}
    risk = {"U": 0.2, "H": 0.5, "r": 0.1}

    pack = asm.assemble(
        trigger_t=0.05,
        discrepancies=[],
        counters=counters,
        env_meta=env_meta,
        risk=risk
    )

    # Assert counters in meta
    assert "counters" in pack.meta
    assert pack.meta["counters"]["abstain"] == 1
    assert pack.meta["counters"]["veto"] == 1
    assert pack.meta["counters"]["ttl_expired"] == 1

    # Assert env meta
    assert "env" in pack.meta
    assert pack.meta["env"]["backend"] == "NullEnv"
    assert pack.meta["env"]["dt"] == 0.005
    assert pack.meta["env"]["substeps"] == 1

    # Assert risk
    assert "risk" in pack.meta
    assert pack.meta["risk"]["U"] == 0.2
    assert pack.meta["risk"]["H"] == 0.5
    assert pack.meta["risk"]["r"] == 0.1
