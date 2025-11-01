from __future__ import annotations
import threading
import time
from typing import Callable, Optional

ControlFn = Callable[[], None]
BackgroundFn = Callable[[], None]

class BandScheduler:
    """
    Minimal fixed-rate scheduler for Control band (no inter-band locks).
    - Runs Control at 1/Hz period in its own thread.
    - Predict/Semantics tasks run in independent background threads.
    - Control NEVER joins or waits on background tasks.
    """
    def __init__(self, control_hz: float):
        assert control_hz > 0
        self._period = 1.0 / control_hz
        self._stop = threading.Event()
        self._ctl_thread: Optional[threading.Thread] = None
        self._bg_threads: list[threading.Thread] = []

    def start_control(self, control_fn: ControlFn) -> None:
        if self._ctl_thread is not None:
            return
        self._stop.clear()
        self._ctl_thread = threading.Thread(target=self._run_control, args=(control_fn,), daemon=True)
        self._ctl_thread.start()

    def _run_control(self, control_fn: ControlFn) -> None:
        next_t = time.perf_counter()
        while not self._stop.is_set():
            t0 = time.perf_counter()
            try:
                control_fn()
            except Exception:
                # In real system, log and continue (Shield will guard actuators)
                pass
            # Fixed-rate sleep without drift
            next_t += self._period
            rem = next_t - time.perf_counter()
            if rem > 0:
                time.sleep(rem)
            else:
                # Overran; do not sleep negative time. Next loop will catch up.
                next_t = time.perf_counter()

    def run_background(self, fn: BackgroundFn) -> None:
        """
        Fire-and-forget background task (Predict/Fuse or Semantics).
        Control must never wait on this.
        """
        th = threading.Thread(target=fn, daemon=True)
        th.start()
        self._bg_threads.append(th)

    def stop(self, timeout: float = 1.0) -> None:
        self._stop.set()
        if self._ctl_thread:
            self._ctl_thread.join(timeout=timeout)
        # Background threads are daemons; they will exit on process end.
