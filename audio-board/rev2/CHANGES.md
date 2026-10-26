# Rev 2 changes

What changed from rev 1, and why, in one or two lines each. `DESIGN.md` describes the current design in full.
Keep this list to the net difference from rev 1. Parts that were added and then removed during rev 2 don't belong here (git has that history).
Designators are rev 2's (see "Designators" below). A part that no longer exists is named by its rev 1 designator, marked "rev 1".

## Inputs
- **Pots removed (rev 1 RV1 input level, RV2 volume, RV3 tone, C10, C11).** Level, volume and tone move to the touchscreen. With the
  input-level pot at mid travel, U1A saw about 250 kΩ of source impedance, which added noise and an ~80 kHz pole.
  R1 (1M to `VREF`) now sets the 1 MΩ guitar load, and U1A runs at unity gain.
- **Input pad added (R20/R21) after U1.** U1's 5 V swing (4.8 Vpp clean at J1) now reaches the Daisy at ≤ 3.4 Vpp, so neither
  passive nor active pickups can overdrive the Daisy pin. Passive pickups lose 3.9 dB of converter signal-to-noise.
- **Rev 1 R5 removed.** R1 biases U1A+ through R2, so rev 1 R5 only sat in parallel and lowered the guitar load to ≈ 0.91 MΩ.
- **AUX input added (J2 → passive sum → `AUDIO_IN_2`).** For backing tracks from a phone or laptop, mixed in after the amp model.
  No buffer: the Seed3's AC-coupled input loads the R3/R4 sum directly. R5 (3.3k to GND) sets the level whatever the module's
  unpublished input impedance is, so a 2 Vrms source can't exceed the Daisy's full scale, and is the DC return.

## Outputs
- **Headphone amp: TPA6111A2 → TPA6132A2 (DirectPath).** It removes rev 1 C14/C15 (470 µF output caps, the two largest parts in the
  headphone section), rev 1 R9–R16 and rev 1 C16, flattens the bass and adds click-and-pop suppression. Its gain is −6 dB (G0 and G1 to GND), so full
  scale doesn't clip 16 Ω headphones.
- **Headphone buffer removed (the second op-amp of rev 1's dual U1, with rev 1 C5 and rev 1 R6).** The Seed3's outputs drive U2 through R10 directly.
- **U1: TLV9062 dual (SOIC-8) → TLV9061 single (SOT-23-5).** Only the guitar input still needs a buffer.
- **Speaker / line send driven by `AUDIO_OUT_2`** (R11/C16, R12, no buffer; R11 is 1k, so the line out loses ≈ 0.9 dB into a 10k input) instead of rev 1's tip-switch line out on the headphone
  jack, which muted the ¼" line out mechanically. Muting the speaker amp in firmware saves battery, ramps without clicks, gives the
  speaker and headphones independent levels, and keeps J5 live with headphones in (record while monitoring).
- **R22 (0 Ω) in series with the line out.** If the Daisy's output turns out to carry DC, R22 is swapped for a 10 µF DC-blocking
  cap without a respin.
- **J6 added:** a keyed internal line out to the speaker amp. J5 stays as an external line out.
- **The headphone jack (J4) is now a Same Sky SJ3-35063AG,** with an isolated detect switch read by the firmware on `HP_DETECT`.

## Power and control
- **J7: 2-pin 5 V header → 8-pin JST-XH to the power board.** One connector for power, the power button, `PWR_HOLD`, battery sense and
  the speaker mute. Adds R13–R16, C17, C18, Q2 and R17. Q1 still provides reverse-polarity protection.
- **Output mute on the STM32's independent watchdog.** The IWDG resets the STM32 if the audio callback stops. The codec's clocks
  stop with it, so its DAC powers down and both outputs go silent. R17 holds the speaker amp off whenever the Daisy is absent, booting or reset.
- **Rev 1 R26 removed, U2's EN tied to `+5V`.** The headphone amp has no hardware mute. The codec does the muting, as it does for J5.
  Driving EN from the Daisy would need a level translator, because the Daisy can run from USB while `+5V` is off.
- **R18/R19 added: `+5V` sense on Daisy pin 22 (`5V_SENSE`).** On USB alone, `+5V` and U2's rails are off, and pin 18's audio would
  reach U2's inputs through C10/C11. The firmware keeps the outputs silent while `5V_SENSE` is low.
- **Display: FB1 and C8 added** to keep the display's current pulses off the analog rail, and **R8/R9 added** in series with the UART
  against miswiring and hot-plugging. R8 is 10k, to limit current into an unpowered display while the Daisy runs from USB.
- **Rev 1 C9 removed.** It sat on the same node as C5 and C4.
- **Rev 1 TP5, TP9, TP10 removed.** Each duplicated an easy-to-probe pad. TP1 (`HP_DETECT`) is the only test point.

## Board
- **New layout:** 4-layer with ground in the middle, 90 × 56.5 mm, with the Daisy flat along the rear edge and every panel jack on the front edge.
- **LCSC part numbers** in the schematic for JLC assembly of the SMD parts.
- **Re-annotated** in sheet order (left to right, then top to bottom by section) so the designators have no gaps.

## Designators
Rev 2 was re-annotated on 2026-10-26. U1, U2, A1 and FB1 kept their numbers. Commits before then, and rev 1, use the old
numbers on the right. A part carried over from rev 1 had the same old number there.

| Rev 2 | Old |
|---|---|
| R1–R19 | R17, R1, R40, R41, R38, R8, R7, R43, R44, R2, R28, R4, R32, R33, R34, R35, R37, R45, R46 |
| C1–C18 | C1, C3, C31, C17, C18, C8, C7, C30, C2, C12, C13, C33, C35, C36, C34, C24, C28, C29 |
| J1–J7 | J1, J9, J4, J5, J2, J8, J3 |
| Q1, Q2 | Q1, Q4 |
| TP1 | TP11 |
