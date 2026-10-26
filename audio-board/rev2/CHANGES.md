# Rev 2 changes

What changed from rev 1, and why, in one or two lines each. `DESIGN.md` describes the current design in full.
Keep this list to the net difference from rev 1. Parts that were added and then removed during rev 2 don't belong here (git has that history).

## Inputs
- **Pots removed (RV1 input level, RV2 volume, RV3 tone, C10, C11).** Level, volume and tone move to the touchscreen. With RV1 at mid
  travel, U1A saw about 250 kΩ of source impedance, which added noise and an ~80 kHz pole.
  R17 (1M to `VREF`) now sets the 1 MΩ guitar load, and U1A runs at unity gain.
- **R5 removed.** R17 biases U1A+ through R1, so R5 only sat in parallel and lowered the guitar load to ≈ 0.91 MΩ.
- **AUX input added (J9 → passive sum → `AUDIO_IN_2`).** For backing tracks from a phone or laptop, mixed in after the amp model.
  No buffer: the Seed3's AC-coupled input loads the R40/R41 sum directly, with R38 (100k) as the DC return.

## Outputs
- **Headphone amp: TPA6111A2 → TPA6132A2 (DirectPath).** It removes C14/C15 (470 µF output caps, the two largest parts in the
  headphone section), R9–R16 and C16, flattens the bass and adds click-and-pop suppression.
- **Headphone buffer removed (U1B, C5, R6).** The Seed3's outputs drive U2 through R2 directly.
- **U1: TLV9062 dual (SOIC-8) → TLV9061 single (SOT-23-5).** Only the guitar input still needs a buffer.
- **Speaker / line send driven by `AUDIO_OUT_2`** (R28/C24, R4, no buffer) instead of J5's tip-switch line out, which muted J2
  mechanically. Muting the speaker amp in firmware saves battery, ramps without clicks, gives the speaker and headphones independent
  levels, and keeps J2 live with headphones in (record while monitoring).
- **J8 added:** a keyed internal line out to the speaker amp. J2 stays as an external line out.
- **J5 is now a Same Sky SJ3-35063AG,** with an isolated detect switch read by the firmware on `HP_DETECT`.

## Power and control
- **J3: 2-pin 5 V header → 8-pin JST-XH to the power board.** One connector for power, the power button, `PWR_HOLD`, battery sense and
  the speaker mute. Adds R32–R35, C28, C29, Q4 and R37. Q1 still provides reverse-polarity protection.
- **Output mute on the STM32's independent watchdog.** The IWDG resets the STM32 if the audio callback stops. The codec's clocks
  stop with it, so its DAC powers down and both outputs go silent. R37 holds the speaker amp off whenever the Daisy is absent, booting or reset.
- **R26 removed, U2's EN tied to `+5V`.** The headphone amp has no hardware mute. The codec does the muting, as it does for J2.
  Driving EN from the Daisy would need a level translator, because the Daisy can run from USB while `+5V` is off.
- **R45/R46 added: `+5V` sense on Daisy pin 22 (`5V_SENSE`).** On USB alone, `+5V` and U2's rails are off, and pin 18's audio would
  reach U2's inputs through C12/C13. The firmware keeps the outputs silent while `5V_SENSE` is low.
- **R43 is 10k** (was 1k), to limit current into an unpowered display while the Daisy runs from USB.
- **Display: FB1 and C30 added** to keep the display's current pulses off the analog rail, and **R43/R44 added** in series with the UART
  against miswiring and hot-plugging.
- **C9 removed.** It sat on the same node as C18 and C17.
- **TP5, TP9, TP10 removed.** Each duplicated an easy-to-probe pad. TP11 (`HP_DETECT`) is the only test point.

## Board
- **New layout:** 4-layer with ground in the middle, 90 × 56.5 mm, with the Daisy flat along the rear edge and every panel jack on the front edge.
- **LCSC part numbers** in the schematic for JLC assembly of the SMD parts.

## Unused reference designators
These designators are unused on rev 2. Removed parts keep their numbers unused rather than being renumbered: C4–C6, C9–C11, C14–C16,
C19–C23, C27, J6, J7, Q2, Q3, R5, R6, R9–R16, R18–R27, R30, R31, R36, R42, RV1–RV3, SW1, TP1–TP10, U3.
