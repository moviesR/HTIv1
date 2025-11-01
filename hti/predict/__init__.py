"""
Predict/Fuse band: surrogate models, OOD/conformal gating, bounded search (BO/CMA-ES).

Latency budgets (p99 caps):
- Surrogate ≤ 2 ms; OOD+conformal ≤ 2 ms; BO tick ≤ 3 ms (≤ 40 ms/s; ≤ 8 props/episode).
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Prediction:
    p_success: float
    p_overforce: float
    ood_score: float
