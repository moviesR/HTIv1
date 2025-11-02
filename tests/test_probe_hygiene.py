from hti.core.clock import FakeClock
from hti.probes.engine import ProbeEngine

def test_probe_hygiene_ttl_refractory_max2_before_action():
    clk = FakeClock(0.0)
    eng = ProbeEngine(time_fn=clk.now, ttl_ms=300, refractory_ms=150, max_before_action=2)

    # First probe allowed
    assert eng.request_probe("squeeze") is True
    eng.cycle()
    assert len(eng.active) == 1
    assert eng.count_since_action == 1

    # Too soon to start another (refractory 150 ms)
    clk.advance(0.10)  # 100 ms
    eng.cycle()
    assert eng.request_probe("dither") is False

    # After refractory, second probe allowed
    clk.advance(0.05)  # now 150 ms
    eng.cycle()
    assert eng.request_probe("dither") is True
    assert eng.count_since_action == 2

    # Third probe before action should be rejected (max_before_action=2)
    clk.advance(0.20)
    eng.cycle()
    assert eng.request_probe("drag") is False

    # TTL expiry should evict old probes after 300 ms from their start
    # We started first at t=0.0, second at t=0.15; move to t=0.31+
    clk.advance(0.01)  # t ~0.31
    eng.cycle()
    # At least the first should be expired; second may still be active depending on exact times
    assert len(eng.active) <= 1

    # Completing an action resets the counter so another probe can be issued
    eng.complete_action()
    assert eng.count_since_action == 0
    assert eng.request_probe("drag") is True
