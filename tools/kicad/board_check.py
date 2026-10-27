#!/usr/bin/env python3
"""Check a KiCad board against its own DRC and against JLCPCB's fabrication and assembly limits.

    board_check.py board.kicad_pcb [--assembly economic|standard|none] [--allow-unrouted] [-v]

Passes:
  1. Project DRC: kicad-cli DRC with the project's own rules, zones refilled in memory, plus schematic
     parity when <board>.kicad_sch sits next to the board. Severities are the project's.
  2. JLC limits: DRC on a temporary copy whose rules are only JLC's capability limits. Errors.
  3. JLC recommended: the same with JLC's preferred values and silkscreen legibility limits. Warnings.
  4. Checks DRC can't express: board size, thickness and layers, slot widths, silk line width and text
     proportions, and for JLC assembly the body-to-edge distance, sides, package size, pin pitch, LCSC
     part numbers and open vias in pads.
The board file is never modified. Exit status is 1 when there are errors (or warnings, with --strict).
See jlcpcb.py for the numbers and their sources.
"""
import argparse
import json
import math
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jlcpcb  # noqa: E402
import kicadenv  # noqa: E402

LCSC_FIELD = re.compile(r"lcsc|jlc", re.I)
TINY_PACKAGE = re.compile(r"(^|[:_])(01005|0201)(_|$)")


class Report:
    def __init__(self):
        self.items = []

    def add(self, severity, category, kind, message, where=()):
        self.items.append({"severity": severity, "category": category, "type": kind, "message": message,
                           "where": list(where)})


# ---------------------------------------------------------------- DRC passes

def violation_key(v):
    return (v["type"], tuple(sorted(i.get("uuid", "") for i in v.get("items", []))))


def where_of(v):
    return [{"desc": i.get("description", ""), "x": i["pos"]["x"], "y": i["pos"]["y"]} for i in v.get("items", [])]


def outer_oz(pcb_text):
    m = re.search(r'\(layer "F\.Cu"\s*\(type "copper"\)\s*\(thickness ([\d.]+)\)', pcb_text)
    return 2 if m and float(m.group(1)) >= 0.06 else 1


def jlc_drc(board, oz, recommended, mask_web):
    """DRC on a temporary copy carrying only JLC's rules."""
    proj_dir = os.path.dirname(board)
    stem = os.path.splitext(os.path.basename(board))[0]
    tmp = tempfile.mkdtemp(prefix="jlc-drc-")
    try:
        with open(board) as f:
            pcb = f.read()
        if recommended:
            pcb = re.sub(r"\(solder_mask_min_width [\d.]+\)\s*", "", pcb)
            pcb = pcb.replace("(pad_to_mask_clearance", f"(solder_mask_min_width {mask_web})\n\t\t(pad_to_mask_clearance", 1)
        with open(os.path.join(tmp, stem + ".kicad_pcb"), "w") as f:
            f.write(pcb)
        pro_path = os.path.join(proj_dir, stem + ".kicad_pro")
        pro = json.load(open(pro_path)) if os.path.exists(pro_path) else {"board": {"design_settings": {}}}
        ds = pro.setdefault("board", {}).setdefault("design_settings", {})
        ds.setdefault("rules", {}).update(jlcpcb.board_minimums(oz, recommended))
        sev = ds.setdefault("rule_severities", {})
        for t in jlcpcb.FAB_TYPES | jlcpcb.SILK_TYPES | jlcpcb.MASK_TYPES:
            sev[t] = "error"
        for cls in pro.get("net_settings", {}).get("classes", []):
            cls["clearance"] = jlcpcb.LIMITS["clearance"][oz]
        with open(os.path.join(tmp, stem + ".kicad_pro"), "w") as f:
            json.dump(pro, f, indent=2)
        with open(os.path.join(tmp, stem + ".kicad_dru"), "w") as f:
            f.write(jlcpcb.dru_recommended(oz) if recommended else jlcpcb.dru_limits(oz))
        report = kicadenv.run_drc(os.path.join(tmp, stem + ".kicad_pcb"), ["--refill-zones"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    types = jlcpcb.FAB_TYPES | (jlcpcb.SILK_TYPES | jlcpcb.MASK_TYPES if recommended else set())
    return [v for v in report.get("violations", []) if v["type"] in types]


# ---------------------------------------------------------------- geometry

def seg_dist(p1, p2, q1, q2):
    """Shortest distance between segments p1-p2 and q1-q2 (0 if they cross)."""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def pt_seg(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

    d1, d2 = cross(q1, q2, p1), cross(q1, q2, p2)
    d3, d4 = cross(p1, p2, q1), cross(p1, p2, q2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(pt_seg(p1, q1, q2), pt_seg(p2, q1, q2), pt_seg(q1, p1, p2), pt_seg(q2, p1, p2))


def rect_to_outline(box, outline):
    l, t, r, b = box
    corners = [(l, t), (r, t), (r, b), (l, b)]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    best = float("inf")
    for poly in outline:
        for a, c in zip(poly, poly[1:] + poly[:1]):
            for e1, e2 in edges:
                best = min(best, seg_dist(e1, e2, a, c))
    return best


def point_in_poly(p, poly):
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < (x2 - x1) * (p[1] - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def poly_dist(p, poly):
    return min(seg_dist(p, p, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


# ---------------------------------------------------------------- checks DRC can't express

def names(items, verbose, n=12):
    items = list(items)
    return ", ".join(items if verbose or len(items) <= n else items[:n] + [f"... (+{len(items) - n}, -v lists all)"])


def board_checks(data, rep, verbose):
    l, t, r, b = data["board"]["bbox"]
    w, h = r - l, b - t
    lo, hi = jlcpcb.LIMITS["board_min"], jlcpcb.LIMITS["board_max_4l"]
    if min(w, h) < lo[0] or max(w, h) > hi[0] or min(w, h) > hi[1]:
        rep.add("error", "JLC fab", "board_size", f"board is {w:.1f} x {h:.1f} mm, outside JLC's {lo[0]:g} x {lo[1]:g} to {hi[0]:g} x {hi[1]:g} mm")
    th = data["board"]["thickness"]
    near = min(jlcpcb.RECOMMENDED["thicknesses"], key=lambda v: abs(v - th))
    if abs(near - th) > 0.05:
        rep.add("warning", "JLC fab", "board_thickness", f"board thickness {th:.3f} mm isn't one of JLC's standard FR-4 options {jlcpcb.RECOMMENDED['thicknesses']}")

    for f in data["footprints"]:
        for p in f["pads"]:
            if p["slot"] and p["drill"]:
                width = min(p["drill"])
                lim = jlcpcb.LIMITS["plated_slot_width"] if p["kind"] == "PTH" else jlcpcb.LIMITS["npth_slot_width"]
                if width < lim:
                    rep.add("error", "JLC fab", "slot_width", f"{f['ref']} pad {p['num'] or '(unnamed)'}: {p['kind']} slot {width:.2f} mm wide, JLC minimum is {lim} mm",
                            [{"desc": f"{f['ref']} pad {p['num']}", "x": p["x"], "y": p["y"]}])

    lw = jlcpcb.RECOMMENDED["silk_line_width"]
    thin = sorted({f["ref"] for f in data["footprints"] for s in f["silk"] if 0 < s["width"] < lw - 1e-6})
    thin += ["board drawing"] * any(0 < s["width"] < lw - 1e-6 for s in data["silk"])
    if thin:
        widths = sorted({s["width"] for f in data["footprints"] for s in f["silk"] if 0 < s["width"] < lw - 1e-6})
        rep.add("warning", "JLC silk", "silk_line_width",
                f"silkscreen lines thinner than JLC's {lw} mm ({', '.join(f'{x:g}' for x in widths)} mm) on {len(thin)} items: {names(thin, verbose)}")
    ratio = jlcpcb.RECOMMENDED["silk_text_ratio"]
    narrow = [t for t in data["texts"] if t["visible"] and t["height"] > 0 and t["thickness"] / t["height"] < ratio - 1e-6]
    if narrow:
        rep.add("warning", "JLC silk", "silk_text_ratio",
                f"{len(narrow)} silkscreen texts have stroke/height under JLC's 1:6 (e.g. {narrow[0]['text']}: {narrow[0]['thickness']:g}/{narrow[0]['height']:g} mm)",
                [{"desc": t["text"], "x": (t["bbox"][0] + t["bbox"][2]) / 2, "y": (t["bbox"][1] + t["bbox"][3]) / 2} for t in narrow])


def assembly_checks(data, mode, vias_filled, rep, verbose):
    lim = jlcpcb.ASSEMBLY[mode]
    l, t, r, b = data["board"]["bbox"]
    w, h = r - l, b - t
    if min(w, h) < lim["board_min"][0] or max(w, h) > max(lim["board_max"]) or min(w, h) > min(lim["board_max"]):
        rep.add("error", "JLC assembly", "pcba_board_size",
                f"{mode.capitalize()} PCBA takes boards from {lim['board_min'][0]:g} x {lim['board_min'][1]:g} to {lim['board_max'][0]:g} x {lim['board_max'][1]:g} mm; this one is {w:.1f} x {h:.1f} mm")
    th = data["board"]["thickness"]
    if lim["thickness"] and not (lim["thickness"][0] - 0.05 <= th <= lim["thickness"][1] + 0.05):
        rep.add("error", "JLC assembly", "pcba_thickness", f"{mode.capitalize()} PCBA takes {lim['thickness'][0]}–{lim['thickness'][1]} mm boards; this one is {th:.2f} mm")
    if lim["layers"] and data["board"]["copper_layers"] not in lim["layers"]:
        rep.add("error", "JLC assembly", "pcba_layers", f"{mode.capitalize()} PCBA takes {lim['layers']} layers; this board has {data['board']['copper_layers']}")

    parts = [f for f in data["footprints"] if f["smd"] and not f["dnp"] and not f["exclude_from_pos"]]
    sides = Counter(f["side"] for f in parts)
    if lim["single_side"] and len(sides) > 1:
        rep.add("error", "JLC assembly", "pcba_sides", f"Economic PCBA places one side only; parts are on both ({dict(sides)})")

    edge = jlcpcb.ASSEMBLY["body_to_edge"]
    for f in parts:
        box = f["body"] or f["courtyard"]
        if not box:
            continue
        d = rect_to_outline(box, data["board"]["outline"])
        if d < edge - 1e-6:
            rep.add("error", "JLC assembly", "body_to_edge", f"{f['ref']} body is {d:.2f} mm from the board edge; JLC needs {edge} mm",
                    [{"desc": f["ref"], "x": f["x"], "y": f["y"]}])
        if TINY_PACKAGE.search(f["lib"]) and mode == "economic":
            rep.add("error", "JLC assembly", "package_size", f"{f['ref']} ({f['lib']}) is smaller than 0402, which Economic PCBA can't place",
                    [{"desc": f["ref"], "x": f["x"], "y": f["y"]}])
        smd = [p for p in f["pads"] if p["kind"] in ("SMD", "CONN") and p["copper"]]
        if len(smd) >= 4:
            areas = sorted((p["bbox"][2] - p["bbox"][0]) * (p["bbox"][3] - p["bbox"][1]) for p in smd)
            median = areas[len(areas) // 2]
            pins = [p for p in smd if (p["bbox"][2] - p["bbox"][0]) * (p["bbox"][3] - p["bbox"][1]) <= 3 * median]
            pitch = min((math.hypot(a["x"] - c["x"], a["y"] - c["y"]) for i, a in enumerate(pins) for c in pins[i + 1:]), default=None)
            if pitch is not None and pitch < lim["min_ic_pitch"] - 1e-6:
                rep.add("error", "JLC assembly", "pin_pitch", f"{f['ref']} pin pitch {pitch:.2f} mm is under {mode.capitalize()} PCBA's {lim['min_ic_pitch']} mm",
                        [{"desc": f["ref"], "x": f["x"], "y": f["y"]}])

    missing = [f["ref"] for f in parts if not any(LCSC_FIELD.search(k) and v.strip() for k, v in f["fields"].items())]
    if missing:
        rep.add("warning", "JLC assembly", "lcsc_part", f"{len(missing)} assembled parts have no LCSC part number field: {names(sorted(missing), verbose)}")

    if not vias_filled:
        hits = defaultdict(list)
        for v in data["vias"]:
            for f in parts:
                for p in f["pads"]:
                    if p["kind"] != "SMD" or not p["copper"] or not p["poly"]:
                        continue
                    poly = p["poly"][0]
                    if point_in_poly((v["x"], v["y"]), poly) or poly_dist((v["x"], v["y"]), poly) < v["dia"] / 2:
                        hits[(f["ref"], p["num"] or "?")].append(v)
        for (ref, num), vs in sorted(hits.items()):
            rep.add("warning", "JLC assembly", "via_in_pad",
                    f"{ref} pad {num} has {len(vs)} open via(s) in it, which can wick solder away in reflow. JLC can plug/fill them (POFV) at extra cost below 6 layers",
                    [{"desc": f"via {x['drill']:g} mm", "x": x["x"], "y": x["y"]} for x in vs])


# ---------------------------------------------------------------- output

def print_report(rep, header, verbose):
    errors = [i for i in rep.items if i["severity"] == "error"]
    warnings = [i for i in rep.items if i["severity"] != "error"]
    print(header)
    for title, group in (("ERRORS", errors), ("WARNINGS", warnings)):
        print(f"\n{title} ({len(group)})")
        if not group:
            print("  none")
        buckets = defaultdict(list)
        for i in group:
            buckets[(i["category"], i["type"], i["message"])].append(i)
        for (cat, kind, msg), items in sorted(buckets.items()):
            spots = [w for i in items for w in i["where"][:1]]
            count = f" x{len(items)}" if len(items) > 1 else ""
            print(f"  [{cat}] {kind}{count}: {msg}")
            shown = spots if verbose else spots[:4]
            for w in shown:
                print(f"      at ({w['x']:.2f}, {w['y']:.2f})  {w['desc']}")
            if len(spots) > len(shown):
                print(f"      ... {len(spots) - len(shown)} more (-v lists all)")
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--assembly", choices=("economic", "standard", "none"), default="economic",
                    help="JLC PCBA service to check against (default economic)")
    ap.add_argument("--mask-color", default="green", choices=sorted(jlcpcb.RECOMMENDED["mask_web"]),
                    help="solder mask colour; black and white need wider webs (default green)")
    ap.add_argument("--outer-oz", type=int, choices=(1, 2), help="outer copper weight (default: read from the stackup)")
    ap.add_argument("--allow-unrouted", action="store_true", help="report unrouted connections as warnings, not errors")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    ap.add_argument("--json", help="also write the findings to this JSON file")
    ap.add_argument("-v", "--verbose", action="store_true", help="list every location, not just the first few")
    args = ap.parse_args()

    board = os.path.abspath(args.board)
    if not os.path.isfile(board):
        sys.exit(f"no such board: {board}")
    stem = os.path.splitext(board)[0]
    with open(board) as f:
        pcb_text = f.read()
    oz = args.outer_oz or outer_oz(pcb_text)
    vias_filled = bool(re.search(r"\((filling|capping)\s+yes\)", pcb_text))
    rep = Report()

    # pass 1: the project's own DRC
    extra = ["--refill-zones"] + (["--schematic-parity"] if os.path.exists(stem + ".kicad_sch") else [])
    proj = kicadenv.run_drc(board, extra)
    # passes 2 and 3: JLC limits and recommended values
    limits = jlc_drc(board, oz, False, None)
    rec = jlc_drc(board, oz, True, jlcpcb.RECOMMENDED["mask_web"][args.mask_color])
    seen = {violation_key(v) for v in limits}
    for v in limits:
        rep.add("error", "JLC fab", v["type"], v["description"], where_of(v))
    for v in rec:
        if violation_key(v) not in seen:
            seen.add(violation_key(v))
            cat = "JLC silk" if v["type"] in jlcpcb.SILK_TYPES else ("JLC mask" if v["type"] in jlcpcb.MASK_TYPES else "JLC fab")
            rep.add("warning", cat, v["type"], v["description"], where_of(v))
    for v in proj.get("violations", []):
        if violation_key(v) not in seen and not v["type"].startswith("lib_footprint"):
            rep.add(v.get("severity", "error"), "project DRC", v["type"], v["description"], where_of(v))
    for v in proj.get("schematic_parity", []):
        rep.add(v.get("severity", "error"), "parity", v["type"], v["description"], where_of(v))
    unrouted = proj.get("unconnected_items", [])
    if unrouted:
        nets = Counter()
        for u in unrouted:
            n = re.findall(r"\[([^\]]+)\]", u["items"][0].get("description", "")) if u.get("items") else []
            nets[n[0] if n else "?"] += 1
        rep.add("warning" if args.allow_unrouted else "error", "project DRC", "unconnected_items",
                f"{len(unrouted)} unrouted connections: " + ", ".join(f"{k} x{v}" if v > 1 else k for k, v in sorted(nets.items())))

    # pass 4: checks DRC can't express
    dump = tempfile.mkstemp(suffix=".json")[1]
    try:
        kicadenv.run_pcbnew_script("board_dump.py", board, dump)
        with open(dump) as f:
            data = json.load(f)
    finally:
        os.remove(dump)
    board_checks(data, rep, args.verbose)
    if args.assembly != "none":
        assembly_checks(data, args.assembly, vias_filled, rep, args.verbose)

    l, t, r, b = data["board"]["bbox"]
    header = (f"JLCPCB check: {os.path.basename(board)}  ({data['board']['copper_layers']} layers, "
              f"{data['board']['thickness']:.2f} mm, {r - l:.1f} x {b - t:.1f} mm, {oz} oz outer copper, "
              f"{args.mask_color} mask, assembly: {args.assembly})")
    errors, warnings = print_report(rep, header, args.verbose)
    failed = bool(errors) or (args.strict and bool(warnings))
    print(f"\nResult: {'FAIL' if failed else 'PASS'} ({len(errors)} errors, {len(warnings)} warnings)")
    if args.json:
        with open(args.json, "w") as f:
            json.dump({"header": header, "findings": rep.items, "failed": failed}, f, indent=1)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
