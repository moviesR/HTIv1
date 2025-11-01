"""
Environment wrappers (dm_control primary). Keep wrappers thin; expose physics/contacts cleanly.
"""

from .dm_env_loader import make_env  # re-export factory
__all__ = ["make_env"]
