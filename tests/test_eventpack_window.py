import math
from hti.io.eventpack import RingBuffer, EventPackAssembler

def _fake_meta():
    # Minimal meta provider with required top-level fields.
    return {
        "config_hash": "deadbeef",
        "physics_hash": "0099d6b12134",
        "sim_seed": 1337,
        "band_clocks": {"reflex_hz": 100, "control_hz": 50, "predict_hz": 20, "semantics_hz": 2},
        "caps": {"force": 12.0, "torque": 6.0, "vel": 0.25, "accel": 1.0, "jerk": 5.0},
        "loop_stats": {"reflex": {"p50": 0.003, "p95": 0.004, "p99": 0.005},
                       "control": {"p50": 0.006, "p95": 0.010, "p99": 0.012}},
        "missed_cycles": {"reflex": 0, "control": 0},
        "risk": {"U": 0.1, "H": 0.2, "r": 0.02},
    }

def test_eventpack_window_and_fields():
    rb = RingBuffer(maxlen=2048)
    dt = 0.01  # 100 Hz
    # Populate 0.0 .. 1.0 s
    t = 0.0
    for i in range(101):
        rb.add(t, {
            "q": [i*0.001],
            "dq": [0.0],
            "tau_cmd": [0.0],
            "tau_est": [0.0],
            "i_motor": [0.0],
            "poseEE": [0.0, 0.0, 0.0],
            "Fn": 0.0,
            "Ft": 0.0,
            "contact_flags": 0,
        })
        t += dt

    assembler = EventPackAssembler(rb, _fake_meta)
    trigger_t = 0.50
    pack = assembler.assemble(trigger_t, discrepancies=["pose_follow_error"], adapter={"v_cap": 0.22},
                              outcome={"success": True, "overforce": False, "ttr_ms": 380})

    # Window should be exactly ±300 ms
    assert math.isclose(pack.t0, 0.20, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(pack.t1, 0.80, rel_tol=0.0, abs_tol=1e-9)
    # Signals within window
    assert len(pack.signals) > 0
    assert min(s["t"] for s in pack.signals) >= pack.t0 - 1e-9
    assert max(s["t"] for s in pack.signals) <= pack.t1 + 1e-9

    # Required meta fields present
    m = pack.meta
    for k in ("config_hash", "physics_hash", "sim_seed", "band_clocks", "caps", "loop_stats", "missed_cycles", "risk"):
        assert k in m, f"missing meta field: {k}"

    # Presence of other required sections
    assert isinstance(pack.discrepancies, list)
    assert pack.adapter is not None
    assert pack.outcome is not None
