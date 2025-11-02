import os
import statistics
import time
import pytest

from hti.core.scheduler import BandScheduler

def _run_soak(control_hz: float, seconds: int) -> float:
    sched = BandScheduler(control_hz=control_hz)
    stamps = []
    def control_fn():
        stamps.append(time.perf_counter())
    sched.start_control(control_fn)
    time.sleep(seconds)
    sched.stop()
    if len(stamps) < 5:
        return 1e9  # fail-safe large p99
    deltas = [stamps[i] - stamps[i-1] for i in range(1, len(stamps))]
    deltas_sorted = sorted(deltas)
    p99 = deltas_sorted[int(0.99 * (len(deltas_sorted) - 1))]
    return p99

@pytest.mark.skipif(
    int(os.environ.get("HTI_SOAK_SEC", "0")) <= 0,
    reason="Set HTI_SOAK_SEC>0 to enable soak test"
)
def test_control_50hz_soak_env_gated():
    """
    Env-gated long soak. Example (local):
      HTI_SOAK_SEC=60 pytest -q tests/test_timing_soak.py::test_control_50hz_soak_env_gated
    CI can set HTI_SOAK_SEC=60 for a 1-minute soak.
    Acceptance (generous jitter ceiling on shared runners):
      p99 inter-arrival < 30 ms
    """
    seconds = int(os.environ["HTI_SOAK_SEC"])
    p99 = _run_soak(control_hz=50.0, seconds=seconds)
    assert p99 < 0.030, f"Soak p99 too high: {p99:.4f}s"
