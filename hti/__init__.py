"""
HTI-Adapter Harness package root.
This package hosts banded runtime components, I/O, and env wrappers.
"""
__all__ = ["core", "predict", "probes", "io", "env", "metrics"]

# Note: fast-path modules (Reflex/Control) must remain allocation-free at runtime.
# This file intentionally does not import submodules to keep import times low.
