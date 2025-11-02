from hti.core.risk import RiskGate
from hti.core.shield import SafetyCaps

def test_accept_under_tau():
    """
    With v_cap=0.05, caps.v_mps=0.25, U=0.2, tau=0.25:
    H = 0.05/0.25 = 0.2
    r = U×H = 0.2×0.2 = 0.04
    r < tau → ACCEPT
    """
    caps = SafetyCaps(v_mps=0.25, a_mps2=1.0, fn_N=12.0, tau_Nm=6.0)
    gate = RiskGate(tau=0.25, uncertainty_stub=0.2)

    obs = {"poseEE": [0, 0, 0.02]}
    cmd = {"v_cap": 0.05}

    result = gate.decide(obs, cmd, caps)

    assert result["decision"] == "accept"
    assert abs(result["H"] - 0.2) < 1e-6
    assert abs(result["U"] - 0.2) < 1e-6
    assert abs(result["risk"] - 0.04) < 1e-6

def test_abstain_over_tau():
    """
    With v_cap=0.25, U=0.6, tau=0.25:
    H = 0.25/0.25 = 1.0
    r = U×H = 0.6×1.0 = 0.6
    r >= tau → ABSTAIN
    """
    caps = SafetyCaps(v_mps=0.25, a_mps2=1.0, fn_N=12.0, tau_Nm=6.0)
    gate = RiskGate(tau=0.25, uncertainty_stub=0.6)

    obs = {"poseEE": [0, 0, 0.02]}
    cmd = {"v_cap": 0.25}

    result = gate.decide(obs, cmd, caps)

    assert result["decision"] == "abstain"
    assert abs(result["H"] - 1.0) < 1e-6
    assert abs(result["U"] - 0.6) < 1e-6
    assert abs(result["risk"] - 0.6) < 1e-6

def test_edge_case_exactly_at_tau():
    """
    r exactly at tau should ABSTAIN (r >= tau)
    """
    caps = SafetyCaps(v_mps=0.25, a_mps2=1.0, fn_N=12.0, tau_Nm=6.0)
    gate = RiskGate(tau=0.25, uncertainty_stub=0.5)

    cmd = {"v_cap": 0.125}  # H = 0.125/0.25 = 0.5; r = 0.5×0.5 = 0.25 = tau
    result = gate.decide({}, cmd, caps)

    assert result["decision"] == "abstain"
    assert abs(result["risk"] - 0.25) < 1e-6
