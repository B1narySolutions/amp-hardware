"""Check a schematic against what its parts can take and what the design claims, for everything a spec says can arrive
at the connectors.

    python3 tools/kicad/circuit_verify.py audio-board/rev2/seed3-carrier.kicad_sch
    python3 tools/kicad/circuit_verify.py board.kicad_sch -v --case "on*" --json report.json

The spec is `<board>.verify.py` next to the schematic (see circuit_spec.py); part models live in tools/kicad/parts/.
For every case (a power state, with each port's nominal source, then each misuse alone) the bound checker
(circuit_bounds.py) works out the range of every voltage and current, and this script checks:

  limits   every pin against its part's absolute maximum (all cases) and operating range (nominal cases, powered)
  clamps   current through ESD diodes and IC protection diodes against their rating, when a limit is exceeded
  ratings  resistor power and capacitor voltage against their rating; polarized caps against reverse voltage
  loads    the lowest impedance an output sees against its minimum load
  ports    current in or out of a connector pin, where the spec gives a limit
  claims   the numbers the design depends on
  structure  parts without a model, exposed pins without an ESD clamp, floating inputs

A result the bounds can't settle (UNPROVEN: the bound goes through a conducting clamp) is then simulated in ngspice
(circuit_sim.py), searching for an input that breaks it. It becomes a FAIL with that input, or SEARCHED with the worst
value reached.

It never modifies anything. The exit status is 1 when a check fails or stays unproven, so it can gate a commit.
"""
import argparse
import fnmatch
import glob
import json
import math
import os
import re
import runpy
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import schnet  # noqa: E402
import circuit_sim  # noqa: E402
from circuit_bounds import Analysis, Circuit, Elem, _UF  # noqa: E402
from circuit_sim import Probe  # noqa: E402
from circuit_spec import Gain, I, V, dc, expand_cases, fmt, matches, parse_passive, parse_value, tone, wave  # noqa: E402

PARTS_DIR = os.path.join(HERE, "parts")
NOT_MODELLED = ("J", "TP", "H", "MH", "FID", "LOGO", "G")   # connectors (ports), test points, holes, artwork

# Resistor power by package when neither a field nor the catalog gives it (typical thick-film ratings).
R_POWER = {"0201": 0.05, "0402": 0.0625, "0603": 0.1, "0805": 0.125, "1206": 0.25, "1210": 0.5, "2010": 0.75,
           "2512": 1.0}


class Limit:
    """One side of a voltage limit: V(node) − V(ref) must stay ≤ offset (side "hi") or ≥ offset (side "lo")."""

    def __init__(self, id, owner, node, ref, side, offset, kind, clamp=None, inject=None, source="", assumed=False,
                 powered=True, input=True):
        self.id, self.owner, self.node, self.ref, self.side, self.offset = id, owner, node, ref, side, offset
        self.kind, self.clamp, self.inject, self.source, self.assumed = kind, clamp, inject, source, assumed
        self.powered, self.input = powered, input


class Builder:
    """What a part model gets: its pins' nets, whether it is powered, its options, and calls that add elements and
    limits. Nodes are pin numbers ("16" or 16), internal nodes private to the part (":in1"), or p.gnd."""

    dc, wave, tone = staticmethod(dc), staticmethod(wave), staticmethod(tone)

    def __init__(self, circ, ref, part, case, config, source):
        self.circ, self.ref, self.part, self.case, self.config, self.source = circ, ref, part, case, config, source
        self.powered = True
        self.value = part["value"]
        self._n = 0

    @property
    def gnd(self):
        return self.circ.gnd

    def node(self, x):
        x = str(x)
        if x == self.circ.gnd or x.startswith(self.ref + ":") or x in self.part["pins"].values():
            return x            # already a net or one of this part's internal nodes
        if x.startswith(":"):
            return self.ref + x
        if x in self.part["pins"]:
            return self.part["pins"][x]
        raise KeyError(f"{self.ref} ({self.value}) has no pin {x}")

    def _name(self, name, kind):
        if name:
            return f"{self.ref}:{name}"
        self._n += 1
        return f"{self.ref}:{kind}{self._n}"

    def _on(self, pos, neg, vmin):
        sp = self.circ.fixed.get(self.node(pos))
        n = self.node(neg)
        sn = dc(0.0) if n == self.gnd else self.circ.fixed.get(n)
        if sp is None or sn is None:
            return True     # not a declared rail: assume it is up
        return sp.lo - sn.hi >= vmin

    def supply(self, pos, neg, vmin, vmax=None, abs_max=None, source=None, assumed=False):
        """Declare a supply pin pair. The part is powered when the rail on pos is up by at least vmin (or the power
        state says so). Adds the supply's absolute maximum and, while the rail is up, its operating range."""
        rail_up = self._on(pos, neg, vmin)
        st = self.case.state
        on = True if self.ref in st.powered else False if self.ref in st.unpowered else rail_up
        self.powered = self.powered and on
        if abs_max is not None:
            self.limit(pos, abs=(None, abs_max), ref=neg, name=f"{pos} supply", source=source, assumed=assumed)
        if vmax is not None and rail_up:
            self.limit(pos, op=(vmin, vmax), ref=neg, name=f"{pos} supply", source=source, assumed=assumed)
        return on

    def res(self, a, b, r, tol=0.0, name=None):
        return self.circ.add(Elem("R", self._name(name, "R"), (self.node(a), self.node(b)), r, tol, owner=self.ref))

    def cap(self, a, b, c, tol=0.0, name=None):
        return self.circ.add(Elem("C", self._name(name, "C"), (self.node(a), self.node(b)), c, tol, owner=self.ref))

    def rail(self, node, stim):
        """A net this part drives stiffly (an internal regulator or charge pump)."""
        self.circ.fix(self.node(node), stim, f"{self.ref} pin {node}")

    def drive(self, node, stim, r=0.0, i_max=None, name=None, assumed=False, source=None):
        """An output: a source behind r ohms. Returns the series resistor (for min_load). i_max limits its current."""
        n = self.node(node)
        nm = self._name(name, "drive")
        if not r:
            self.circ.fix(n, stim, nm)
            return None
        self.circ.fix(nm + ".src", stim, nm)
        e = self.circ.add(Elem("R", nm, (nm + ".src", n), r, owner=self.ref))
        if i_max is not None:
            self.circ.drives.append((e, i_max, source or self.source, assumed))
        return e

    def amp(self, out, inp, inn, gain, lo=None, hi=None, swing=0.0, name=None, gbw=1e6):
        """V(out) = gain × (V(inp) − V(inn)), its output held within swing of the lo and hi rails. gbw (Hz) only
        matters to the simulator, for op-amps."""
        nm = self._name(name, "amp")
        o = self.node(out)
        e = self.circ.add(Elem("E", nm, (o, self.node(inp), self.node(inn)), gain, owner=self.ref, gbw=gbw))
        if hi is not None:
            self.clamp(out, hi, -swing, name=f"{nm.split(':', 1)[1]}.hi", report=False, limiter=True, amp=nm)
        if lo is not None:
            self.clamp(lo, out, -swing, name=f"{nm.split(':', 1)[1]}.lo", report=False, limiter=True, amp=nm)
        return e

    def opamp(self, out, inp, inn, lo, hi, swing=0.0, name=None, gbw=1e6):
        return self.amp(out, inp, inn, 1e6, lo, hi, swing, name, gbw)

    def clamp(self, a, b, v_on, r_dyn=0.0, i_max=None, name=None, report=True, source=None, assumed=False,
              limiter=False, amp=None):
        """A diode-like clamp from a to b that conducts once V(a) − V(b) passes v_on (a number, or (min, max)).
        a or b may be a number: a clamp to a fixed level."""
        vmin, vmax = (v_on, v_on) if isinstance(v_on, (int, float)) else v_on
        na = self.circ.level(a) if isinstance(a, float) else self.node(a)
        nb = self.circ.level(b) if isinstance(b, float) else self.node(b)
        return self.circ.add(Elem("D", self._name(name, "D"), (na, nb), owner=self.ref, vmin=vmin, vmax=vmax,
                                  r_dyn=r_dyn, i_max=i_max, report=report, source=source or self.source,
                                  assumed=assumed, limiter=limiter, amp=amp))

    def tvs(self, a, b, vbr, r_dyn=1.0, i_max=None, name=None, source=None, assumed=False):
        """A bidirectional TVS between a and b, conducting at vbr = (min, max) either way."""
        nm = name or "tvs"
        return (self.clamp(a, b, vbr, r_dyn, i_max, f"{nm}+", True, source, assumed),
                self.clamp(b, a, vbr, r_dyn, i_max, f"{nm}-", True, source, assumed))

    def switch(self, d, s, g, vth, r_on, polarity=1, i_max=None, name=None, source=None, assumed=False):
        """A MOSFET channel from d to s: on when polarity × (V(g) − V(s)) is above vth[1], off below vth[0]."""
        return self.circ.add(Elem("S", self._name(name, "S"), (self.node(d), self.node(s), self.node(g)), 0.0,
                                  owner=self.ref, polarity=polarity, vth=vth, r_on=r_on, i_max=i_max,
                                  source=source or self.source, assumed=assumed))

    def limit(self, pin, abs=None, op=None, ref=None, inject=None, clamp=False, name=None, source=None,
              assumed=False, input=True):
        """Voltage limits on a pin. abs and op are (lo, hi); each side is None, a number relative to ref (GND by
        default), or (pin, offset) relative to another pin of this part: abs=(("2", -0.5), ("5", 0.5)).
        clamp=True adds the pin's protection diodes at both absolute limits ("lo" or "hi": one side only); inject is
        the current they may take. input=False marks a pin that may float without harm (a MOSFET's drain)."""
        node = self.node(pin)
        refnode = self.node(ref) if ref is not None else self.gnd
        label = name or str(pin)
        for kind, rng in (("abs", abs), ("op", op)):
            if rng is None:
                continue
            for side, spec in zip(("lo", "hi"), rng):
                if spec is None:
                    continue
                r, off = (self.node(spec[0]), spec[1]) if isinstance(spec, tuple) else (refnode, spec)
                c = None
                if kind == "abs" and clamp in (True, side):
                    cname = f"{label}.prot{'+' if side == 'hi' else '-'}"
                    c = (self.clamp(node, r, (off, off + 0.5), name=cname, i_max=inject, report=False)
                         if side == "hi" else
                         self.clamp(r, node, (-off, -off + 0.5), name=cname, i_max=inject, report=False))
                self.circ.limits.append(Limit(f"{self.ref}.{label} {kind}", self.ref, node, r, side, off, kind,
                                              c.name if c else None, inject, source or self.source, assumed,
                                              self.powered, input))

    def min_load(self, node, ohms, exclude, band=(20.0, 20e3), source=None, assumed=False):
        """The impedance seen at node (with the element `exclude`, usually the driver's own resistor, taken out)
        must not drop below ohms anywhere in the band."""
        self.circ.loads.append((self.ref, self.node(node), ohms, exclude.name, band, source or self.source, assumed))


# --------------------------------------------------------------------------------------------------------- the parts


def load_library(dirs):
    """Part models (MATCH, model) and passive catalog entries (CATALOG) from every .py file in the given folders."""
    models, catalog = [], {}
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "*.py"))):
            if os.path.basename(path).startswith("_"):
                continue
            mod = runpy.run_path(path)
            if "CATALOG" in mod:
                catalog.update(mod["CATALOG"])
            if "model" in mod:
                models.append({"match": mod["MATCH"], "model": mod["model"], "source": mod.get("SOURCE", ""),
                               "file": os.path.relpath(path)})
    return models, catalog


def find_model(models, part):
    keys = [part["value"]] + [part["fields"].get(f, "") for f in ("MPN", "Part Number")]
    for m in models:
        if any(fnmatch.fnmatch(k.upper(), pat.upper()) for k in keys if k for pat in m["match"]):
            return m
    return None


def _package(footprint):
    m = re.search(r"_(\d{4})_\d{4}Metric", footprint)
    return m.group(1) if m else None


def passive(circ, ref, part, catalog):
    """Resistors and capacitors straight from the schematic: value, tolerance and rating from fields, the catalog
    (by LCSC number) or the package. Returns a list of ratings to check."""
    value, rating = parse_passive(part["value"])
    if value is None:
        circ.notes.append(f"{ref}: can't read the value {part['value']!r}")
        return []
    f = part["fields"]
    cat = catalog.get(f.get("LCSC", ""), {})
    tol = _percent(f.get("Tolerance")) or cat.get("tol")
    a, b = part["pins"].get("1"), part["pins"].get("2")
    if ref.startswith("R"):
        tol = 0.01 if tol is None else tol
        e = circ.add(Elem("R", ref, (a, b), value, tol, owner=ref))
        power = _watts(f.get("Power")) or cat.get("power")
        src = "catalog" if cat.get("power") else "package"
        if power is None:
            power = R_POWER.get(_package(part["footprint"]))
        return [("power", e, power, src)] if power else [("power", e, None, "unknown")]
    polar = os.path.basename(part["footprint"].split(":")[-1]).startswith("CP")
    tol = (0.2 if polar else 0.1) if tol is None else tol
    e = circ.add(Elem("C", ref, (a, b), value, tol, owner=ref))
    rating = rating or _volts(f.get("Voltage")) or cat.get("volts")
    src = "value" if parse_passive(part["value"])[1] else "catalog" if cat.get("volts") else "field"
    out = [("voltage", e, rating, src if rating else "unknown")]
    if polar:
        circ.limits.append(Limit(f"{ref} reverse", ref, a, b, "lo", -0.5, "abs",
                                 source="aluminium electrolytics take about 0.5 V reverse; pin 1 is +"))
    return out


def _percent(text):
    m = re.match(r"^\s*±?\s*(\d+(?:\.\d+)?)\s*%", text or "")
    return float(m.group(1)) / 100 if m else None


def _watts(text):
    if not text:
        return None
    m = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*W", text)
    if m:
        return int(m.group(1)) / int(m.group(2))
    v, unit = parse_value(text.strip())
    return v if unit.upper() == "W" else None


def _volts(text):
    if not text:
        return None
    v, unit = parse_value(text.strip())
    return v if unit.upper() == "V" else None


def port_net(parts, pin):
    ref, _, num = pin.partition(".")
    if ref not in parts or num not in parts[ref]["pins"]:
        raise KeyError(f"the spec names port {pin}, which isn't a pin in the schematic")
    return parts[ref]["pins"][num]


def build(spec, parts, library, case, gnd):
    """The circuit for one case: rails, ports, then every part's model."""
    models, catalog = library
    circ = Circuit(gnd)
    circ.ratings, circ.ports, circ.unmodelled = [], {}, []
    for net, on in spec.rails.items():
        circ.fix(net, on if net in case.state.rails else dc(0.0), f"rail {net}")
    for pin, stim in case.stims.items():
        net = port_net(parts, pin)
        circ.ports[pin] = (net, stim)
        if stim.kind != "open":
            if stim.r > 0:
                circ.fix(f"{pin}:src", stim, f"port {pin}")
                circ.add(Elem("R", f"{pin}:r", (f"{pin}:src", net), stim.r, owner=pin))
            else:
                circ.fix(net, stim, f"port {pin}")
        if stim.clamp:
            lo, hi = stim.clamp
            for nm, a, b in ((f"{pin}:clamp+", net, circ.level(hi)), (f"{pin}:clamp-", circ.level(lo), net)):
                circ.add(Elem("D", nm, (a, b), owner=pin, vmin=0.0, vmax=0.0, r_dyn=0.0, i_max=stim.i_max,
                              report=False, source="spec", assumed=False))
    for ref in sorted(parts, key=_refkey):
        part = parts[ref]
        if ref in case.state.absent or part["dnp"]:
            continue
        if ref[0] in "RC" and ref[1:2].isdigit():
            circ.ratings += passive(circ, ref, part, catalog)
            continue
        m = find_model(models, part)
        if m is None:
            if not ref.startswith(NOT_MODELLED):
                circ.unmodelled.append(f"{ref} ({part['value']})")
            continue
        p = Builder(circ, ref, part, case, spec.configs.get(ref, {}), m["source"])
        m["model"](p)
    return circ


def _refkey(ref):
    m = re.match(r"([A-Za-z]+)(\d*)", ref)
    return (m.group(1), int(m.group(2) or 0))


# -------------------------------------------------------------------------------------------------------------- checks


class Result:
    def __init__(self, id, group, status, text, margin, case, source="", note="", assumed=False, scale=1.0):
        self.id, self.group, self.status, self.text, self.margin = id, group, status, text, margin
        self.case, self.source, self.note, self.assumed = case, source, note, assumed
        self.rel = margin / scale if scale else margin     # margin as a fraction of the limit, for ranking
        self.waiver = ""
        self.probe, self.case_key, self.forced = None, None, {}   # for simulating an unproven result


def _vterms(node, ref, gnd):
    t = [("v", node, 1.0)]
    if ref and ref != gnd:
        t.append(("v", ref, -1.0))
    return t


def check_case(spec, circ, case, cache):
    """Run the bound checker on one case and return its results."""
    a = Analysis(circ, cache)
    results = []
    for branch in a.run():
        a.use(branch)
        label = case.name + _branch_label(branch)
        for r in _check_branch(spec, circ, case, a, branch, label):
            r.case_key, r.forced = case.name, branch["forced"]
            results.append(r)
    results += _structure_case(spec, circ, case, a)
    return results, a


def _branch_label(branch):
    forced = branch["forced"]
    return " [" + ", ".join(f"{k.split(':')[0]} {v}" for k, v in sorted(forced.items())) + "]" if forced else ""


def _verdict(ok, loose):
    """pass when the bound proves it; fail when the bound is tight, so the violation can really happen; unproven
    when a loose bound (through a clamp) crosses the limit."""
    return "pass" if ok else "unproven" if loose else "fail"


LOOSE_NOTE = ("the bound goes through a node a clamp or amplifier rail holds, so it may be pessimistic; a simulation "
              "can settle it")


def _check_branch(spec, circ, case, a, branch, label):
    gnd = circ.gnd
    out = []
    nominal = case.kind == "nominal"
    clamps = {e.name: e for e in circ.elems if e.kind == "D"}
    cur = {}

    def clamp_i(name):
        if name not in cur:
            cur[name] = a.clamp_current(clamps[name])
        return cur[name]

    def add(id, group, ok, loose, text, margin, source="", note="", assumed=False, scale=1.0, probe=None):
        status = _verdict(ok, loose)
        if status == "unproven" and not note:
            note = LOOSE_NOTE
        r = Result(id, group, status, text, margin, label, source, note, assumed, scale)
        r.probe = probe
        out.append(r)

    def across(a_, b_):
        return [("v", a_, 1.0), ("v", b_, -1.0)]

    # pin limits
    lims = [l for l in circ.limits if l.kind == "abs" or (nominal and l.powered)]
    for l, b in zip(lims, a.bound([_vterms(l.node, l.ref, gnd) for l in lims])):
        val = b.hi if l.side == "hi" else b.lo
        margin = (l.offset - b.hi) if l.side == "hi" else (b.lo - l.offset)
        refname = "" if l.ref == gnd else f" − V({_short(l.ref)})"
        what = f"V({_short(l.node)}){refname}"
        text = f"{what} reaches {fmt(val, 'V')} ({'≤' if l.side == 'hi' else '≥'} {fmt(l.offset, 'V')}, {l.kind})"
        ok, loose, note, scale = margin >= -1e-9, b.loose, "", max(abs(l.offset), 0.5)
        if not ok and l.clamp:
            # Over the limit means the protection diodes conduct: the current decides.
            i, loose = clamp_i(l.clamp)
            if l.inject is not None and i <= l.inject:
                ok, margin, scale = True, l.inject - i, l.inject
                text = f"{what} clamped by its protection diodes: {fmt(i, 'A')} ≤ {fmt(l.inject, 'A')} injection"
            else:
                rating = f"rating {fmt(l.inject, 'A')}" if l.inject is not None else "no injection rating known"
                note = f"protection diodes take up to {fmt(i, 'A')} ({rating})" + (f"; {LOOSE_NOTE}" if loose else "")
        terms, side = _vterms(l.node, l.ref, gnd), (1 if l.side == "hi" else -1)
        probe = Probe(terms, side, l.offset, [(terms, side)], clamp=l.clamp, inject=l.inject)
        add(f"{l.id} {l.side}", "limit", ok, loose, text, margin, l.source, note, l.assumed, scale, probe)

    # clamps with their own rating (ESD diodes), and the clamps standing for a port's protection diodes
    for c in clamps.values():
        if not c.report and not (c.owner in circ.ports and c.i_max is not None):
            continue
        i, loose = clamp_i(c.name)
        if i <= 0:
            continue
        if c.i_max is None:
            out.append(Result(f"{c.name} current", "clamp", "info", f"{fmt(i, 'A')} through {c.name}", 0, label,
                              c.source))
            continue
        probe = Probe([("clamp", c.name, 1.0)], 1, c.i_max, [(across(*c.nodes), 1)], unit="A")
        add(f"{c.name} current", "clamp", i <= c.i_max, loose, f"{fmt(i, 'A')} through {c.name} "
            f"(max {fmt(c.i_max, 'A')})", c.i_max - i, c.source, assumed=c.assumed, scale=c.i_max, probe=probe)

    # passive ratings
    rated = [r for r in circ.ratings if r[2]]
    for (kind, e, rating, src), b in zip(rated, a.bound([[("v", e.nodes[0], 1.0), ("v", e.nodes[1], -1.0)]
                                                         for _, e, _, _ in rated])):
        v = max(abs(b.lo), abs(b.hi))
        if kind == "power":
            p = v * v / (e.value * (1 - e.tol))
            ratio = p / rating
            text = f"{fmt(p, 'W')} in {e.name} ({fmt(v, 'V')} across it; rated {fmt(rating, 'W')}, {src})"
        else:
            ratio = v / rating
            text = f"{fmt(v, 'V')} across {e.name} (rated {fmt(rating, 'V')}, {src})"
        status = _verdict(ratio <= 1, b.loose)
        if status == "pass" and ratio > spec.warn_ratio:
            status = "warn"
        terms = across(*e.nodes)
        r = Result(f"{e.name} {kind}", "rating", status, text, 1 - ratio, label,
                   note=LOOSE_NOTE if status == "unproven" else "")
        r.probe = Probe(terms, 0, rating, [(terms, 1), (terms, -1)], unit="W" if kind == "power" else "V",
                        square=e.value * (1 - e.tol) if kind == "power" else None)
        out.append(r)

    # switches that are on: channel current
    for s in [e for e in circ.elems if e.kind == "S" and branch["sw"].get(e.name) == "on" and e.i_max]:
        b = a.bound([[("v", s.nodes[0], 1.0), ("v", s.nodes[1], -1.0)]])[0]
        i = max(abs(b.lo), abs(b.hi)) / s.r_on
        terms = across(*s.nodes[:2])
        probe = Probe([("switch", s.name, 1.0)], 0, s.i_max, [(terms, 1), (terms, -1)], unit="A")
        add(f"{s.name} current", "switch", i <= s.i_max, b.loose,
            f"{fmt(i, 'A')} through {s.name}'s channel when on (max {fmt(s.i_max, 'A')})", s.i_max - i, s.source,
            assumed=s.assumed, scale=s.i_max, probe=probe)

    # driver output currents
    for e, i_max, src, assumed in circ.drives:
        b = a.bound([[("r", e.name, 1.0)]])[0]
        i = max(abs(b.lo), abs(b.hi))
        terms = [("r", e.name, 1.0)]
        add(f"{e.name} current", "drive", i <= i_max, b.loose, f"{fmt(i, 'A')} out of {e.name} (max {fmt(i_max, 'A')})",
            i_max - i, src, assumed=assumed, scale=i_max, probe=Probe(terms, 0, i_max, [(terms, 1), (terms, -1)],
                                                                      unit="A"))

    # port currents
    for pin, (net, stim) in circ.ports.items():
        if stim.i_max is None:
            continue
        i, loose = 0.0, False
        if stim.kind != "open":
            b = a.bound([[("r", f"{pin}:r", 1.0)]] if stim.r > 0 else [[("i", net, 1.0)]])[0]
            i, loose = max(abs(b.lo), abs(b.hi)), b.loose
        for side in ("+", "-"):
            if f"{pin}:clamp{side}" in clamps:
                ci, cl = clamp_i(f"{pin}:clamp{side}")
                i, loose = max(i, ci), loose or cl
        terms = [("r", f"{pin}:r", 1.0)]
        probe = (Probe(terms, 0, stim.i_max, [(terms, 1), (terms, -1)], unit="A")
                 if stim.kind != "open" and stim.r > 0 else None)
        add(f"port {pin} current", "port", i <= stim.i_max, loose,
            f"{fmt(i, 'A')} in or out of {pin} (max {fmt(stim.i_max, 'A')}: {stim.describe()})", stim.i_max - i, "spec",
            scale=stim.i_max, probe=probe)

    # output loads: the lowest impedance each output sees, wherever the ports are
    for ref, node, ohms, excl, band, src, assumed in circ.loads:
        if node in a.fixed:
            continue
        z = a.impedance(node, [excl], band)
        add(f"{_short(node)} load", "load", z >= ohms, False, f"{_short(node)} sees ≥ {fmt(z, 'Ω')} over "
            f"{fmt(band[0], 'Hz')}–{fmt(band[1], 'Hz')} (min load {fmt(ohms, 'Ω')})", (z - ohms) / ohms, src,
            assumed=assumed)

    # claims
    for cl in spec.claims:
        if not matches(cl.cases, case):
            continue
        q = cl.quantity
        loose = False
        try:
            if isinstance(q, V):
                lo, hi, _, loose = a.bound([_vterms(q.net, q.ref, gnd)])[0]
                unit = "V"
            elif isinstance(q, I) and q.ref in clamps:
                hi, loose = clamp_i(q.ref)
                lo, unit = 0.0, "A"
            elif isinstance(q, I):
                lo, hi, _, loose = a.bound([[("r", q.ref, 1.0)]])[0]
                unit = "A"
            elif isinstance(q, Gain):
                if q.net in a.fixed:
                    out.append(Result(f"claim: {cl.name}", "claim", "info",
                                      f"{q.describe()}: not linear here, a clamp or rail holds {q.net}", 0, label,
                                      cl.source))
                    continue
                srcs = [f"{p}:src" if circ.ports[p][1].r > 0 else circ.ports[p][0] for p in q.ports]
                g_lo, g_hi = a.gain(srcs, q.net, q.f)
                lo, hi = 20 * math.log10(max(g_lo, 1e-15)), 20 * math.log10(max(g_hi, 1e-15))
                unit = "dB"
            else:
                raise TypeError(f"unknown quantity {q!r}")
        except KeyError as err:
            out.append(Result(f"claim: {cl.name}", "claim", "fail", f"{q.describe()}: no such net or part {err}", 0,
                              label, cl.source))
            continue
        ok = (cl.lo is None or lo >= cl.lo - 1e-12) and (cl.hi is None or hi <= cl.hi + 1e-12)
        margin = min(lo - cl.lo if cl.lo is not None else math.inf, cl.hi - hi if cl.hi is not None else math.inf)
        if unit == "dB":
            rng = f"{lo:.2f}..{hi:.2f} dB"
            want = "..".join(f"{x:.2f}" if x is not None else "" for x in (cl.lo, cl.hi)) + " dB"
        else:
            rng = f"{fmt(lo, unit)}..{fmt(hi, unit)}"
            want = "..".join(fmt(x, unit) if x is not None else "" for x in (cl.lo, cl.hi))
        scale = max(abs(x) for x in (cl.lo, cl.hi) if x is not None)
        probe = None
        if unit != "dB":
            terms = (_vterms(q.net, q.ref, gnd) if isinstance(q, V) else
                     [("clamp", q.ref, 1.0)] if q.ref in clamps else [("r", q.ref, 1.0)])
            seed = across(*clamps[q.ref].nodes) if isinstance(q, I) and q.ref in clamps else terms
            hi_side = cl.lo is None or (cl.hi is not None and hi - cl.hi >= cl.lo - lo)
            probe = Probe(terms, 1 if hi_side else -1, cl.hi if hi_side else cl.lo, [(seed, 1 if hi_side else -1)],
                          unit=unit)
        add(f"claim: {cl.name}", "claim", ok, loose, f"{q.describe()} = {rng} (want {want})", margin, cl.source,
            scale=scale or 1.0, probe=probe)
    return out


def _short(node):
    return node.lstrip("/")


def _structure_case(spec, circ, case, a):
    """Floating inputs: a pin with limits on a net with no DC path to a source, in this case's first branch."""
    out = []
    b = a.branches[0]
    fixed = b["fixed"]
    uf = _UF()
    ground = "\0ground"
    for n in list(fixed) + [circ.gnd]:
        uf.union(n, ground)
    for e in circ.elems:
        if e.kind == "R" or (e.kind == "S" and b["sw"].get(e.name) == "on"):
            uf.union(e.nodes[0], e.nodes[1])
        elif e.kind == "E":
            uf.union(e.nodes[0], ground)
    seen = set()
    for l in circ.limits:
        if l.node in seen or l.node.startswith("level:") or not (l.powered and l.input):
            continue
        seen.add(l.node)
        if uf.find(l.node) != uf.find(ground):
            out.append(Result(f"{_short(l.node)} floating", "structure", "fail",
                              f"{_short(l.node)} ({l.owner}) has no DC path to a rail, port or output", 0, case.name))
    return out


def structure(spec, parts, circ_on):
    """Checks that don't depend on the case: parts without a model, exposed ports without an ESD diode."""
    out = []
    for u in circ_on.unmodelled:
        out.append(Result(f"{u.split()[0]} model", "structure", "warn",
                          f"{u} has no model in tools/kicad/parts/, so the check treats it as absent", 0, "all"))
    for note in circ_on.notes:
        out.append(Result("note", "structure", "warn", note, 0, "all"))
    for pin, port in spec.ports.items():
        if not port.exposed:
            continue
        net = port_net(parts, pin)
        diodes = sorted({e.owner for e in circ_on.elems
                         if e.kind == "D" and net in e.nodes and e.owner in parts and e.owner.startswith("D")})
        if diodes:
            out.append(Result(f"port {pin} ESD", "structure", "pass", f"{pin} ({_short(net)}) has {', '.join(diodes)}",
                              0, "all"))
        else:
            out.append(Result(f"port {pin} ESD", "structure", "fail",
                              f"{pin} ({_short(net)}) is exposed but has no ESD diode on its net", 0, "all"))
    return out


# ---------------------------------------------------------------------------------------------------------- reporting


def apply_waivers(spec, results, cases_by_name):
    for r in results:
        if r.status not in ("fail", "unproven", "warn"):
            continue
        case = cases_by_name.get(r.case.split(" [")[0])
        for w in spec.waivers:
            if fnmatch.fnmatch(r.id, w.check) and (case is None or matches(w.cases, case)):
                r.status, r.waiver = "waived", w.reason
                break


def summarize(results):
    """The worst result per check id (failures first, then the smallest margin)."""
    order = {"fail": 0, "unproven": 1, "searched": 2, "warn": 3, "waived": 4, "info": 5, "pass": 6}
    worst, counts = {}, {}
    for r in results:
        counts[r.id] = counts.get(r.id, 0) + 1
        w = worst.get(r.id)
        if w is None or (order[r.status], r.margin) < (order[w.status], w.margin):
            worst[r.id] = r
    return sorted(worst.values(), key=lambda r: (order[r.status], r.group, r.margin)), counts


def report(title, cases, worst, sampled, verbose, n_parts, elapsed, assumed_n):
    lines = [f"{title}",
             f"  {len({c.state.name for c in cases})} power states, {len(cases)} cases, {n_parts} parts modelled; "
             f"{'every tolerance corner' if not sampled else 'tolerance corners sampled for large groups'}"
             f"; {elapsed:.1f} s", ""]
    tag = {"fail": "FAIL", "unproven": "UNPROVEN", "searched": "SEARCHED", "warn": "WARN", "waived": "waived",
           "info": "info", "pass": "ok"}
    shown = [r for r in worst if r.status in ("fail", "unproven", "searched", "warn", "waived")]
    for r in shown:
        lines.append(f"{tag[r.status]:8s} {r.id}")
        lines.append(f"         {r.text}")
        lines.append(f"         case: {r.case}")
        if r.note:
            lines.append(f"         {r.note}")
        if r.waiver:
            lines.append(f"         waived: {r.waiver}")
        if r.assumed:
            lines.append("         (uses a value not confirmed from a datasheet)")
    passed = [r for r in worst if r.status == "pass"]
    if shown:
        lines.append("")
    lines.append(f"{len(passed)} checks pass" + (". Closest to their limits:" if passed else "."))
    close = sorted([r for r in passed if r.group in ("limit", "rating", "clamp", "claim", "port", "drive")
                    and r.margin > 1e-6], key=lambda r: r.rel)[: (len(passed) if verbose else 8)]
    for r in close:
        lines.append(f"  {r.id:28s} {r.text}  [{r.case}]")
    infos = [r for r in worst if r.status == "info"]
    if infos and verbose:
        lines.append("")
        lines.append("Clamps conducting with no rating to check against:")
        for r in infos:
            lines.append(f"  {r.text}  [{r.case}]")
    if assumed_n:
        lines.append("")
        lines.append(f"{assumed_n} limits use values not confirmed from a datasheet; `-v` lists them.")
    return "\n".join(lines)


def net_table(circ, a, branch):
    a.use(branch)
    rows = []
    for n in sorted(a.nodes):
        if n.startswith(("level:",)) or ".src" in n or n.endswith(":src"):
            continue
        lo, hi, kind = branch["ranges"][n]
        rows.append((n, lo, hi, kind))
    return rows


def simulate(unproven, kept, budget, out_dir):
    """Search for counterexamples to the unproven results, one search per case and switch branch. A result whose
    limit a run breaks becomes a FAIL with that input; the rest become SEARCHED with the worst value reached."""
    todo = [r for r in unproven if r.probe is not None]
    if not todo:
        return ""
    if circuit_sim.engine() is None:
        return "ngspice not found (install KiCad, or set NGSPICE_LIB): unproven results were not simulated."
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    groups = {}
    for r in todo:
        groups.setdefault((r.case_key, tuple(sorted(r.forced.items()))), []).append(r)
    runs = 0
    for (case_key, forced), rs in groups.items():
        a = kept[case_key]
        branch = next(b for b in a.branches if b["forced"] == dict(forced))
        save = (lambda k: os.path.join(out_dir, re.sub(r"[^A-Za-z0-9.+-]+", "_", rs[k].id) + ".cir")) if out_dir else None
        try:
            outcomes = circuit_sim.search(a, branch, [r.probe for r in rs], budget=budget, save=save)
        except circuit_sim.SimError as err:
            for r in rs:
                r.note += f"; simulation failed: {str(err).splitlines()[0]}"
            continue
        for r, o in zip(rs, outcomes):
            runs = max(runs, o.runs)
            if o.value is None:
                r.note += f"; no simulation ran ({o.note})" if o.note else "; no simulation ran"
                continue
            p = o.probe
            reached = f"{fmt(o.value, p.unit)} (limit {fmt(p.limit, p.unit)})"
            if o.max_current is not None and o.max_current > 1e-9:
                rating = f"rated {fmt(p.inject, 'A')}" if p.inject is not None else "no rating known"
                reached += f"; its protection diodes took up to {fmt(o.max_current, 'A')} over the runs ({rating})"
            if o.broken:
                r.status = "fail"
                r.note = f"simulation breaks it: {reached}, with {o.what}"
            else:
                r.status = "searched"
                r.note = (f"no counterexample in {o.runs} simulations: the worst reached {reached}, with {o.what}. "
                          f"The static bound stays as the guarantee")
            if o.note:
                r.note += f" ({o.note})"
    sim = circuit_sim.engine()
    return (f"Simulated {len(todo)} unproven result(s) in {len(groups)} case(s) with ngspice ({sim.runs} runs). "
            "SEARCHED means no input tried broke the limit: evidence, not proof.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("schematic", help="the .kicad_sch to check")
    ap.add_argument("--spec", help="the spec file (default: <schematic stem>.verify.py)")
    ap.add_argument("--case", help="only cases whose name matches this fnmatch pattern")
    ap.add_argument("--nets", action="store_true", help="print every net's range in each nominal case")
    ap.add_argument("-v", "--verbose", action="store_true", help="list every check, not just problems")
    ap.add_argument("--json", help="write every result to this file")
    ap.add_argument("--no-sim", action="store_true", help="don't simulate the results the bounds can't prove")
    ap.add_argument("--sim-budget", type=int, default=12, help="random variants per case simulated (default 12)")
    ap.add_argument("--sim-out", help="write each counterexample's SPICE netlist into this folder")
    args = ap.parse_args(argv)

    sch = os.path.abspath(args.schematic)
    spec_path = args.spec or os.path.splitext(sch)[0] + ".verify.py"
    if not os.path.isfile(spec_path):
        sys.exit(f"No spec at {spec_path}. Write one (see tools/kicad/README.md, 'Circuit check').")
    t0 = time.time()
    sys.path.insert(0, HERE)
    spec = runpy.run_path(spec_path)["spec"]
    parts = schnet.load(sch)
    if parts is None:
        sys.exit(f"Can't read {sch}")
    library = load_library([PARTS_DIR, os.path.join(os.path.dirname(spec_path), "parts")])
    gnd = getattr(spec, "ground", "GND")

    cases = expand_cases(spec)
    if args.case:
        cases = [c for c in cases if fnmatch.fnmatch(c.name, args.case)]
    cache, results, sampled = {}, [], False
    first = None
    tables, kept = [], {}
    for case in cases:
        circ = build(spec, parts, library, case, gnd)
        if first is None:
            first = circ
        res, a = check_case(spec, circ, case, cache)
        results += res
        kept[case.name] = a
        sampled |= a.sampled
        if args.nets and case.kind == "nominal":
            tables.append((case.name, net_table(circ, a, a.branches[0])))
    results += structure(spec, parts, first)
    apply_waivers(spec, results, {c.name: c for c in cases})
    worst, counts = summarize(results)
    sim_note = ""
    if not args.no_sim:
        sim_note = simulate([r for r in results if r.status == "unproven"], kept, args.sim_budget, args.sim_out)
        worst, counts = summarize(results)
    n_parts = len([r for r in parts if not r.startswith(NOT_MODELLED)]) - len(first.unmodelled)
    assumed_n = len({r.id for r in results if r.assumed})
    title = f"Circuit check: {os.path.relpath(sch)} (spec {os.path.basename(spec_path)})"
    print(report(title, cases, worst, sampled, args.verbose, n_parts, time.time() - t0, assumed_n))
    if sim_note:
        print("\n" + sim_note)
    if args.verbose:
        assumed = sorted({(r.id, r.source) for r in results if r.assumed})
        if assumed:
            print("\nLimits from values not confirmed from a datasheet:")
            for i, s in assumed:
                print(f"  {i}: {s}")
    for name, rows in tables:
        print(f"\nNet ranges, {name}:")
        for n, lo, hi, kind in rows:
            print(f"  {_short(n):34s} {fmt(lo, 'V'):>10s} .. {fmt(hi, 'V'):<10s} {'' if kind == 'dc' else '(varies)'}")
    if args.json:
        with open(args.json, "w") as f:
            json.dump([r.__dict__ for r in results], f, indent=1, default=str)
    return 1 if any(r.status in ("fail", "unproven") for r in worst) else 0


if __name__ == "__main__":
    sys.exit(main())
