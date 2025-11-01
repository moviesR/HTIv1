from __future__ import annotations
from typing import Sequence, Tuple

"""
Success/TTR detector for PnP_smoke task.
Locks acceptance metric shape; when we swap in dm_control it's a drop-in.
"""

def detect_lift_success(poses: Sequence[Tuple[float, float, float]], z0: float = 0.02, dz: float = 0.03) -> bool:
    """
    Success if any poseEE.z exceeds z0+dz and remains >= that for ≥ 0.20 s (20 samples @100 Hz).

    Args:
        poses: Sequence of (x, y, z) EE poses
        z0: Initial z height (default 0.02 m)
        dz: Required lift height (default 0.03 m)

    Returns:
        True if sustained lift detected, False otherwise
    """
    threshold = z0 + dz
    consec = 0
    for _, _, z in poses:
        if z >= threshold:
            consec += 1
            if consec >= 20:
                return True
        else:
            consec = 0
    return False

def ttr_ms(poses: Sequence[Tuple[float, float, float]], dt: float, z0: float = 0.02, dz: float = 0.03) -> int | None:
    """
    Time-to-result in milliseconds: time from start to first stable lift.

    Args:
        poses: Sequence of (x, y, z) EE poses
        dt: Timestep in seconds (e.g., 0.01 for 100 Hz)
        z0: Initial z height (default 0.02 m)
        dz: Required lift height (default 0.03 m)

    Returns:
        TTR in milliseconds, or None if no stable lift detected
    """
    threshold = z0 + dz
    consec = 0
    for i, (_, _, z) in enumerate(poses):
        if z >= threshold:
            consec += 1
            if consec >= 20:
                # first index where we got a stable lift
                first_idx = i - consec + 1
                return int(round(first_idx * dt * 1000))
        else:
            consec = 0
    return None
