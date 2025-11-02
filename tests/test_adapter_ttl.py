from hti.core.adapter import AdapterManager, AdapterDelta
from hti.core.clock import FakeClock

def test_adapter_ttl_expiry_and_rollback_flag():
    """
    Adapters must auto-expire at TTL and trigger rollback within ≤ 1 Control cycle.
    We simulate time deterministically using FakeClock (no sleeps).
    """
    clk = FakeClock(t0=0.0)
    mgr = AdapterManager(time_fn=clk.now)
    ttl_ms = 300
    mgr.apply(AdapterDelta(ttl_ms=ttl_ms, payload={"v_cap": 0.2}))
    # Active immediately
    assert mgr.active is not None
    assert mgr.rollback_requested is False
    # Advance just before TTL
    clk.advance((ttl_ms - 1) / 1000.0)
    mgr.cycle()
    assert mgr.active is not None
    assert mgr.rollback_requested is False
    # Cross TTL boundary
    clk.advance(0.002)
    mgr.cycle()
    assert mgr.active is None
    assert mgr.rollback_requested is True
    # Next cycle, rollback flag should clear
    mgr.cycle()
    assert mgr.rollback_requested is False
