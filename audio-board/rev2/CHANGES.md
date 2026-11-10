# Rev 2 changes

The net difference from rev 1, one or two lines each. `DESIGN.md` has the design and the reasons. Parts added and then
removed during rev 2 don't belong here (git has that history). Designators are rev 2's (see "Designators"); a part that
no longer exists is named by its rev 1 designator, marked "rev 1".

## Inputs
- **Pots removed (rev 1 RV1 input level, RV2 volume, RV3 tone, C10, C11).** Level, volume and tone move to the
  touchscreen. R1 (1M to `VREF`) now sets the 1 MΩ guitar load, and U1A runs at unity gain.
- **R20 (470 Ω) added after U1,** to limit current into the Daisy pin. Passive pickups only, so there is no pad.
- **Rev 1 R5 removed.** It sat in parallel with R1 and lowered the guitar load to ≈ 0.91 MΩ.
- **AUX input added (J2 → R3/R4 passive sum → `AUDIO_IN_2`),** with R5 (470 Ω to GND) and C3, and no buffer.

## Outputs
- **Headphone amp: TPA6111A2 → MAX9722A (DirectDrive, TSSOP-16),** at a gain of −1 set by R25–R28 (10k). It removes
  rev 1 C14/C15 (470 µF output caps), rev 1 R9–R16 and rev 1 C16.
- **Headphone buffer removed (the second op-amp of rev 1's dual U1, with rev 1 C5 and rev 1 R6).** The Seed3's output
  drives U2 through R10 directly.
- **U1: TLV9062 dual (SOIC-8) → TLV9061 single (SOT-23-5).** Only the guitar input still needs a buffer.
- **Speaker send driven by `AUDIO_OUT_2`** (R11/C16, R12, no buffer) instead of rev 1's tip-switch line out on the
  headphone jack, so the firmware mutes and levels the speaker separately.
- **¼" line out removed.** The sponsor doesn't ask for one, and recording to a DAW goes through the Daisy's USB-C.
- **J5 added:** a 2-way 3.5 mm screw terminal to the speaker amp's differential input, LINE+ (`LINE_OUT`) and LINE−
  (`LINE_REF`, GND through R21, 1k).
- **The headphone jack (J4) is now a Same Sky SJ3-35063AG,** with an isolated detect switch on `HP_DETECT`.

## Power and control
- **J6: 2-pin 5 V header → 4-way 3.5 mm screw terminal to the power board:** 5V, GND, battery sense and the speaker
  mute. Adds R13, R22, C17, Q2, R17 and R23. Q1 still provides reverse-polarity protection. The power switch is on the
  power board; power rev 1 has no low-battery cutoff.
- **Screw terminals for every board-to-board connection (J3, J5, J6),** each labelled on the silkscreen.
- **Output mute on the STM32's independent watchdog,** fed only from the audio callback. A reset stops the codec's
  clocks, which silences both outputs, and R17 holds the speaker amp muted.
- **U2's SHDN tied to `+5V`.** The headphone amp has no hardware mute, as in rev 1 (whose TPA6111A2 had SHUTDOWN tied to
  GND).
- **R18/R19 added: `+5V` sense on Daisy pin 22 (`5V_SENSE`),** so the firmware keeps the outputs silent while `+5V` is
  off and the Daisy runs from USB.
- **Display: J3 carries only the UART and GND.** The display takes its power from the power board. **R8/R9 (10k each)
  added** in series with the UART.
- **R22, R23 and R24 added against a 5 V wire on a signal terminal:** R13/R22 halve BAT, R23 limits Q2's current, and
  R24 divides RX with R9. R24 also lets the firmware tell when no display is connected.
- **Rev 1 C9 removed.** It sat on the same node as C5 and C4.
- **Rev 1 TP5, TP9, TP10 removed.** TP1 (`HP_DETECT`) is the only test point.

## Board
- **ESD diodes added (D1–D5, PESD5V0S1BA)** from every jack signal contact to GND: J1 tip, J2 tip/ring, J4 tip/ring.
- **New layout:** 2-layer, 90 × 56.5 mm, with GND pours on both sides tied by stitching vias, so it fits a free capstone
  fab (2 layers, under 100 × 100 mm). Every audio net stays on the top layer. The Daisy lies flat along the rear edge
  and every panel jack sits on the front edge. Three M2.5 mounting holes and three fiducials.
- **Every part hand-solderable with an iron:** 0805 and larger passives on hand-solder pads, SOT-23, SOD-323 and the
  TSSOP U2.
- **Parts sourced from DigiKey:** `MPN`, `Manufacturer`, `DigiKey` and `Datasheet` fields in the schematic, and
  `seed3-carrier-digikey.csv` as the order.
- **Re-annotated** in sheet order. R20–R28 were added afterwards and are numbered last. R14–R16, C8, C18 and FB1 were
  removed afterwards, which leaves gaps in the designators.

## Designators
Rev 2 was re-annotated on 2026-10-26. U1, U2 and A1 kept their numbers. Commits before then, and rev 1, use the old
numbers on the right. A part carried over from rev 1 had the same old number there.

| Rev 2 | Old |
|---|---|
| R1–R19 | R17, R1, R40, R41, R38, R8, R7, R43, R44, R2, R28, R4, R32, R33, R34, R35, R37, R45, R46 |
| C1–C18 | C1, C3, C31, C17, C18, C8, C7, C30, C2, C12, C13, C33, C35, C36, C34, C24, C28, C29 |
| J1–J6 | J1, J9, J4, J5, J8, J3 |
| Q1, Q2 | Q1, Q4 |
| TP1 | TP11 |
