# Rev 3 changes

What changed from audio board rev 2 (`../rev2/`) and power board rev 1 (`../../power-board/`), and why, in one or two lines
each. `DESIGN.md` describes the current design in full. Keep this list to the net difference from those two boards.
Designators are rev 3's: sheet 1 keeps rev 2's, sheet 2 is power rev 1's plus 100 (see "Designators").

## One board
- **Audio rev 2 and power rev 1 are one board,** 100 × 78 mm, 4 layers. They were a 90 × 56.5 mm 2-layer board and a
  98 × 98 mm 2-layer board joined by screw terminals and wires.
- **Schematic:** sheet 1 is rev 2's audio sheet. Sheet 2 (`power.kicad_sch`) is power rev 1's sheet with every designator +100,
  joined to sheet 1 by six sheet pins: `+5V_AUDIO` (sheet 1's `+5V`, rev 2's `5V_IN`), `BATT_SENSE`, `SPK_MUTE`, `LINE_OUT`, `LINE_REF` and the
  new `AMP_FAULTZ`.
- **Sheet 2 redrawn** on A3 in signal-flow blocks, with wires in place of most labels. Its nets take sheet 1's names
  (power rev 1's `BAT_MON`, `Line+` and `Line−` are now `BATT_SENSE`, `LINE_OUT` and `LINE_REF`). Value fields hold values,
  not descriptions (R105 `0R`, JP101/JP103 `BYPASS`, L101/L102 `10uH`); the notes on the sheet carry the reasons. U1's value is its ordered part number
  (TLV9061QDBVRQ1), and C104/C106 read 25 V, as the part they carry.
- **Removed: the four terminals between the boards:** audio J5 (speaker send) and J6 (power, battery level, mute), and power
  J3 and J4 (rev 1 numbers). Their nets join on the board.
- **The DFR0571 5 V buck stays off the board,** on J106 (its input) and J107 (its output), as on power rev 1.

## Circuit
- **Q102 (AO3401A) added** between J107 and `+5V_RAW`, gate to GND. A reversed 5 V source on J107 no longer puts −5 V on
  U103 or the display (power rev 1 had no protection at J7). The DFR0571's own swapped wires short its output instead,
  because its grounds are common.
- **J102's pins swapped:** pin 2 is SPK+ and pin 1 SPK−, so the speaker traces from L101/L102 don't cross. Marked on the
  silkscreen.
- **Removed: Q1, R23, R13 and R22.** Q1 (rev 2's 5 V reverse protection) is redundant with Q102, so FB101 feeds `+5V`
  directly. R23 (Q2's series resistor) guarded an inter-board wire that no longer exists. R13/R22 halved power rev 1's
  divider a second time; instead R102 is 100k (was 30k), so R102/R103 alone give VBAT / 11 on pin 25, the same firmware
  constant, from 9.1 kΩ.
- **F101 is a Bel 0683G3150-01** SMD slow-blow fuse (3.15 A, 2 kA DC interrupting) instead of a T3.15A 5 × 20 mm fuse in a
  Bulgin FX0457 holder: same rating, 12 × 4.65 mm instead of 36 × 13 mm. Soldered, not swappable.
- **C18 (100 pF C0G) added** from U1A's + input to GND: RF filtering at the op-amp pin against the display's Wi-Fi bursts.
- **JP106–JP108 added:** U101's AM2–AM0 reach GND through solder jumpers bridged in copper (on the back), instead of
  straight to GND. Cutting one moves the class D's switching frequency if it beats with U2's charge pump.
- **FB1 (BLM18HG601SN1D) added** between C1 and C2 on the guitar input: with C1 and C18 it blocks Wi-Fi RF before the board's
  input traces.
- **C2 is 47 nF C0G** (was 1 µF X7R): not microphonic at the 1 MΩ input. The input's high-pass moves from 0.16 Hz to 3.4 Hz.
- **C19/C20 (10 pF C0G) added** on `DISPLAY_UART_TX`/`DISPLAY_UART_RX`, the Daisy side of R8/R9: RF filtering on the display UART.
- **U2 has its own supply filter:** R29 (2.2 Ω) from `+5V` and C21 (10 µF) form `HP_5V` for U2's supply pins, so its
  charge pump stays off `+5V` (which also feeds U1, `VREF` and the Daisy).
- **C108/C109 are 470 nF C0G 1206** (were 1.5 µF X7R 1206): not microphonic at the speaker amp's inputs. Its high-pass moves
  from 1.7 Hz to 5.6 Hz.
- **FAULTZ reaches Daisy pin 32:** R114 (18k) to GND divides R112's pull-up to ≈ 3.2 V, through a sixth sheet pin, so the
  firmware can show a latched speaker fault. Power rev 1 left FAULTZ on a test point only.
- **J106 is a JST XH header** (S2B-XH-A, keyed) instead of a 2-way screw terminal like J107 beside it: the DFR0571's two
  wire pairs can no longer go in swapped, which put 12 V on the 5 V side through the module (power rev 1's J6/J7 allow it).
- **D102/D103 (BAT54H Schottkys) added** from U101's SDZ and MUTE to PVCC: at switch-off C125 and C124 held those pins
  above a falling PVCC and discharged into U101's unrated protection diodes.
- **R30 (1k) added** between `AMP_FAULTZ` and Daisy pin 32, in case the firmware drives the pin.
- **U2 is a TPA6130A2RTJR** (4 × 4 mm WQFN, I2C volume) instead of the MAX9722AEUE+ (TSSOP-16), since JLC assembles rev 3:
  3,842 at $0.99 on LCSC against 76 at $5.03. Signal on the − inputs through C10/C11 (now 470 nF C0G), + inputs to GND
  through C22/C23 (470 nF C0G); the gain resistors R25–R28 are gone, and the gain is set over I2C. New Daisy pins: 12/13
  (I2C1, R32/R33 2.2k pull-ups to `3V3_D`, pin 38) and 27 (`HP_SD`, R34 100k pull-down): U2 is off until the firmware
  enables it, and through every reset.
- **Nothing else changed electrically.** A netlist comparison against audio rev 2 and power rev 1 shows only the five joined
  nets, the four removed terminals, Q102, C18, FB1, C2's value, C19/C20, JP106–JP108, the removed Q1/R23/R13/R22, R102's
  value, F101's part, J102's swapped pins, R29/C21 (`HP_5V`), C108/C109's value, R114 and R30 with the `AMP_FAULTZ` link, D102/D103, J106's part, and the U2 block
  (U2, C10–C15, C22/C23, R32–R34, no R25–R28) with Daisy pins 12, 13, 27 and 38.

## Board
- **Black solder mask** on both sides, white silkscreen, set in the stackup. Choose them on JLC's order page too.
- **4 layers, JLC04161H-7628:** In1 is solid GND with no tracks; In2 is GND fill with the slow and DC nets that cross; B.Cu
  is GND with a PVCC pour under the class D. Rev 2's 2-layer hops stay, now over In1.
- **Layout:** the Daisy stands upright in the middle, USB on the rear edge, between the audio side (left and front) and the
  power side (right). The jacks stay on the front edge. Rev 2's input buffer block keeps its routing; the U2 block is new
  (QFN). The class D
  is near the right edge with L101 and L102 upright above and below its outputs and the speaker terminal between them; the
  switch terminal, fuse and 12 V jack run along the rear edge, and the 5 V and display terminals sit on the left edge.
- **Moved from rev 2:** J3 to the left edge, R8/R9/R24 next to it; the AUX sum, mute, sense and speaker-send parts beside the
  upright Daisy; C4 and C5 into the 5 V filter column; all four mounting holes and the fiducials.
- **Moved from power rev 1's arrangement:** the audio 5 V filter (FB101, JP101, JP102, C104, C105) now sits beside C5, at the
  analog rail's entry; R107 sits in the mute column; L101/L102 stand upright; C112 sits below U101.
- **U101:** nine vias in its exposed pad and ten under its body, a back-side mask opening under the pad, bootstrap caps at
  the output pins, and wide output traces. Power rev 1 routed the outputs at about 0.25 mm.
- **Rules:** a `HighCurrent` net class (1.5 mm) for the battery, PVCC, output and speaker nets, neck-down rules at U101 and
  U103, and the five new 5 V nets in `Power`. ERC excludes U101's two PBTL output ties, with the reason.
- **Passives resized for reflow:** resistors 0603 (R105 still 2512); capacitors 0603 up to 220 nF and 0805 from 680 nF; C7
  still 1210. KiCad's standard footprints replace the hand-solder ones. Values, positions and references are unchanged.
- **Silkscreen:** pin legends for every new terminal, and every test point's net beside its reference; the back-side credits give the board and revision, both designers, the course code and the date, set in
  Orbitron (SIL Open Font License), which is embedded in the board file so any KiCad plots it the same.

## Parts
- **The order** (`seed3-carrier-digikey.csv`) is the ordered build of rev 2 and rev 1 (`../../amp-digikey-order.csv`) with
  these changes: no four-way terminals and three fewer two-way ones (J106 is a JST XH header); Q102 in place of Q1 (one AO3401A); C18, FB1, C19/C20, R29, C21 and R114
  added; D102/D103 (NSVBAT54HT1G) and R30 added; U2 a TPA6130A2RTJR, with C22/C23 (470 nF C0G), R32/R33 (2.2k) and R34
  (100k) added, R25–R28 gone and C10/C11 470 nF C0G instead of 4.7 µF X5R; J106 a JST S2B-XH-A, with an XHP-2 housing and a pre-crimped lead for the
  module's cable; C108/C109 470 nF C0G; R13, R22 and R23 gone and R102 100k; the Bel 0683G SMD fuse in place of the FX0457 holder and its 5 × 20 mm fuse;
  and none of rev 1's experiment parts, which that build's spares cover.
- **New part numbers for every resized passive,** same value with equal or better rating, except C103 (10 µF 16 V X7R 0805). The 10k, 100k and 10 Ω resistors are Stackpole RMCF0603: YAGEO's
  0603 versions had none in stock.
- **LCSC numbers on every SMD part** for JLC assembly (JLC Basic equivalents for the commodity passives), with
  `jlc-assembly.kicad_jobset`, `jlc-rotations.csv` and the exported BOM and CPL in `fab/assembly/`. F101 is hand-soldered
  (no JLC stock) and left out of the CPL.

## Designators
Sheet 1 keeps rev 2's designators (`../rev2/CHANGES.md` maps them to rev 1). On sheet 2, every part is power rev 1's number
plus 100: U1 → U101, U3 → U103, Q1 → Q101, J1 → J101, R5 → R105, TP9 → TP109 and so on. Q102, D102, D103, R114 and JP106–JP108 are new. Power rev 1's J3 and J4
are gone; U102 is the off-board DFR0571 (no footprint).
