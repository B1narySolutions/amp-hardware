#!/usr/bin/env python3
"""Run every check in the repo and print one summary line each.

    uv run tools/check_all.py                 # every board
    uv run tools/check_all.py audio-board     # only boards under this folder
    uv run tools/check_all.py --full          # also print each check's whole report

For every .kicad_pcb: the board check (board_check.py). For every schematic with a <stem>.verify.py spec beside it: the
circuit check (circuit_verify.py) and the fault check (circuit_faults.py). Then the circuit checker's own tests. A
failing check's whole report is printed after the summary. Exits 1 if any check fails.

The summary lines are what CLAUDE.md asks for in the commit message after a board or schematic change.
"""
import argparse
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KICAD_TOOLS = os.path.join(ROOT, "tools", "kicad")

# board_check.py options per board, relative to the repo root. Boards not listed use its defaults (JLC Economic PCBA).
BOARD_CHECK_ARGS = {
    "audio-board/rev2/seed3-carrier.kicad_pcb": ["--assembly", "none"],   # hand-soldered, parts from DigiKey
}


def find(suffix, under):
    """Files ending in suffix under these folders, skipping hidden folders and KiCad's backups."""
    found = []
    for top in under:
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and not d.endswith("-backups"))
            found += [os.path.join(dirpath, f) for f in sorted(filenames) if f.endswith(suffix)]
    return found


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def board_summary(out):
    m = re.search(r"^Result: .*$", out, re.M)
    return m.group(0) if m else None


def circuit_summary(out):
    tags = re.findall(r"^(FAIL|UNPROVEN|SEARCHED|WARN|waived) ", out, re.M)
    passed = re.search(r"^(\d+) checks pass", out, re.M)
    if not passed:
        return None
    parts = [f"{passed.group(1)} pass"]
    for tag in ("FAIL", "UNPROVEN", "SEARCHED", "WARN", "waived"):
        if tags.count(tag):
            parts.append(f"{tags.count(tag)} {tag.lower()}")
    return ", ".join(parts)


def faults_summary(out):
    damage = re.search(r"^Damage \((\d+)\)", out, re.M)
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    if not lines:
        return None
    return (f"{damage.group(1)} damaging faults; " if damage else "") + lines[-1]


def tests_summary(out):
    m = re.search(r"^\d+ tests passed$", out, re.M)
    return m.group(0) if m else None


def run(name, width, script, args, summarize):
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(KICAD_TOOLS, script), *args], cwd=ROOT,
                       capture_output=True, text=True)
    out = r.stdout + (("\n" + r.stderr) if r.stderr.strip() else "")
    summary = summarize(r.stdout) or (r.stderr.strip().splitlines() or ["no output"])[-1]
    ok = r.returncode == 0
    print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}s} {summary}  ({time.time() - t0:.0f} s)", flush=True)
    return ok, name, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("under", nargs="*", help="only check boards under these folders (default: the whole repo)")
    ap.add_argument("--full", action="store_true", help="print every check's whole report, not just the failures'")
    args = ap.parse_args()

    under = [os.path.abspath(u) for u in args.under] or [ROOT]
    boards = find(".kicad_pcb", under)
    specs = find(".verify.py", under)
    if not boards and not specs:
        sys.exit(f"No .kicad_pcb or .verify.py under {', '.join(args.under) or 'the repo'}")

    jobs = [(f"board check {rel(pcb)}", "board_check.py", [rel(pcb), *BOARD_CHECK_ARGS.get(rel(pcb), [])],
             board_summary) for pcb in boards]
    for spec in specs:
        sch = rel(spec[: -len(".verify.py")] + ".kicad_sch")
        jobs += [(f"circuit check {sch}", "circuit_verify.py", [sch], circuit_summary),
                 (f"fault check {sch}", "circuit_faults.py", [sch], faults_summary)]
    jobs.append(("circuit checker tests", "test_circuit_verify.py", [], tests_summary))
    width = max(len(j[0]) for j in jobs)
    results = [run(name, width, *rest) for name, *rest in jobs]

    failed = [r for r in results if not r[0]]
    for ok, name, out in results:
        if args.full or not ok:
            print(f"\n{'=' * 20} {name}\n{out.rstrip()}")
    print(f"\n{len(results) - len(failed)} of {len(results)} checks pass" + (f"; failed: {', '.join(n for _, n, _ in failed)}"
                                                                           if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
