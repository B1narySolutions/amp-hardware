# Rev 3 changes

The net difference from audio board rev 2 (`../rev2/`) and power board rev 1 (`../../power-board/`), one or two lines
each. `DESIGN.md` has the reasons in full. Designators are rev 3's (see "Designators").

## One board
- **Audio rev 2 and power rev 1 are one board,** 100 × 78 mm, 4 layers. They were a 90 × 56.5 mm and a 98 × 98 mm
  2-layer board joined by screw terminals and wires.
- **Schematic:** sheet 1 is rev 2's audio sheet. Sheet 2 (`power.kicad_sch`) is power rev 1's sheet with every designator
  +100, joined by six sheet pins: `+5V_AUDIO` (sheet 1's `+5V`, rev 2's `5V_IN`), `BATT_SENSE`, `SPK_MUTE`, `LINE_OUT`,
  `LINE_REF` and the new `AMP_FAULTZ`.
- **Sheet 2 redrawn** on A3 in signal-flow blocks. Its nets take sheet 1's names (power rev 1's `BAT_MON`, `Line+` and
  `Line−` are `BATT_SENSE`, `LINE_OUT` and `LINE_REF`). Value fields hold values, not descriptions (R105 `0R`,
  JP101/JP103 `BYPASS`, L101/L102 `10uH`); U1's is its ordered part number, and C104/C106 read 25 V, as their part.
- **Removed: the four terminals between the boards:** audio J5 and J6, power J3 and J4 (rev 1 numbers).
- **The DFR0571 stays off the board,** on J106 (its input) and J107 (its output), as on power rev 1.

## Circuit
- **Q102 (AO3401A) added** between J107 and `+5V_RAW`, gate to GND: a reversed 5 V source on J107 no longer reaches U103
  or the display.
- **Removed: Q1, R23, R13 and R22.** Q102 covers Q1. R23 guarded an inter-board wire that is gone. R13/R22 halved the
  battery divider a second time; R102 is 100k instead (was 30k), so pin 25 still reads VBAT / 11, from 9.1 kΩ.
- **J102's pins swapped:** pin 2 is SPK+ and pin 1 SPK−, so the speaker traces don't cross.
- **F101 is a Bel 0683G3150-01** SMD slow-blow fuse (3.15 A) instead of a 5 × 20 mm fuse in a Bulgin FX0457 holder:
  same rating, 12 × 4.65 mm instead of 36 × 13 mm. Soldered, not swappable.
- **Guitar input RF filtering:** FB1 (BLM18HG601SN1D) added between C1 and C2, and C18 (100 pF C0G) at U1A's + input.
- **C2 is 47 nF C0G** (was 1 µF X7R): not microphonic at the 1 MΩ input. Its high-pass moves from 0.16 Hz to 3.4 Hz.
- **C19/C20 (10 pF C0G) added** on the display UART, the Daisy side of R8/R9.
- **U2 is a TPA6130A2RTJR** (WQFN, I2C volume) instead of the MAX9722AEUE+ (TSSOP), since JLC assembles rev 3. Signal on
  the − inputs through C10/C11 (now 470 nF C0G), + inputs to GND through C22/C23; R25–R28 are gone. New Daisy pins:
  12/13 (I2C1, R32/R33 pull-ups to `3V3_D`, pin 38) and 27 (`HP_SD`, R34 pull-down).
- **U2 has its own supply filter:** R29 (2.2 Ω) and C21 (10 µF) form `HP_5V`, keeping its charge pump off `+5V`.
- **C108/C109 are 470 nF C0G** (were 1.5 µF X7R, both 1206): not microphonic. The high-pass moves from 1.7 Hz to 5.6 Hz.
- **FAULTZ reaches Daisy pin 32** through the R112/R114 divider (≈ 3.2 V) and R30 (1k). Power rev 1 left it on a test
  point.
- **JP106–JP108 added:** U101's AM2–AM0 reach GND through cuttable jumpers, to move the switching frequency.
- **J106 is a keyed JST XH header** (S2B-XH-A) instead of a screw terminal: the DFR0571's two wire pairs can't be swapped.
- **D102/D103 (BAT54H) added** from U101's SDZ and MUTE to PVCC, for switch-off.
- **Nothing else changed electrically:** a netlist comparison against both boards shows only the changes above and the
  joined nets.

## Board
- **4 layers, JLC04161H-7628,** black mask, white silkscreen. In1 is solid GND; In2 is GND fill with the nets that cross
  the Daisy; B.Cu is GND with a PVCC pour under the class D.
- **Layout:** the Daisy stands upright in the middle, between the audio side (left and front) and the power side
  (right). Jacks on the front edge, battery entry on the rear edge, class D and speaker terminal on the right edge, 5 V
  and display terminals on the left edge. Rev 2's input buffer block keeps its routing; the U2 block is new.
- **U101:** nine vias in its exposed pad and ten under its body, a back-side mask opening, bootstrap caps at the output
  pins, and wide output traces (power rev 1's were about 0.25 mm).
- **Rules:** a `HighCurrent` net class (1.5 mm), neck-down rules at U101 and U103, and the new 5 V nets in `Power`. ERC
  excludes U101's two PBTL output ties, with the reason.
- **Passives resized for reflow:** resistors 0603 (R105 still 2512); capacitors 0603 up to 220 nF and 0805 from 680 nF;
  KiCad's standard footprints replace the hand-solder ones.
- **Silkscreen:** pin legends for every terminal and every test point's net; back-side credits in Orbitron (SIL Open
  Font License), embedded in the board file.

## Parts
- **The order** (`seed3-carrier-digikey.csv`) is the ordered build of rev 2 and rev 1 (`../../amp-digikey-order.csv`)
  with the circuit changes above, new part numbers for the resized passives, and none of rev 1's experiment parts.
- **LCSC numbers on every SMD part** for JLC assembly, with `jlc-assembly.kicad_jobset`, `jlc-rotations.csv` and the
  exported BOM and CPL in `fab/assembly/`. F101 is hand-soldered and left out of the CPL.

## Designators
Sheet 1 keeps rev 2's designators (`../rev2/CHANGES.md` maps them to rev 1). On sheet 2, every part is power rev 1's
number plus 100: U1 → U101, R5 → R105, TP9 → TP109 and so on. Q102, D102, D103, R114 and JP106–JP108 are new. Power rev
1's J3 and J4 are gone; U102 is the off-board DFR0571 (no footprint).
