#!/usr/bin/env python3
"""Look at a fab zip the way the fab will: render its Gerbers and drill files, and check that they fit together.

    gerber_view.py board_gerber.zip -o <scratch>/gerbers      # top.png, bottom.png and one PNG per layer
    gerber_view.py board_gerber.zip                          # the checks only, no images

It reads the zip (or a folder of Gerbers), not the board, so it shows what was actually exported. Checks:
  - every layer a 2-layer JLC order needs is there (copper, mask and silkscreen on both sides, outline, plated drill),
    and nothing in the zip is unrecognised;
  - the outline is a closed shape, and its size;
  - every copper and mask layer, and every drill hit, lies inside the outline's bounding box (a layer exported with
    another origin or a stray item shows up here); silkscreen past the outline is only reported, since connector
    silk at the board edge is expected and JLC clips it;
  - every plated hole lands on copper on both sides.
top.png is the board from above as JLC makes it: green mask, gold where the mask opens over copper, white silkscreen,
black holes. bottom.png is the same from below, mirrored as you'd see it with the board flipped. Exit status is 1 when
a check fails.

Gerbers are rendered with pygerber; drill files are read here (KiCad's Excellon: mm, decimal, G85 slots).
"""
import argparse
import os
import re
import sys
import tempfile
import zipfile

import numpy as np

DPMM = 20            # pixels per mm for the checks and the composites

# Protel extension -> layer, as kicad-cli names them.
LAYERS = {"gtl": "F.Cu", "gbl": "B.Cu", "gts": "F.Mask", "gbs": "B.Mask", "gto": "F.Silkscreen",
          "gbo": "B.Silkscreen", "gm1": "Edge.Cuts", "gtp": "F.Paste", "gbp": "B.Paste"}
REQUIRED = ["F.Cu", "B.Cu", "F.Mask", "B.Mask", "F.Silkscreen", "B.Silkscreen", "Edge.Cuts"]
INNER = re.compile(r"^g(\d+)$")       # inner copper: .g2, .g3 ...

MASK_GREEN = (22, 92, 48)
MASK_OVER_COPPER = (40, 130, 70)
BARE_FR4 = (196, 170, 110)
GOLD = (212, 175, 55)
SILK = (245, 245, 245)
HOLE = (20, 20, 20)
OUTSIDE = (255, 255, 255)


# ---------------------------------------------------------------- reading the files

def collect(src, tmp):
    """Copy the fab files out of a zip (or folder) into tmp by bare name. Returns {layer: path}, drills, unknown."""
    files = {}
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for info in z.infolist():
                name = os.path.basename(info.filename)     # never trust a member's directories
                if info.is_dir() or not name or name.startswith("."):
                    continue
                with open(os.path.join(tmp, name), "wb") as f:
                    f.write(z.read(info))
                files[name] = os.path.join(tmp, name)
    elif os.path.isdir(src):
        for name in sorted(os.listdir(src)):
            if os.path.isfile(os.path.join(src, name)) and not name.startswith("."):
                files[name] = os.path.join(src, name)
    else:
        sys.exit(f"not a zip file or a folder: {src}")
    layers, drills, unknown = {}, {}, []
    for name, path in sorted(files.items()):
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext in LAYERS:
            layers[LAYERS[ext]] = path
        elif INNER.match(ext):
            layers[f"In{int(INNER.match(ext).group(1)) - 1}.Cu"] = path
        elif ext == "drl":
            drills["NPTH" if "NPTH" in name.upper() else "PTH"] = path
        elif ext in ("gbrjob",):
            continue
        else:
            unknown.append(name)
    return layers, drills, unknown


def read_drill(path):
    """[(x, y, x2, y2, diameter)] in Gerber coordinates (mm); x2/y2 equal x/y for a round hole."""
    tools, hits, current = {}, [], None
    with open(path) as f:
        for line in f:
            line = line.strip()
            m = re.match(r"T(\d+)C([\d.]+)$", line)
            if m:
                tools[m.group(1)] = float(m.group(2))
                continue
            m = re.match(r"T(\d+)$", line)
            if m:
                current = m.group(1)
                continue
            m = re.match(r"X(-?[\d.]+)Y(-?[\d.]+)(?:G85X(-?[\d.]+)Y(-?[\d.]+))?$", line)
            if m and current in tools:
                x, y = float(m.group(1)), float(m.group(2))
                x2 = float(m.group(3)) if m.group(3) else x
                y2 = float(m.group(4)) if m.group(4) else y
                hits.append((x, y, x2, y2, tools[current]))
    return hits


class Canvas:
    """A common pixel grid over the outline's bounding box (plus a margin), Gerber y up -> image y down."""

    def __init__(self, x0, y0, x1, y1, margin=2.0):
        self.x0, self.y1 = x0 - margin, y1 + margin
        self.w = int(round((x1 - x0 + 2 * margin) * DPMM))
        self.h = int(round((y1 - y0 + 2 * margin) * DPMM))

    def px(self, x, y):
        return (x - self.x0) * DPMM, (self.y1 - y) * DPMM

    def blank(self):
        return np.zeros((self.h, self.w), dtype=bool)


def render_layer(path, canvas):
    """The layer's dark (drawn) area as a boolean mask on the canvas, and its own bounding box in mm."""
    from pygerber.gerberx3.api.v2 import ColorScheme, GerberFile, PixelFormatEnum
    from PIL import Image
    parsed = GerberFile.from_file(path).parse()
    info = parsed.get_info()
    box = tuple(float(v) for v in (info.min_x_mm, info.min_y_mm, info.max_x_mm, info.max_y_mm))
    out = canvas.blank()
    if box[2] <= box[0] or box[3] <= box[1]:
        return out, None
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        parsed.render_raster(tmp.name, dpmm=DPMM, color_scheme=ColorScheme.COPPER_ALPHA,
                             pixel_format=PixelFormatEnum.RGBA)
        alpha = np.array(Image.open(tmp.name).convert("RGBA"))[:, :, 3] > 127
    left, top = canvas.px(box[0], box[3])
    left, top = int(round(left)), int(round(top))
    h, w = alpha.shape
    # clip the layer's image onto the canvas
    cx0, cy0 = max(0, left), max(0, top)
    cx1, cy1 = min(canvas.w, left + w), min(canvas.h, top + h)
    if cx1 > cx0 and cy1 > cy0:
        out[cy0:cy1, cx0:cx1] = alpha[cy0 - top:cy1 - top, cx0 - left:cx1 - left]
    return out, box


def holes_mask(hits, canvas):
    from PIL import Image, ImageDraw
    img = Image.new("L", (canvas.w, canvas.h), 0)
    d = ImageDraw.Draw(img)
    for x, y, x2, y2, dia in hits:
        (ax, ay), (bx, by) = canvas.px(x, y), canvas.px(x2, y2)
        r = dia / 2 * DPMM
        d.line([(ax, ay), (bx, by)], fill=255, width=max(1, int(round(2 * r))))
        for cx, cy in ((ax, ay), (bx, by)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    return np.array(img) > 0


def board_area(outline):
    """Inside the outline: everything a flood fill from the canvas corner (outside) can't reach."""
    from PIL import Image, ImageDraw
    # .copy(): Pillow's flood fill silently does nothing on an image that shares a numpy array's buffer
    img = Image.fromarray(np.where(outline, 255, 0).astype(np.uint8)).copy()
    ImageDraw.floodfill(img, (0, 0), 128)
    a = np.array(img)
    return a == 0, (a == 0).any()


# ---------------------------------------------------------------- composites

def composite(board, cu, mask_open, silk, holes, mirror):
    img = np.empty(board.shape + (3,), dtype=np.uint8)
    img[:] = OUTSIDE
    img[board] = MASK_GREEN
    img[board & cu] = MASK_OVER_COPPER
    img[board & mask_open & ~cu] = BARE_FR4
    img[board & mask_open & cu] = GOLD
    img[board & silk & ~mask_open] = SILK
    img[holes] = HOLE
    return img[:, ::-1] if mirror else img


def save(img, path):
    from PIL import Image
    if img.dtype == bool:
        img = np.where(img, 0, 255).astype(np.uint8)
    Image.fromarray(img).save(path)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="the fab zip, or a folder of Gerbers and drill files")
    ap.add_argument("-o", "--out-dir", help="write top.png, bottom.png and one PNG per layer here (your scratchpad)")
    args = ap.parse_args()

    problems, notes = [], []
    with tempfile.TemporaryDirectory(prefix="gerber_view-") as tmp:
        layers, drills, unknown = collect(os.path.abspath(args.source), tmp)
        for name in unknown:
            problems.append(f"{name}: not a Gerber or drill file this check knows")
        missing = [l for l in REQUIRED if l not in layers] + ([] if "PTH" in drills else ["plated drill file"])
        if missing:
            problems.append("missing: " + ", ".join(missing))
        if "Edge.Cuts" not in layers:
            print("\n".join(f"FAIL  {p}" for p in problems + ["no outline, so nothing else can be checked"]))
            return 1

        # the outline sets the canvas
        from pygerber.gerberx3.api.v2 import GerberFile
        info = GerberFile.from_file(layers["Edge.Cuts"]).parse().get_info()
        ox0, oy0, ox1, oy1 = (float(v) for v in (info.min_x_mm, info.min_y_mm, info.max_x_mm, info.max_y_mm))
        canvas = Canvas(ox0, oy0, ox1, oy1)
        masks, boxes = {}, {}
        for layer, path in sorted(layers.items()):
            masks[layer], boxes[layer] = render_layer(path, canvas)
        board, closed = board_area(masks["Edge.Cuts"])
        if not closed:
            problems.append("the outline isn't a closed shape: a fill from outside reaches everywhere")
            board = ~canvas.blank()
        # the outline is drawn with a line width; its centre line is what the fab routes
        lw = 0.1
        print(f"outline {ox1 - ox0 - lw:.2f} x {oy1 - oy0 - lw:.2f} mm (to the line centre)")

        def outside(box, slack):
            return box and (box[0] < ox0 - slack or box[1] < oy0 - slack or box[2] > ox1 + slack or box[3] > oy1 + slack)

        for layer in sorted(layers):
            box = boxes[layer]
            drawn = int(masks[layer].sum())
            if layer == "Edge.Cuts":
                continue
            if box is None or drawn == 0:
                (notes if "Paste" in layer else problems).append(f"{layer} is empty")
                continue
            if outside(box, 0.01):
                # Gerber y is up: the board's top edge (rear, low KiCad y) is the high Gerber y
                over = {"left": ox0 - box[0], "right": box[2] - ox1, "top": box[3] - oy1, "bottom": oy0 - box[1]}
                past = ", ".join(f"{side} {d:.2f} mm" for side, d in over.items() if d > 0.01)
                (notes if "Silkscreen" in layer else problems).append(f"{layer} extends past the outline: {past}")
            print(f"{layer:<14s} {os.path.basename(layers[layer]):<34s} {box[2] - box[0]:6.1f} x {box[3] - box[1]:5.1f} mm")

        hits = {k: read_drill(p) for k, p in drills.items()}
        for kind, hs in sorted(hits.items()):
            slots = sum(1 for h in hs if (h[0], h[1]) != (h[2], h[3]))
            sizes = sorted({h[4] for h in hs})
            print(f"{kind + ' drill':<14s} {os.path.basename(drills[kind]):<34s} {len(hs) - slots} holes, {slots} slots, "
                  f"{sizes[0]:.3f}..{sizes[-1]:.3f} mm" if hs else f"{kind} drill: no holes")
            stray = [h for h in hs if not (ox0 <= h[0] <= ox1 and oy0 <= h[1] <= oy1)]
            if stray:
                problems.append(f"{len(stray)} {kind} hits outside the outline, first at ({stray[0][0]}, {stray[0][1]})")

        # every plated hole needs copper around it on every copper layer
        coppers = [l for l in layers if l.endswith(".Cu")]
        for x, y, x2, y2, dia in hits.get("PTH", []):
            for layer in coppers:
                cx, cy = canvas.px((x + x2) / 2, (y + y2) / 2)
                r = int(dia / 2 * DPMM) + 2         # just past the drill's edge
                ring = masks[layer][max(0, int(cy) - r):int(cy) + r + 1, max(0, int(cx) - r):int(cx) + r + 1]
                if ring.size == 0 or ring.mean() < 0.5:
                    problems.append(f"plated hole at ({x}, {y}) ⌀{dia} mm has no copper around it on {layer}")
                    break

        if args.out_dir:
            os.makedirs(args.out_dir, exist_ok=True)
            all_holes = holes_mask(hits.get("PTH", []) + hits.get("NPTH", []), canvas)
            blank = canvas.blank()
            for side, mirror in (("F", False), ("B", True)):
                img = composite(board, masks.get(f"{side}.Cu", blank), masks.get(f"{side}.Mask", blank),
                                masks.get(f"{side}.Silkscreen", blank), all_holes, mirror)
                save(img, os.path.join(args.out_dir, "top.png" if side == "F" else "bottom.png"))
            for layer, m in masks.items():
                save(m | masks["Edge.Cuts"], os.path.join(args.out_dir, layer.replace(".", "_") + ".png"))
            save(all_holes | masks["Edge.Cuts"], os.path.join(args.out_dir, "drills.png"))
            print(f"wrote top.png, bottom.png, drills.png and {len(masks)} layer PNGs to {args.out_dir} "
                  f"({canvas.w} x {canvas.h} px, {DPMM} px/mm)")

    for n in notes:
        print(f"note  {n}")
    for p in problems:
        print(f"FAIL  {p}")
    print("Result: " + ("FAIL" if problems else "PASS") + f" ({len(problems)} problems, {len(notes)} notes)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
