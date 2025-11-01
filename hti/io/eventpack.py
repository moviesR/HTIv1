from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple, Any
import bisect

WINDOW_S = 0.300  # ±300 ms windows

@dataclass
class EventPack:
    t0: float
    t1: float
    signals: List[Dict[str, Any]]
    meta: Dict[str, Any]
    discrepancies: List[str]
    adapter: Dict[str, Any] | None = None
    outcome: Dict[str, Any] | None = None

class RingBuffer:
    """
    Minimal time-indexed buffer for signals/meta needed to assemble EventPacks.
    Stores tuples (t, payload_dict). Use fixed dt (e.g., 0.01 for 100 Hz) for deterministic tests.
    """
    def __init__(self, maxlen: int = 512):
        self._ts: List[float] = []
        self._xs: List[Dict[str, Any]] = []
        self._maxlen = maxlen

    def add(self, t: float, payload: Dict[str, Any]) -> None:
        self._ts.append(t)
        self._xs.append(payload)
        if len(self._ts) > self._maxlen:
            # evict from front
            self._ts = self._ts[-self._maxlen :]
            self._xs = self._xs[-self._maxlen :]

    def window(self, t0: float, t1: float) -> List[Dict[str, Any]]:
        """Return payloads with timestamps in [t0, t1]."""
        # Since ts is increasing, we can bisect for indices.
        i0 = bisect.bisect_left(self._ts, t0)
        i1 = bisect.bisect_right(self._ts, t1)
        return [self._xs[i] | {"t": self._ts[i]} for i in range(i0, i1)]

class EventPackAssembler:
    """
    Builds EventPacks by slicing the ring buffer around a trigger time.
    meta_provider(): returns dict with required meta (config_hash, physics_hash, seeds, band clocks, caps, loop stats).
    """
    def __init__(self, ring: RingBuffer, meta_provider: Callable[[], Dict[str, Any]]):
        self._ring = ring
        self._meta_provider = meta_provider

    def assemble(self, trigger_t: float, discrepancies: List[str] | None = None, adapter: Dict[str, Any] | None = None,
                 outcome: Dict[str, Any] | None = None, counters: Dict[str, int] | None = None,
                 env_meta: Dict[str, Any] | None = None, risk: Dict[str, float] | None = None) -> EventPack:
        """
        Assemble EventPack with optional counters, env metadata, and risk fields.

        Args:
            trigger_t: Trigger time for ±300ms window
            discrepancies: List of discrepancy types
            adapter: AdapterDelta info
            outcome: Task outcome info
            counters: {"abstain": int, "veto": int, "ttl_expired": int}
            env_meta: {"backend": str, "dt": float, "substeps": int}
            risk: {"U": float, "H": float, "r": float}
        """
        t0 = trigger_t - WINDOW_S
        t1 = trigger_t + WINDOW_S
        sigs = self._ring.window(t0, t1)
        meta = self._meta_provider()

        # Merge in optional fields
        if counters is not None:
            meta["counters"] = counters
        if env_meta is not None:
            meta["env"] = env_meta
        if risk is not None:
            meta["risk"] = risk

        return EventPack(
            t0=t0,
            t1=t1,
            signals=sigs,
            meta=meta,
            discrepancies=discrepancies or [],
            adapter=adapter,
            outcome=outcome,
        )
