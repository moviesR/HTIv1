from __future__ import annotations
from typing import Iterable
import math

def cvar(values: Iterable[float], alpha: float) -> float:
    """
    CVaR@alpha (expected shortfall): mean of the worst alpha-fraction.
    alpha in (0,1]. If alpha * n < 1, uses at least 1 element.
    """
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0:
        raise ValueError("cvar requires non-empty values")
    k = max(1, int(math.ceil(alpha * n)))
    return sum(xs[:k]) / k
