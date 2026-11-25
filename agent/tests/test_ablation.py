from agent.tools import Toolbox


def test_off_switches_engine_checks_in_setup_c():
    box = Toolbox("cases", "C", "A5_operator_line", "units per shift?", off=("scope", "validity"))
    assert box.engine.flags["scope"] is False and box.engine.flags["validity"] is False
    assert box.engine.flags["units"] is True


def test_default_keeps_every_check_on():
    box = Toolbox("cases", "C", "A5_operator_line", "units per shift?")
    assert all(box.engine.flags.values())
