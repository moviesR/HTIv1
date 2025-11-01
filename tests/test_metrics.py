from hti.metrics import cvar

def test_cvar_basic_alpha_point_one():
    xs = [0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
    v = cvar(xs, alpha=0.1)
    assert v == 0.2

def test_cvar_small_sets():
    xs = [1.0]
    assert cvar(xs, 0.1) == 1.0
    xs2 = [1.0, 2.0]
    assert cvar(xs2, 0.25) == 1.0  # worst 25% -> ceil(0.5)=1 element
