"""Look for a real counterexample to a check the static bounds couldn't settle, by simulating the circuit in ngspice.

circuit_verify.py calls search() for its UNPROVEN results. The circuit comes from the same elements and part models as
the static check, written out as a SPICE netlist. Diode clamps become diodes, amplifiers with rail limits become
behavioural sources, MOSFETs become voltage-controlled switches. It runs on KiCad's own libngspice, through ctypes.

The search starts from what the bound engine says is worst for each probe in the linear circuit
(Analysis.worst_input): the bang-bang waveform for "any waveform" sources, the worst frequency and phase for tones,
the extreme of each constant, and the worst tolerance corner. It then varies those at random: frequencies, phases,
square waves and steps, tolerance corners and clamp voltages. A simulation can find a failure but never prove a pass,
so the outcome is either a counterexample (the input that breaks the check) or the worst value the search reached.
"""
import ctypes
import math
import random
import re
import threading

import numpy as np

import kicadenv
from circuit_spec import fmt

DIODE_VF = 0.6        # a clamp diode's drop at its turn-on, subtracted from the clamp voltage by a series source
DIODE_RS = 1.0        # least series resistance of a clamp diode (Ω): an ideal one stalls ngspice's time step
AMP_ROUT = 10.0       # amplifier output resistance (Ω), for the same reason; real op-amps have tens of ohms
AMP_GAIN = 1e4        # open-loop gain cap: closes feedback loops to 0.01 % without making Newton's job stiff
LIMIT_SOFT = 0.01     # V: the rail limits are rounded over this much, so the output has no sharp corner
RUN_TIMEOUT = 30.0    # s of wall time for one simulation before it is stopped
# Solver settings, tried in turn when a run doesn't converge: (method, reltol, diode emission coefficient).
SOLVERS = [("trap", 1e-3, 1), ("gear", 1e-3, 1), ("gear", 1e-3, 2), ("trap", 3e-3, 2)]
MAX_STEPS = 4e5       # time steps allowed for one tone run; longer settling is cut short (and said so)


class SimError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------------------- ngspice


class _VecInfo(ctypes.Structure):
    _fields_ = [("v_name", ctypes.c_char_p), ("v_type", ctypes.c_int), ("v_flags", ctypes.c_short),
                ("v_realdata", ctypes.POINTER(ctypes.c_double)), ("v_compdata", ctypes.c_void_p),
                ("v_length", ctypes.c_int)]


class Ngspice:
    """ngspice's shared library, driven through its C API. One per process."""

    _SendChar = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
    _SendStat = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
    _Exit = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
    _BgRun = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)

    def __init__(self, path):
        self.path = path
        self.lib = ctypes.CDLL(path)
        self.log = []
        self._done = threading.Event()        # set by ngspice when its background thread finishes a run
        self._cb = (self._SendChar(self._char), self._SendStat(lambda *a: 0), self._Exit(self._exit),
                    self._BgRun(self._bg))
        self.lib.ngSpice_Init.argtypes = [self._SendChar, self._SendStat, self._Exit, ctypes.c_void_p,
                                          ctypes.c_void_p, self._BgRun, ctypes.c_void_p]
        self.lib.ngSpice_Circ.argtypes = [ctypes.POINTER(ctypes.c_char_p)]
        self.lib.ngSpice_Command.argtypes = [ctypes.c_char_p]
        self.lib.ngGet_Vec_Info.restype = ctypes.POINTER(_VecInfo)
        self.lib.ngGet_Vec_Info.argtypes = [ctypes.c_char_p]
        self.lib.ngSpice_running.restype = ctypes.c_bool
        self.lib.ngSpice_Init(self._cb[0], self._cb[1], self._cb[2], None, None, self._cb[3], None)
        self.runs = 0

    def _char(self, text, ident, user):
        self.log.append(text.decode("utf-8", "replace"))
        return 0

    def _exit(self, status, unload, quit, ident, user):
        self.log.append(f"ngspice exit {status}")
        return 0

    def _bg(self, not_running, ident, user):
        if not_running:
            self._done.set()
        return 0

    def run(self, lines, vectors):
        """Load a netlist, run it, and return the requested vectors as arrays."""
        self.log = []
        arr = (ctypes.c_char_p * (len(lines) + 1))(*[l.encode() for l in lines], None)
        if self.lib.ngSpice_Circ(arr) != 0:
            raise SimError("ngspice rejected the netlist:\n" + "".join(self.log[-20:]))
        self._done.clear()
        self.lib.ngSpice_Command(b"bg_run")
        if not self._done.wait(RUN_TIMEOUT):
            self.lib.ngSpice_Command(b"bg_halt")
            self._done.wait(5.0)
            self.lib.ngSpice_Command(b"destroy all")
            self.lib.ngSpice_Command(b"remcirc")
            raise SimError(f"a simulation ran past {RUN_TIMEOUT:.0f} s and was stopped")
        self.runs += 1
        errors = [l for l in self.log if re.search(r"error|singular|too small|aborted", l, re.I)]
        out = {}
        try:
            for name in vectors:
                p = self.lib.ngGet_Vec_Info(name.encode())
                if not p:
                    raise SimError(f"ngspice produced no vector {name}" + ("".join(errors) and ":\n" + "".join(errors)))
                v = p.contents
                if not v.v_realdata or v.v_length == 0:
                    raise SimError(f"ngspice returned no data for {name}:\n" + "".join(errors or self.log[-15:]))
                out[name] = np.ctypeslib.as_array(v.v_realdata, shape=(v.v_length,)).copy()
        finally:
            self.lib.ngSpice_Command(b"destroy all")
            self.lib.ngSpice_Command(b"remcirc")
        return out


_engine = None


def engine():
    """The shared ngspice instance, or None if ngspice can't be found or loaded."""
    global _engine
    if _engine is None:
        path = kicadenv.ngspice_lib()
        if path is None:
            return None
        try:
            _engine = Ngspice(path)
        except OSError:
            return None
    return _engine


# ------------------------------------------------------------------------------------------------------------- netlist


def _num(x):
    return f"{x:.9g}"


def _soft(which, a, b):
    """min or max of two expressions with the corner rounded over LIMIT_SOFT, which ngspice converges on."""
    sign = "-" if which == "min" else "+"
    return f"(0.5*(({a})+({b}){sign}sqrt((({a})-({b}))^2+{_num(LIMIT_SOFT ** 2)})))"


class Netlist:
    """A case's circuit as SPICE, for one set of inputs, part values and clamp voltages.

    Only the part of the circuit that can affect the given nodes goes in: everything connected to them through
    elements, cut at fixed nodes (rails and sources), which nothing on the far side can move."""

    def __init__(self, circ, sw_fixed, nodes):
        self.circ, self.gnd = circ, circ.gnd
        self.sw_fixed = sw_fixed
        fixed = lambda n: n == circ.gnd or n in circ.fixed
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for e in circ.elems:
            free = [n for n in e.nodes if not fixed(n)]
            for a, b in zip(free, free[1:]):
                parent[find(a)] = find(b)
        roots = {find(n) for n in nodes if not fixed(n)}
        self.elems = [(i, e) for i, e in enumerate(circ.elems, 1)
                      if any(not fixed(n) and find(n) in roots for n in e.nodes)]
        self.fixed = sorted({n for _, e in self.elems for n in e.nodes if n in circ.fixed} |
                            {n for n in nodes if n in circ.fixed})
        names = sorted({n for _, e in self.elems for n in e.nodes} | set(self.fixed) | set(nodes))
        self.node = {n: f"n{i}" for i, n in enumerate(names, 1)}
        self.node[self.gnd] = "0"
        self.limiters = {}
        for _, e in self.elems:
            if e.kind == "D" and getattr(e, "amp", None):
                self.limiters.setdefault(e.amp, []).append(e)
        # element name -> the SPICE source whose current is the element's current
        self.spice = {}
        for i, e in self.elems:
            if e.kind == "D" and not getattr(e, "amp", None):
                self.spice[e.name] = f"vd{i}"
            elif e.kind == "S" and sw_fixed.get(e.name) != "off":
                self.spice[e.name] = f"vs{i}"

    def v(self, n):
        return "0" if n == self.gnd else f"v({self.node[n]})"

    def lines(self, inputs, values, clamp_high, t_stop, t_step, t_start, t_max, save, solver=0):
        method, reltol, emission = SOLVERS[solver]
        out = ["* circuit check counterexample, written by tools/kicad/circuit_sim.py"]
        out += [f"* {sp} = {n}" for n, sp in sorted(self.node.items(), key=lambda kv: kv[1]) if sp != "0"]
        out.append(f".options reltol={reltol:g} vntol={reltol * 1e-3:g} abstol={reltol * 1e-8:g} method={method} itl4=200")
        models = []
        for i, e in self.elems:
            nd = [self.node[n] for n in e.nodes]
            val = values.get(e.name, e.value)
            if e.kind == "R":
                out.append(f"R{i} {nd[0]} {nd[1]} {_num(val)}")
            elif e.kind == "C":
                out.append(f"C{i} {nd[0]} {nd[1]} {_num(val)}")
            elif e.kind == "E":
                out += self._amp(i, e, nd)
            elif e.kind == "D":
                if getattr(e, "amp", None):
                    continue
                v_on = e.vmax if clamp_high else e.vmin
                out.append(f"VD{i} {nd[0]} xd{i} DC {_num(v_on - DIODE_VF * emission)}")
                out.append(f"D{i} xd{i} {nd[1]} DM{i}")
                models.append(f".model DM{i} D(IS=1e-14 N={emission} RS={_num(max(e.r_dyn, DIODE_RS))})")
            elif e.kind == "S":
                state = self.sw_fixed.get(e.name)
                if state == "off":
                    continue
                out.append(f"VS{i} xs{i} {nd[1]} DC 0")
                if state == "on":
                    out.append(f"R{i} {nd[0]} xs{i} {_num(e.r_on)}")
                else:
                    cp, cn = (nd[2], nd[1]) if e.polarity > 0 else (nd[1], nd[2])
                    out.append(f"S{i} {nd[0]} xs{i} {cp} {cn} SW{i}")
                    models.append(f".model SW{i} SW(VT={_num(sum(e.vth) / 2)} VH=0 RON={_num(e.r_on)} ROFF=1e9)")
        for k, n in enumerate(self.fixed, 1):
            out.append(f"VF{k} {self.node[n]} 0 {self._source(self.circ.fixed[n], inputs.get(n))}")
        for n, sp in sorted(self.node.items()):
            if sp != "0":
                out.append(f"RLEAK_{sp} {sp} 0 1e12")
        out += models
        out.append(".save " + " ".join(save))
        out.append(f".tran {_num(t_step)} {_num(t_stop)} {_num(t_start)} {_num(t_max)}")
        out.append(".end")
        return out

    def _amp(self, i, e, nd):
        """An amplifier. A closed-loop gain stage is a behavioural source. An op-amp (gain ≥ 1000) is a
        transconductance into R ‖ C, which gives it its open-loop gain and gain-bandwidth product and keeps the
        feedback loop from being a stiff algebraic one. A soft clamp keeps the internal node inside the rails, so the
        output comes off a rail as quickly as a rail-to-rail part. Either way the output limits are the model's
        rail clamps, rounded over LIMIT_SOFT, and the output has AMP_ROUT in series."""
        hi = lo = None
        for c in self.limiters.get(e.name, []):
            if c.nodes[0] == e.nodes[0]:                  # out ≤ V(rail) + v_on
                hi = f"({self.v(c.nodes[1])}+({_num(c.vmin)}))"
            if c.nodes[1] == e.nodes[0]:                  # out ≥ V(rail) − v_on
                lo = f"({self.v(c.nodes[0])}-({_num(c.vmin)}))"
        inp, inn = self.v(e.nodes[1]), self.v(e.nodes[2])
        eps = _num((LIMIT_SOFT / 10) ** 2)                  # the op-amp clamp starts within a few mV of its rail
        lines = []
        if e.value < 1000:
            expr = f"{_num(e.value)}*({inp}-{inn})"
            if hi:
                expr = _soft("min", expr, hi)
            if lo:
                expr = _soft("max", expr, lo)
            lines.append(f"B{i} xb{i} 0 V={expr}")
        else:
            gain = min(e.value, AMP_GAIN)
            pole = getattr(e, "gbw", 1e6) / gain
            x = f"x{i}"
            lines += [f"G{i} 0 {x} {self._n(e.nodes[1])} {self._n(e.nodes[2])} 1",
                      f"R{i}x {x} 0 {_num(gain)}", f"C{i}x {x} 0 {_num(1 / (2 * math.pi * pole * gain))}"]
            ramps = []
            if hi:
                ramps.append(f"0.5*((v({x})-{hi})+sqrt((v({x})-{hi})^2+{eps}))")
            if lo:
                ramps.append(f"-0.5*(({lo}-v({x}))+sqrt(({lo}-v({x}))^2+{eps}))")
            if ramps:
                lines.append(f"B{i}w {x} 0 I={_num(1000.0)}*({'+'.join(ramps)})")
            lines.append(f"B{i} xb{i} 0 V=v({x})")
        lines.append(f"RB{i} xb{i} {self.node[e.nodes[0]]} {_num(AMP_ROUT)}")
        return lines

    def _n(self, n):
        return self.node[n]

    @staticmethod
    def _source(stim, inp):
        if inp is None:
            return f"DC {_num(stim.mid if stim.kind != 'tone' else stim.mid)}"
        if inp[0] == "dc":
            return f"DC {_num(inp[1])}"
        if inp[0] == "tone":
            _, f, phase = inp[:3]
            amp = inp[3] if len(inp) > 3 else stim.amp
            return f"DC {_num(stim.mid)} SIN({_num(stim.mid)} {_num(amp)} {_num(f)} 0 0 {_num(phase)})"
        pts, last = [], -1.0
        for t, v in inp[1]:
            if t > last + 1e-15:
                pts.append(f"{_num(t)} {_num(v)}")
                last = t
        return f"DC {_num(inp[1][0][1])} PWL({' '.join(pts)})"


# ------------------------------------------------------------------------------------------------------------- probes


class Probe:
    """What to measure for one check and when it counts as broken.

    terms   the quantity, as the bound engine's terms; ("clamp", name, k) and ("switch", name, k) add element currents
    side    +1: the check breaks above limit; −1: below; 0: |value| above limit
    square  compare value² / square instead (resistor power: square is the resistance)
    clamp   for a limit with protection diodes: the clamp whose current decides, and the injection rating (None: any
            conduction past the limit breaks it)
    seeds   (terms, side) pairs to start the search from
    """

    def __init__(self, terms, side, limit, seeds, square=None, clamp=None, inject=None, unit="V"):
        self.terms, self.side, self.limit, self.seeds = terms, side, limit, seeds
        self.square, self.clamp, self.inject, self.unit = square, clamp, inject, unit

    def key(self):
        return (repr(self.terms), self.side, self.limit, self.square, self.clamp, self.inject)

    def score(self, series):
        """How far past the limit the run went (> 0 means broken), the worst value reached, and the most current its
        protection clamp carried (None without one)."""
        x = series["value"]
        current = float(np.max(series["clamp"])) if self.clamp is not None else None
        if self.square:
            val = float(np.max(x * x) / self.square)
            return val - self.limit, val, current
        if self.side > 0:
            val = float(np.max(x))
            over = val - self.limit
        elif self.side < 0:
            val = float(np.min(x))
            over = self.limit - val
        else:
            val = float(np.max(np.abs(x)))
            over = val - self.limit
        if self.clamp is not None and over > 0:
            tol = max(0.01 * abs(self.limit), 0.01)
            if over < tol:
                return over - tol, val, current
            if self.inject is not None:
                return current - self.inject, val, current
        return over, val, current


def _series(net, vec, probe, values):
    """Evaluate a probe's quantity (and its clamp's current) from simulated vectors."""
    total = 0.0
    for kind, what, k in probe.terms:
        if kind == "v":
            if what != net.gnd:
                total = total + k * vec[net.v(what)]
        elif kind == "r":
            e = net.circ.element(what)
            r = values.get(e.name, e.value)
            va = vec[net.v(e.nodes[0])] if e.nodes[0] != net.gnd else 0.0
            vb = vec[net.v(e.nodes[1])] if e.nodes[1] != net.gnd else 0.0
            total = total + k * (va - vb) / r
        elif kind in ("clamp", "switch"):
            total = total + k * vec[f"i({net.spice[what]})"]
    out = {"value": np.broadcast_to(total, vec["time"].shape)}
    if probe.clamp is not None:
        out["clamp"] = vec[f"i({net.spice[probe.clamp]})"]
    return out


def _save_list(net, probes):
    names = {"time"}
    for p in probes:
        for kind, what, _ in p.terms:
            if kind == "v" and what != net.gnd:
                names.add(net.v(what))
            elif kind == "r":
                e = net.circ.element(what)
                names |= {net.v(n) for n in e.nodes[:2] if n != net.gnd}
            elif kind in ("clamp", "switch"):
                names.add(f"i({net.spice[what]})")
        if p.clamp is not None:
            names.add(f"i({net.spice[p.clamp]})")
    return sorted(names)


# -------------------------------------------------------------------------------------------------------------- search


class Trial:
    def __init__(self, inputs, values, clamp_high, settle, label):
        self.inputs, self.values, self.clamp_high, self.settle, self.label = inputs, values, clamp_high, settle, label

    def timing(self, attempt=0):
        """(t_stop, t_step, t_start, t_max, periods, final) for one attempt at this trial. Tones get a short run
        first; search() lengthens it while the peak still moves from one period to the next. A waveform runs to its
        end; constants only need the operating point and a moment after."""
        tones = [i[1] for i in self.inputs.values() if i[0] == "tone"]
        pwl_end = max([i[1][-1][0] for i in self.inputs.values() if i[0] == "pwl"] or [0.0])
        if tones:
            fmax, fmin = max(tones), min(tones)
            t_max = 1.0 / (40 * fmax)
            cap = min(5 * self.settle, MAX_STEPS * t_max, 20.0)
            settle = min(max(30.0 / fmin, 0.02) * 4 ** attempt, cap)
            settle = max(settle, pwl_end)
            t_stop = settle + 4.0 / fmin
            return t_stop, t_stop / 4000, settle, t_max, 1.0 / fmin, settle >= cap
        t_stop = max(pwl_end, min(5 * self.settle, 1.0), 1e-6) * 1.0001
        return t_stop, t_stop / 4000, 0.0, t_stop / 200, None, True


def _describe(trial, circ):
    parts = []
    for n, inp in sorted(trial.inputs.items()):
        who = circ.fixed_by.get(n, n)
        if inp[0] == "dc":
            parts.append(f"{who} at {fmt(inp[1], 'V')}")
        elif inp[0] == "tone":
            amp = inp[3] if len(inp) > 3 else circ.fixed[n].amp
            parts.append(f"{who}: {fmt(amp, 'V')} peak at {fmt(inp[1], 'Hz')}")
        else:
            edges = (len(inp[1]) - 2) // 2
            lo, hi = min(v for _, v in inp[1]), max(v for _, v in inp[1])
            what = "a step" if edges == 1 else f"{edges} steps" if edges > 1 else "a constant"
            parts.append(f"{who}: {what} between {fmt(lo, 'V')} and {fmt(hi, 'V')} over {fmt(inp[1][-1][0], 's')}")
    corner = "worst tolerance corner" if trial.values else "nominal parts"
    return "; ".join(parts) + f" ({corner}, {trial.label})"


def _variants(seed, circ, analysis_tol, rng, n):
    """Random neighbours of a seed: other frequencies, phases, levels, square waves, steps and tolerance corners."""
    out = []
    for _ in range(n):
        inputs = {}
        for node, inp in seed.inputs.items():
            st = circ.fixed[node]
            if inp[0] == "tone":
                f = min(max(inp[1] * math.exp(rng.gauss(0, 1.0)), st.band[0]), st.band[1])
                amp = st.amp if rng.random() < 0.8 else st.amp * rng.random()
                inputs[node] = ("tone", f, rng.uniform(0, 360), amp)
            elif inp[0] == "dc":
                inputs[node] = ("dc", rng.choice([st.lo, st.hi]) if rng.random() < 0.8 else rng.uniform(st.lo, st.hi))
            else:
                horizon = max(inp[1][-1][0], 1e-6)
                r = rng.random()
                if r < 0.4:
                    period = horizon * math.exp(rng.uniform(math.log(1e-3), math.log(2.0)))
                    cycles = int(min(horizon / period, 200))
                    pts, t, hi = [(0.0, st.hi)], 0.0, True
                    for _ in range(max(cycles * 2, 1)):
                        t += period / 2
                        pts += [(t, st.hi if hi else st.lo), (t + horizon * 1e-9, st.lo if hi else st.hi)]
                        hi = not hi
                    pts.append((horizon, pts[-1][1]))
                    inputs[node] = ("pwl", pts)
                elif r < 0.8:
                    a, b = (st.lo, st.hi) if rng.random() < 0.5 else (st.hi, st.lo)
                    t = horizon * rng.uniform(0.3, 0.99)
                    inputs[node] = ("pwl", [(0.0, a), (t, a), (t + horizon * 1e-9, b), (horizon, b)])
                else:
                    inputs[node] = inp
        values = dict(seed.values)
        for e in analysis_tol:
            if rng.random() < 0.3:
                values[e.name] = e.value * (1 + e.tol * rng.choice([-1, 1]))
        out.append(Trial(inputs, values, rng.random() < 0.5, seed.settle, "random variant"))
    return out


class Outcome:
    def __init__(self, probe):
        self.probe, self.over, self.value, self.trial, self.runs, self.note = probe, -math.inf, None, None, 0, ""
        self.current = self.max_current = None

    @property
    def broken(self):
        return self.over > 0


def _settled(t, series, period):
    """Whether every probe's peak in the last period is within 0.5 % (or 1 mV / 1 µA) of the one before."""
    if not period:
        return True
    end = t[-1]
    last = (t > end - period)
    prev = (t > end - 2 * period) & ~last
    if not last.any() or not prev.any():
        return False
    for ser in series:
        for x in ser.values():
            a, b = np.max(np.abs(x[last])), np.max(np.abs(x[prev]))
            if abs(a - b) > max(0.005 * max(a, b), 1e-6):
                return False
    return True


_searched = {}


def search(analysis, branch, probes, budget=12, seed=0, save=None):
    """Simulate one case's branch to look for inputs that break the probes. Returns an Outcome per probe, and writes
    the worst run's netlist for each broken probe to save(probe_index) when given. A search whose subcircuit,
    sources and probes match an earlier one (the same circuit in another switch branch) reuses its outcomes."""
    sim = engine()
    if sim is None:
        raise SimError("ngspice not found: install KiCad or set NGSPICE_LIB")
    circ = analysis.circ
    rng = random.Random(seed)
    sw = branch["sw"]
    probe_nodes = set()
    for p in probes:
        for kind, what, _ in p.terms:
            probe_nodes |= set(circ.element(what).nodes) if kind != "v" else {what}
        if p.clamp is not None:
            probe_nodes |= set(circ.element(p.clamp).nodes)
    net = Netlist(circ, dict(branch["forced"]), probe_nodes)
    key = (tuple((e.key(), getattr(e, "vmin", None), getattr(e, "vmax", None), net.sw_fixed.get(e.name))
                 for _, e in net.elems),
           tuple((n, circ.fixed[n].kind, circ.fixed[n].lo, circ.fixed[n].hi, circ.fixed[n].band) for n in net.fixed),
           tuple(p.key() for p in probes), budget, seed)
    if key in _searched:
        return _searched[key]
    tol = [e for e in circ.elems if e.kind in "RC" and e.tol > 0]
    seeds, seen = [], set()
    for p in probes:
        for terms, side in p.seeds:
            inputs, values, settle = analysis.worst_input(terms, side, sw)
            high = p.clamp is None and not p.square
            key = (repr(sorted(inputs.items())), repr(sorted(values.items())), high)
            if key not in seen:
                seen.add(key)
                seeds.append(Trial(inputs, values, high, settle, "the bound's worst case"))
    trials = list(seeds)
    for s in seeds:
        trials += _variants(s, circ, tol, rng, max(budget // max(len(seeds), 1), 1))
    outcomes = [Outcome(p) for p in probes]
    names = _save_list(net, probes)
    failed, last_error = 0, ""
    for trial in trials:
        for attempt in range(4):
            t_stop, t_step, t_start, t_max, period, final = trial.timing(attempt)
            vec, err = None, None
            for solver in range(len(SOLVERS)):
                lines = net.lines(trial.inputs, trial.values, trial.clamp_high, t_stop, t_step, t_start, t_max, names,
                                  solver)
                try:
                    vec = sim.run(lines, names)
                    break
                except SimError as e:
                    err = e
            if vec is None:
                failed += 1
                last_error = str(err).splitlines()[0]
                break
            series = [_series(net, vec, p, trial.values) for p in probes]
            settled = _settled(vec["time"], series, period)
            if final or settled:
                break
        if vec is None:
            continue
        for p, o, ser in zip(probes, outcomes, series):
            if period:
                keep = vec["time"] >= vec["time"][-1] - 2 * period    # the last two periods: steady state
                ser = {k: v[keep] for k, v in ser.items()}
            over, val, current = p.score(ser)
            o.runs += 1
            if current is not None:
                o.max_current = max(o.max_current or 0.0, current)
            if over > o.over:
                o.over, o.value, o.current, o.trial, o.lines = over, val, current, trial, lines
                o.note = "" if settled else "its tone run reached the length limit before the peaks settled"
    for k, o in enumerate(outcomes):
        o.what = _describe(o.trial, circ) if o.trial else ""
        if failed:
            o.note = (o.note + "; " if o.note else "") + f"{failed} of {len(trials)} runs didn't converge ({last_error})"
        if save and o.trial is not None and o.broken:
            with open(save(k), "w") as f:
                f.write("\n".join(o.lines) + "\n")
    _searched[key] = outcomes
    return outcomes
