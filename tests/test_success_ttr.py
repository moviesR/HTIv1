from hti.core.success import detect_lift_success, ttr_ms

def test_detect_lift_and_ttr():
    # 100 Hz; z starts increasing from i=10
    # At i=10: z = 0.02 + 0*0.001 = 0.020
    # At i=40: z = 0.02 + 30*0.001 = 0.050 (crosses threshold 0.05)
    # Need 20 consecutive samples above threshold, stable at i=59
    # first_idx = 59 - 20 + 1 = 40
    # TTR = 40 * 10ms = 400ms
    poses = [(0, 0, 0.02 + max(0, i - 10) * 0.001) for i in range(100)]
    assert detect_lift_success(poses, z0=0.02, dz=0.03) is True
    ms = ttr_ms(poses, dt=0.01, z0=0.02, dz=0.03)
    # first stable index ≈ 40; 40*10ms = 400 ms
    assert 380 <= ms <= 420
