#!/usr/bin/env python3
"""Render a KiCad schematic to a PNG you can look at, whole or zoomed to parts or a window, and list a part's pin nets.

    sch_view.py board.kicad_sch -o sheet.png                       # the whole sheet
    sch_view.py board.kicad_sch --around U2,C13 -o u2.png           # zoomed to these symbols, labels included
    sch_view.py board.kicad_sch --zoom 250,330,60,110 -o area.png   # a window in sheet mm (x0,x1,y0,y1)
    sch_view.py board.kicad_sch --pins U2                           # each pin's net, from KiCad's own netlist

It plots the schematic to PDF with kicad-cli (KiCad's own drawing, so it looks exactly like the editor's plot) and
rasterises that with pypdfium2. Coordinates are sheet mm from the top-left corner, y down: the numbers the schematic
editor shows. The schematic is never modified.

--around finds each symbol in the root sheet's file and frames its body, pins and visible fields. On a hierarchical
design it only knows the root sheet; use --page and --zoom for the others.
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicadenv  # noqa: E402
import schnet  # noqa: E402
from schnet import _find, _one, _parse  # noqa: E402

MAX_PX = 2400        # long side of the image, unless --dpi says otherwise
MAX_DPI = 400


# ---------------------------------------------------------------- symbol geometry from the .kicad_sch

def _num(x):
    return float(x)


def _lib_points(lib_sym, unit, style):
    """Body and pin points of one unit of an embedded library symbol, in library coordinates (y up)."""
    pts = []
    name = lib_sym[1].split(":")[-1]
    for sub in _find(lib_sym, "symbol"):
        parts = sub[1].rsplit("_", 2)
        if len(parts) != 3 or parts[0] != name:
            continue
        u, s = int(parts[1]), int(parts[2])
        if u not in (0, unit) or s not in (0, style):
            continue
        for item in sub[2:]:
            if not isinstance(item, list):
                continue
            kind = item[0]
            if kind == "pin":
                at = _one(item, "at")
                x, y, ang = _num(at[0]), _num(at[1]), _num(at[2]) if len(at) > 2 else 0.0
                length = _num(_one(item, "length", "0"))
                pts += [(x, y), (x + length * math.cos(math.radians(ang)), y + length * math.sin(math.radians(ang)))]
            elif kind in ("rectangle",):
                for key in ("start", "end"):
                    p = _one(item, key)
                    pts.append((_num(p[0]), _num(p[1])))
            elif kind in ("polyline", "bezier"):
                for xy in _find(_find(item, "pts")[0], "xy") if _find(item, "pts") else []:
                    pts.append((_num(xy[1]), _num(xy[2])))
            elif kind == "circle":
                c, r = _one(item, "center"), _num(_one(item, "radius", "0"))
                pts += [(_num(c[0]) - r, _num(c[1]) - r), (_num(c[0]) + r, _num(c[1]) + r)]
            elif kind == "arc":
                for key in ("start", "mid", "end"):
                    p = _one(item, key)
                    if p:
                        pts.append((_num(p[0]), _num(p[1])))
    return pts


def _place(pt, at, mirror):
    """A library point on the sheet: flip y, rotate as the symbol is rotated (counter-clockwise on screen), mirror."""
    x, y = pt[0], -pt[1]
    a = math.radians(_num(at[2]) if len(at) > 2 else 0.0)
    xr = x * math.cos(a) + y * math.sin(a)
    yr = -x * math.sin(a) + y * math.cos(a)
    if mirror == "y":
        xr = -xr
    elif mirror == "x":
        yr = -yr
    return _num(at[0]) + xr, _num(at[1]) + yr


def symbol_boxes(sch_path):
    """Reference -> (x0, y0, x1, y1) in sheet mm for every symbol in this sheet file, fields included."""
    with open(sch_path, encoding="utf-8") as f:
        tree = _parse(f.read())
    libs = {s[1]: s for s in _find(_find(tree, "lib_symbols")[0], "symbol")} if _find(tree, "lib_symbols") else {}
    boxes = {}
    for sym in _find(tree, "symbol"):
        lib_id = _one(sym, "lib_id")
        if not lib_id:
            continue
        props = {p[1]: p for p in _find(sym, "property")}
        ref = props.get("Reference", [None, None, "?"])[2]
        if ref.startswith("#"):          # power symbols and flags
            continue
        at = _one(sym, "at")
        mirror = _one(sym, "mirror")
        unit = int(_one(sym, "unit", "1"))
        style = int(_one(sym, "body_style", _one(sym, "convert", "1")))
        pts = [_place(p, at, mirror) for p in _lib_points(libs.get(lib_id, []), unit, style)] if lib_id in libs else []
        pts.append((_num(at[0]), _num(at[1])))
        for p in props.values():
            effects = _find(p, "effects")
            hidden = effects and (any(c == "hide" for c in effects[0]) or _one(effects[0], "hide") == "yes")
            pat = _one(p, "at")
            if pat and not hidden and p[2]:
                pts.append((_num(pat[0]), _num(pat[1])))
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        box = (min(xs), min(ys), max(xs), max(ys))
        if ref in boxes:                 # another unit of the same part
            b = boxes[ref]
            box = (min(b[0], box[0]), min(b[1], box[1]), max(b[2], box[2]), max(b[3], box[3]))
        boxes[ref] = box
    return boxes


# ---------------------------------------------------------------- plotting

def plot_pdf(sch, out_pdf):
    r = subprocess.run([kicadenv.kicad_cli(), "sch", "export", "pdf", "-o", out_pdf, sch],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(out_pdf):
        noise = ("Fontconfig warning",)
        err = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if not l.startswith(noise))
        sys.exit(f"kicad-cli couldn't plot {sch}:\n{err}")


def render(pdf_path, page_no, window, dpi, out_png):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(pdf_path)
    if not 1 <= page_no <= len(pdf):
        sys.exit(f"the schematic has {len(pdf)} page(s); there is no page {page_no}")
    page = pdf[page_no - 1]
    w_pt, h_pt = page.get_size()
    mm = 72 / 25.4
    w_mm, h_mm = w_pt / mm, h_pt / mm
    x0, y0, x1, y1 = window or (0, 0, w_mm, h_mm)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w_mm, x1), min(h_mm, y1)
    if x1 <= x0 or y1 <= y0:
        sys.exit(f"the window is outside the {w_mm:.0f} x {h_mm:.0f} mm sheet")
    if dpi is None:
        dpi = min(MAX_DPI, MAX_PX / (max(x1 - x0, y1 - y0) / 25.4))
    crop = (x0 * mm, (h_mm - y1) * mm, (w_mm - x1) * mm, y0 * mm)     # left, bottom, right, top in points
    img = page.render(scale=dpi / 72, crop=crop, fill_color=(255, 255, 255, 255)).to_pil()
    img.save(out_png)
    return (x0, y0, x1, y1), dpi, img.size, (w_mm, h_mm), len(pdf)


def print_pins(sch, ref):
    parts = schnet.load(sch)
    if not parts or ref not in parts:
        sys.exit(f"{ref} isn't in {sch}")
    p = parts[ref]
    print(f"{ref}  {p['value']}  {p['footprint']}")
    key = lambda n: (0, int(n)) if n.isdigit() else (1, n)
    for pin in sorted(p["pins"], key=key):
        print(f"  pin {pin:<4s} {p['pins'][pin]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("schematic")
    ap.add_argument("-o", "--output", help="PNG to write (put it in your scratchpad, not the repo)")
    ap.add_argument("--around", help="comma-separated references to frame, e.g. U2,C13")
    ap.add_argument("--margin", type=float, default=5.0, help="mm around --around's symbols (default 5)")
    ap.add_argument("--zoom", help="window x0,x1,y0,y1 in sheet mm")
    ap.add_argument("--page", type=int, default=1, help="page of a hierarchical design (default 1, the root)")
    ap.add_argument("--dpi", type=float, help=f"resolution (default: fit {MAX_PX} px, at most {MAX_DPI} dpi)")
    ap.add_argument("--pins", metavar="REF", help="print each pin's net for this part (no image needed)")
    args = ap.parse_args()

    sch = os.path.abspath(args.schematic)
    if not sch.endswith(".kicad_sch") or not os.path.isfile(sch):
        sys.exit(f"not a .kicad_sch file: {args.schematic}")
    if args.pins:
        print_pins(sch, args.pins)
        if not args.output:
            return 0
    if not args.output:
        sys.exit("give -o <file.png> (or --pins REF on its own)")
    if args.around and args.zoom:
        sys.exit("use --around or --zoom, not both")

    window = None
    if args.zoom:
        try:
            x0, x1, y0, y1 = (float(v) for v in args.zoom.split(","))
        except ValueError:
            sys.exit("--zoom takes x0,x1,y0,y1 in mm")
        window = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    elif args.around:
        if args.page != 1:
            sys.exit("--around only knows the root sheet (page 1); use --zoom on other pages")
        boxes = symbol_boxes(sch)
        refs = [r.strip() for r in args.around.split(",") if r.strip()]
        missing = [r for r in refs if r not in boxes]
        if missing:
            sys.exit(f"not on the root sheet: {', '.join(missing)}")
        m = args.margin
        window = (min(boxes[r][0] for r in refs) - m, min(boxes[r][1] for r in refs) - m,
                  max(boxes[r][2] for r in refs) + m, max(boxes[r][3] for r in refs) + m)

    with tempfile.TemporaryDirectory(prefix="sch_view-") as tmp:
        pdf = os.path.join(tmp, "sheet.pdf")
        plot_pdf(sch, pdf)
        (x0, y0, x1, y1), dpi, size, sheet, pages = render(pdf, args.page, window, args.dpi, args.output)
    print(f"wrote {args.output}: {size[0]} x {size[1]} px at {dpi:.0f} dpi, sheet mm x {x0:.1f}..{x1:.1f}, "
          f"y {y0:.1f}..{y1:.1f} (page {args.page} of {pages}, {sheet[0]:.0f} x {sheet[1]:.0f} mm)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
