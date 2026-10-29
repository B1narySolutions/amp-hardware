---
name: kicad-board-view
description: Render a KiCad PCB (.kicad_pcb) to a PNG you can look at, whole or zoomed to parts or a window, with real pad shapes, tracks, vias, silkscreen labels and the unrouted ratsnest. Use whenever you need to see a board in this repo — before planning placement or routing, after any scripted edit, or when the user asks how part of the board looks.
---

# View a KiCad board

Render with `tools/kicad/board_view.py` (through `uv run`, which supplies matplotlib; it calls KiCad's Python itself), then
open the PNG with the Read tool. Write PNGs to your scratchpad, not the repo.

```bash
uv run tools/kicad/board_view.py <board.kicad_pcb> -o <scratch>/board.png                  # whole board
uv run tools/kicad/board_view.py <board.kicad_pcb> --around U2,C9 --margin 2 -o <scratch>/u2.png
uv run tools/kicad/board_view.py <board.kicad_pcb> --zoom X0,X1,Y0,Y1 --net-names -o <scratch>/area.png
```

Reading the image:
- Coordinates are KiCad board mm, y down: the same numbers DRC reports and `boardedit.py` takes.
- Pads: GND green, power red, other nets yellow, unconnected grey; white circles or slots are drills.
- Tracks: F.Cu red, B.Cu blue, inner purple, drawn at true width. Vias: green for GND, grey otherwise.
- Purple boxes are reference labels where KiCad actually puts them. Dashed grey boxes are courtyards.
- Thin coloured lines are KiCad's own unrouted connections (from DRC). `--net-names` labels them.

Tips:
- Zoom whenever you need to judge clearances or pin-level routing. The whole-board view is for floor planning.
- `--no-ratsnest` skips DRC (about 2 s faster). `--side B` shows the bottom side's silkscreen and SMD pads.
- `--json path` keeps the board dump (parts, pads with polygons and nets, tracks, vias, zones, outline). It's handy for
  measuring things in Python instead of by eye.

See `tools/kicad/README.md` for details. To check a board use the `kicad-board-check` skill, and to change one the
`kicad-board-edit` skill.
