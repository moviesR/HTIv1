"""
HTI core band: clocks, rate controllers, Shield (last-writer gate), Adapter manager.

Implementation notes (contracts):
- No inter-band locks; Control/Reflex must not await slower bands.
- Rollback of any applied AdapterDelta must occur ≤ 1 Control cycle.
- Expose minimal, typed interfaces; constants live in configs/system_slice.yaml.
"""

from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class AdapterDelta:
    """Bounded control deltas (caps + TTL enforced by Control/Shield)."""
    ttl_ms: int
    source: Literal["predict", "probe", "manual"] = "predict"
    payload: dict = None  # e.g., {"dgains": {...}, "v_cap": 0.2, "mu_comp": 0.1}
