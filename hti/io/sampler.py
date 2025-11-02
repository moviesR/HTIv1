from __future__ import annotations
from typing import Dict, Any, Callable
from hti.io.eventpack import RingBuffer

"""
Sampler: thin helper to push per-step samples into RingBuffer.
No allocations in fast paths; extend with τ_cmd, i_motor, etc. as needed.
"""

class Sampler:
    """
    Stream environment observations and commands into the ring buffer.
    Call sample_env() each Control cycle after env.step().
    """
    def __init__(self, ring: RingBuffer, time_fn: Callable[[], float]):
        self._ring = ring
        self._now = time_fn

    def sample_env(self, obs: Dict[str, Any], cmd: Dict[str, Any]) -> None:
        """
        Push (t, payload) into ring buffer.
        Minimal set; extend later with τ_cmd, i_motor, etc.
        """
        payload = {
            "poseEE": obs.get("poseEE"),
            "Fn": obs.get("Fn", 0.0),
            "Ft": obs.get("Ft", 0.0),
            "contact_flags": obs.get("contact_flags", 0),
            "cmd": cmd,
        }
        self._ring.add(self._now(), payload)
