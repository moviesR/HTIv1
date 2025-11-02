"""
I/O band: ring buffers, EventPack assembly, structured logging.
EventPack windows are fixed at ±300 ms around a trigger.
"""

from .eventpack import EventPack, EventPackAssembler, RingBuffer
__all__ = ["EventPack", "EventPackAssembler", "RingBuffer"]
