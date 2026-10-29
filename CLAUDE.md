# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Hardware for a capstone guitar amp, in KiCad 10:
- `audio-board/rev2/` is the Seed3 carrier: a Daisy Seed3 (A1, socketed) with the guitar and AUX inputs, the headphone
  amp (U2, MAX9722A) and screw terminals to the power board and display. It is a 2-layer board, hand-soldered with an
  iron, with every part from DigiKey (`seed3-carrier-digikey.csv` is the order).
- `power-board/` has no KiCad project yet. Its README lists everything the carrier expects from it.
- `interfaces/carrier-power.py` is the contract between the two boards, in code. Both boards' circuit-check specs load it.
- `tools/kicad/` holds the scripts that view, check and edit boards, and the circuit checker. `tools/kicad/README.md`
  documents them in full.

## Commands

The tools run through `uv run`, which builds `.venv` from `pyproject.toml` and `uv.lock` (matplotlib and numpy) on first
use. They find KiCad 10 at `/Applications/KiCad` themselves. `kicad-cli` isn't on PATH, and `pcbnew` only imports under KiCad's bundled Python:
`/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`.

```bash
# Board: project DRC, schematic parity and JLC fab limits. The carrier is hand-assembled, so skip JLC's assembly rules.
uv run tools/kicad/board_check.py audio-board/rev2/seed3-carrier.kicad_pcb --assembly none

# Render the board to a PNG (write it to the scratchpad, not the repo)
uv run tools/kicad/board_view.py audio-board/rev2/seed3-carrier.kicad_pcb --around U2,C9 -o <scratch>/u2.png

# Circuit check: worst-case stress, design claims, the interface contract and the test plan's expected readings
uv run tools/kicad/circuit_verify.py audio-board/rev2/seed3-carrier.kicad_sch        # -v lists every check

# Assembly faults (opens, shorts, wrong values, solder bridges from the PCB): damage and test-plan coverage
uv run tools/kicad/circuit_faults.py audio-board/rev2/seed3-carrier.kicad_sch

# The circuit checker's own tests, all or one
uv run tools/kicad/test_circuit_verify.py
uv run python -c "import sys; sys.path.insert(0, 'tools/kicad'); import test_circuit_verify as t; t.test_values()"
```

Every checker exits 1 on a failure. Scripted board edits import `tools/kicad/boardedit.py` and run under KiCad's Python.
The `kicad-board-edit`, `kicad-board-view`, `kicad-board-check` and `kicad-circuit-verify` skills in `.claude/skills/`
explain how to use each tool and how to read its results.

## How the pieces fit together

**The circuit check** reads three inputs, kept apart so each can be reused:
1. **The schematic**, through a `kicad-cli` netlist (`schnet.py`).
2. **Part models** in `tools/kicad/parts/`, one file per part, shared by every board. Each takes its numbers from the
   datasheet, cites the section in `source=`, and marks any guessed number `assumed=True`. Every part except a resistor,
   capacitor or connector needs a model.
3. **The spec**, `<board>.verify.py`, next to the schematic. It holds the rails, what the outside world can put on each
   connector pin (nominal and misuse), the power states, firmware pin modes, the claims DESIGN.md depends on, waivers,
   and the test plan's DMM readings. The engine is `circuit_bounds.py`. `circuit_sim.py` runs ngspice to settle results
   the bounds can't prove.

`circuit_faults.py` reuses the same spec, and reads `.kicad_pcb` beside the schematic to find possible solder bridges.

**Documents and the spec must agree.** Keep these pairs in step when one changes:
- **`audio-board/rev2/DESIGN.md` and the spec.** DESIGN.md is the current design and the reasons for it, not its
  history. Each `spec.claim` and `spec.waive` cites a DESIGN.md section.
- **`audio-board/TEST_PLAN.md` and the spec.** The spec's `stage1.measure`/`stage2.voltage` lines mirror TEST_PLAN
  stages 1 and 2 by reading id. The circuit check fails when a reading no longer matches the schematic.
- **`power-board/README.md` and `interfaces/carrier-power.py`.** The README explains each number in the contract.
  The contract is shared with whoever designs the power board, so ask before changing it.
- **`audio-board/rev2/CHANGES.md`** records only the net difference from rev 1.

**KiCad libraries:** project footprints are in `audio-board/Seed3_Carrier.pretty` and symbols in
`audio-board/seed3-carrier.kicad_sym`. The tables in `rev2/` reach them through `${KIPRJMOD}/..`, so a copy of the
board outside `rev2/` reports `lib_footprint_issues`.

## Git workflow

- **Commit straight to `main` and push. Don't open PRs.** `main` isn't protected, and there's one committer.
- **Parallel sessions in worktrees** can't check out `main` (git allows a branch in only one worktree), so each uses a
  short-lived local branch. When its work is done, rebase it on `main`, fast-forward `main` to it
  (`git merge --ff-only`), push, and delete the branch.
- **Run sessions in parallel only when they touch different KiCad files.** `.kicad_pcb` and `.kicad_sch` files merge
  badly, so work on the same board or schematic goes one session at a time, on `main`.

## Working rules

- **After a schematic or board change,** run the board check, the circuit check and the fault check, and put their
  results in the commit message: errors, pass/fail counts, and anything new that's waived or failing.
- **Don't add a waiver on your own.** Add one only when the user agrees, or when DESIGN.md already records the decision.
  Don't change a port's assumed environment in the spec to make a check pass.
- **Before a scripted board edit,** make sure the board isn't open in KiCad: an open board has a
  `~seed3-carrier.kicad_pcb.lck` beside it. Use one `Board` per process. KiCad 10's bindings break after the first add
  or remove, so `boardedit` reads everything first and applies changes in `save()`.
- **Keep edit scripts in the scratchpad.** Never commit a script that replays a whole layout, because it would undo
  later edits made in KiCad.
- **Expected board-check warnings:** about 21 `silk_edge_clearance` warnings come from the edge-mounted connectors
  (J1–J6). Don't trim their footprints to clear them.
- **JLC's limits** are in `tools/kicad/jlcpcb.py`, with their sources and the date they were read.
