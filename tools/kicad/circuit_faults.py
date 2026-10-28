"""What likely assembly faults do to a board, and whether the bring-up test plan catches them before power-up.

    python3 tools/kicad/circuit_faults.py audio-board/rev2/seed3-carrier.kicad_sch
    python3 tools/kicad/circuit_faults.py board.kicad_sch --bridge-gap 0.3 -v --json faults.json

Faults, one at a time:
  open     a two-pin part missing or not soldered
  short    a two-pin part shorted (solder under it, or the part failed short)
  value    a resistor a decade off (×10 or ÷10): the wrong reel or a misread code
  missing  a multi-pin part missing
  bridge   solder between two pads of different nets that sit close on the board, from the .kicad_pcb next to the
           schematic: any two pads within --bridge-gap, or two pads of one part within --bridge-gap-part
For each fault, the circuit check (circuit_verify.py) runs on the faulted schematic in the spec's fault states, with
nominal sources and nominal part values. It reports the checks the fault newly breaks: damage (an absolute maximum or
rating) or function (an operating range or a claim). A bridge or short between two supplies is damage by itself. Then
each of the spec's test-plan resistance checks is worked out on the faulted board: a reading that moves by more than
10 % (or between open and connected) catches the fault.

The exit status is 1 when a damaging fault isn't caught by any test-plan check: it would reach power-up unnoticed.
"""
import argparse
import copy
import json
import math
import os
import runpy
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import circuit_bounds  # noqa: E402
import circuit_verify as cv  # noqa: E402
import kicadenv  # noqa: E402
import schnet  # noqa: E402
from circuit_spec import expand_cases, parse_value  # noqa: E402

TWO_PIN = ("R", "C", "D", "L", "FB")
SKIP = ("J", "TP", "H", "MH", "FID", "LOGO", "G", "A")   # connectors, test points, art, plug-in modules


class SupplyShort(Exception):
    def __init__(self, text, possible=False):
        super().__init__(text)
        self.possible = possible


class Fault:
    def __init__(self, kind, name, refs, nets=None, factor=None, pads=None):
        self.kind, self.name, self.refs, self.nets, self.factor = kind, name, refs, nets, factor
        self.pads = pads or []

    def apply(self, parts, fixed, gnd, force=False):
        """(the faulted parts, {net: the net it was joined into}). Raises SupplyShort when the fault joins two nets that
        are both held by a supply, unless force."""
        out, rename = copy.deepcopy(parts), {}
        if self.kind in ("open", "missing"):
            out[self.refs[0]]["dnp"] = True
        elif self.kind == "value":
            p = out[self.refs[0]]
            v, _ = parse_value(p["value"].split()[0])
            p["value"] = _value_text(v * self.factor)
        else:
            a, b = self.nets
            if a in fixed and b in fixed and not force:
                own = [fixed[n].split("'s pin")[0] for n in (a, b) if "'s pin" in fixed[n]]
                if len(own) == 2 and own[0] == own[1]:
                    raise SupplyShort(f"ties two of {own[0]}'s own outputs together ({_short(a)}, {_short(b)}); how "
                                      f"{own[0]} copes is outside its model", possible=True)
                raise SupplyShort(f"ties {_short(a)} ({fixed[a]}) to {_short(b)} ({fixed[b]}): two sources fight")
            rank = lambda n: (n != gnd, n not in fixed, n)      # keep GND, then a supply, then the first name
            keep, drop = sorted((a, b), key=rank)
            rename[drop] = keep
            for part in out.values():
                for pin, net in part["pins"].items():
                    if net == drop:
                        part["pins"][pin] = keep
        return out, rename


def _value_text(v):
    for scale, p in ((1e6, "M"), (1e3, "k"), (1.0, "")):
        if v >= scale:
            return f"{v / scale:g}{p}"
    return f"{v:g}"


def _short(net):
    return net.lstrip("/")


def _refkey(ref):
    return cv._refkey(ref)


def part_faults(parts):
    out = []
    for ref in sorted(parts, key=_refkey):
        p = parts[ref]
        if p["dnp"] or ref.startswith(SKIP):
            continue
        pins = [n for n in p["pins"].values() if not n.startswith("unconnected-")]
        if ref.startswith(TWO_PIN) and len(p["pins"]) == 2:
            out.append(Fault("open", f"{ref} open", [ref]))
            a, b = p["pins"].get("1"), p["pins"].get("2")
            if a and b and a != b:
                out.append(Fault("short", f"{ref} shorted", [ref], nets=(a, b)))
            if ref.startswith("R") and parse_value(p["value"].split()[0])[0]:
                out.append(Fault("value", f"{ref} ×10 ({p['value']} → {_value_text(parse_value(p['value'])[0] * 10)})",
                                 [ref], factor=10.0))
                out.append(Fault("value", f"{ref} ÷10 ({p['value']} → {_value_text(parse_value(p['value'])[0] / 10)})",
                                 [ref], factor=0.1))
        elif len(pins) >= 2:
            out.append(Fault("missing", f"{ref} missing", [ref]))
    return out


# ------------------------------------------------------------------------------------------------------- bridges


def _seg_dist(p, q, r, s):
    """Distance between segments pq and rs."""
    def pt_seg(a, b, c):
        bx, by, cx, cy = b[0] - a[0], b[1] - a[1], c[0] - a[0], c[1] - a[1]
        L = bx * bx + by * by
        t = 0.0 if L == 0 else max(0.0, min(1.0, (cx * bx + cy * by) / L))
        dx, dy = cx - t * bx, cy - t * by
        return math.hypot(dx, dy)
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2, d3, d4 = cross(r, s, p), cross(r, s, q), cross(p, q, r), cross(p, q, s)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(pt_seg(p, q, r), pt_seg(p, q, s), pt_seg(r, s, p), pt_seg(r, s, q))


def _poly_dist(A, B):
    best = math.inf
    for oa in A:
        for ob in B:
            for i in range(len(oa)):
                p, q = oa[i], oa[(i + 1) % len(oa)]
                for j in range(len(ob)):
                    best = min(best, _seg_dist(p, q, ob[j], ob[(j + 1) % len(ob)]))
                    if best == 0.0:
                        return 0.0
    return best


def bridge_faults(board, gap, gap_part):
    """Pads of different nets close enough on the same copper layer for solder to join them, one fault per pair of
    nets (the pad pairs that would do it listed with it)."""
    fd, dump = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        kicadenv.run_pcbnew_script("board_dump.py", board, dump)
        with open(dump) as f:
            data = json.load(f)
    finally:
        os.remove(dump)
    pads = []
    for fp in data["footprints"]:
        for p in fp["pads"]:
            if p["kind"] == "NPTH" or not p["net"] or not p["poly"]:
                continue
            layers = {"F", "B"} if p["kind"] == "PTH" else {fp["side"]}
            pads.append((fp["ref"], p["num"], p["net"], layers, p["bbox"], p["poly"]))
    found = {}
    for i in range(len(pads)):
        ra, na, neta, la, ba, pa = pads[i]
        for j in range(i + 1, len(pads)):
            rb, nb, netb, lb, bb, pb = pads[j]
            if neta == netb or not (la & lb):
                continue
            limit = gap_part if ra == rb else gap
            if ba[0] - bb[2] > limit or bb[0] - ba[2] > limit or ba[1] - bb[3] > limit or bb[1] - ba[3] > limit:
                continue
            d = _poly_dist(pa, pb)
            if d <= limit:
                key = tuple(sorted((neta, netb)))
                found.setdefault(key, []).append((d, f"{ra}.{na}", f"{rb}.{nb}"))
    out = []
    for (a, b), hits in sorted(found.items()):
        hits.sort()
        d, pa, pb = hits[0]
        more = f" and {len(hits) - 1} more" if len(hits) > 1 else ""
        out.append(Fault("bridge", f"bridge {pa}–{pb}{more} ({_short(a)} ↔ {_short(b)}, {d:.2f} mm)",
                         sorted({pa.split('.')[0], pb.split('.')[0]}), nets=(a, b), pads=[(x, y) for _, x, y in hits]))
    return out


# -------------------------------------------------------------------------------------------------------- running


class Outcome:
    def __init__(self, fault):
        self.fault, self.damage, self.function, self.caught, self.possible = fault, [], [], [], False
        self.supply_short = self.error = None


def _worst(results):
    order = {"fail": 0, "unproven": 1, "searched": 2, "warn": 3, "waived": 4, "info": 5, "pass": 6}
    w = {}
    for r in results:
        k = (r.case_key, r.id)
        if k not in w or order[r.status] < order[w[k].status]:
            w[k] = r
    return w


def run(spec_path, sch, board, gap, gap_part, states, verbose, progress=print):
    spec = runpy.run_path(spec_path)["spec"]
    parts = schnet.load(sch)
    library = cv.load_library([cv.PARTS_DIR, os.path.join(os.path.dirname(spec_path), "parts")])
    gnd = getattr(spec, "ground", "GND")
    names = states or spec.fault_states or [spec.states[0].name]
    cases = [c for c in expand_cases(spec) if c.kind == "nominal" and c.state.name in names]
    circuit_bounds.NOMINAL_ONLY = True

    def check(p):
        res, cache = [], {}
        for case in cases:
            try:
                circ = cv.build(spec, p, library, case, gnd)
            except ValueError as err:          # two sources on one net: a supply short that `fixed` didn't foresee
                raise SupplyShort(str(err))
            r, _ = cv.check_case(spec, circ, case, cache)
            res += r
        cv.apply_waivers(spec, res, {c.name: c for c in cases})
        return _worst(res)

    base = check(parts)
    nets = {net for p in parts.values() for net in p["pins"].values()}
    fixed = {gnd: "ground"}
    for case in cases:
        circ = cv.build(spec, parts, library, case, gnd)
        for n in circ.fixed:
            if n in nets:
                fixed[n] = circ.fixed_by[n].replace(" pin ", "'s pin ").replace("rail ", "the rail ")
    readings = [(st, m) for st in spec.stages for m in st.checks]

    def measure(p, rename):
        out = {}
        for st in spec.stages:
            try:
                out.update(cv.stage_readings(spec, p, library, st, gnd, rename))
            except (KeyError, ValueError, RuntimeError):
                pass                         # a stage this fault keeps from being built takes no readings
        return out

    healthy = measure(parts, {})
    faults = part_faults(parts)
    if board and os.path.isfile(board):
        faults += bridge_faults(board, gap, gap_part)
    outcomes = []
    t0 = time.time()
    for k, fault in enumerate(faults, 1):
        o = Outcome(fault)
        try:
            fp, rename = fault.apply(parts, fixed, gnd)
            now = check(fp)
            for key, r in now.items():
                if r.status not in ("fail", "unproven"):
                    continue
                was = base.get(key)
                if was is not None and was.status in ("fail", "unproven", "waived"):
                    continue
                (o.damage if r.damage else o.function).append(r)
                o.possible |= r.status == "unproven"
        except SupplyShort as err:
            o.supply_short, o.possible = str(err), err.possible
            fp, rename = fault.apply(parts, fixed, gnd, force=True)
        except Exception as err:   # one fault the check can't model shouldn't stop the others
            o.error = f"couldn't check it: {type(err).__name__}: {err}"
            fp, rename = fault.apply(parts, fixed, gnd, force=True)
        reads = measure(fp, rename)
        for st, m in readings:
            key = (m["id"], m["a"], m["b"])
            if key not in reads or key not in healthy:
                continue
            h, f = healthy[key], reads[key]
            if m["kind"] == "ohms":
                moved = (math.isinf(h) != math.isinf(f)) or (not math.isinf(h) and abs(f - h) > max(0.1 * h, 0.5))
                seen = f"{fmt_reading(h)} → {fmt_reading(f)}"
            else:
                # A voltage reading catches the fault when it can no longer land inside the expected band (or, with no
                # band, near the healthy reading).
                lo, hi = m["expect"] if m["expect"] else (h[0] - max(0.1 * abs(h[0]), 0.05),
                                                          h[1] + max(0.1 * abs(h[1]), 0.05))
                moved = f[1] < lo or f[0] > hi
                seen = f"{_volts(h)} → {_volts(f)}"
            if moved and not any(c.startswith(f"{m['id']} (") for c in o.caught):
                o.caught.append(f"{m['id']} ({seen})")
        outcomes.append(o)
        if verbose and progress:
            progress(f"  [{k}/{len(faults)}] {fault.name}")
    suggestions = suggest(spec, parts, library, gnd, fixed, outcomes)
    return spec, faults, outcomes, cases, time.time() - t0, suggestions


PROBE_ORDER = ("TP", "J", "A", "R", "C", "D", "L", "Q", "U")    # where a probe lands most easily


def _probe_pin(parts, net, named=()):
    """Where to put the DMM probe for a net: GND and rails by name, then a test point, connector or socket pin, then a
    passive's pad."""
    if net in named:
        return _short(net)
    best = None
    for ref, p in parts.items():
        for pin, n in p["pins"].items():
            if n != net:
                continue
            rank = next((i for i, pre in enumerate(PROBE_ORDER) if ref.startswith(pre)), len(PROBE_ORDER))
            key = (rank, cv._refkey(ref), pin)
            if best is None or key < best[0]:
                best = (key, f"{ref}.{pin}")
    return best[1] if best else net


def suggest(spec, parts, library, gnd, fixed, outcomes):
    """For each damaging fault no reading catches, an unpowered resistance reading that would: between the fault's
    nets, or from one of them to GND or a supply, whichever moves first."""
    stage = next((st for st in spec.stages if not st.rails), None)
    if stage is None:
        return []
    healthy = cv.stage_circuit(spec, parts, library, stage, gnd)
    supplies = [gnd] + [n for n in fixed if n in spec.rails]
    out = []
    for o in outcomes:
        if o.caught or not (o.damage or o.supply_short):
            continue
        f = o.fault
        nets = list(f.nets) if f.nets else [n for n in parts[f.refs[0]]["pins"].values()]
        pairs = [(a, b) for i, a in enumerate(nets) for b in nets[i + 1:]] + [(a, s) for a in nets for s in supplies
                                                                              if s != a]
        fp, rename = f.apply(parts, fixed, gnd, force=True)
        faulty = cv.stage_circuit(spec, fp, library, stage, gnd)
        for a, b in pairs:
            h = cv.resistance(healthy, a, b)
            x = cv.resistance(faulty, rename.get(a, a), rename.get(b, b))
            if (math.isinf(h) != math.isinf(x)) or (not math.isinf(h) and abs(x - h) > max(0.1 * h, 0.5)):
                ends = sorted((_probe_pin(parts, a, supplies), _probe_pin(parts, b, supplies)),
                              key=lambda e: (e in [_short(n) for n in supplies], e))
                out.append((f"{ends[0]} → {ends[1]}", fmt_reading(h), f.name))
                break
    merged = {}
    for reading, expect, name in out:
        merged.setdefault((reading, expect), []).append(name)
    return [(r, e, names) for (r, e), names in merged.items()]


def fmt_reading(r):
    return cv.fmt_ohms(r)


def _volts(r):
    lo, hi = r
    return cv.fmt(lo, "V") if abs(hi - lo) < 0.02 else f"{cv.fmt(lo, 'V')}..{cv.fmt(hi, 'V')}"


def _what(results):
    """The checks a fault breaks, one line each, worst-first, deduplicated across cases."""
    seen, out = set(), []
    for r in sorted(results, key=lambda r: (r.status != "fail", r.rel)):
        if r.id in seen:
            continue
        seen.add(r.id)
        out.append(f"{r.id}: {r.text}" + (" (unproven: the bound goes through a clamp)" if r.status == "unproven" else ""))
    return out


def report(sch, faults, outcomes, cases, elapsed, verbose, gap, gap_part, n_readings, suggestions=()):
    kinds = {}
    for f in faults:
        kinds[f.kind] = kinds.get(f.kind, 0) + 1
    order = ["open", "short", "value", "missing", "bridge"]
    lines = [f"Fault check: {os.path.relpath(sch)}",
             "  " + ", ".join(f"{kinds[k]} {k}" for k in order if k in kinds) +
             f" (bridges: pads within {gap} mm, or {gap_part} mm on one part); checked in "
             + ", ".join(c.name for c in cases) + f"; {n_readings} test-plan readings; {elapsed:.0f} s", ""]
    damage = [o for o in outcomes if o.damage or o.supply_short]
    function = [o for o in outcomes if not (o.damage or o.supply_short) and o.function]
    quiet = [o for o in outcomes if not (o.damage or o.supply_short or o.function)]
    rank = lambda o: (0 if o.supply_short else 1, not any(r.owner and r.owner.startswith("A") for r in o.damage),
                      o.possible, bool(o.caught))

    def entry(o, detail):
        shown = ", ".join(o.caught[:4]) + (f" and {len(o.caught) - 4} more" if len(o.caught) > 4 else "")
        tag = "caught by " + shown if o.caught else "NOT CAUGHT by the test plan"
        lines.append(f"  {o.fault.name}")
        if o.supply_short:
            lines.append(f"      {o.supply_short}")
        for w in detail[: (None if verbose else 2)]:
            lines.append(f"      {w}")
        if len(detail) > 2 and not verbose:
            lines.append(f"      … and {len(detail) - 2} more")
        lines.append(f"      {tag}")

    lines.append(f"Damage ({len(damage)}): a part goes past an absolute maximum or rating"
                 + (" (or may: unproven)" if any(o.possible for o in damage) else ""))
    for o in sorted(damage, key=rank):
        entry(o, _what(o.damage))
    lines += ["", f"Function only ({len(function)}): an operating range, a claim or a floating input, nothing damaged"]
    shown = sorted(function, key=lambda o: bool(o.caught))
    for o in shown if verbose else [o for o in shown if not o.caught][:12]:
        entry(o, _what(o.function))
    if not verbose:
        caught = sum(1 for o in function if o.caught)
        lines.append(f"  ({caught} of {len(function)} caught by the test plan; the uncaught ones are listed, -v lists all)")
    errors = [o for o in outcomes if o.error]
    if errors:
        lines += ["", f"Not checked ({len(errors)}):"] + [f"  {o.fault.name}: {o.error}" for o in errors]
    quiet = [o for o in quiet if not o.error]
    lines += ["", f"No effect found ({len(quiet)}): the board still meets every check in these states"]
    if verbose:
        for o in quiet:
            lines.append(f"  {o.fault.name}" + (f"  (caught by {', '.join(o.caught)})" if o.caught else ""))
    missed = [o for o in damage if not o.caught]
    lines += ["", f"{len(missed)} damaging fault(s) not caught by the test plan's readings."
              if missed else "Every damaging fault changes at least one of the test plan's readings."]
    if suggestions:
        lines += ["", "Readings that would catch them (unpowered, with the test plan's first stage fitted the same way):"]
        for reading, expect, names in suggestions:
            lines.append(f"  {reading}: expect {expect}   catches {'; '.join(names)}")
    return "\n".join(lines), missed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("schematic", help="the .kicad_sch to check")
    ap.add_argument("--spec", help="the spec file (default: <schematic stem>.verify.py)")
    ap.add_argument("--board", help="the .kicad_pcb for solder bridges (default: next to the schematic)")
    ap.add_argument("--bridge-gap", type=float, default=0.4, help="mm between pads of different parts (default 0.4)")
    ap.add_argument("--bridge-gap-part", type=float, default=1.0,
                    help="mm between pads of the same part, such as socket or IC pins (default 1.0)")
    ap.add_argument("--state", action="append", help="power state(s) to check faults in (default: the spec's)")
    ap.add_argument("-v", "--verbose", action="store_true", help="every fault and everything it breaks")
    ap.add_argument("--json", help="write every outcome to this file")
    args = ap.parse_args(argv)
    sch = os.path.abspath(args.schematic)
    spec_path = args.spec or os.path.splitext(sch)[0] + ".verify.py"
    board = args.board or os.path.splitext(sch)[0] + ".kicad_pcb"
    spec, faults, outcomes, cases, elapsed, suggestions = run(spec_path, sch, board, args.bridge_gap,
                                                              args.bridge_gap_part, args.state, args.verbose)
    n_readings = sum(len(st.checks) for st in spec.stages)
    text, missed = report(sch, faults, outcomes, cases, elapsed, args.verbose, args.bridge_gap, args.bridge_gap_part,
                          n_readings, suggestions)
    print(text)
    if args.json:
        with open(args.json, "w") as f:
            json.dump([{"fault": o.fault.name, "kind": o.fault.kind, "supply_short": o.supply_short,
                        "damage": _what(o.damage), "function": _what(o.function), "caught_by": o.caught}
                       for o in outcomes], f, indent=1)
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
