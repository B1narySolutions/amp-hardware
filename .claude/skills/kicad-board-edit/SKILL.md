---
name: kicad-board-edit
description: Make scripted, incremental edits to a KiCad PCB with tools/kicad/boardedit.py — move or rotate parts, add tracks and vias, drop GND vias with stubs, change pad nets (e.g. a pin swap) or mark pads unconnected, add/replace/remove footprints straight from the schematic (new parts, new packages or connectors), set fields such as Value or LCSC, add/move/remove silkscreen text, remove selected tracks, place reference labels. Use when the user asks to change placement, routing or parts in a .kicad_pcb and the change is easier to script than to describe for the GUI.
---

# Edit a KiCad board by script

Write a short script that imports `tools/kicad/boardedit.py` and run it with **KiCad's** Python
(macOS: `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`).
Keep the script in your scratchpad: it describes one change, not the board. Never commit a script that replays a whole
layout, because it would undo every later edit made in KiCad.

```python
import sys; sys.path.insert(0, "tools/kicad")
from boardedit import Board

# Illustration: C1, R5, U3 and the nets stand for whatever the change needs.
b = Board("path/to/board.kicad_pcb")
b.place("C1", 120.0, 80.0, rot=-90)                        # mm, degrees; side="B" flips
b.track("/SIG", [b.pad("R5", "2"), (124.0, 82.0), b.pad("U3", "3")], width=0.25, layer="F.Cu")
b.via(124.0, 82.0, "/SIG")                                 # dia 0.6 / drill 0.3 by default
b.gnd_via("C1", "2", dx=0, dy=1.4)                         # via plus 0.5 mm stub from the pad
b.set_pad_net("U3", "7", "/NEW_NET")                       # creates the net if needed
b.set_pad_unconnected("U3", "8")                           # KiCad's unconnected-(U3-<pin>-Pad8) net
b.remove_tracks(nets=["/SIG"], region=(110, 70, 130, 90))  # needs a filter; nets=["*"] = all nets
b.replace_footprint("J5", x=185.4, y=69.0, rot=90)         # footprint, fields, link, pad nets from the schematic
b.add_footprint("R21", 179.3, 66.9)                        # a part that's in the schematic but not the board
b.remove_footprint("FB1")                                  # also removes the copper hanging off its pads
b.set_field("R9", "Value", "10k")                          # any field ("LCSC", ...); new ones are hidden
b.text("LINE+", 185.4, 71.75)                              # free silkscreen text; move_text/remove_text(s, near=)
b.auto_labels(["C1"], prefer={"C1": ["left"]})             # or b.label("C1", x, y); b.label("J1", height=1.0) resizes in place
print(b.save())                                            # writes the file, refills zones
```

Rules that keep this safe:
- **Before editing:** the board must not be open in KiCad's PCB editor, or KiCad will overwrite the change on its next save.
  The editor writes a lock file `~<board>.kicad_pcb.lck` beside the board while it's open. If that file exists, ask the user
  to close the board. A running KiCad with only the schematic open (`~<board>.kicad_sch.lck`) is fine for board-only edits. Start from a clean git tree, or commit
  first, so the edit is its own diff.
- **One `Board` per process.** pcbnew objects break for the rest of the process once anything is added or removed, so
  after `save()` run a new script to edit again. Read pad positions with `b.pad()` before `save()`.
- `track`/`via` need a net that exists on the board or that this script creates (`set_pad_net`, `add_footprint`,
  `replace_footprint`).
- Rotation: a 2-pad part at 0° has pad 1 on the left, at 180° on the right, at 90° below and at −90° above.
- Change the `.kicad_sch` first (new part, new footprint, pinout, value), then the board. `add_footprint` and
  `replace_footprint` read the schematic next to the board for the footprint, fields, symbol link and pad nets, the way
  KiCad's "Update PCB from Schematic" does, so parity holds. A pin swap made with `set_pad_net` must be made in the
  schematic too. Confirm with the check either way.
- `replace_footprint`/`remove_footprint` remove the copper on the old pads up to the next junction, via or part
  (`tracks=False` keeps it). Clear longer stale routes with `remove_tracks`, and re-route.

After every edit:
1. Look at it with the `kicad-board-view` skill (zoom on what changed).
2. Run the `kicad-board-check` skill. Use `--allow-unrouted` mid-layout, and get it free of new errors.
3. Update the design docs that describe placement or routing, if the repo has them (e.g. `DESIGN.md`), then commit.

Full API and the reasons behind these rules: `tools/kicad/README.md` and the docstrings in `boardedit.py`.
