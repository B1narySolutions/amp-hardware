"""What a circuit check needs besides the schematic: what can arrive at each connector, which rails are up, how the firmware
sets the pins, and what the design claims. Part models (tools/kicad/parts/) use the same sources.

A board's spec is a Python file next to its schematic, `<board>.verify.py`, that builds a `Spec` named `spec`:

    from circuit_spec import Spec, V, I, Gain, dc, wave, tone, load, open_
    spec = Spec()
    spec.rail("+5V", dc(4.70, 5.25))
    spec.port("J2.3", nominal=tone(2.83, r=1), misuse=[wave(-5, 5, r=10, label="line out at full level")])
    spec.state("on", rails=["+5V"])
    spec.claim("AUX peak", V("/AUDIO_IN_2"), lo=-1.13, hi=1.13, cases="nominal")

Voltages are in volts, currents in amps, resistances in ohms, frequencies in Hz.
"""
import fnmatch
import re

# ---------------------------------------------------------------------------------------------------------------- sources


class Stim:
    """What one source can do.

    kind is one of:
      "dc"    constant, somewhere in lo..hi (a supply rail, a battery voltage);
      "wave"  any waveform inside lo..hi, steps and DC included (a fault, a pedal, a logic output);
      "tone"  a sine of any frequency in `band` around a fixed offset, lo..hi being offset -/+ peak (an audio source);
      "open"  nothing connected.
    r is the source's output resistance, or a (min, max) range when it isn't known exactly (checked at both ends, like a
    part tolerance). clamp=(lo, hi) adds the far end's protection diodes, which hold the pin inside lo..hi and take the
    excess current; i_max limits the current in or out of the port (through r and the clamp).
    """

    def __init__(self, kind, lo=0.0, hi=0.0, r=0.0, band=None, clamp=None, i_max=None, label=""):
        if kind not in ("dc", "wave", "tone", "open"):
            raise ValueError(f"unknown source kind {kind!r}")
        if hi < lo:
            raise ValueError(f"source range {lo}..{hi} is upside down")
        self.kind, self.lo, self.hi = kind, float(lo), float(hi)
        if isinstance(r, (tuple, list)):
            r_lo, r_hi = max(float(r[0]), 1.0), float(r[1])     # 1 Ω floor: a corner can't be a short
            self.r, self.r_tol, self.r_range = (r_lo + r_hi) / 2, (r_hi - r_lo) / (r_hi + r_lo), (float(r[0]), r_hi)
        else:
            self.r, self.r_tol, self.r_range = float(r), 0.0, None
        self.band = tuple(band) if band else None
        self.clamp, self.i_max, self.label = clamp, i_max, label

    @property
    def mid(self):
        return (self.lo + self.hi) / 2

    @property
    def amp(self):
        return (self.hi - self.lo) / 2

    def describe(self):
        if self.label:
            return self.label
        if self.kind == "open":
            return "open"
        r = (f", {fmt(self.r_range[0], 'Ω')}..{fmt(self.r_range[1], 'Ω')}" if self.r_range else
             f", {fmt(self.r, 'Ω')}" if self.r else "")
        if self.kind == "tone":
            off = f" on {fmt(self.mid, 'V')}" if self.mid else ""
            return f"sine ≤ {fmt(self.amp, 'V')} peak{off}, {fmt(self.band[0], 'Hz')}–{fmt(self.band[1], 'Hz')}{r}"
        if self.lo == self.hi:
            return f"{fmt(self.lo, 'V')}{r}"
        what = "DC" if self.kind == "dc" else "any waveform"
        return f"{what} {fmt(self.lo, 'V')}..{fmt(self.hi, 'V')}{r}"


def dc(lo, hi=None, r=0.0, **kw):
    """A constant voltage somewhere in lo..hi (hi defaults to lo)."""
    return Stim("dc", lo, lo if hi is None else hi, r=r, **kw)


def wave(lo, hi, r=0.0, **kw):
    """Any waveform that stays inside lo..hi, including DC and steps."""
    return Stim("wave", lo, hi, r=r, **kw)


def tone(peak, band=(20.0, 20e3), offset=0.0, r=0.0, **kw):
    """A sine of at most `peak` volts at any frequency in `band`, on a constant `offset`."""
    return Stim("tone", offset - peak, offset + peak, r=r, band=band, **kw)


def load(r, **kw):
    """A resistor to GND: an input that loads the pin and drives nothing."""
    return Stim("dc", 0.0, 0.0, r=r, **kw)


def open_(**kw):
    """Nothing connected (a clamp=(lo, hi) still models a powered-off input's protection diodes)."""
    return Stim("open", **kw)


# ------------------------------------------------------------------------------------------------------------- quantities


class V:
    """The voltage of a net (or a part's internal node, "A1:in1"), relative to `ref` (GND by default)."""

    def __init__(self, net, ref=None):
        self.net, self.ref = net, ref

    def describe(self):
        return f"V({self.net})" if self.ref is None else f"V({self.net}, {self.ref})"


class I:
    """The current through a two-terminal part (R, C), flowing from its pin 1 to its pin 2."""

    def __init__(self, ref):
        self.ref = ref

    def describe(self):
        return f"I({self.ref})"


class Gain:
    """The gain in dB from one or more sources, driven together in phase, to a net, at frequency f. A source is a port
    ("J2.3") or a model's own source node ("A1:out18.src")."""

    def __init__(self, ports, net, f):
        self.ports = [ports] if isinstance(ports, str) else list(ports)
        self.net, self.f = net, float(f)

    def describe(self):
        return f"gain({'+'.join(self.ports)} → {self.net} @ {fmt(self.f, 'Hz')})"


# ------------------------------------------------------------------------------------------------------------------ spec


class Port:
    def __init__(self, pin, nominal, misuse, exposed, note):
        self.pin, self.nominal, self.misuse, self.exposed, self.note = pin, nominal, misuse, exposed, note


class State:
    def __init__(self, name, rails, powered, unpowered, absent, ports, misuse, note):
        self.name, self.rails, self.note = name, set(rails), note
        self.powered, self.unpowered, self.absent = set(powered), set(unpowered), set(absent)
        self.ports, self.misuse = dict(ports or {}), misuse


class Claim:
    def __init__(self, name, quantity, lo, hi, cases, source):
        self.name, self.quantity, self.lo, self.hi, self.cases, self.source = name, quantity, lo, hi, cases, source


class Waiver:
    def __init__(self, check, cases, reason):
        self.check, self.cases, self.reason = check, cases, reason


class Spec:
    """Everything a board's check knows besides the schematic. See the module docstring."""

    def __init__(self):
        self.rails = {}       # net -> Stim while the rail is on (it is 0 V while off)
        self.ports = {}       # "J6.3" -> Port
        self.states = []      # power states, each checked on its own
        self.configs = {}     # ref -> firmware pin modes and other model options
        self.claims, self.waivers = [], []
        self.provided = []    # (Interface, {signal: pin}) this board drives
        self.stages = []      # unpowered resistance checks from the test plan
        self.fault_states = None  # power states the fault check runs in (default: the first)
        self.warn_ratio = 0.8  # stress above this fraction of a rating is a warning

    def rail(self, net, on):
        """A supply net the board receives or makes. Each power state lists the rails that are on; the rest sit at 0 V."""
        self.rails[net] = on

    def port(self, pin, nominal, misuse=(), exposed=False, note=""):
        """What the outside world can put on a connector pin ("J6.3").

        nominal: a Stim, or a list of alternatives (a jack with and without a plug). misuse: alternatives that must not
        damage anything (a wire on the wrong terminal); each is checked on its own, with every other port nominal.
        exposed: the pin is on a cable or jack someone can touch, so it needs ESD protection.
        """
        self.ports[pin] = Port(pin, nominal if isinstance(nominal, (list, tuple)) else [nominal],
                               list(misuse) if isinstance(misuse, (list, tuple)) else [misuse], exposed, note)

    def state(self, name, rails=(), powered=(), unpowered=(), absent=(), ports=None, misuse=True, note=""):
        """A power state: the rails that are on, parts powered some other way (a module on USB) or not at all, parts
        not fitted, and port overrides (a display that is off). misuse=False skips the misuse cases in this state."""
        self.states.append(State(name, rails, powered, unpowered, absent, ports, misuse, note))

    def config(self, ref, **options):
        """Model options for one part, usually firmware pin modes: config("A1", out=[14, 28], adc=[22, 25])."""
        self.configs.setdefault(ref, {}).update(options)

    def claim(self, name, quantity, lo=None, hi=None, cases="nominal", source=""):
        """A number the design depends on: quantity must stay inside lo..hi in every matching case."""
        self.claims.append(Claim(name, quantity, lo, hi, cases, source))

    def waive(self, check, cases, reason):
        """Accept a failing check (fnmatch pattern on its id) in matching cases, and say why."""
        self.waivers.append(Waiver(check, cases, reason))

    def provides(self, iface, pins, cases="nominal"):
        """This board drives these signals of a contract ({signal: pin}): check, in the matching cases (the states in
        which it drives them), that each pin stays inside the contract's range and that its source resistance stays
        under the contract's maximum."""
        self.provided.append((iface, dict(pins), cases))

    def test_stage(self, name, absent=(), rails=None, ports=None):
        """A bring-up test stage (see Stage). The circuit check verifies each expected value against the schematic;
        the fault check works out which assembly faults each reading catches."""
        st = Stage(name, absent, rails, ports)
        self.stages.append(st)
        return st


class Interface:
    """A connector between two boards, as a contract both boards' specs load. For each signal it says which board drives
    it and what that board promises: a source (range, kind, and source resistance, often a range). The receiving
    board's spec takes its port assumption from it, with iface.source(name). The driving board's spec checks its own
    output against it with spec.provides(iface, {name: pin}). When either side changes the contract, both checks see it.

        iface = Interface("carrier–power board")
        iface.signal("BAT", by="power board", source=dc(0, 3.3, r=(0, 10e3)), note="README: Battery level")
    """

    def __init__(self, name):
        self.name, self.signals = name, {}

    def signal(self, name, by, source, note=""):
        self.signals[name] = {"by": by, "source": source, "note": note}

    def source(self, name):
        return self.signals[name]["source"]

    @staticmethod
    def load(path):
        """The Interface named `interface` in a contract file (a path relative to the calling spec works)."""
        import inspect
        import os
        import runpy
        if not os.path.isabs(path):
            caller = inspect.stack()[1].frame.f_globals.get("__file__", "")
            path = os.path.join(os.path.dirname(os.path.abspath(caller)), path)
        return runpy.run_path(path)["interface"]


class Stage:
    """A stage of the bring-up test plan: DMM checks made with some parts not fitted. Unpowered, it takes resistance
    readings; with rails (net -> Stim, the bench supply) it takes DC voltage readings, the ports set by `ports`
    (pin -> Stim) and every other port open."""

    def __init__(self, name, absent, rails=None, ports=None):
        self.name, self.absent, self.checks = name, set(absent), []
        self.rails, self.ports = dict(rails or {}), dict(ports or {})

    def measure(self, id, a, b, expect=None, note=""):
        """A DMM resistance check from a to b (each a pin "J2.3", "A1.25" or a net name). expect: ohms (±10 %),
        (lo, hi), "open" (≥ 10 MΩ) or "short" (≤ 1 Ω). Without expect it only counts toward fault coverage."""
        if self.rails:
            raise ValueError(f"{self.name} is powered: take voltage readings with voltage()")
        self.checks.append({"id": id, "a": a, "b": b, "expect": expect, "note": note, "kind": "ohms"})

    def voltage(self, id, a, expect=None, b="GND", note=""):
        """A DMM DC voltage check at a (against b, GND by default) in a powered stage. expect: (lo, hi) in volts."""
        if not self.rails:
            raise ValueError(f"{self.name} is unpowered: take resistance readings with measure()")
        self.checks.append({"id": id, "a": a, "b": b, "expect": expect, "note": note, "kind": "volts"})


class Case:
    """One combination that gets checked: a power state, each port's source, and nominal or misuse."""

    def __init__(self, state, kind, stims, misuse_port=None, note="", variant=""):
        self.state, self.kind, self.stims, self.misuse_port, self.note = state, kind, stims, misuse_port, note
        self.variant = variant

    @property
    def name(self):
        if self.kind == "nominal":
            return self.state.name + (f" ({self.variant})" if self.variant else "")
        return f"{self.state.name} + {self.misuse_port}: {self.note}"


def matches(selector, case):
    """Case selectors: "all", "nominal", "misuse", a state name (that state's nominal cases), or an fnmatch pattern
    on the case name ("on*" is every case in state "on", misuse included). A list matches if any entry does."""
    if selector in ("all", "*"):
        return True
    if isinstance(selector, (list, tuple)):
        return any(matches(s, case) for s in selector)
    if selector in ("nominal", "misuse"):
        return case.kind == selector
    if selector == case.state.name:
        return case.kind == "nominal"
    return fnmatch.fnmatch(case.name, selector)


def expand_cases(spec, limit=256):
    """Every case to check: for each power state, each combination of nominal alternatives, then each misuse alone."""
    cases = []
    for st in spec.states:
        base = {}
        for pin, port in spec.ports.items():
            over = st.ports.get(pin)
            base[pin] = [over] if isinstance(over, Stim) else list(over) if over else port.nominal
        combos = [{}]
        for pin, alts in base.items():
            combos = [dict(c, **{pin: a}) for c in combos for a in alts]
            if len(combos) > limit:
                raise ValueError(f"too many nominal combinations in state {st.name!r}")
        for c in combos:
            alts = [f"{p} {s.describe()}" for p, s in c.items() if len(base[p]) > 1]
            cases.append(Case(st, "nominal", c, variant=", ".join(alts)))
        if st.misuse:
            for pin, port in spec.ports.items():
                if pin in st.ports:
                    continue
                for alt in port.misuse:
                    cases.append(Case(st, "misuse", dict(combos[0], **{pin: alt}), misuse_port=pin, note=alt.describe()))
    return cases


# ----------------------------------------------------------------------------------------------------------------- values

_SI = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3, "": 1.0, "k": 1e3, "K": 1e3, "M": 1e6,
       "Meg": 1e6, "G": 1e9, "R": 1.0}
_NUM = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(Meg|[pnuµμmkKMGR]?)(\d*)\s*([A-Za-zΩ]*)\s*$")


def parse_value(text):
    """A component value as KiCad writes it: "4.7uF", "3.3k", "4k7", "1M", "470", "2R2". Returns (number, unit letters)."""
    m = _NUM.match(text)
    if not m:
        return None, ""
    whole, prefix, frac, unit = m.groups()
    num = float(f"{whole}.{frac}") if frac and "." not in whole else float(whole)
    return num * _SI[prefix], unit


def parse_passive(text):
    """Split a passive's Value field into its value and an optional voltage rating: "47uF 16V" -> (47e-6, 16.0)."""
    value, rating = None, None
    for tok in text.replace(",", " ").split():
        if re.match(r"^\d+(\.\d+)?V$", tok):
            rating = float(tok[:-1])
        elif value is None:
            value, _ = parse_value(tok)
    return value, rating


def fmt(x, unit=""):
    """A number with an SI prefix: fmt(0.00027, "A") -> "270 µA"."""
    if x is None:
        return "—"
    if x != x:
        return "nan"
    if abs(x) == float("inf"):
        return ("−" if x < 0 else "") + "∞" + (" " + unit if unit else "")
    a = abs(x)
    if a < 1e-15:
        return f"0 {unit}".strip()
    for scale, p in ((1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"), (1e-12, "p")):
        if a >= scale * 0.9995 or scale == 1e-12:
            v = x / scale
            s = f"{v:.3g}" if abs(v) < 100 else f"{v:.0f}"
            s = s.replace("-", "−")
            return f"{s} {p}{unit}".strip() if unit or p else s
    return f"{x:.3g}"
