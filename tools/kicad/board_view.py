#!/usr/bin/env python3
"""Render a KiCad board to PNG: pads, tracks, vias, silkscreen, labels and the ratsnest.

    board_view.py board.kicad_pcb [-o out.png] [--zoom X0,X1,Y0,Y1 | --around REF[,REF..]] [options]

Coordinates are KiCad board coordinates in mm (y grows downwards), the same ones the PCB editor and
DRC reports use. Pads are drawn with their real shapes. Copper colours: GND green, nets in a class
named like "Power" (or +5V-style names) red, other nets yellow, no net grey. Tracks: F.Cu red,
B.Cu blue, inner layers purple. The ratsnest (thin coloured lines) is KiCad's own list of unrouted
connections, taken from DRC.
"""
import argparse
import colorsys
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicadenv  # noqa: E402

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle
except ImportError:
    sys.exit("board_view.py needs matplotlib in the python3 that runs it (pip3 install matplotlib).")

POWER_NAME = re.compile(r"^/?(\+\d|\+?V(CC|DD|IN|BAT|BUS)|.*5V|.*3V3|.*12V)", re.I)


def pad_colour(pad):
    net = pad["net"]
    if pad["kind"] == "NPTH" or not net or net.startswith("unconnected-"):
        return "#b5b5b5"
    if net == "GND":
        return "#2f9e5b"
    if "power" in pad.get("netclass", "").lower() or POWER_NAME.match(net):
        return "#d9534f"
    return "#e0b83a"


def net_colour(name):
    h = (sum(ord(c) * 31 ** i for i, c in enumerate(name)) % 997) / 997.0
    return colorsys.hsv_to_rgb(h, 0.85, 0.75)


def ratsnest(board):
    """Unrouted connections as ((x1, y1), (x2, y2), net) from kicad-cli DRC."""
    report = kicadenv.run_drc(board)
    lines = []
    for u in report.get("unconnected_items", []):
        items = u.get("items", [])
        if len(items) != 2:
            continue
        nets = re.findall(r"\[([^\]]+)\]", items[0].get("description", ""))
        a, b = items[0]["pos"], items[1]["pos"]
        lines.append(((a["x"], a["y"]), (b["x"], b["y"]), nets[0] if nets else ""))
    return lines


def extent(data, args):
    if args.zoom:
        x0, x1, y0, y1 = map(float, args.zoom.split(","))
        return x0, x1, y0, y1
    if args.around:
        refs = set(args.around.split(","))
        boxes = [f["courtyard"] or f["label"]["bbox"] for f in data["footprints"] if f["ref"] in refs]
        if not boxes:
            sys.exit(f"--around: none of {sorted(refs)} found on the board")
        m = args.margin
        return (min(b[0] for b in boxes) - m, max(b[2] for b in boxes) + m,
                min(b[1] for b in boxes) - m, max(b[3] for b in boxes) + m)
    l, t, r, b = data["board"]["bbox"]
    return l - 2, r + 2, t - 2, b + 2


def render(data, rats, args):
    x0, x1, y0, y1 = extent(data, args)
    xr, yr = x1 - x0, y1 - y0
    width_in = args.width
    height_in = width_in * yr / xr
    fig = plt.figure(figsize=(width_in, height_in + 0.6), dpi=args.dpi)
    ax = fig.add_axes([0.03, 0.6 / (height_in + 0.6) * 0.7, 0.95, height_in / (height_in + 0.6) * 0.97])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_aspect("equal", adjustable="box")
    pts_per_mm = min(width_in * 0.95 * 72 / xr, height_in * 0.97 * 72 / yr)
    side = args.side + "."

    for poly in data["board"]["outline"]:
        ax.add_patch(Polygon(poly, closed=True, fill=False, ec="black", lw=1.2, zorder=1))
    for z in data["zones"]:
        for poly in z["outline"]:
            ax.add_patch(Polygon(poly, closed=True, fill=False, ec="#9aa5b1", lw=0.6, ls=":", zorder=1))

    for f in data["footprints"]:
        if f["courtyard"] and f["side"] == args.side:
            l, t, r, b = f["courtyard"]
            ax.add_patch(Rectangle((l, t), r - l, b - t, fill=False, ec="#c8c8c8", lw=0.5, ls="--", zorder=1))
        for s in f["silk"]:
            if s["layer"].startswith(side):
                for poly in s["poly"]:
                    ax.add_patch(Polygon(poly, closed=True, fc="#4a4a4a", ec="none", alpha=0.8, zorder=4))
        for p in f["pads"]:
            onside = p["kind"] in ("PTH", "NPTH") or f["side"] == args.side
            for poly in p["poly"]:
                ax.add_patch(Polygon(poly, closed=True, fc=pad_colour(p), ec="#333" if p["kind"] == "PTH" else "none",
                                     lw=0.4, alpha=0.85 if onside else 0.25, zorder=2))
            if p["drill"]:
                w, h = p["drill"]
                if p["slot"] and abs(w - h) > 1e-3:
                    r = min(w, h) / 2
                    ax.add_patch(FancyBboxPatch((p["x"] - w / 2 + r, p["y"] - h / 2 + r), w - 2 * r, h - 2 * r,
                                                boxstyle=f"round,pad={r}", fc="white", ec="#555", lw=0.4, zorder=5))
                else:
                    ax.add_patch(Circle((p["x"], p["y"]), w / 2, fc="white", ec="#555", lw=0.4, zorder=5))
    for s in data["silk"]:
        if s["layer"].startswith(side):
            for poly in s["poly"]:
                ax.add_patch(Polygon(poly, closed=True, fc="#4a4a4a", ec="none", alpha=0.8, zorder=4))

    for t in data["tracks"]:
        col = "#c0392b" if t["front"] else ("#2e86de" if t["layer"] in ("B.Cu",) else "#8e44ad")
        ax.plot([t["x1"], t["x2"]], [t["y1"], t["y2"]], "-", color=col, lw=t["width"] * pts_per_mm,
                solid_capstyle="round", alpha=0.75 if t["front"] else 0.55, zorder=3)
    for v in data["vias"]:
        ax.add_patch(Circle((v["x"], v["y"]), v["dia"] / 2, fc="#2f9e5b" if v["net"] == "GND" else "#7f8c8d",
                            ec="#222", lw=0.4, zorder=6))
        ax.add_patch(Circle((v["x"], v["y"]), v["drill"] / 2, fc="white", ec="none", zorder=7))

    if not args.no_labels:
        for t in data["texts"]:
            if not t["visible"] or not t["layer"].startswith(side):
                continue
            l, tp, r, b = t["bbox"]
            ax.add_patch(Rectangle((l, tp), r - l, b - tp, fill=False, ec="#7b2cbf", lw=0.6, zorder=8))
            ax.text((l + r) / 2, (tp + b) / 2, t["text"], ha="center", va="center", color="#5a189a", weight="bold",
                    fontsize=max(4.0, min(t["height"] * pts_per_mm * 0.9, 14)), clip_on=True, zorder=9)

    for a, b, net in rats:
        col = net_colour(net)
        ax.plot([a[0], b[0]], [a[1], b[1]], "-", color=col, lw=0.9, zorder=10)
        if args.net_names:
            ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 0.4, net.lstrip("/"), color=col, fontsize=6,
                    ha="center", clip_on=True, zorder=10)

    step = 1 if max(xr, yr) <= 40 else (2 if max(xr, yr) <= 80 else 5)
    ax.set_xticks([v for v in range(int(x0), int(x1) + 1) if v % step == 0])
    ax.set_yticks([v for v in range(int(y0), int(y1) + 1) if v % step == 0])
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.2, lw=0.5)
    fig.text(0.03, 0.15 / (height_in + 0.6), f"{os.path.basename(data['file'])}  ·  {args.side} side  ·  "
             "pads: GND green, power red, signal yellow  ·  tracks: F.Cu red, B.Cu blue, inner purple  ·  "
             f"ratsnest: {len(rats)} unrouted", fontsize=8, color="#444")
    fig.savefig(args.out)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("-o", "--out", help="PNG to write (default: <board>.png in the temp folder)")
    ap.add_argument("--zoom", help="window X0,X1,Y0,Y1 in board mm")
    ap.add_argument("--around", help="zoom to these references, comma separated")
    ap.add_argument("--margin", type=float, default=3.0, help="margin around --around parts, mm (default 3)")
    ap.add_argument("--side", choices=("F", "B"), default="F", help="side whose silkscreen and SMD pads to show")
    ap.add_argument("--no-ratsnest", action="store_true", help="skip DRC and the ratsnest (faster)")
    ap.add_argument("--net-names", action="store_true", help="label ratsnest lines with their net")
    ap.add_argument("--no-labels", action="store_true", help="hide reference labels")
    ap.add_argument("--width", type=float, default=16.0, help="image width in inches (default 16)")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--json", help="also keep the board dump at this path")
    args = ap.parse_args()

    board = os.path.abspath(args.board)
    if not os.path.isfile(board):
        sys.exit(f"no such board: {board}")
    if not args.out:
        args.out = os.path.join(tempfile.gettempdir(), os.path.splitext(os.path.basename(board))[0] + ".png")
    dump = args.json or tempfile.mkstemp(suffix=".json")[1]
    kicadenv.run_pcbnew_script("board_dump.py", board, dump)
    with open(dump) as f:
        data = json.load(f)
    if not args.json:
        os.remove(dump)
    rats = [] if args.no_ratsnest else ratsnest(board)
    render(data, rats, args)
    print(args.out)


if __name__ == "__main__":
    main()
