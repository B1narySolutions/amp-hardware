---
name: kicad-board-check
description: Check a KiCad PCB against its own DRC, schematic parity and JLCPCB's fabrication and assembly rules (track/space, drills, annular rings, hole spacing, edge clearance, silkscreen legibility, solder mask, body-to-edge 2.5 mm, Economic PCBA limits, LCSC part numbers, vias in pads). Use after every board edit, before committing board changes, and whenever the user asks if a board is ready to order or manufacturable at JLC.
---

# Check a KiCad board for JLCPCB

```bash
python3 tools/kicad/board_check.py <board.kicad_pcb>                      # Economic PCBA, green mask
python3 tools/kicad/board_check.py <board.kicad_pcb> --allow-unrouted     # mid-layout: unrouted becomes a warning
python3 tools/kicad/board_check.py <board.kicad_pcb> --assembly standard --mask-color black -v --json <scratch>/report.json
```

It never modifies the board and takes about 6 s. Exit status 1 means errors (`--strict` counts warnings too).

What the categories mean:
- `[JLC fab]` errors are outside JLC's stated capability: the board can't be built as drawn. Fix them.
- `[JLC fab]` / `[JLC silk]` / `[JLC mask]` warnings are below JLC's recommended or legibility values. JLC still builds the
  board. Report them, and fix them when the user wants the board to meet JLC's recommendations.
- `[JLC assembly]` applies to parts JLC places: SMD-attribute footprints that aren't DNP or excluded from position files.
  Choose `--assembly none` for a bare-board order.
- `[project DRC]` and `[parity]` are the project's own rules and the schematic. They're the same as KiCad's DRC dialog.

How to use the result:
- Quote the findings to the user with their locations (board mm), grouped as the tool prints them. Don't silently "fix"
  a design decision the docs record (e.g. the U2 exposed-pad vias in DESIGN.md are intentional and show as a via-in-pad
  warning). Say what each finding means and propose the fix.
- After fixing, rerun until the errors are gone. Use the `kicad-board-view` skill to look at the spots it names.
- The JLC numbers and their sources are in `tools/kicad/jlcpcb.py`, read from JLC's capability pages on 2026-10-27.
  If the user asks about a limit, cite that file. If JLC's pages may have changed, re-check them and update the file.
