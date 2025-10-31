from __future__ import annotations
from typing import Any, Optional, Mapping

"""
dm_control wrapper (stub).

M0 goal (later):
  - Load MJCF for UR5-like + worn parallel gripper
  - Expose reset(seed), step(action), observation(), and raw MuJoCo physics handle
  - Provide hooks for contact impulses and per-step logging at 100/50 Hz

This stub returns None so imports stay safe in CI until assets are added.
"""

def make_env(config: Optional[Mapping[str, Any]] = None) -> Any:
    """
    Factory: create and return a dm_control environment bound to the given config.
    Placeholder: returns None until assets and real wrapper are implemented.
    """
    _ = config  # reserved for future use
    return None
