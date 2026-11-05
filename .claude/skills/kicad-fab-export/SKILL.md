---
name: kicad-fab-export
description: Export a KiCad board as the zip of Gerbers and drill files JLCPCB takes, with tools/kicad/fab_export.py, and look at the result with tools/kicad/gerber_view.py. The export runs the board check first, exports with fixed settings from JLC's KiCad guide, checks the files fit together (layers present, all inside the outline, plated holes on copper) and reports the board size and hole sizes; --check says whether a committed zip still matches the board. gerber_view renders the zip as the fab will make it (top and bottom composites, each layer). Use when the user asks for Gerbers, a fab zip or files to order a board, after a board change on a board that has a committed fab zip, or when check_all reports a stale fab zip.
---

# Export a board for JLCPCB

```bash
uv run tools/kicad/fab_export.py <board.kicad_pcb>                  # board check, then write the zip
uv run tools/kicad/fab_export.py <board.kicad_pcb> --check          # does the committed zip match the board?
uv run tools/kicad/fab_export.py <board.kicad_pcb> -o <scratch>/x.zip   # a zip somewhere else (e.g. to try something)
uv run tools/kicad/fab_export.py <board.kicad_pcb> --paste          # add paste layers: only for a stencil or JLC assembly
```

The zip goes where `FAB_ZIPS` in `tools/check_all.py` says (the carrier's is `audio-board/rev2/fab/B1NARY_SOLUTIONS_gerber.zip`,
the name the capstone manual asks for), else to `<board folder>/fab/<name>_gerber.zip`. To give a new board a fixed
name, add it to `FAB_ZIPS`; check_all then checks that zip too. The script never modifies the board, and the zip is
the only file it writes. It takes about 7 s.

What it does, so you don't have to:
- Runs `board_check.py` with the board's options from `check_all.py` (the carrier uses `--assembly none`) and writes
  nothing if the check has errors.
- Exports every copper layer, both mask and silkscreen layers and Edge.Cuts, plus PTH and NPTH Excellon files, with
  fixed settings (no X2, Protel extensions, silkscreen clipped at mask openings, zones refilled, mm, slots as G85).
  It ignores the plot settings saved in KiCad's GUI, so the zip is the same whoever runs it.
- Leaves out the paste layers by default: the carrier is hand-soldered and JLC doesn't need them for a bare board.

Reading the output and reporting it:
- Give the user the zip path, the board outline size, the layer count and the smallest plated hole. JLC prices boards
  up to 100 x 100 mm at the cheapest rate, and the capstone fab needs every hole to be at least 13 mil (0.33 mm).
- "board check: Result: PASS (0 errors, N warnings)" is the same check as the `kicad-board-check` skill. About 23
  warnings are expected on the carrier (21 connector silk at the edge, 2 silk widths on footprints).
- A note that the board is open in KiCad means unsaved edits there aren't in the zip. Ask the user to save first.
- "with uncommitted changes to the board" means the zip shows a board state that isn't committed yet. Commit the
  board and the zip together.

Rules:
- If the board check fails, show the errors and fix them (or ask). Use `--ignore-check-errors` only when the user
  says to export anyway, and say so in the commit message.
- After any board change on a board listed in `FAB_ZIPS`, re-export, and commit the zip with the board change.
  `uv run tools/check_all.py` fails with "fab zip ... STALE" until you do. Don't edit the files in the zip by hand.
- Don't change the export settings in `fab_export.py` to get a different result for one order. If JLC or the
  capstone fab asks for something different, tell the user and change the script for every board.
- Before the user uploads it, suggest they check JLC's online Gerber viewer on the order page. It shows the board as
  JLC reads it, and it's the last chance to catch a missing layer or a wrong outline.

## Looking at the zip

`fab_export.py` already runs `gerber_view.py`'s checks on every zip before writing it ("gerber check: Result: ..."). To
see the board as the fab will make it, render the zip and open the PNGs with the Read tool:

```bash
uv run tools/kicad/gerber_view.py audio-board/rev2/fab/B1NARY_SOLUTIONS_gerber.zip -o <scratch>/gerbers
```

- `top.png`: green mask, gold where the mask opens over copper, tan for bare board in a mask opening, white silk,
  black holes. `bottom.png` is the underside, mirrored as you'd see it with the board flipped. One PNG per layer and
  `drills.png` show each file alone.
- Look for: every pad gold (not green: a missing mask opening), silkscreen clear of pads (the export clips it at mask
  openings), the B.Cu ground pour and the back credits present, holes centred in their pads, nothing outside the outline.
- The checks: every layer present, the outline closed, copper, mask and drills inside it, and every plated hole on
  copper on both sides. A FAIL means the zip is wrong; don't upload it. The carrier has one expected note: F.Silkscreen
  extends past the outline (J1's panel-nose outline, 9 mm past the front edge, and connector silk at the edges). JLC
  clips silk at the board edge.
