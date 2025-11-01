from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Callable

class MonotonicClock:
    """
    Wall-time monotonic clock for runtime scheduling and timing tests.
    """
    def now(self) -> float:
        return time.perf_counter()

@dataclass
class FixedStepSimClock:
    """
    Deterministic sim-time clock advanced by fixed dt per tick().
    Use for sim stepping and EventPack timestamps (avoid wall clock drift).
    """
    dt: float
    t: float = 0.0

    def now(self) -> float:
        return self.t

    def tick(self) -> float:
        self.t += self.dt
        return self.t

class FakeClock:
    """
    Test-only clock you can advance manually (no sleeps in tests).
    """
    def __init__(self, t0: float = 0.0):
        self._t = t0
    def now(self) -> float:
        return self._t
    def advance(self, dt: float) -> float:
        self._t += dt
        return self._t
