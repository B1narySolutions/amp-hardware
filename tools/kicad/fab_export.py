#!/usr/bin/env python3
"""Export a KiCad board as a zip of Gerbers and drill files for JLCPCB.

    fab_export.py board.kicad_pcb                  # check the board, then write the zip
    fab_export.py board.kicad_pcb -o out.zip       # another zip path
    fab_export.py board.kicad_pcb --paste          # also the paste layers (for a stencil or JLC assembly)
    fab_export.py board.kicad_pcb --check          # is the committed zip still what the board exports?

Steps:
  1. Runs board_check.py (project DRC, schematic parity, JLC limits) and stops if it reports errors. Pass
     --ignore-check-errors only when the user has accepted those errors.
  2. Exports into a temporary folder with kicad-cli, with fixed settings that follow JLC's KiCad guide, so the
     result doesn't depend on the plot settings saved from KiCad's GUI:
       Gerbers: every copper layer, F/B mask, F/B silkscreen, Edge.Cuts (plus F/B paste with --paste);
                Protel extensions, no X2 attributes, silkscreen clipped by the mask openings, 4.6 mm format,
                zones refilled in memory first.
       Drill:   Excellon, mm, decimal, absolute origin, PTH and NPTH in separate files, slots as G85.
  3. Checks that every expected file is there and not empty, and reads the board size, hole sizes and slot
     count back from the files.
  4. Writes the zip through a temporary file, so a failed run never leaves a half-written zip.

The board file is never modified. The only file written is the zip. Exit status is 1 on any failure, and with
--check when the zip is missing or no longer matches the board (dates and KiCad's version line are ignored).

The zip's default path is the board's entry in FAB_ZIPS (tools/check_all.py), or <board folder>/fab/<board name>_gerber.zip for a board not listed.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import kicadenv  # noqa: E402
# Per-board settings live in check_all.py: the board check's options (e.g. --assembly none) and the zip path.
from check_all import BOARD_CHECK_ARGS, FAB_ZIPS  # noqa: E402

GERBER_OPTS = ["--no-x2", "--subtract-soldermask", "--check-zones", "--precision", "6"]
DRILL_OPTS = ["--format", "excellon", "--excellon-units", "mm", "--excellon-zeros-format", "decimal",
              "--drill-origin", "absolute", "--excellon-oval-format", "alternate", "--excellon-separate-th"]

# Lines that change on every export (or with KiCad's version) without the board changing.
VOLATILE = re.compile(r"CreationDate|GenerationSoftware|Created by KiCad|DRILL file|^; #@! TF\.CreationDate")


def rel(path):
    """Repo-relative path for files in the repo, the absolute path otherwise."""
    r = os.path.relpath(path, ROOT)
    return path if r.startswith("..") else r.replace(os.sep, "/")


def default_zip(board):
    listed = FAB_ZIPS.get(rel(board))
    if listed:
        return os.path.join(ROOT, listed)
    stem = os.path.splitext(os.path.basename(board))[0]
    return os.path.join(os.path.dirname(board), "fab", f"{stem}_gerber.zip")


def copper_layers(pcb_text):
    """The board's copper layers in stack order, from its (layers ...) table."""
    block = re.search(r"\(layers\s*\n(.*?)\n\s*\)", pcb_text, re.S)
    if not block:
        sys.exit("can't find the board's layer table")
    found = re.findall(r'\(\d+\s+"([^"]+\.Cu)"\s+(?:signal|power|mixed|jumper)', block.group(1))
    order = lambda n: (0, 0) if n == "F.Cu" else (2, 0) if n == "B.Cu" else (1, int(re.sub(r"\D", "", n) or 0))
    return sorted(found, key=order)


def layer_file(stem, layer, ext):
    return f"{stem}-{layer.replace('.', '_')}.{ext}"


def expected_files(stem, coppers, paste):
    """File name -> layer, as kicad-cli names them with Protel extensions."""
    files = {}
    for i, cu in enumerate(coppers):
        ext = "gtl" if cu == "F.Cu" else "gbl" if cu == "B.Cu" else f"g{i + 1}"
        files[layer_file(stem, cu, ext)] = cu
    for layer, ext in [("F.Mask", "gts"), ("B.Mask", "gbs"), ("F.Silkscreen", "gto"), ("B.Silkscreen", "gbo"),
                       ("Edge.Cuts", "gm1")] + ([("F.Paste", "gtp"), ("B.Paste", "gbp")] if paste else []):
        files[layer_file(stem, layer, ext)] = layer
    files[f"{stem}-PTH.drl"] = "plated holes"
    files[f"{stem}-NPTH.drl"] = "non-plated holes"
    return files


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"{os.path.basename(cmd[0])} {cmd[1]} {cmd[2]} {cmd[3]} failed:\n{r.stdout}{r.stderr}")


def export(board, out_dir, paste, pcb_text):
    cli = kicadenv.kicad_cli()
    coppers = copper_layers(pcb_text)
    layers = coppers + ["F.Mask", "B.Mask", "F.Silkscreen", "B.Silkscreen", "Edge.Cuts"]
    if paste:
        layers += ["F.Paste", "B.Paste"]
    run([cli, "pcb", "export", "gerbers", "-o", out_dir, "-l", ",".join(layers), *GERBER_OPTS, board])
    run([cli, "pcb", "export", "drill", "-o", out_dir, *DRILL_OPTS, board])
    stem = os.path.splitext(os.path.basename(board))[0]
    files = expected_files(stem, coppers, paste)
    missing = [f for f in files if not os.path.isfile(os.path.join(out_dir, f))]
    if missing:
        sys.exit("kicad-cli didn't write " + ", ".join(missing))
    # a Gerber with only its header is about 1 kB; drill files may legitimately have no holes
    empty = [f for f in files if not f.endswith(".drl") and not has_draws(os.path.join(out_dir, f))]
    if empty:
        sys.exit("these Gerbers came out empty: " + ", ".join(empty))
    return files


# ---------------------------------------------------------------- reading the files back

def has_draws(path):
    """True when a Gerber draws or flashes anything (a D01/D03 operation)."""
    with open(path) as f:
        return any(re.search(r"D0[13]\*", line) for line in f)


def outline_size(path):
    """Width and height of the Edge.Cuts Gerber in mm (4.6 format)."""
    xs, ys = [], []
    x = y = None
    with open(path) as f:
        for line in f:
            m = re.match(r"(?:G0[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+)?(?:J-?\d+)?D0[12]\*", line)
            if m:
                x = int(m.group(1)) / 1e6 if m.group(1) else x
                y = int(m.group(2)) / 1e6 if m.group(2) else y
                xs.append(x)
                ys.append(y)
    if not xs:
        sys.exit("the Edge.Cuts Gerber has no outline")
    return max(xs) - min(xs), max(ys) - min(ys)


def drill_summary(path):
    """(holes, slots, smallest tool mm) from an Excellon file KiCad wrote in mm/decimal."""
    tools, holes, slots, current = {}, 0, 0, None
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
            if line.startswith("X") and current:
                if "G85" in line:
                    slots += 1
                else:
                    holes += 1
    return holes, slots, (min(tools.values()) if tools else None)


def normalized(data):
    return [l for l in data.decode("utf-8", "replace").splitlines() if not VOLATILE.search(l)]


def compare(zip_path, fresh_dir, files):
    """Names of files that differ between the zip and a fresh export (or are missing from either side)."""
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        stale = sorted(names ^ set(files))
        for name in sorted(names & set(files)):
            with open(os.path.join(fresh_dir, name), "rb") as f:
                if normalized(z.read(name)) != normalized(f.read()):
                    stale.append(name)
    return stale


# ---------------------------------------------------------------- main

def board_check(board, extra):
    cmd = [sys.executable, os.path.join(HERE, "board_check.py"), board, *extra]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    result = re.search(r"^Result: .*$", r.stdout, re.M)
    return r.returncode == 0, (result.group(0) if result else "no result line"), r.stdout + r.stderr


def git_state(board):
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        dirty = subprocess.run(["git", "status", "--porcelain", "--", board], cwd=ROOT, capture_output=True, text=True)
        return head.stdout.strip() or "?", bool(dirty.stdout.strip())
    except OSError:
        return "?", False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("-o", "--output", help="zip path (default: FAB_ZIPS, or <board folder>/fab/<name>_gerber.zip)")
    ap.add_argument("--paste", action="store_true", help="include F/B paste layers (stencil or JLC assembly)")
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 if the zip is missing or differs from a fresh export")
    ap.add_argument("--ignore-check-errors", action="store_true",
                    help="write the zip even though the board check reports errors (only when the user accepts them)")
    ap.add_argument("--assembly", choices=("economic", "standard", "none"),
                    help="passed to board_check.py (default: the board's entry in check_all.py, else economic)")
    args = ap.parse_args()

    board = os.path.abspath(args.board)
    if not board.endswith(".kicad_pcb") or not os.path.isfile(board):
        sys.exit(f"not a .kicad_pcb file: {args.board}")
    zip_path = os.path.abspath(args.output) if args.output else default_zip(board)
    if not zip_path.endswith(".zip"):
        sys.exit(f"the output must be a .zip: {zip_path}")
    with open(board) as f:
        pcb_text = f.read()

    lock = os.path.join(os.path.dirname(board), f"~{os.path.basename(board)}.lck")
    if os.path.exists(lock):
        print(f"note: the board is open in KiCad ({os.path.basename(lock)}); unsaved changes there aren't in the zip")
    head, dirty = git_state(board)

    with tempfile.TemporaryDirectory(prefix="fab_export-") as tmp:
        files = export(board, tmp, args.paste, pcb_text)

        if args.check:
            if not os.path.isfile(zip_path):
                print(f"STALE  {rel(zip_path)} doesn't exist; run fab_export.py {rel(board)}")
                return 1
            stale = compare(zip_path, tmp, files)
            if stale:
                print(f"STALE  {rel(zip_path)} no longer matches the board: {', '.join(stale)}. "
                      f"Re-export with fab_export.py {rel(board)}")
                return 1
            print(f"OK  {rel(zip_path)} matches the board")
            return 0

        extra = ["--assembly", args.assembly] if args.assembly else BOARD_CHECK_ARGS.get(rel(board), [])
        ok, result, report = board_check(board, extra)
        print(f"board check: {result}")
        if not ok:
            if not args.ignore_check_errors:
                print(report.rstrip())
                print("\nNo zip written: the board check has errors. Fix them, or rerun with --ignore-check-errors "
                      "if the user has accepted them.")
                return 1
            print("writing the zip anyway (--ignore-check-errors)")

        os.makedirs(os.path.dirname(zip_path), exist_ok=True)
        fd, partial = tempfile.mkstemp(suffix=".zip.partial", dir=os.path.dirname(zip_path))
        os.close(fd)
        try:
            with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as z:
                for name in sorted(files):
                    z.write(os.path.join(tmp, name), name)
            os.replace(partial, zip_path)
        finally:
            if os.path.exists(partial):
                os.remove(partial)

        stem = os.path.splitext(os.path.basename(board))[0]
        w, h = outline_size(os.path.join(tmp, layer_file(stem, "Edge.Cuts", "gm1")))
        pth = drill_summary(os.path.join(tmp, f"{stem}-PTH.drl"))
        npth = drill_summary(os.path.join(tmp, f"{stem}-NPTH.drl"))

    print(f"wrote {rel(zip_path)}  ({len(files)} files, {os.path.getsize(zip_path) // 1024} kB)")
    for name in sorted(files):
        print(f"  {name:<34s} {files[name]}")
    print(f"board outline {w:.2f} x {h:.2f} mm, {len(copper_layers(pcb_text))} copper layers")
    for label, (holes, slots, smallest) in (("plated", pth), ("non-plated", npth)):
        if holes or slots:
            print(f"{label} holes: {holes}" + (f" + {slots} slots" if slots else "") +
                  (f", smallest {smallest:.3f} mm ({smallest / 0.0254:.1f} mil)" if smallest else ""))
    print(f"from commit {head}" + (" with uncommitted changes to the board" if dirty else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
