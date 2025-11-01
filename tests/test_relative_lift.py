"""
Test relative lift detection.

Success and TTR should be measured relative to initial z0 (first pose),
not hardcoded absolute values.
"""
from hti.core.success import detect_lift_success, ttr_ms


def test_relative_lift_from_high_starting_position():
    """Success detector should work with high starting z (e.g., DmControlEnv at z=0.72)."""
    # Simulate EE starting at z=0.72 (table + 2cm), lifting to 0.78
    z0 = 0.72
    poses = [(0.0, 0.0, z0)] * 10  # Start at z0

    # Lift by 0.06m (6cm) over next 30 samples
    for i in range(30):
        z = z0 + (0.06 * (i + 1) / 30.0)
        poses.append((0.0, 0.0, z))

    # Hold stable for 20 samples at z=0.78
    for _ in range(20):
        poses.append((0.0, 0.0, 0.78))

    # Should detect success with dz=0.05 (5cm threshold)
    success = detect_lift_success(poses, z0=z0, dz=0.05)
    assert success, "Should detect lift from high starting position"


def test_relative_ttr_from_high_starting_position():
    """TTR should compute time relative to z0, not absolute z."""
    z0 = 0.72
    dt = 0.02  # 50 Hz

    # Start at z0 for 10 samples (200ms)
    poses = [(0.0, 0.0, z0)] * 10

    # Lift by 0.06m over 30 samples (600ms)
    for i in range(30):
        z = z0 + (0.06 * (i + 1) / 30.0)
        poses.append((0.0, 0.0, z))

    # Hold stable for 20 samples (400ms)
    for _ in range(20):
        poses.append((0.0, 0.0, 0.78))

    # TTR should be ~200ms (when threshold first crossed) to ~800ms (when stable)
    # Threshold = z0 + dz = 0.72 + 0.05 = 0.77
    # Crosses at sample ~10 + 25 = 35, stable at 35+20=55, first_idx = 35
    ttr = ttr_ms(poses, dt=dt, z0=z0, dz=0.05)

    assert ttr is not None, "Should detect TTR"
    # First crosses threshold around sample 35, but needs 20 stable samples
    # So first_idx = 55 - 20 + 1 = 36, but let me recalculate...
    # At sample 10+25=35, z ≈ z0 + 0.06*(25/30) = 0.72 + 0.05 = 0.77 (at threshold)
    # Needs 20 consecutive, so at sample 35+19=54, first_idx = 54-19 = 35
    # TTR = 35 * 20ms = 700ms
    assert 600 <= ttr <= 800, f"TTR should be ~700ms, got {ttr}ms"


def test_lift_from_low_starting_position():
    """Should work with NullEnv's low starting z=0.02."""
    z0 = 0.02
    dt = 0.02  # 50 Hz

    poses = [(0.0, 0.0, z0)] * 10

    # Lift by 0.04m (4cm) over 20 samples
    for i in range(20):
        z = z0 + (0.04 * (i + 1) / 20.0)
        poses.append((0.0, 0.0, z))

    # Hold stable
    for _ in range(20):
        poses.append((0.0, 0.0, 0.06))

    success = detect_lift_success(poses, z0=z0, dz=0.03)
    assert success, "Should detect lift from low starting position"

    ttr = ttr_ms(poses, dt=dt, z0=z0, dz=0.03)
    assert ttr is not None and ttr > 0, "Should compute TTR"
