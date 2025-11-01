from hti.core.clock import FakeClock
from hti.io.eventpack import RingBuffer, EventPackAssembler
from hti.io.sampler import Sampler

def test_sampler_feeds_eventpack():
    clk = FakeClock(0.0)
    ring = RingBuffer(maxlen=256)
    sampler = Sampler(ring, clk.now)
    # simulate 100 Hz for 0.5 s
    for i in range(50):
        sampler.sample_env({"poseEE": [0, 0, 0.02 + i * 0.0005]}, {"v_cap": 0.05})
        clk.advance(0.01)
    asm = EventPackAssembler(ring, lambda: {
        "config_hash": "deadbeef",
        "physics_hash": "0099d6b12134",
        "sim_seed": 1337,
        "band_clocks": {},
        "caps": {},
        "loop_stats": {},
        "missed_cycles": {},
        "risk": {}
    })
    pack = asm.assemble(trigger_t=0.25, discrepancies=[], adapter={"v_cap": 0.05}, outcome={"success": False})
    assert len(pack.signals) > 0
