---
name: kicad-schematic
description: Look at and change a KiCad schematic (.kicad_sch) in this repo. tools/kicad/sch_view.py renders the sheet to PNG, whole or zoomed to symbols or a window, and lists any part's pin nets from KiCad's own netlist. Covers checking connections, changing values and part fields (MPN, DigiKey, Voltage, Dielectric), and keeping the board, spec, DESIGN.md, TEST_PLAN.md and the DigiKey order in step. Use whenever you need to see or read the schematic, before and after any schematic change, or when the user asks how part of the circuit is wired.
---

# Look at and change a schematic

```bash
uv run tools/kicad/sch_view.py <board>.kicad_sch -o <scratch>/sheet.png                  # the whole sheet
uv run tools/kicad/sch_view.py <board>.kicad_sch --around U2,C13 -o <scratch>/u2.png      # zoomed to symbols
uv run tools/kicad/sch_view.py <board>.kicad_sch --zoom 250,330,60,110 -o <scratch>/a.png # window, sheet mm
uv run tools/kicad/sch_view.py <board>.kicad_sch --pins U2                               # each pin's net
```

Open the PNG with the Read tool. Write PNGs to your scratchpad, not the repo. The drawing is KiCad's own PDF plot, so
it matches the editor. Coordinates are sheet mm from the top-left, y down. The whole A3 sheet shows every block and
its labels, but small values and pin numbers are hard to read at that size: find the area, then zoom. `--around` frames the symbols' bodies, pins and visible fields (`--margin`
widens it). It only knows the root sheet; on a hierarchical design use `--page` and `--zoom` for the others.

**Check connections with `--pins`, not by eye.** It reads KiCad's netlist, the same one the board and the circuit check
use, so a wire that looks connected but isn't (a missing junction, a label one character off, a pin end a grid step
away) shows up as a separate net. Unnamed nets read like `Net-(C2-Pad2)`.

## Changing the schematic

- **The schematic must not be open in KiCad's schematic editor.** It writes `~<board>.kicad_sch.lck` beside the file
  while it's open; if that exists, ask the user to close it. Start from a clean git tree, so the change is its own
  diff. Only one session edits a schematic at a time (CLAUDE.md).
- **Field changes** (Value, MPN, Manufacturer, DigiKey, Voltage, Dielectric, Datasheet) are safe to make in the
  `.kicad_sch` text with Edit: find the symbol by its `(property "Reference" "C2"` line and change the property in that
  block only. Every part has MPN, Manufacturer, DigiKey and Datasheet fields (DESIGN.md "Parts sourcing"); keep them
  consistent with each other.
- **Wiring changes, new symbols and new sheets** are easier and safer in KiCad's editor. Describe the change for the
  user, with the pins and nets from `--pins`, unless they ask you to make it. If you do edit wiring in the text, wires
  must end exactly on pin ends (1.27 mm grid), a T junction needs a `(junction ...)`, and a new symbol needs its
  library symbol in the file's `lib_symbols`. Check every touched net with `--pins` afterwards.
- **Before and after:** render the area (`--around`) before the change and again after it, and look at both. Check
  that no text overlaps a wire or another label.

Conventions on this sheet: values without the unit for resistors (`10k`, `1M`, `470`) and with it for capacitors
(`1uF`, `100pF`); a capacitor's voltage in its Voltage field or in the value (`47uF 16V`); GND symbols point down and
`+5V` up; decoupling caps drawn beside the pin they serve; each subcircuit in a dashed box with a bold title and a
short note saying what its parts do. A change that alters what a note says changes the note too.

## After a change, keep everything in step

1. `uv run tools/check_all.py`: the circuit check reads the schematic, and the board check's parity pass compares it
   with the board.
2. **The board:** a new part, footprint or pinout goes onto the board with the `kicad-board-edit` skill
   (`add_footprint`/`replace_footprint` read the schematic). A value or field change reaches the board through
   `set_field`, or the user's "Update PCB from Schematic".
3. **The spec** (`<board>.verify.py`): a new part with a pin limit needs a model in `tools/kicad/parts/`; a new audio
   net goes into `spec.audio(...)`; a new capacitor's MPN goes into `parts/passives_mpn.py` if the check can't read its
   dielectric.
4. **The documents:** DESIGN.md when the design or its reasons change, TEST_PLAN.md when a reading changes (the
   circuit check says which), and the DigiKey order (`seed3-carrier-digikey.csv`) when a part number changes. Don't
   edit the order on its own: the schematic is the source.
5. Commit with the check results in the message (CLAUDE.md).
