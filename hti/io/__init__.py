"""
I/O band: ring buffers, EventPack assembly, structured logging.
EventPack windows are fixed at ±300 ms around a trigger.
"""

from dataclasses import dataclass
from typing import Dict, List

@dataclass
class EventPack:
    t0: float
    t1: float
    signals: Dict
    meta: Dict
    discrepancies: List[str]
    adapter: Dict | None = None
