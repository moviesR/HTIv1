"""
HTI core band: clocks, rate controllers, Shield (last-writer gate), Adapter manager.

Implementation notes (contracts):
- No inter-band locks; Control/Reflex must not await slower bands.
- Rollback of any applied AdapterDelta must occur ≤ 1 Control cycle.
- Expose minimal, typed interfaces; constants live in configs/system_slice.yaml.
"""
