from hti.core.shield import Shield, SafetyCaps

def test_shield_veto_over_limit_and_rollback_same_cycle():
    """
    If proposed command violates hard caps, Shield must veto and return fallback
    in the same Control cycle (no extra waits).
    """
    caps = SafetyCaps(v_mps=0.25, a_mps2=1.0, fn_N=12.0, tau_Nm=6.0)
    shield = Shield(caps)

    baseline = {"v_cap": 0.20, "fn": 6.0, "tau": 2.0}      # known-safe baseline
    proposed = {"v_cap": 0.40, "fn": 6.0, "tau": 2.0}      # exceeds v_mps

    decision = shield.evaluate(proposed_cmd=proposed, fallback_cmd=baseline)

    assert decision.accepted is False
    assert "v_cap" in decision.reason
    # "Actuator write" must use Shield's final_cmd (fallback baseline here)
    actuated = decision.final_cmd
    assert actuated == baseline

def test_shield_last_writer_property_accept_path():
    """
    When proposed command is within caps, Shield should accept it, and it must
    be the LAST writer before actuators (i.e., final_cmd == proposed).
    """
    caps = SafetyCaps(v_mps=0.25, a_mps2=1.0, fn_N=12.0, tau_Nm=6.0)
    shield = Shield(caps)

    baseline = {"v_cap": 0.20, "fn": 6.0, "tau": 2.0}
    proposed = {"v_cap": 0.22, "fn": 8.0, "tau": 5.0}

    decision = shield.evaluate(proposed_cmd=proposed, fallback_cmd=baseline)

    assert decision.accepted is True
    # Shield is the final arbiter; actuators should receive final_cmd == proposed
    actuated = decision.final_cmd
    assert actuated == proposed
