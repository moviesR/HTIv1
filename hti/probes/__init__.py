"""
Probe engine: deterministic micro-actions (squeeze, dither, drag) with TTL/refractory.
Produces EventPacks (±300 ms windows) for audit and learning.
"""

from dataclasses import dataclass
from typing import Dict, List

@dataclass
class ProbeSpec:
    sequence: List[Dict]  # [(name, params, ceilings, aborts), ...]
    ttl_ms: int = 300
    refractory_ms: int = 150
    max_before_action: int = 2

from .engine import ProbeEngine  # re-export
__all__ = ["ProbeSpec", "ProbeEngine"]
