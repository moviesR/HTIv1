from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Literal, Optional, Callable

TimeFn = Callable[[], float]

@dataclass
class AdapterDelta:
    """
    Bounded control deltas (payload carries Δgains, v_cap, μ_comp, etc.).
    TTL enforced by Control/Shield; rollback must occur ≤ 1 Control cycle.
    """
    ttl_ms: int
    source: Literal["predict", "probe", "manual"] = "predict"
    payload: Dict = None

class AdapterManager:
    """
    Minimal TTL/rollback manager for AdapterDeltas.
    Control calls .cycle() each frame to evict expired adapters.
    """
    def __init__(self, time_fn: TimeFn):
        self._time = time_fn
        self._active: Optional[AdapterDelta] = None
        self._expiry_s: Optional[float] = None
        self._rollback_requested: bool = False

    @property
    def active(self) -> Optional[AdapterDelta]:
        return self._active

    @property
    def rollback_requested(self) -> bool:
        return self._rollback_requested

    def apply(self, delta: AdapterDelta) -> None:
        now = self._time()
        self._active = delta
        self._expiry_s = now + (delta.ttl_ms / 1000.0)
        self._rollback_requested = False

    def cycle(self) -> None:
        """
        Called by Control band each frame. If TTL expired, clear and request rollback.
        """
        if self._active is None or self._expiry_s is None:
            self._rollback_requested = False
            return
        if self._time() >= self._expiry_s:
            # Expire and ask Control to rollback in this or next frame.
            self._active = None
            self._expiry_s = None
            self._rollback_requested = True
        else:
            self._rollback_requested = False
