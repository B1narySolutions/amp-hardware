# KiCad board tools

Scripts for looking at, checking and editing the KiCad boards in this repo from the command line.
Claude Code uses them through the skills in `.claude/skills/`, and they work just as well by hand.

| Tool | What it does |
|---|---|
| `board_view.py` | Renders a board to PNG: real pad shapes, tracks to scale, vias, silkscreen, labels and the ratsnest. Zooms to a window or to parts |
| `board_check.py` | Runs the project's DRC and schematic parity, then checks the board against JLCPCB's fabrication and assembly limits |
| `boardedit.py` | Python library for scripted, incremental edits: placing parts, adding tracks and vias, GND vias with stubs, net changes, removing selected tracks and placing labels |

Supporting files: `board_dump.py` exports a board to JSON for the viewer and checker; `jlcpcb.py` holds JLC's numbers, their sources and the KiCad rules built from them; `kicadenv.py` finds KiCad.

## Requirements

- KiCad 10 (tested with 10.0.5). The tools find its Python and `kicad-cli` in the default macOS install. Elsewhere, set
  `KICAD_PYTHON` (a Python that can `import pcbnew`; on Windows, KiCad's `bin\python.exe`) and `KICAD_CLI`.
- `python3` with matplotlib for the viewer (`pip3 install matplotlib`). The checker only needs the standard library.

`board_view.py` and `board_check.py` run under the system `python3` and call KiCad's Python for anything that needs `pcbnew`.
`boardedit.py` is imported by a script you run under KiCad's Python.

## Coordinates

Everything is in mm, in KiCad's board coordinates: the numbers the PCB editor shows and DRC reports use, with y growing downwards.
Rotation follows KiCad (+90 is counter-clockwise): a 2-pad part at 0° has pad 1 on the left, at 180° on the right, at 90° below
pad 2 and at −90° above it.

## View

```bash
python3 tools/kicad/board_view.py audio-board/rev2/seed3-carrier.kicad_pcb -o /tmp/board.png
python3 tools/kicad/board_view.py audio-board/rev2/seed3-carrier.kicad_pcb --around U2,C9 --margin 2 -o /tmp/u2.png
python3 tools/kicad/board_view.py audio-board/rev2/seed3-carrier.kicad_pcb --zoom 150,190,50,80 --net-names
```

Pads: GND green, power red (a net class named like "Power", or `+5V`-style names), other nets yellow, no net grey.
Tracks: F.Cu red, B.Cu blue, inner layers purple. Purple boxes are reference labels where KiCad places them.
The thin coloured lines are KiCad's own unrouted connections, taken from DRC. `--no-ratsnest` skips DRC for a faster render.
`--side B` shows the bottom silkscreen and SMD pads.

## Check

```bash
python3 tools/kicad/board_check.py audio-board/rev2/seed3-carrier.kicad_pcb
python3 tools/kicad/board_check.py board.kicad_pcb --assembly standard --mask-color black -v --json report.json
```

It never modifies the board. It runs four passes:

1. **Project DRC:** `kicad-cli` DRC with the project's own rules and zones refilled in memory, plus schematic parity when
   `<board>.kicad_sch` sits next to the board. Severities are the project's.
2. **JLC limits:** DRC on a temporary copy whose only rules are JLC's capability limits (track, space, drills, annular rings,
   hole spacing, hole-to-copper, copper-to-edge, SMD pad spacing). These are **errors**: the board can't be built as drawn.
3. **JLC recommended:** the same with JLC's preferred values and silkscreen legibility limits (1.0 mm text, 0.15 mm strokes,
   0.15 mm silk-to-pad, solder mask web). These are **warnings**: JLC builds the board, but it may print poorly or yield worse.
4. **Checks DRC can't express:** board size and thickness, slot widths, silk line widths and text proportions. For JLC
   assembly (`--assembly economic`, the default, or `standard`; `none` skips these): component body at least 2.5 mm from the
   edge, single-sided placement for Economic, no package smaller than 0402 for Economic, IC pin pitch, an LCSC part number on
   every assembled part, and open vias in pads.

Unrouted connections are errors unless `--allow-unrouted`. The exit status is 1 when there are errors (`--strict` counts
warnings too), so the checker can gate a commit or CI.

The JLC numbers live in `jlcpcb.py` with their sources and the date they were read. JLC updates its capability pages: re-check
them before ordering, and update `jlcpcb.py` when they change. Outer copper weight comes from the stackup (2 oz tightens the
track, space and annular limits).

## Edit

```python
# run with KiCad's Python, e.g.
# /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 my_edit.py
import sys; sys.path.insert(0, "tools/kicad")
from boardedit import Board

# Illustration: C1, R5, U3 and the nets stand for whatever the change needs.
b = Board("path/to/board.kicad_pcb")
b.place("C1", 120.0, 80.0, rot=-90)                   # immediate
b.gnd_via("C1", "2", dx=0, dy=1.4)                    # via plus a 0.5 mm stub from the pad
b.track("/SIG", [b.pad("R5", "2"), (124.0, 82.0), b.pad("U3", "3")], width=0.25)
b.remove_tracks(nets=["/SIG"], region=(110, 70, 130, 90))
b.set_pad_net("U3", "7", "/NEW_NET")                  # creates the net if needed; None = unconnected
b.auto_labels(["C1"])                                 # or label("C1", x, y)
print(b.save())                                       # writes the file, then refills zones
```

- **Incremental:** it only changes what you name. `remove_tracks` needs a filter (`nets`, `layers`, `region`; `nets=["*"]` means
  every net), so a script can't silently wipe the routing.
- **One `Board` per process.** In KiCad 10's Python bindings, once anything is added to or removed from a board, pcbnew objects
  read afterwards come back as bare `SwigPyObject`s, even from boards loaded later. `Board` therefore reads everything first,
  applies placements at once, and applies every add and remove in `save()`. After `save()`, start a new process.
- `FindNet()` is unreliable in the same way, so nets come from the pads, tracks and zones that use them. A net nothing uses yet
  can only be created through `set_pad_net`.
- `pcbnew.ZONE_FILLER` crashes without a GUI, so `save()` refills zones with `kicad-cli pcb drc --refill-zones --save-board`.
- `auto_labels` tests real silkscreen shapes, not bounding boxes. A label that finds no clear spot is reported in the return
  value; place it with `label()`.

Work on a copy or a clean git tree, then view and check the result before committing.
