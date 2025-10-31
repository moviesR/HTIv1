from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Dict, Optional

TimeFn = Callable[[], float]

@dataclass
class ActiveProbe:
    name: str
    t_start: float
    t_expire: float
    params: Dict

class ProbeEngine:
    """
    Deterministic probe hygiene:
      - TTL per probe (default 300 ms)
      - Refractory between probe starts (default 150 ms)
      - Max 2 probes before the first "action" (user must call complete_action())
    Engine is clock-driven (no sleeps); call cycle() each Control/Predict loop.
    """
    def __init__(self, time_fn: TimeFn, ttl_ms: int = 300, refractory_ms: int = 150, max_before_action: int = 2):
        self._time = time_fn
        self._ttl = ttl_ms / 1000.0
        self._refractory = refractory_ms / 1000.0
        self._max_before_action = max_before_action
        self._active: List[ActiveProbe] = []
        self._last_start_t: Optional[float] = None
        self._count_since_action: int = 0

    @property
    def active(self) -> List[ActiveProbe]:
        return list(self._active)

    @property
    def count_since_action(self) -> int:
        return self._count_since_action

    def cycle(self) -> None:
        """Evict expired probes."""
        now = self._time()
        self._active = [p for p in self._active if p.t_expire > now]

    def can_start(self) -> bool:
        now = self._time()
        if self._count_since_action >= self._max_before_action:
            return False
        if self._last_start_t is None:
            return True
        return (now - self._last_start_t) >= self._refractory

    def request_probe(self, name: str, params: Optional[Dict] = None) -> bool:
        """Attempt to start a probe. Returns True if started under hygiene rules."""
        if not self.can_start():
            return False
        now = self._time()
        ap = ActiveProbe(
            name=name,
            t_start=now,
            t_expire=now + self._ttl,
            params=params or {},
        )
        self._active.append(ap)
        self._last_start_t = now
        self._count_since_action += 1
        return True

    def complete_action(self) -> None:
        """Call when the primary action (e.g., first pick attempt) begins; resets the 'max_before_action' counter."""
        self._count_since_action = 0
