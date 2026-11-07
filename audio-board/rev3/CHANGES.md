# Rev 3 changes

What changed from audio board rev 2 (`../rev2/`) and power board rev 1 (`../../power-board/`), and why, in one or two lines
each. `DESIGN.md` describes the current design in full. Keep this list to the net difference from those two boards.
Designators are rev 3's: sheet 1 keeps rev 2's, sheet 2 is power rev 1's plus 100 (see "Designators").

## One board
- **Audio rev 2 and power rev 1 are one board,** 122 × 78 mm, 4 layers. They were a 90 × 56.5 mm 2-layer board and a
  98 × 98 mm 2-layer board joined by screw terminals and wires.
- **Schematic:** sheet 1 is rev 2's audio sheet. Sheet 2 (`power.kicad_sch`) is power rev 1's sheet with every designator +100,
  joined to sheet 1 by five sheet pins: `5V_IN`, `BATT_SENSE_CONN`, `SPK_MUTE`, `LINE_OUT` and `LINE_REF`.
- **Removed: the four terminals between the boards:** audio J5 (speaker send) and J6 (power, battery level, mute), and power
  J3 and J4 (rev 1 numbers). Their nets join on the board.
- **The DFR0571 5 V buck stays off the board,** on J106 (its input) and J107 (its output), as on power rev 1.

## Circuit
- **Q102 (AO3401A) added** between J107 and `+5V_RAW`, gate to GND. A reversed 5 V source on J107 no longer puts −5 V on
  U103 or the display (power rev 1 had no protection at J7). The DFR0571's own swapped wires short its output instead,
  because its grounds are common. Q1 stays as it was.
- **J102's pins swapped:** pin 2 is SPK+ and pin 1 SPK−, so the speaker traces from L101/L102 don't cross. Marked on the
  silkscreen.
- **Nothing else changed electrically.** A netlist comparison against audio rev 2 and power rev 1 shows only the five joined
  nets, the four removed terminals and Q102.

## Board
- **Black solder mask** on both sides, white silkscreen, set in the stackup. Choose them on JLC's order page too.
- **4 layers, JLC04161H-7628:** In1 is solid GND with no tracks; In2 is GND fill with the slow and DC nets that cross; B.Cu
  is GND with a PVCC pour under the class D. Rev 2's 2-layer hops stay, now over In1.
- **Layout:** the Daisy stands upright in the middle, USB on the rear edge, between the audio side (left and front) and the
  power side (right). The jacks stay on the front edge. Rev 2's input buffer and U2 blocks keep their routing. The class D
  is at the right edge with the speaker terminal; the 12 V jack, fuse and switch terminal run along the rear edge, and the
  5 V and display terminals sit on the left edge.
- **Moved from rev 2:** J3 to the left edge, R8/R9/R24 next to it; the AUX sum, mute, sense and speaker-send parts beside the
  upright Daisy; Q1, C4 and C5 into the 5 V filter column; all four mounting holes and the fiducials.
- **Moved from power rev 1's arrangement:** the audio 5 V filter (FB101, JP101, JP102, C104, C105) now sits beside Q1, at the
  analog rail's entry, and R107 sits beside R23.
- **U101:** nine vias in its exposed pad and ten under its body, a back-side mask opening under the pad, bootstrap caps at
  the output pins, and wide output traces. Power rev 1 routed the outputs at about 0.25 mm.
- **Rules:** a `HighCurrent` net class (1.5 mm) for the battery, PVCC, output and speaker nets, neck-down rules at U101 and
  U103, and the five new 5 V nets in `Power`. ERC excludes U101's two PBTL output ties, with the reason.
- **Silkscreen:** pin legends for every new terminal, and every test point's net beside its reference; the back-side credits name both designers and rev 3, set in
  Orbitron (SIL Open Font License), which is embedded in the board file so any KiCad plots it the same.

## Parts
- **The order** (`seed3-carrier-digikey.csv`) is the ordered build of rev 2 and rev 1 (`../../amp-digikey-order.csv`) with
  three changes: no four-way terminals and two fewer two-way ones, one more AO3401A (Q102), and none of rev 1's experiment
  parts, which that build's spares cover.
- **C10/C11's DigiKey number** is DigiKey's renumbered listing, 1276-CL21A475KACLRNCCT-ND (same part).

## Designators
Sheet 1 keeps rev 2's designators (`../rev2/CHANGES.md` maps them to rev 1). On sheet 2, every part is power rev 1's number
plus 100: U1 → U101, U3 → U103, Q1 → Q101, J1 → J101, R5 → R105, TP9 → TP109 and so on. Q102 is new. Power rev 1's J3 and J4
are gone; U102 is the off-board DFR0571 (no footprint).
