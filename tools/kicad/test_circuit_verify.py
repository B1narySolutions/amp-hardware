"""Tests for the circuit check: the bound engine on circuits with known answers, and one spec end to end.

    python3 tools/kicad/test_circuit_verify.py        (or pytest tools/kicad)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_bounds import Analysis, Circuit, Elem  # noqa: E402
from circuit_spec import Spec, dc, expand_cases, load, open_, parse_passive, parse_value, tone, wave  # noqa: E402
import circuit_verify as cv  # noqa: E402


def near(x, want, tol=1e-3):
    return abs(x - want) <= tol * max(1.0, abs(want))


def analyse(c):
    a = Analysis(c, {})
    a.run()
    a.use(a.branches[0])
    return a


def hpf(src):
    c = Circuit("GND")
    c.fix("src", src, "test")
    c.add(Elem("C", "C1", ("src", "n"), 1e-6))
    c.add(Elem("R", "R1", ("n", "GND"), 1e6))
    return c


def test_coupling_cap_doubles_any_waveform():
    # Hold +1 V until C1 charges, then step to −1 V: n jumps to −2 V. A sine never does that.
    b = analyse(hpf(wave(-1, 1))).bound([[("v", "n", 1)]])[0]
    assert near(b.hi, 2.0) and near(b.lo, -2.0) and not b.loose


def test_coupling_cap_passes_a_tone():
    b = analyse(hpf(tone(1.0))).bound([[("v", "n", 1)]])[0]
    assert near(b.hi, 1.0) and near(b.lo, -1.0)


def test_rc_lowpass_never_overshoots():
    c = Circuit("GND")
    c.fix("src", wave(-1, 1), "test")
    c.add(Elem("R", "R1", ("src", "n"), 1e3))
    c.add(Elem("C", "C1", ("n", "GND"), 1e-6))
    b = analyse(c).bound([[("v", "n", 1)]])[0]
    assert near(b.hi, 1.0) and near(b.lo, -1.0)


def test_divider_tolerance_corners_are_exact():
    c = Circuit("GND")
    c.fix("v5", dc(5.0), "rail")
    c.add(Elem("R", "R1", ("v5", "m"), 10e3, 0.01))
    c.add(Elem("R", "R2", ("m", "GND"), 10e3, 0.01))
    v, i = analyse(c).bound([[("v", "m", 1)], [("r", "R1", 1)]])
    assert near(v.lo, 2.475) and near(v.hi, 2.525) and v.kind == "dc"
    assert near(i.lo, 5.0 / 20.2e3) and near(i.hi, 5.0 / 19.8e3)


def test_same_node_cancels():
    c = Circuit("GND")
    c.fix("v5", dc(4.7, 5.25), "rail")
    c.add(Elem("R", "R1", ("v5", "GND"), 1e3))
    b = analyse(c).bound([[("v", "v5", 1), ("v", "v5", -1)]])[0]
    assert b.lo == 0 and b.hi == 0


def test_clamp_limits_its_node_and_reports_current():
    c = Circuit("GND")
    c.fix("src", wave(-10, 10), "test")
    c.add(Elem("R", "Rs", ("src", "n"), 1e3))
    for name, ab in (("Dp", ("n", "GND")), ("Dn", ("GND", "n"))):
        c.add(Elem("D", name, ab, vmin=6.0, vmax=6.0, r_dyn=0.0, i_max=None, limiter=False))
    c.add(Elem("C", "C2", ("n", "m"), 1e-6))
    c.add(Elem("R", "R2", ("m", "GND"), 1e6))
    a = analyse(c)
    n, m = a.bound([[("v", "n", 1)], [("v", "m", 1)]])
    assert near(n.hi, 6.0) and near(n.lo, -6.0)
    assert near(m.hi, 12.0) and m.loose          # behind the clamp: sound, but no longer tight
    assert near(a.clamp_current(c.element("Dp"))[0], 4e-3)
    assert near(a.clamp_current(c.element("Dn"))[0], 4e-3)


def test_follower_output_stays_inside_its_rails():
    c = Circuit("GND")
    c.fix("src", wave(-0.5, 5.5), "test")
    c.fix("vp", dc(5.0), "rail")
    c.add(Elem("R", "Rin", ("src", "inp"), 1e3))
    c.add(Elem("E", "U1", ("out", "inp", "out"), 1e6))
    c.add(Elem("D", "U1.hi", ("out", "vp"), vmin=-0.02, vmax=-0.02, r_dyn=0, i_max=None, limiter=True))
    c.add(Elem("D", "U1.lo", ("GND", "out"), vmin=-0.02, vmax=-0.02, r_dyn=0, i_max=None, limiter=True))
    c.add(Elem("R", "Rl", ("out", "GND"), 10e3))
    b = analyse(c).bound([[("v", "out", 1)]])[0]
    assert near(b.lo, 0.02) and near(b.hi, 4.98)


def test_undecided_gate_checks_both_states():
    c = Circuit("GND")
    c.fix("g", wave(0, 3.3), "gpio")
    c.fix("v5", dc(5.0), "rail")
    c.add(Elem("R", "Rpu", ("v5", "d"), 10e3))
    c.add(Elem("S", "Q", ("d", "GND", "g"), polarity=1, vth=(1.0, 2.5), r_on=5.0))
    a = Analysis(c, {})
    states = sorted(b["sw"]["Q"] for b in a.run())
    assert states == ["off", "on"]


def test_values():
    assert parse_value("4k7")[0] == 4700 and parse_value("2R2")[0] == 2.2 and parse_value("1Meg")[0] == 1e6
    assert parse_value("100pF") == (1e-10, "F")
    assert parse_passive("47uF 16V") == (47e-6, 16.0)


def test_spec_end_to_end():
    """A port through a 1k into a pin rated 0..3.6 V with 5 mA protection diodes: 3.3 V passes, a 5 V misuse is
    clamped within the rating, a 12 V misuse fails."""
    parts = {
        "J1": {"value": "CONN", "footprint": "", "fields": {}, "dnp": False, "pins": {"1": "/IN", "2": "GND"}},
        "R1": {"value": "1k", "footprint": "R_0603_1608Metric", "fields": {}, "dnp": False,
               "pins": {"1": "/IN", "2": "/PIN"}},
        "U1": {"value": "TESTCHIP", "footprint": "", "fields": {}, "dnp": False, "pins": {"1": "/PIN", "2": "+3V3"}},
    }

    def model(p):
        p.limit("1", abs=(-0.3, ("2", 0.3)), clamp=True, inject=5e-3)

    library = ([{"match": ["TESTCHIP"], "model": model, "source": "test", "file": "test"}], {})
    spec = Spec()
    spec.rail("+3V3", dc(3.3))
    spec.port("J1.1", nominal=wave(0, 3.3), misuse=[dc(5.0, label="5 V"), dc(12.0, label="12 V")])
    spec.state("on", rails=["+3V3"])
    status = {}
    for case in expand_cases(spec):
        circ = cv.build(spec, parts, library, case, "GND")
        results, _ = cv.check_case(spec, circ, case, {})
        status[case.name] = {r.id: r.status for r in results if r.id.startswith("U1.1 abs hi")}
    assert status["on"]["U1.1 abs hi"] == "pass"
    assert status["on + J1.1: 5 V"]["U1.1 abs hi"] == "pass"     # (5 − 3.6) V / 1 kΩ = 1.4 mA ≤ 5 mA
    assert status["on + J1.1: 12 V"]["U1.1 abs hi"] == "fail"    # 8.4 mA


# --- contracts, test-plan readings and faults

def _two_board_parts():
    """J1.1 → R1 (1k) → /OUT → R2 (1k) → GND, with J1.2 on GND."""
    return {
        "J1": {"value": "CONN", "footprint": "", "fields": {}, "dnp": False, "pins": {"1": "/IN", "2": "GND"}},
        "R1": {"value": "1k", "footprint": "R_0603_1608Metric", "fields": {}, "dnp": False,
               "pins": {"1": "/IN", "2": "/OUT"}},
        "R2": {"value": "1k", "footprint": "R_0603_1608Metric", "fields": {}, "dnp": False,
               "pins": {"1": "/OUT", "2": "GND"}},
        "J2": {"value": "CONN", "footprint": "", "fields": {}, "dnp": False, "pins": {"1": "/OUT", "2": "GND"}},
    }


def test_source_resistance_range_covers_both_ends():
    # A source of 0..10 V through 0..10 kΩ into 10 kΩ: the pin spans 0..10 V (r at its low end).
    from circuit_spec import Interface
    iface = Interface("test")
    iface.signal("SIG", by="other board", source=dc(0, 10, r=(0, 10e3)))
    spec = Spec()
    spec.port("J1.1", nominal=iface.source("SIG"))
    spec.port("J2.1", nominal=load(1e6))
    spec.state("on")
    case = expand_cases(spec)[0]
    circ = cv.build(spec, _two_board_parts(), ([], {}), case, "GND")
    a = analyse(circ)
    b = a.bound([[("v", "/IN", 1)]])[0]
    assert near(b.lo, 0.0) and b.hi > 9.9


def test_contract_checks_range_and_source_resistance():
    from circuit_spec import Interface
    iface = Interface("test")
    iface.signal("OUT", by="this board", source=dc(0, 3, r=(0, 600)))
    for r_limit, want in ((600, "pass"), (400, "fail")):
        iface.signals["OUT"]["source"] = dc(0, 3, r=(0, r_limit))
        spec = Spec()
        spec.port("J1.1", nominal=dc(5.0, r=0.01))
        spec.port("J2.1", nominal=load(1e6))
        spec.provides(iface, {"OUT": "J2.1"})
        spec.state("on")
        case = expand_cases(spec)[0]
        circ = cv.build(spec, _two_board_parts(), ([], {}), case, "GND")
        res, _ = cv.check_case(spec, circ, case, {})
        status = {r.id: r.status for r in res}
        assert status["contract test: OUT"] == "pass"                 # 2.5 V, inside 0..3 V
        assert status["contract test: OUT source resistance"] == want  # 500 Ω (1k ‖ 1k)


def test_stage_readings_and_their_expectations():
    spec = Spec()
    spec.port("J1.1", nominal=open_())
    spec.port("J2.1", nominal=open_())
    spec.state("on")
    st = spec.test_stage("stage 1")
    st.measure("1", "J1.1", "GND", expect=2e3)
    st.measure("2", "J2.1", "J1.1", expect=1e3)
    st.measure("3", "J1.1", "GND", expect="open")
    res = {r.id.split()[2]: r.status for r in cv.check_stages(spec, _two_board_parts(), ([], {}), "GND")}
    assert res == {"1": "pass", "2": "pass", "3": "fail"}


def test_fault_check_finds_and_catches_a_short():
    import circuit_faults as cf
    parts = _two_board_parts()
    faults = cf.part_faults(parts)
    assert {f.name for f in faults} >= {"R1 open", "R1 shorted", "R2 open", "R2 shorted"}
    short = next(f for f in faults if f.name == "R2 shorted")
    fp, rename = short.apply(parts, {"GND": "ground"}, "GND")
    assert rename == {"/OUT": "GND"} and fp["R1"]["pins"]["2"] == "GND"
    spec = Spec()
    spec.port("J1.1", nominal=open_())
    spec.port("J2.1", nominal=open_())
    st = spec.test_stage("stage 1")
    st.measure("1", "J1.1", "GND", expect=2e3)
    before = cv.stage_readings(spec, parts, ([], {}), st, "GND")
    after = cv.stage_readings(spec, fp, ([], {}), st, "GND", rename)
    assert near(before[("1", "J1.1", "GND")], 2e3) and near(after[("1", "J1.1", "GND")], 1e3)


# --- the simulator (skipped when ngspice can't be found)

import circuit_sim  # noqa: E402
from circuit_sim import Probe  # noqa: E402


def simulate(c, probe, budget=4):
    a = Analysis(c, {})
    branch = a.run()[0]
    a.use(branch)
    return circuit_sim.search(a, branch, [probe], budget=budget)[0]


def needs_ngspice(f):
    def run():
        if circuit_sim.engine() is None:
            print(f"skip {f.__name__}: no ngspice")
            return
        f()
    run.__name__ = f.__name__
    return run


@needs_ngspice
def test_sim_finds_the_coupling_cap_worst_case():
    # The bound engine's bang-bang seed: hold +1 V, step to −1 V. The simulator reaches the bound's −2 V.
    o = simulate(hpf(wave(-1, 1)), Probe([("v", "n", 1)], -1, -1.9, [([("v", "n", 1)], -1)]))
    assert o.broken and near(o.value, -2.0, 1e-2)


@needs_ngspice
def test_sim_settles_a_clamp_the_bound_cannot():
    # Behind a ±6 V clamp, the bound treats the clamped node as any waveform in ±6 V: m ≤ 12 V, loose. A real
    # square wave through the clamp gets there, so the simulator turns it into a counterexample.
    c = Circuit("GND")
    c.fix("src", wave(-10, 10), "test")
    c.add(Elem("R", "Rs", ("src", "n"), 1e3))
    for name, ab in (("Dp", ("n", "GND")), ("Dn", ("GND", "n"))):
        c.add(Elem("D", name, ab, vmin=6.0, vmax=6.0, r_dyn=0.0, i_max=None, limiter=False))
    c.add(Elem("C", "C2", ("n", "m"), 1e-6))
    c.add(Elem("R", "R2", ("m", "GND"), 1e6))
    o = simulate(c, Probe([("v", "m", 1)], 1, 10.0, [([("v", "m", 1)], 1)]), budget=8)
    assert o.broken and 10.0 < o.value < 12.5


@needs_ngspice
def test_sim_clamp_current_matches_ohms_law():
    c = Circuit("GND")
    c.fix("src", wave(-10, 10), "test")
    c.add(Elem("R", "Rs", ("src", "n"), 1e3))
    c.add(Elem("D", "Dp", ("n", "GND"), vmin=6.0, vmax=6.0, r_dyn=0.0, i_max=None, limiter=False))
    o = simulate(c, Probe([("clamp", "Dp", 1)], 1, 1e-3, [([("v", "n", 1)], 1)], unit="A"))
    assert o.broken and near(o.value, 4e-3, 0.05)       # (10 − 6) V / 1 kΩ, less the diode's soft knee


@needs_ngspice
def test_sim_op_amp_clips_at_its_rails():
    c = Circuit("GND")
    c.fix("src", tone(4.0, offset=2.5), "test")
    c.fix("vp", dc(5.0), "rail")
    c.add(Elem("R", "Rin", ("src", "inp"), 1e3))
    c.add(Elem("E", "U1", ("out", "inp", "out"), 1e6, gbw=10e6))
    c.add(Elem("D", "U1.hi", ("out", "vp"), vmin=-0.02, vmax=-0.02, r_dyn=0, i_max=None, limiter=True, amp="U1"))
    c.add(Elem("D", "U1.lo", ("GND", "out"), vmin=-0.02, vmax=-0.02, r_dyn=0, i_max=None, limiter=True, amp="U1"))
    c.add(Elem("R", "Rl", ("out", "GND"), 10e3))
    o = simulate(c, Probe([("v", "out", 1)], 1, 5.0, [([("v", "out", 1)], 1)]))
    assert not o.broken and 4.95 < o.value <= 4.98


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, f in tests:
        f()
        print(f"ok  {name}")
    print(f"{len(tests)} tests passed")
