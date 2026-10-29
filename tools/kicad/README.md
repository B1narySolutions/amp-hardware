# KiCad board tools

Scripts for looking at, checking and editing the KiCad boards in this repo from the command line.
Claude Code uses them through the skills in `.claude/skills/`, and they work just as well by hand.

| Tool | What it does |
|---|---|
| `board_view.py` | Renders a board to PNG: real pad shapes, tracks to scale, vias, silkscreen, labels and the ratsnest. Zooms to a window or to parts |
| `board_check.py` | Runs the project's DRC and schematic parity, then checks the board against JLCPCB's fabrication and assembly limits |
| `boardedit.py` | Python library for scripted, incremental edits: placing parts, adding tracks and vias, GND vias with stubs, net changes, removing selected tracks and placing labels |
| `circuit_verify.py` | Checks a schematic against what every part can take and what the design claims, for everything a spec says can reach the connectors: worst-case bounds on every voltage and current, then simulation for the results the bounds can't settle. Also checks interface contracts between boards and the test plan's expected readings |
| `circuit_faults.py` | Injects assembly faults one at a time (opens, shorts, wrong values, missing parts, solder bridges from the PCB) and reports what each damages and whether the test plan catches it |

Supporting files: `board_dump.py` exports a board to JSON for the viewer and checker; `jlcpcb.py` holds JLC's numbers, their sources and the KiCad rules built from them; `kicadenv.py` finds KiCad and resolves footprint libraries; `schnet.py` reads each part's footprint, fields, symbol link and pin nets from the schematic (through a kicad-cli netlist).
The circuit check is `circuit_spec.py` (the spec format), `circuit_bounds.py` (the bound engine), `circuit_sim.py` (the
simulator search), `parts/` (part models and passive ratings, shared by every board) and `test_circuit_verify.py`.
Contracts between boards live in `/interfaces/`.

## Requirements

- KiCad 10 (tested with 10.0.5). The tools find its Python and `kicad-cli` in the default macOS install. Elsewhere, set
  `KICAD_PYTHON` (a Python that can `import pcbnew`; on Windows, KiCad's `bin\python.exe`) and `KICAD_CLI`.
- `python3` with matplotlib for the viewer (`pip3 install matplotlib`). The board checker only needs the standard
  library; the circuit check needs numpy (`pip3 install numpy`). Its simulator is KiCad's own ngspice library
  (`libngspice`), loaded directly. Set `NGSPICE_LIB` to use another copy.

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
b.set_pad_net("U3", "7", "/NEW_NET")                  # creates the net if needed
b.set_pad_unconnected("U3", "8")                      # KiCad's unconnected-(U3-<pin>-Pad8) net
b.set_field("R5", "Value", "10k")                     # or any field, e.g. "LCSC"; immediate
b.replace_footprint("J5", x=185.4, y=69.0, rot=90)    # new footprint/pinout from the schematic
b.add_footprint("R21", 179.3, 66.9)                   # in the schematic, not yet on the board
b.remove_footprint("FB1")                             # and the copper hanging off its pads
b.text("LINE+", 185.4, 71.75)                         # free silkscreen text; move_text / remove_text
b.auto_labels(["C1"])                                 # or label("C1", x, y)
print(b.save())                                       # writes the file, then refills zones
```

- **Incremental:** it only changes what you name. `remove_tracks` needs a filter (`nets`, `layers`, `region`; `nets=["*"]` means
  every net), so a script can't silently wipe the routing.
- **One `Board` per process.** In KiCad 10's Python bindings, once anything is added to or removed from a board, pcbnew objects
  read afterwards come back as bare `SwigPyObject`s, even from boards loaded later. `Board` therefore reads everything first,
  applies placements at once, and applies every add and remove in `save()`. After `save()`, start a new process.
- `FindNet()` is unreliable in the same way, so nets come from the pads, tracks and zones that use them. A net nothing uses yet
  is created by `set_pad_net`, `add_footprint` or `replace_footprint`, and `track`/`via` can use it in the same script.
- **Footprints come from the schematic.** `add_footprint(ref, x, y)` and `replace_footprint(ref)` read the `.kicad_sch` next to the
  board (a kicad-cli netlist, so hierarchy and KiCad's net names come out exactly as "Update PCB from Schematic" sees them): the
  footprint named in the symbol's Footprint field, its value and fields (LCSC, Description, ...), the symbol link parity checks,
  and every pad's net and pin function. Edit the schematic first, then run the board script. Arguments override any of it;
  `link=False` skips the schematic (parity then reports the part). Libraries resolve through the project's and the user's
  `fp-lib-table`, then KiCad's stock footprint folder.
- `replace_footprint` keeps the old position, rotation, side and label size unless told otherwise. Like `remove_footprint`, it
  removes the copper attached to the old pads by default (`tracks=False` keeps it): each chain of track from a pad up to the next
  junction, via or other part's pad, and any via left with nothing else on it. Longer routes beyond a junction stay; clear them
  with `remove_tracks`. Free vias, such as an exposed pad's, aren't attached by track and stay too.
- `text`, `move_text` and `remove_text` handle free board text (pin names beside a terminal block, a revision mark). Text that
  appears more than once needs `near=(x, y)`. Back-side text is mirrored. `auto_labels` treats board text as an obstacle.
- `pcbnew.ZONE_FILLER` crashes without a GUI, so `save()` refills zones with `kicad-cli pcb drc --refill-zones --save-board`.
- `auto_labels` tests real silkscreen shapes, not bounding boxes. A label that finds no clear spot keeps its old position
  and is reported in the return value; place it with `label(ref, x, y)`. `label(ref, height=1.0, thickness=0.15)` resizes a
  label where it is.

Before editing, make sure the board isn't open in KiCad's PCB editor: the editor writes `~<board>.kicad_pcb.lck` beside an
open board, and would overwrite a scripted change on its next save. Work on a copy or a clean git tree, then view and check
the result before committing.

## Circuit check

```bash
python3 tools/kicad/circuit_verify.py audio-board/rev2/seed3-carrier.kicad_sch
python3 tools/kicad/circuit_verify.py board.kicad_sch -v --case "on*" --nets --json report.json
python3 tools/kicad/circuit_verify.py board.kicad_sch --sim-out /tmp/counterexamples   # keep each failing run's netlist
python3 tools/kicad/test_circuit_verify.py
```

DRC checks geometry; this checks electrical stress, the way a unit test checks code. It never modifies anything. The exit
status is 1 when a check fails or can't be proven. It takes about 3 s on the Seed3 carrier, simulation included.

It needs three things, kept apart so each can be reused:

1. **The schematic.** The netlist comes from `kicad-cli`, as in `schnet.py`. Resistors and capacitors are modelled from
   their values; ratings come from the Value ("47uF 16V"), a Voltage/Power/Tolerance field, `parts/passives_lcsc.py` by
   LCSC number, or the package.
2. **Part models** in `parts/`, one file per part, shared by every board. Each has `MATCH` (Value or MPN patterns), `SOURCE`
   (the datasheet and its sections) and `model(p)`, which describes the part with a few calls: `p.supply`, `p.limit` (absolute
   and operating limits per pin, optionally with protection diodes and their injection rating), `p.opamp`/`p.amp`,
   `p.clamp`/`p.tvs`, `p.switch` (MOSFETs), `p.drive` (outputs), `p.rail` and `p.min_load`. Use `p.powered` to model the
   part switched off. A value read from a datasheet gets its section in `source=`. A value you had to assume gets
   `assumed=True` and a reason, and `-v` lists every one.
3. **A spec** next to the schematic, `<board>.verify.py`. It is Python that builds a `Spec` (see `circuit_spec.py`):
   - `spec.rail(net, on)`: supply nets and their range while on (0 V while off).
   - `spec.port(pin, nominal, misuse, exposed)`: what the outside world can put on each connector pin. Sources are
     `dc(lo, hi)` (constant), `wave(lo, hi)` (any waveform, steps included), `tone(peak, band)` (a sine anywhere in the
     band), `load(r)` and `open_()`, each with a source resistance `r=` and, for inputs at the far end, `clamp=` and `i_max=`.
   - `spec.state(...)`: power states (rails on, parts powered another way, parts not fitted, port overrides).
   - `spec.config(ref, ...)`: firmware pin modes for parts that need them (the Daisy's GPIO).
   - `spec.claim(name, V(net) | I(part) | Gain(ports, net, f), lo, hi, cases)`: numbers the design depends on.
   - `spec.waive(check, cases, reason)`: accepted failures, each with its reason.
   - `spec.provides(iface, {signal: pin}, cases)`: signals this board drives under an interface contract (below).
   - `spec.test_stage(name, absent, rails, ports)`: a bring-up test stage, with its readings: `measure(id, a, b, expect)`
     for resistance on an unpowered stage, `voltage(id, a, expect)` on a powered one (`rails` is the bench supply).
   - `spec.fault_states`: the power states the fault check runs in.

Each power state is checked with every port at its nominal source, then once per misuse alternative (one fault at a time).
For each case it bounds every node and checks every pin limit, every protection-diode current, resistor power, capacitor
voltage (and reverse voltage on electrolytics), MOSFET channel current, output loads, port currents and the claims. It
also checks structure: parts with no model, exposed pins with no ESD diode on their net, and powered inputs with no DC path.

### What the verdicts mean

- **pass**: proven. No source inside the spec and no part inside its tolerance can break the limit.
- **FAIL**: the bound is tight, so some combination of sources and tolerances really does reach it (or gets arbitrarily
  close). Fix the circuit, change the spec if it is wrong, or waive the check with the reason.
- **UNPROVEN**: the bound crosses the limit, but it goes through a node held by a conducting clamp or an amplifier at its
  rail. There the check treats the node as any waveform inside the clamp's window, which is sound but can be far too
  pessimistic. The simulator then searches for a counterexample (below). A result stays UNPROVEN only with `--no-sim`,
  when ngspice isn't found, or when the quantity can't be simulated.
- **FAIL** with "simulation breaks it": the simulator found an input inside the spec that breaks the limit. The note
  gives the input and value, and `--sim-out` saves the run as a SPICE netlist you can open.
- **SEARCHED**: no simulated input broke the limit, and the note gives the worst one reached. This is evidence, not proof,
  so the static bound stays as the only guarantee. It doesn't fail the exit status.

### How the bounds are worked out

A case becomes a linear circuit, and each quantity is a sum over its sources. A constant source contributes its DC gain.
A tone contributes the largest |H(jω)| in its band. A `wave` contributes ∫|h(t)| dt, the impulse response's L1 norm: the exact
worst case over every waveform inside the range. That is why a coupling cap followed by a resistor to a bias can swing
twice the input's range (a long +U, then a step to −U), which no sine sweep shows. DC gains are evaluated at every corner of
the resistor tolerances, which is exact because each node voltage is monotonic in each resistor. Dynamic gains are
evaluated at every corner of up to 10 tolerant parts, and at 256 sampled corners beyond that (the report says so). Clamps
and amplifier rails are handled by substitution. A MOSFET whose gate can sit either side of its threshold is checked in
both states.

### Contracts between boards

A connector between two boards is a contract file in `/interfaces/` (`interfaces/carrier-power.py` for the Seed3 carrier
and the power board). For each signal it records which board drives it and what that board promises: a source with its
range and its source resistance, often as a range such as `r=(0, 10e3)`. A source-resistance range is checked at both
ends, like a part tolerance. Both boards' specs load the same file with `Interface.load(path)`:

- The receiving board uses `iface.source(name)` as its port assumption, so it checks itself against exactly what the
  other board promises.
- The driving board lists the signal in `spec.provides(...)`. The check then confirms, in the given cases, that the pin
  stays inside the promised range and that its source resistance (the highest |Z| looking into the board, the receiver
  removed) stays under the promised maximum.

When either side changes a number, rerunning both checks shows which board no longer holds its side.

### Test-plan readings

A spec can carry the bring-up test plan's DMM checks. Each reading with an `expect` is worked out from the schematic and
reported under "test plan", so a test plan that falls behind the schematic shows up as a FAIL. Resistance readings use the
resistors only: capacitors are charged, diodes and MOSFETs are off, nothing is powered. Voltage readings use the bound
engine in the stage's powered state. The schematic doesn't model a jack's internal switch, so a reading that depends on
one belongs in the stage only with the switch open.

### Fault check

```bash
python3 tools/kicad/circuit_faults.py audio-board/rev2/seed3-carrier.kicad_sch
python3 tools/kicad/circuit_faults.py board.kicad_sch -v --bridge-gap 0.3 --json faults.json
```

It injects one fault at a time:
- **Two-pin parts:** open or shorted.
- **Resistors:** a decade off (×10, ÷10).
- **Multi-pin parts:** missing.
- **Solder bridges:** between pads of different nets on the same copper layer, within `--bridge-gap` (0.4 mm) across
  parts or `--bridge-gap-part` (1.0 mm) within one part. These come from the `.kicad_pcb` next to the schematic, through
  `board_dump.py`.

For each fault it runs the circuit check in the spec's `fault_states`, with nominal sources and nominal part values (no
tolerance corners or simulation), in parallel across `--jobs` processes (the cores, up to 8): about 3 s for 200
faults on the carrier. It reports:
- **Damage:** a check the fault newly breaks is an absolute maximum or rating. A fault that ties two supplies together is
  damage by itself. One between two outputs of the same part is "possible", since that's outside the part's model.
- **Function only:** an operating range, a claim or a floating input.
- **No effect found.**
- **Caught by:** the test-plan readings the fault moves. A resistance moving by more than 10 %, or between open and
  connected, counts. So does a voltage leaving its expected band.

For each damaging fault nothing catches, it suggests one unpowered reading that would catch it, probed at a test point,
connector or socket pin where it can. The exit status is 1 while a damaging fault goes uncaught.

Limits: a part's own internal supplies (a charge pump's rails) are ideal sources in its model. A fault that would stop a
charge pump therefore doesn't move its rails, even though the powered test plan would see it.

### Speed

Almost none of the time goes into the numerical work itself (eigenvalues and solves on matrices of a few dozen rows). It
goes into the bookkeeping around it, so the engine is organised to avoid repeating it:
- **Per subcircuit:** each subcircuit keeps every tolerance corner stacked in one array. The worst-case gain for a sine
  is one numpy call over all corners and frequencies, and each quantity's transfer data is cached. A case that shares a
  subcircuit with an earlier one reuses it.
- **Per clamp and switch state:** the grouping into subcircuits, and which elements touch each node, are worked out
  once and kept, not redone for every quantity.
- **Fault check:** faults run in separate processes.

The real scaling limit is the number of tolerance corners: 2^n for n tolerant parts in one subcircuit. Exact
enumeration stops at 14 resistors (DC) and 10 parts (dynamic). Beyond that it samples, and the report says so.

### How the simulation works

`circuit_sim.py` writes the case's circuit as a SPICE netlist from the same elements, keeping only the part connected to
the quantity, cut at rails and sources. Clamps become diodes behind an offset source, and switches become
voltage-controlled switches. Op-amps become a transconductance into R ‖ C, giving their open-loop gain and gain-bandwidth
product (`gbw=` in the part model), then a soft limit at the model's rails. ngspice runs it through its C API.

Each unproven result gets a search. The seeds come from `Analysis.worst_input`, which says what drives the quantity
furthest in the linear circuit: the bang-bang waveform that reaches the L1 bound for `wave` sources, the worst frequency
with every tone peaking together, the extreme of each constant, and the worst tolerance corner. Around each seed it then
tries random variants (`--sim-budget`, default 12 per case): other frequencies, phases and amplitudes, square waves and
steps, other tolerance corners, and clamps at both ends of their voltage window. Tone runs start short and are
lengthened until the peak stops moving from one period to the next. A run that doesn't converge is retried with other
solver settings. Identical subcircuits in different switch branches share one search.

Limits: it models what datasheets give, so a model is only as good as its numbers. ESD and surge pulses
(kilovolts, nanoseconds) need layout parasitics, so they are only checked structurally. Static clamp currents are worked out
with the other diode clamps on the same circuit off, which mostly overstates them. A search only tries the inputs above,
so SEARCHED means no counterexample was found, not that none exists.
