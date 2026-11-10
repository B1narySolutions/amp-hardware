# Audio board rev 2 — design

How the board works now, and why. `CHANGES.md` lists what changed from rev 1, and `../TEST_PLAN.md` is the bring-up and
test procedure. Each fact has one home in this file; other sections point to it. Write the design as it stands, not its
history (git has that).

The board holds a Daisy Seed3 (A1, in two 1×20 sockets), the analog input and output stages, the headphone amp and the
connectors to the power board and display. Volume, tone, input trim and mute come from the touchscreen over the UART, so
the board has no pots or encoder. A master volume encoder, if there is one, goes on the touchscreen / ESP32 side.

## Signal paths

U1 is a TLV9061 single op-amp (SOT-23-5), the guitar input buffer, on `+5V` (pin 5) and GND (pin 2). The AUX input and
both outputs connect to the Daisy with no op-amp.

### Mid-rail reference (VREF)
R6/R7 (10k/10k) from `+5V`, with C7 (47 µF): `VREF` ≈ 2.5 V. With 5k source impedance, C7 gives a ≈ 0.7 Hz corner, which
keeps noise on `+5V` out of `VREF`. Its only load is R1.

### Guitar input (J1 → `AUDIO_IN_1`)
J1 tip → C1 (100 pF to GND, RF shunt) → C2 (1 µF) → R1 (1M to `VREF`) → R2 (1k) → U1A follower → R20 (470 Ω) →
`AUDIO_IN_1` (Daisy pin 16). J1's tip switch shorts the tip to GND with nothing plugged in.
- **R1** sets the 1 MΩ load and the DC bias. **R2**, the only series resistance, protects U1A's input from plug-in
  transients.
- **Unity gain, no level pot.** A pot at mid travel put about 250 kΩ in front of U1A (noise, and an ~80 kHz pole). Input
  trim is in firmware.
- **Passive pickups only, no pad.** Active pickups and boost pedals are out of scope. With the module's ≈ 5 kΩ input,
  R20 costs ≈ 0.8 dB, so the Daisy's 3.6 Vpp full scale is reached at ≈ 3.9 Vpp at J1, ≈ 12 dB above a 1 Vpp hard strum.
- **R20 limits current into the Daisy pin** to ≈ 1–2 mA if U1 (≈ 4.8 Vpp swing on 5 V) is driven past the input's
  ±1.8 V absolute maximum by a boost pedal or a fault.
- **DC:** pin 16 sits at `VREF` through R20. The input is AC-coupled on the module, so no DC current flows.

### AUX input (J2 → `AUDIO_IN_2`)
J2 (SJ3-35063AG, 3.5 mm TRS) tip and ring → R3/R4 (10k each, passive stereo-to-mono sum) → R5 (470 Ω to GND) and C3
(1 nF) → `AUDIO_IN_2` (Daisy pin 17). J2's detect switch (pins 5 and 6) is not connected.
- **No buffer, no coupling cap.** The Seed3's inputs are AC-coupled on the module (Seed3 datasheet, Table 1 note) and
  the source is a phone or laptop output.
- **Daisy input impedance: 5 kΩ ±20%, assumed.** That is the TAC5242's figure at its own pins (TAC5242 datasheet, ADC
  parameters and section 7.3). The Seed3 datasheet gives none for the module pin; its own input circuits drive the pin
  through 1k or 100 Ω (Figures 3.2 and 3.4), which fits. TEST_PLAN 5.17 measures the level with the Daisy fitted.
- **R5 sets the level whatever that impedance is.** R3 ‖ R4 (5k) into R5 alone is −21.3 dB (a gain of 0.086): with no
  load from the module, a 2 Vrms laptop output (5.7 Vpp) reaches the pin at 0.17 Vrms (0.49 Vpp, ±0.24 V peak). R5 is
  also the source's DC return, and holds the node at GND with an empty jack or the Daisy out.
- **R5 is 470 Ω to protect the unpowered codec.** A source can keep playing into J2 with the board off, and the codec's
  inputs are rated −0.3 V to AVDD + 0.3 V with no injection rating (TAC5242 datasheet, §6.1). A 2 Vrms source then
  reaches ±0.23 V at worst (codec input at 6 kΩ, 1 % resistors). 560 Ω gives ±0.27 V (≈ 1.2 dB louder); 680 Ω passes
  0.3 V.
- **Level:** the same signal on both channels (most backing tracks) arrives at −22.2 / −22.0 / −21.9 dB with the codec
  at 4k / 5k / 6k, so 2 Vrms reaches the Daisy at ≈ 0.45 Vpp (−18 dBFS). One channel alone, the other at 0 V, is
  −28.0 dB. A quiet 0.5 Vrms phone lands around −30 dBFS. The firmware adds the gain back (about 18 dB takes 2 Vrms to
  full scale); the ADC's 119 dB dynamic range leaves a quiet phone ≈ 89 dB above its noise.
- **C3** filters RF from the cable: ≈ 400 kHz against the node's ≈ 400 Ω (≈ 370 kHz with the Daisy out).
- **Source load:** ≈ 10.4–10.9k per channel. **Noise:** the node's ≈ 2.6 nV/√Hz is far below a backing track.
  **Use:** backing tracks bypass NAM, mixed in after the amp model, to both outputs.

### Headphone output (`AUDIO_OUT_1` → J4)
`AUDIO_OUT_1` (Daisy pin 18) → R10 (3.3k) / C9 (1 nF to GND) → `HP_SOURCE` → C10/C11 (4.7 µF each) → R25/R27 (10k) → U2
INL−/INR−, with R26/R28 (10k) from each output back to its input. U2 (MAX9722AEUE+) drives J4 (`HP_L` tip, `HP_R` ring)
directly.
- **What the Seed3 outputs are rated for:** 1 Vrms at 0 dBFS (Seed3 datasheet, Table 3). The datasheet gives no output
  impedance, minimum load or coupling-cap value for pins 18/19, and says only the *inputs* are AC-coupled.
  - **Line-out mode, not headphones.** One single-ended pin per channel at 1 Vrms matches only the TAC5242's MD5 high /
    MD4 low mode, "Single-ended output; Line-out only" (TAC5242 datasheet, Table 7-10), minimum load 600 Ω. It drives
    16 Ω headphones (62.5 mW) only in its differential modes, hence U2. Electrosmith's own headphone circuit (Seed3
    datasheet, Figure 3.9) also adds an amp.
  - **DC level: probably 0 V, not confirmed.** Figure 3.9 wires pin 18 straight across a volume pot to GND, which
    suggests no DC on the pin (a pot that carries DC crackles). TEST_PLAN 5.16 measures it.
- **No buffer.** U2's inverting inputs are virtual grounds, so the Daisy sees R10 plus R25 ‖ R27 (5k), ≈ 8.3 kΩ.
- **R10/C9** filter the DAC's out-of-band noise: ≈ 80 kHz (R10 ‖ 5k with 1 nF).
- **Level:** R10 against R25 ‖ R27 is a −4.4 dB divider, and U2's gain is −1 (R26/R25 = R28/R27), so full scale puts
  ≈ 0.60 Vrms on each output: 22 mW into 16 Ω, 11 mW into 32 Ω (≈ 108 dB SPL in typical 98 dB/mW headphones).
- **Why unity gain:** U2 delivers 70 mW into 16 Ω and 130 mW into 32 Ω at 1 % THD with both channels driven in phase,
  the mono case here (MAX9722A datasheet, Electrical Characteristics and "Output Power"): ≈ 1.06 and 2.0 Vrms, a margin
  of 4.9 dB and 10 dB. The datasheet asks for 10k feedback resistors (larger ones raise the offset through the 50 nA
  input bias current), so to lower the gain, raise R25/R27.
- **Low end:** C10/C11 into R25/R27 is a 3.4 Hz high-pass. The Daisy's own output coupling adds a second one; its value
  isn't published.
- **U2, MAX9722A (DirectDrive):** an internal charge pump inverts the supply onto PVSS, so the outputs swing about 0 V
  with no output caps. Click-and-pop suppression, short-circuit and thermal protection, ±8 kV HBM on the outputs;
  2.4–5.5 V supply; charge pump at 600 kHz (505–800 kHz); PSRR 80 dB at 217 Hz; output noise 6 µVrms (22 Hz–22 kHz). Its
  16-pin TSSOP (0.65 mm pitch, no exposed pad) solders with an iron.
- **Wiring** (datasheet Typical Application Circuit and Figure 7): inverting, with external gain resistors. INL+/INR+ go
  straight to SGND, as the datasheet says to when the jack's ground isn't sensed. SHDN (active low) is tied to `+5V`
  (see "Output mute"). C13 is the flying cap, C14 holds PVSS to PGND, C12 bypasses PVDD to PGND and C15 SVDD to SGND:
  1 µF X7R 50 V each, the datasheet's value. PVSS and SVSS are tied at the device, as are PVDD and both SVDD pins.
- **Output offset:** ±2.5 mV maximum input offset at a noise gain of 2, plus 50 nA through 10k: at most ≈ ±5.5 mV at J4,
  ≈ 0.3 mA into 16 Ω.
- **No click from the input caps at power-up:** `HP_SOURCE` and U2's inverting inputs both sit at 0 V. The datasheet's
  advice to delay SHDN applies only to a source with a DC bias.

### Headphone detect (`HP_DETECT`)
J4 (Same Sky SJ3-35063AG, 3.5 mm stereo, through hole;
[datasheet](https://www.sameskydevices.com/product/resource/sj3-3506x.pdf)): pins 1/2/3 are sleeve/ring/tip on
GND/`HP_R`/`HP_L`. Pins 5 and 6 are an isolated normally-open switch that closes when a plug is in: pin 5 to GND, pin 6
straight to `HP_DETECT` (Daisy pin 23, PA3), with TP1. **Low = headphones in.**
- **No external pull-up, series resistor or RC.** The switch is on this board, not on a cable, and isolated from the
  plug. The firmware enables PA3's pull-up and debounces, as in the Seed3 datasheet's switch circuits (Figures 2.1 and
  2.2).
- **Footprint:** `Seed3_Carrier.pretty/Jack_3.5mm_SameSky_SJ3-35063AG_Horizontal.kicad_mod`, from the datasheet's
  recommended layout (rev 1.01, page 2). The jack face sits at the board edge (X = −2.4 mm from pin 1) with the nose
  overhanging. The AG variant has no pin 4. J2 uses the same part and footprint.

### Speaker send (`AUDIO_OUT_2` → J5)
`AUDIO_OUT_2` (Daisy pin 19) → R11/C16 (1k/3.3 nF, ~48 kHz low-pass) → `LINE_OUT`, with R12 (100k) to GND. `LINE_OUT`
goes to J5 pin 1 (LINE+); J5 pin 2 (LINE−) is `LINE_REF`, GND through R21 (1k). There is no external line out:
recording to a DAW goes through the Daisy's USB-C.
- **No buffer:** R11 plus a ≥ 10k amp input is far above the 600 Ω line-out minimum (see "What the Seed3 outputs are
  rated for"). With no `VREF` bias or coupling caps in the path, `LINE_OUT` doesn't drift at power-on.
- **No DC-blocking cap: this path assumes pin 19 sits at 0 V DC** (see "DC level" under "Headphone output"). If
  TEST_PLAN 5.16 finds more than a few tens of mV there, that DC reaches J5 and R12 (the power board's C8/C9 block it
  from the speaker amp's inputs). The fix, if it clicks, is 10 µF in series between C16 and `LINE_OUT`: a cut trace or
  a respin.
- **R11** is the output impedance and isolates the Daisy from cable capacitance (≈ 44 kHz with 3 m of typical cable).
  With R21, a differential input sees a 2k source: ≈ 1.7 dB loss into 10k (with R12; ≈ 0.83 Vrms at full scale),
  ≈ 3.0 dB into 5k. With `LINE_OUT` shorted the Daisy sees 1k, still above its 600 Ω minimum.
- **R12** is the DC return for the Daisy's output coupling cap.
- **J5** is a 2-way 3.5 mm screw terminal (Phoenix PT 1,5/2-3,5-H) on the right edge, marked LINE+ and LINE−. It feeds
  the speaker amp on the power board (or an off-the-shelf class D module while prototyping) over a short twisted pair
  routed away from the guitar input and speaker wires.
- **Pseudo-differential.** LINE− is the audio board's ground through 1k, not an inverted signal. Wire LINE+ to the amp's
  IN+ and LINE− to its IN− **only**, never to the amp's GND as well: that would close a ground loop through J6 and J5.
  The amp amplifies only LINE+ − LINE−, so the voltage between the boards' grounds (the power board's supply current in
  J6's GND wire) is rejected. R21 equals R11 because the rejection depends on equal source impedances; C16 lowers
  LINE+'s only above ≈ 20 kHz. A shorted pair loads the Daisy with 2k.
- **Why a separate speaker output:** the speaker amp can shut down while headphones are in, mute ramps don't click, and
  the two outputs get independent levels.
- **Speaker wiring** is on the power board: the cone's spade tabs (6.3 mm / 4.8 mm) take crimped quick-disconnects, and
  neither speaker wire may be grounded (most class D outputs are bridged).

### Jack ESD protection (D1–D5)
Every jack contact that carries a signal has a Nexperia PESD5V0S1BA (SOD-323, C19224) to GND at the jack: D1 `GTR_TIP`
(J1 tip), D2/D3 `AUX_TIP`/`AUX_RING` (J2), D4/D5 `HP_L`/`HP_R` (J4).
- **Why:** these contacts are touched and hot-plugged. U2's outputs are rated ±8 kV HBM, but a jack sees IEC 61000-4-2
  discharges, which are harsher.
- **Why this part:** bidirectional, so it never conducts on an audio signal's negative half. 5 V working voltage, above
  every signal here (the largest, a hot active guitar, is ≈ ±2.4 V where U1 clips it). 5 nA leakage against the 1 MΩ
  input; 35 pF, small next to a guitar cable's few hundred pF.
- **Not protected:** the J2/J4 detect switches, which are isolated from the plug.

### Output mute (STM32 watchdog)
A hung Daisy can loop its last audio buffer at full level, so every output must go silent when audio stops.
- **How it works:** the firmware feeds the STM32's independent watchdog (IWDG) only from the audio callback. The IWDG
  runs on its own clock, so if the callback stops (hung firmware, stalled DMA, fault handler), it resets the STM32.
  Through reset, boot and DFU the Daisy's pins float.
- **The codec mutes.** The STM32 clocks the TAC5242, which powers down its DAC by itself when its audio clocks stop
  (TAC5242 datasheet, section 7.4.1). An IWDG reset therefore silences pins 18/19, and with them J4 and J5. It doesn't
  help while a DMA loops a stale buffer with the CPU hung, which is why the IWDG has to reset the chip. The datasheet
  doesn't say whether the power-down clicks; TEST_PLAN 5.16 records it.
- **Speaker:** `SPK_EN` (Daisy pin 28) drives Q2's gate, and R17 (100k) holds it low while the pins float. Q2 (2N7002)
  pulls `SPK_MUTE` (J6 pin 4) to GND through R23 (470 Ω) to play; the power board pulls it up to mute.
  - **Why Q2:** the power board can pull `SPK_MUTE` up to any voltage without back-powering an unpowered Daisy.
  - **R23** limits Q2's current if 5 V lands on MUTE while Q2 is on: ≈ 11 mA, 59 mW in R23. Q2's RDS(on) alone (7 Ω max)
    would allow 0.75 A or more, far past its 115 mA rating. Against the power board's pull-up (4.7k or more), Q2 and R23
    still pull `SPK_MUTE` below 0.5 V (≈ 0.24 V against 10k).
- **Headphones: no hardware mute.** U2's SHDN is tied to `+5V`, so U2 is on whenever `+5V` is up, and the codec does
  the muting. U2's click-and-pop suppression covers its own power-up and power-down.
  - **Why SHDN isn't driven from the Daisy:** the Daisy can run from USB while `+5V` is off (see "Running from USB
    alone"), and SHDN is rated to SVDD + 0.3 V. It would take a level translator with supply isolation, two decoupling
    caps and a pull-down.
  - **The cost:** anything on pin 18 while the Daisy boots reaches the headphones (TEST_PLAN 7.1 records it), and U2
    draws its 5.5 mA quiescent (13 mA maximum) while only the speaker is in use.
- **Trade-off:** an external retriggerable one-shot on an audio-callback toggle would watch from outside the STM32, for
  7 more parts. The IWDG is inside the chip it watches. Never feed it from the main loop.

## Power

`5V_IN` arrives on J6 pin 1 and goes through Q1 (AO3401A P-FET, reverse-polarity protection) onto `+5V`, which feeds
Daisy VIN (pin 39), U1, U2, `VREF` and the `5V_SENSE` divider (R18/R19).
- **Why Q1:** a screw terminal has no key, so 5 V and GND can be swapped, as can clip leads on a bench supply (TEST_PLAN
  2.12). The Seed3's VIN is reverse-protected on the module, but U1 and U2 are not. Q1 drops about 50 mV at 1 A.
- **Wires on the wrong terminal:** Q1 only covers 5 V and GND swapped. If 5 V lands on a signal terminal:
  - `BATT_SENSE_CONN`: R13/R22 halve it, so Daisy pin 25 sees at most 2.65 V. Pin 25 is the STM32's PA7, a TT_a pin with
    a 4.0 V absolute maximum and no positive injection current (STM32H750 datasheet DS12556, Tables 19 and 20), so a
    series resistor alone can't protect it.
  - `SPK_MUTE`: Q2 is rated 60 V and survives while off. While on, R23 limits the current (see "Output mute").
  - J3: R8 limits the current into Daisy TX, and R9 with R24 divides RX (see "Display connector (J3)").
  - J5's LINE+: R11 puts ≈ 3 mA into the codec output's protection: the worst case, which it will probably survive.

  GND sits between 5V and the signals on J6, so a stray strand from the 5 V wire can only reach GND.
- **Bulk at the power entry:** C5 (47 µF electrolytic) and C4 (100 nF) at Q1's output. C5's ESR damps the ringing
  between the wiring's inductance and the ceramics; the Seed3 datasheet recommends extra filtering on VIN.
- **Local decoupling:** C6 at U1 pin 5, and C12 (PVDD) and C15 (SVDD) at U2.
- **Display supply:** the power board feeds the display directly, so its current pulses (ESP32 Wi-Fi, backlight PWM)
  never flow through Q1 or `+5V`.

### Running from USB alone
USB doesn't drive the VIN pin: on the module, USB VBUS and VIN each reach the regulators' input through their own diode
(Seed3 datasheet, Figure 1.0, "Onboard USB Power"). With USB plugged in and the power board off (flashing or debugging),
the Daisy runs while `+5V` is at 0 V, and any Daisy output that is high pushes current into an unpowered part through
that part's input protection diodes.
- **Q1 conducts backwards** if `+5V` is lifted, because its gate is tied to GND. That would only leak a little current
  to the power board. Nothing on the audio board back-powers `+5V`.
- **Display UART:** the display is unpowered too, and Daisy TX idles high into it through R8 (see "Display connector
  (J3)").
- **Headphone input (`5V_SENSE`):** C10/C11 pass pin 18's audio through R25/R27 to U2's inputs, which are rated SVSS −
  0.3 V to SVDD + 0.3 V (MAX9722A datasheet, Absolute Maximum Ratings). With `+5V` off both rails are at 0 V, so the
  inputs may only see ±0.3 V; full scale is ±1.4 V. R10 and R25/R27 limit the current into U2's protection diodes to
  ≈ 0.07 mA (worst case), still outside the rating. So R18/R19 (100k/100k) divide `+5V` to ≈ 2.5 V on `5V_SENSE` (Daisy
  pin 22, ADC_0), and while it reads low the firmware keeps both outputs silent (see "Firmware requirements").
  - **Why not `BATT_SENSE`:** a bench supply on J6 gives it no reading.
  - **Why 100k/100k:** the divider draws 25 µA, and R19 holds the pin at 0 V with `+5V` off. The Daisy's VIN is `+5V`,
    so the divider can't back-power it.
  - **No filter cap:** the firmware uses a long ADC sample time for the 50k source instead.
  - **Limit: a fast power loss.** The firmware reacts within one or two audio blocks plus the codec's output delay, a
    few ms. If `+5V` collapses faster (the 5 V wire pulled out of J6 under load), the last few ms of audio still reach
    U2's unpowered inputs at ≈ 0.07 mA. TEST_PLAN 5.18 measures this.

## Connectors

### What each connector can see
The outside world the audio board is designed for, case by case. A design review checks every IC pin against these, one
misuse at a time with everything else normal, in each power state. Misuse may stop the board working, but must not
damage it.

| Pin | Normal | Misuse that must not damage anything |
|---|---|---|
| J6.1 5V | 4.75–5.25 V while on (`power-board/README.md`) | 5 V and GND swapped (−5.25 V), TEST_PLAN 2.12 |
| J6.3 BAT | 0–3.3 V from 10 kΩ or less | A 5 V wire on BAT |
| J6.4 MUTE | Power board's pull-up, 4.7 kΩ or more to at most 5.25 V | A 5 V wire on MUTE |
| J3.2 TX | The display's RX: high impedance, clamped to −0.5…3.8 V, 1 mA at most | A 5 V wire on TX |
| J3.3 RX | The display's TX: 0–3.3 V logic from ≈ 50 Ω | A 5 V wire on RX |
| J5.1 LINE+ | The speaker amp's input: 10 kΩ–1 MΩ | LINE+ shorted to GND; a 5 V wire on LINE+ |
| J5.2 LINE− | The speaker amp's input: 10 kΩ–1 MΩ | A 5 V wire on LINE− |
| J1 tip (guitar) | Passive pickups, 1.5 V peak (3 Vpp) from ≈ 10 kΩ, 20 Hz–20 kHz | An 18 V boost pedal at full output, 9 V peak from 1 kΩ (out of scope: may distort, must survive) |
| J2 tip/ring (AUX) | A 2 Vrms laptop, 2.83 V peak, the same signal on both | Pro line out at full level, ±5 V from 10 Ω |
| J4 tip/ring | Headphones, 16 Ω or more | — |
| J4.6 detect | Open (no plug), or switched to GND (plug in) | — |

Power states: **on** (power board up, Daisy running); **Daisy out** (TEST_PLAN stage 2); **USB only** (Daisy on its own
USB, power board and display off, see "Running from USB alone"); **off** (everything off while a guitar or phone may
still play, and the display may still be on); **reversed** (5 V and GND swapped). The jack pins (J1, J2, J4) are touched
by people, so each needs an ESD diode (D1–D5, see "Jack ESD protection"). Every capacitor on the audio path, from
the jacks through the Daisy to J4 and J5, should be C0G or film. Today C2 (X7R) and C10/C11 (X5R) aren't: see
"Open items".

### Power board connector (J6)
J6 is a 4-way 3.5 mm screw terminal (Phoenix PT 1,5/4-3,5-H) on the rear edge: nothing to crimp, and a damaged wire is
quick to replace. The power switch is on the power board, which cuts the 5 V output itself.

| Pin | Silkscreen | Net | Direction | Daisy pin | Use |
|---|---|---|---|---|---|
| 1 | 5V | `5V_IN` | Power board → audio board | 39 (VIN) via Q1 | 5 V supply |
| 2 | GND | GND | — | 20 / 40 | Ground |
| 3 | BAT | `BATT_SENSE_CONN` | Power board → audio board | 25 (`BATT_SENSE`) | Battery voltage scaled to ≤ 3.3 V. R13/R22 (10k/10k) halve it and C17 (100 nF) filters it into the ADC |
| 4 | MUTE | `SPK_MUTE` | Audio board → power board | 28 (`SPK_EN`) via Q2 and R23 | Open-drain speaker-amp mute (see "Output mute") |

- **Pin order:** seen from the wire side, the terminals read 5V, GND, BAT, MUTE from left to right.
- **One 5 V and one GND pin:** the audio board draws well under 1 A, and a PT 1,5 contact is rated 17.5 A. No supply
  current returns through J5 (see "Speaker send").
- **R13/R22 halve the battery level:** 0–3.3 V on BAT reads as 0–1.65 V on pin 25. That protects the pin (see "Wires on
  the wrong terminal") and keeps the top of the range below the ADC's own 3.3 V reference, which may sit a little low.
  With the amp off, a divider still holding BAT near 3.3 V puts at most 1.65 V on the unpowered Daisy's pin.
- **The reading depends on the power board's divider too.** R13 + R22 load BAT with 20k, so pin 25 reads
  V × 10k / (20k + R_source), where V is the divider's open-circuit output and R_source its source impedance.
- **The power board's divider (rev 1)** is R2/R3 (30k/10k, 1 %) from its switched battery rail (`VBAT_PROTECTED`): a
  ratio of 0.25 from a 7.5 kΩ source, so BAT is 3.15 V at 12.6 V. Pin 25 then reads
  VBAT × 0.25 × 10k / (20k + 7.5k) = **VBAT / 11**: 1.15 V at 12.6 V, 1.01 V at 11.1 V, 0.82 V at 9.0 V. With all four
  resistors at 1 %, the ratio is within ±2.4 % worst case.
- **C17:** a ≈ 320 Hz corner (10k ‖ 10k). It also supplies the ADC's sampling charge.

**Power board requirements** (`../../power-board/README.md` collects these with everything else the audio board needs
from the power board)
- Keep `BATT_SENSE_CONN` within 0–3.3 V.
- Keep the `BATT_SENSE` divider's source impedance at 10 kΩ or less, and record its ratio and impedance here (rev 1:
  0.25 from 7.5 kΩ, above). The reading is then at least a third of BAT, and the firmware needs both numbers.
- Switch the `BATT_SENSE` divider off with the 5 V output, so it doesn't drain the battery while the amp is off.
- Pull `SPK_MUTE` up on the amp side, with 4.7 kΩ or more to at most the 5 V rail (5.25 V), so the amp is muted when this board is
  unpowered or unplugged. Q2 pulls it low through R23 (470 Ω): ≈ 0.24 V against 10k, ≈ 0.5 V against 4.7k. The amp's
  mute input has to read that as low.
- Provide the power switch and a low-battery cutoff: the audio board has no way to turn the power off.
- Supply the display's 5 V directly, with its own wire pair.

### Display connector (J3)
J3 is a 3-way 3.5 mm screw terminal (Phoenix PT 1,5/3-3,5-H) on the rear edge next to J6: 1 GND, 2 `UART_TX_CONN` (TX),
3 `UART_RX_CONN` (RX), marked on the silkscreen. R8 and R9 (10k) sit in series with TX and RX to Daisy USART1 (pins
14/15, `DISPLAY_UART_TX`/`DISPLAY_UART_RX`).
- **J3's GND:** the UART needs a common reference. Some of the display's return current comes back through it and
  across to J6's GND; the two sit side by side, so that current stays in the rear-right corner.
- **R8:** with the Daisy on USB alone, its TX idles high into an unpowered display. 10k keeps the current into the
  display's RX protection diode to ≈ 0.27 mA.
- **R9:** the display can be powered from its own USB, so the power-up order isn't fixed. 10k limits the current from a
  powered display into an unpowered Daisy's RX pin the same way. Both also add a little ESD margin.
- **R24 (100k) pulls `DISPLAY_UART_RX` to GND.** With R9 it divides a 5 V wire on RX to at most 4.78 V at pin 15 (PB7),
  inside the Seed3's 0–5 V GPIO rating (the STM32 itself allows VDD + 4 V there while powered). The display's 3.3 V high
  arrives at ≈ 3.0 V, above the 0.7 × VDD (≈ 2.3 V) the input needs.
- **R24 also detects the display.** With the display unplugged or off, RX stays low: the UART flags one break (a
  framing error), then waits for the line to go high again. A line that idles high means a display is connected and
  powered. PB7's internal pull-up has to stay off, or it fights R24.
- **Baud rate limit:** 10k with ~50 pF of cable and pin capacitance is ≈ 0.5 µs: fine up to 230400 baud (a 4.3 µs bit),
  not for 921600. To go faster, lower R8 and R9 and accept more current.

### Daisy pins
Used: 14/15 (display UART), 16/17 (audio in), 18/19 (audio out), 20/40 (GND), 22 `5V_SENSE`, 23 `HP_DETECT`,
25 `BATT_SENSE`, 28 `SPK_EN`, 39 VIN. Every other pin, including `3V3_A` (21), `3V3_D` (38) and USB D−/D+ (36/37), is
marked no-connect. With the Daisy out, its sockets give probe access to every net, so there are no breakout headers.
USB stays on the Daisy's own connector.

## Firmware requirements
- **IWDG:** start it early in boot, with a timeout of about 10 ms. Feed it **only** from the audio callback.
- **Outputs:** speaker mix on output 2, headphones on output 1. Start the codec at digital silence and ramp up: U2 is
  always on, so the headphones hear whatever pin 18 does from boot. End the chain with an output clamp or limiter and a
  NaN/Inf guard. Cap the speaker level about 5 dB below full scale (the speaker amp clips on the battery above that).
- **`SPK_EN` (pin 28):** a low output at start; high after the first audio callback has started; low while headphones
  are in.
- **`HP_DETECT` (pin 23, PA3):** internal pull-up on, debounced, **low = headphones in**. Going in: ramp `AUDIO_OUT_2`
  down, then `SPK_EN` low. Coming out: `SPK_EN` high, then ramp `AUDIO_OUT_2` up.
- **`5V_SENSE` (pin 22, ADC_0):** longest ADC sample time (50k source); ≈ 2.4–2.5 V with `+5V` at 4.85–5.0 V.
  - **Before starting audio:** require it above 2.35 V (`+5V` ≥ 4.7 V) for at least 10 ms, then ramp the outputs up. U2
    is fully on 80 µs after it is enabled (MAX9722A datasheet, SHDN to Full Operation Time).
  - **While running:** sample it from the audio callback on every block (ADC on DMA, so the callback only reads the last
    value). Below 2.2 V (`+5V` < 4.4 V, still well above U2's 2.4 V minimum) write silence from that block on, until the
    start-up condition is met again. The thresholds give 0.15 V of hysteresis.
  - This applies on USB alone on the bench too.
- **`BATT_SENSE` (pin 25, ADC):** VBAT = 11 × V(pin 25) with the power board's rev 1 divider (see "Power board connector
  (J6)"). Send the level to the display every few seconds and warn when it gets low: power board rev 1 has no
  low-battery cutoff (its supervisor watches only the 5 V), so the pack's own protection or the 5 V buck's dropout ends
  it.
- **Display UART:** 230400 baud or less; PB7's (pin 15) internal pull-up off; a line held low is "no display"; restart
  reception after a framing error or break. Volume and mute come from the display; ramp volume changes.
- **AUX:** mix `AUDIO_IN_2` (mono) in after the NAM model and cabinet EQ, to both outputs, with its own level control
  from the display and ≈ 22 dB of make-up gain (see "AUX input").
- **Settings:** save when they change (debounced, to spare the flash), not at shutdown: the power switch is on the power
  board, so the power can disappear at any time.

## Open items
- **Watchdog mute:** stall the audio callback in a debug build. Check that J4 and J5 go silent and `SPK_MUTE` mutes
  within ~10–20 ms.
- **Speaker amp mute polarity:** the power board's TPA3118D2 has an active-high MUTE pin, so it matches with no inverter
  (see power-board/README.md). Check it on the built boards.
- **Wire ends:** ferrules or solid wire in the screw terminals. Tinned stranded wire creeps under the screw and loosens.
- **2N7002 gate drive:** Q2 is driven from 3.3 V logic. That should be enough for the small pull-up current on
  `SPK_MUTE`, but check it on the board.
- **Headphone level:** full scale is ≈ 0.60 Vrms per channel (TEST_PLAN 7.8). If that's too loud, or the hiss is audible
  with sensitive headphones, raise R25 and R27 together (20k gives ≈ −4 dB, ≈ 0.38 Vrms) and keep R26/R28 at 10k.
- **AUX input level:** after TEST_PLAN 5.17, measure a phone and a laptop at full volume through J2: 2 Vrms should reach
  ≈ 0.44–0.45 Vpp, and can't exceed 0.49 Vpp. If the firmware gain for quiet phones brings up audible noise, R5 can go
  up to 560 Ω (see "AUX input").
- **Hot passive pickups:** play the hottest passive guitar available hard into J1 (TEST_PLAN 5.19) and confirm its peaks
  stay below ≈ 3.9 Vpp.
- **Polarity:** U2 inverts the signal. Decide whether the firmware negates the output.
- **Class II ceramics on the audio path:** C2 (1 µF X7R) is in series with the guitar signal into the 1 MΩ node, and
  C10/C11 (4.7 µF X5R) with the headphone path. The material is piezoelectric, so knocks can become signal; distortion
  from C2 is negligible (it drops almost none of the signal into 1 MΩ). Tap the board with a guitar plugged in
  (TEST_PLAN 6.5). If it's audible, C2 can become a 100 nF C0G in the same 1206 footprint (with R1 the corner moves from
  0.16 Hz to 1.6 Hz). C10/C11 sit on a ≈ 2 kΩ node, so they matter less; film parts would be the fix there.
- **Headphone low-end corner with the Daisy fitted:** TEST_PLAN 3B.3 (Daisy out) checks C10/C11 alone (≈ 3.4 Hz). Sweep
  it again in Stage 5 with the Daisy in and record the corner.
- **Headphone noise while the Daisy boots:** check TEST_PLAN 7.1 and 7.6 for clicks on J4 at power-up, reset and DFU
  entry. If they are loud, the fallback is to drive SHDN from the Daisy through a level translator.
- **USB-alone power transitions:** in TEST_PLAN 5.18, record how long U2's input stays outside SVSS − 0.3 V … SVDD +
  0.3 V. If it is more than a few ms at full scale, raise the firmware's 2.2 V threshold or shorten the audio block.
- **Line-out level:** the loss through R11 and R21 grows as the amp's input impedance falls. The TPA3118D2's is ≈ 60k at
  20 dB of gain (≈ 0.15 dB loss), down to 9k at 36 dB, which the power board must not use. It runs at 20 dB from the
  12 V power bank, where full scale clips the speaker, so the firmware caps the speaker level about 5 dB below full
  scale (see power-board/README.md, "The amp: TI TPA3118D2").
- **Soldering U2:** the TSSOP's 0.65 mm pitch takes flux and a fine tip or drag soldering. TEST_PLAN 0.1, 1.6a and 1.8
  catch bridges.
- **Mechanical:** no enclosure yet: recheck the outline, jack and hole positions against its drawing. The Seed3's USB-C
  overhangs the PCB by 1.55 mm and stands 3.25 mm tall (Seed3 datasheet, page 8); the board's 3D placeholder is the
  original Seed's outline. Front panel under 3 mm, Neutrik's limit for the NRJ4HF's nut; the SJ3 noses stand 3.0 mm
  proud of their faces, so they fit it too.

## Layout

### Stackup
2 layers, 1.6 mm FR-4, 1 oz copper on both sides. It fits the capstone fab's free-board limits (2 layers, under
100 × 100 mm) and JLC's standard 2-layer process. Page numbers refer to Eric Bogatin, *Bogatin's Practical Guide to
Prototype Breadboard and PCB Design* (Artech House, 2021).

| Layer | Use |
|---|---|
| F.Cu (top) | Every part and nearly all routing, with a GND pour filling the space around it |
| B.Cu (bottom) | A GND pour over the whole board. Its only traces are a few short hops (below) and the display UART along the rear edge |

- **The bottom is the ground plane.** Every audio net stays on F.Cu from end to end, with B.Cu ground 1.5 mm below.
  Where two top-layer traces cross, the one that doesn't carry audio drops to B.Cu for a few mm: the analog `+5V` branch
  (six hops, about 2–3 mm each), the `+5V` link between U2's SVDD pins (2.6 mm, under U2), `HP_DETECT` (4 mm and 5.7 mm)
  and the display UART. A layer change on an audio net would add two vias to its path.
- **The hops cut the back pour under some audio traces.** Each leaves a slot about 1 mm wide: `+5V` under `AUDIO_IN_1`,
  `AUX_TIP`, `AUX_RING`, `AUDIO_OUT_1`, `AUDIO_OUT_2` and `HP_SOURCE`, and `HP_DETECT` under `AUDIO_OUT_1` and
  `AUDIO_OUT_2`. None crosses the 1 MΩ guitar node. The slots don't matter:
  - **Return path:** the front pour runs beside each audio trace across the slot, with a stitching via 1.7–2.7 mm from
    each hop. The detour adds about 1 nH, ≈ 0.1 mΩ at 20 kHz; at under 1 mA the ground shift is about 0.1 µV.
  - **Coupling from `+5V`:** each crossing is at most about 20 fF. Into the highest-impedance crossed net (`HP_SOURCE`,
    ≈ 2 kΩ) that is about −106 dB at 20 kHz: 50 mV of ripple becomes ≈ 0.25 nV, against U2's 6 µVrms output noise. The
    hops sit upstream of the decoupling at each load (C6, C12, C15, R6's C7 filter).
  - **Fast edges:** a 3 mm slot only matters at many GHz, and the ESD diodes sit at the jacks, ahead of every hop.
  - **Bridging the crossings** with 0 Ω resistors on F.Cu would cost seven parts for no measurable gain.
- **Front pour:** GND on F.Cu around the routing (0.3 mm clearance), tied to the back pour by about 160 stitching vias
  (0.6/0.35 mm, every 5 mm or so) and by the GND via beside every SMD ground pad. It guards neighbouring audio traces,
  with a stitching via between `AUDIO_IN_2` and `AUDIO_OUT_1` below the Daisy, and between INR− and OUTR and INL− and
  OUTL at U2. Islands no via reaches are removed (Bogatin's warning about pours on signal layers, pp. 461–464, is about
  poorly stitched ones). Both pours are inset 0.5 mm from the board edge.
- **No power plane:** one is only needed above about 20 A (pp. 466, 479). The board draws about 1 A at most, and a
  20 mil (0.5 mm) trace carries 3 A (p. 466). A plane would also spread `+5V`, with the Daisy's digital current pulses,
  under the analog circuits.
- **One GND net, no split.** A split only helps with sub-millivolt noise below 100 kHz when more than 10 A of
  low-frequency current flows in the ground plane (p. 465). Analog and digital are separated by placement.
- **Why 1.6 mm:** the jacks and the Daisy sockets take force at every plug-in. It is also the cheapest thickness.
- **No controlled impedance.** USB doesn't leave the Daisy.

### Board outline and placement
90 × 56.5 mm, 2 mm corner radius; the front panel is the bottom edge. The jacks set the width. Laying the Daisy flat
along the rear edge, with no breakout headers, sets the depth. The board file has the positions; the reasons:
- **J1 (guitar), J2 (AUX), J4 (headphones)** on the front edge, inputs on the left, outputs on the right. Every jack
  mounts against the back of a flat front panel, so their body faces line up on the edge, not their nose tips. J1
  (Neutrik NRJ4HF) is rear-mounted: a nut on its 8.9 mm threaded nose clamps it from the front (Ø11.2 mm panel hole).
  The SJ3 noses (3.0 mm) go into the panel holes.
- **A1 (Daisy)** flat along the rear edge, USB on the left edge, reachable for flashing. Pins 1–20 face the front, so
  audio pins 16–19 face the analog band. Pins 21–40 (power, controls, `HP_DETECT`) face the rear.
- **U1** at the end of the guitar row, beside J1's tip: the high-impedance input stays short, and U1's low-impedance
  output makes the long run to Daisy pin 16.
- **U2** lower right, right of J4, the only open area that takes the TSSOP, its four gain resistors and four caps.
  Supplies and charge pump are on its top row; inputs and outputs on its bottom row, toward J4.
- **J6 and J3** side by side on the rear edge at the Daisy's right end. Display return current through J3's GND flows to
  J6 without passing under U1, U2, J1 or J2.
- **J5** on the right edge. It carries no ground current, so it doesn't need to sit by J6, and the right edge keeps the
  speaker wiring away from the guitar input.

### Passive placement
All parts sit on the top side, each filter or divider at its load. The long runs are then the low-impedance ones (a
source output, the DAC output, an op-amp output), and every high-impedance node is a few mm long. The analog section
fills the band between the Daisy and the front jacks. Power, the display and the power board controls sit in the
rear-right corner, as far from J1, U1 and U2 as the board allows: the power board's regulators and class D amp are the
noisiest things the audio board connects to.

- **Guitar input (most sensitive):** one straight row on F.Cu from J1's tip to U1 pin 3, about 18 mm, with no vias. The
  1 MΩ node is about 4.5 mm of trace, and `VREF` a few mm.
- **AUX input:** the block sits right under Daisy pins 16–17. J2's ring and tip run about 20 mm, driven by the source.
  The ≈ 400 Ω `AUDIO_IN_2` node is about 11 mm. Nothing crosses the guitar row.
- **Headphone path:** `AUDIO_OUT_1`, the DAC output, makes the long run to R10. `HP_SOURCE` (≈ 2 kΩ) is then about
  17 mm, the cost of reaching both sides of U2 without a layer change.
- **Speaker send:** R11, C16, R12 and R21 sit at J5. `AUDIO_OUT_2` makes the long run (about 30 mm on F.Cu), so the 1k
  `LINE_OUT` and `LINE_REF` stretches are only about 5 mm each.
- **Decoupling:** C6 is 1.5 mm from U1's pin 5. C13 and C14 are each within 2 mm of U2's pins. C12 and C15 sit 4–6 mm
  along the `+5V` feed; PVDD and SVDD are tied at the device, so they work as one 2 µF bypass.
- **Power corner:** each terminal's parts sit in a column below it. Power enters at J6 pin 1 → Q1 → C4 and C5 on short
  wide traces. Each terminal's function is printed on the silkscreen (5V, GND, BAT, MUTE; RX, TX, GND; LINE+, LINE−),
  because nothing else stops a wire landing on the wrong terminal.
- **GND vias:** every SMD GND pad has its own 0.6/0.35 mm via, 1–1.6 mm from the pad on a 0.4–0.5 mm stub. No vias in
  pads. Each ESD diode's via keeps its discharge path to a few mm.
- **Spacing:** parts from different blocks keep at least 1 mm of copper between pads, for an iron and for a 0.2 mm trace
  between them. Decoupling caps sit closer on purpose: C6 and R2 at U1's pins (0.80 and 0.83 mm), C14 and U2's pin 8
  (0.55 mm), C12 and C15 (0.55 mm).
- **Mounting holes:** three non-plated M2.5 holes, plus J1's panel nut at the front-left corner. H2 and H3 sit 4 mm in
  from the rear-right and front-right corners. H1 sits between the Daisy's front socket row and J1's back face, where it
  supports the board when the module is pressed into its sockets. The rear-left corner has no room for a hole.
- **Fiducials:** FID1–FID3, 1 mm copper dots with 2 mm mask openings, placed asymmetrically, for machine assembly.
- **Silkscreen:** references are 1.0 mm high with 0.15 mm strokes, JLC's minimum for legible text.

### Routing under the Daisy
`5V_SENSE`, `BATT_SENSE`, `SPK_EN` and the display UART reach the Daisy on F.Cu between its two socket rows, away from
the analog band. They are DC levels or slow logic.
- **Daisy VIN (`+5V`, 0.6 mm)** leaves C4 beside Q1 and runs along the rear edge to pin 39. The analog `+5V` branch
  leaves C5, the `+5V` star, for U1, R6 and U2, so the Daisy's current pulses never flow in it. The 60 mm VIN run drops
  ≈ 15 mV at 250 mA.
- **The display UART uses B.Cu** because J3 is on the far side of J6: on F.Cu, TX and RX would cross every J6 column.
  They run along the rear edge, a strip of the back pour that carries nothing.

### U2 (TSSOP-16)
- **Footprint:** `Package_SO:TSSOP-16_4.4x5mm_P0.65mm`.
- **Under the body:** the SVSS–PVSS and SVDD–PVDD links on F.Cu, the B.Cu hop for SVDD pin 11, and GND vias for PGND,
  SGND, INL+ and INR+. They're board items, not part of the footprint: move them with U2.
- **Grounds:** the datasheet asks for PGND and SGND to meet at a single point. With ground on both layers under the part
  (cut only by the 2.6 mm SVDD hop), that point is the plane right under U2.
- **The datasheet's layout advice** (Layout and Grounding): charge-pump caps to PGND, PVDD tied to SVDD and PVSS to SVSS
  at the device, and switching traces kept away from SGND and the audio path. C13 and C14 sit on the top row's side,
  away from the inputs and outputs on the bottom row.

### Design rules
Board Setup (`seed3-carrier.kicad_pro`) holds the absolute minimums and net class defaults. `seed3-carrier.kicad_dru`
adds the per-class ranges, including the maximums. All values are within JLC's standard 2-layer limits.

| Item | Min | Default | Max |
|---|---|---|---|
| Signal track (Default class, not GND) | 0.2 mm | 0.2 mm | 0.5 mm |
| GND track | 0.2 mm | 0.5 mm | 2 mm |
| Power track (`Power` class) | 0.5 mm | 1 mm | 2 mm |
| Power track inside U1's courtyard | 0.3 mm | 0.5 mm | 2 mm |
| Power track inside U2's courtyard | 0.2 mm | 0.25 mm | 2 mm |
| Via, Default class | 0.6 / 0.35 mm | 0.6 / 0.35 mm | 0.8 / 0.4 mm |
| Via, `Power` class | 0.6 / 0.35 mm | 0.8 / 0.4 mm | 0.8 / 0.4 mm |
| Clearance (both classes) | 0.2 mm | | |
| Copper to board edge | 0.5 mm | | |
| Hole to hole, hole clearance | 0.25 mm | | |
| Via annular ring | 0.125 mm | | |

- **Via drill:** the capstone fab needs every hole to be at least 13 mil (0.33 mm), so the smallest via drill is
  0.35 mm. With the 0.6 mm pad that leaves a 0.125 mm annular ring (JLC's minimum is 0.075 mm).
- **`Power` class:** `+5V`, `/5V_IN` (the class also lists `/3V3_A`, which is unused on the audio board). GND stays in
  Default.
- **Neck-down at U1 and U2:** a 1 mm power trace cannot reach U2's 0.4 mm pads (0.65 mm pitch) or U1 pin 5. Inside each
  IC's courtyard, two rules set the default to the pad width (U2: 0.25 mm, U1: 0.5 mm). Anywhere else a Power trace
  under 0.5 mm fails DRC. Rules later in `seed3-carrier.kicad_dru` win, so the neck-down rules come after "Power track
  width".
- **Presets:** tracks 0.2, 0.25, 0.3, 0.5 and 1.0 mm; vias 0.6/0.35 and 0.8/0.4 mm.
- **Thermal reliefs:** every pad joins the GND pours with 0.5 mm spokes and a 0.5 mm gap, SMD pads included, because a
  pad tied solidly into a pour would not heat up enough under an iron. Vias stay solid. The "Thermal reliefs on
  through-hole pads" rule in `seed3-carrier.kicad_dru` enforces it for through-hole pads in any zone added later.
- **Fiducials:** the "Fiducial pour clearance" rule keeps both pours 1 mm from FID1–FID3, clear of their mask openings.

## Parts sourcing
Every part is hand-soldered with an iron and comes from DigiKey. Each symbol has `MPN`, `Manufacturer`, `DigiKey` and
`Datasheet` fields, copied to the board, and `seed3-carrier-digikey.csv` is this board's parts list (DigiKey's BOM
upload format, one line per part number). The order placed on 2026-11-05 is `../../amp-digikey-order.csv`;
its Notes column lists the stock substitutes. Check stock again before any later build.

- **U2:** the EUE suffix is the TSSOP; the ETE is the QFN. Don't substitute the MAX9722B: it has a fixed −2 V/V gain,
  and R25–R28 assume the A.
- **U1** is the automotive-grade TLV9061-Q1 in the same SOT-23-5 (DBV) package. The symbol's Value still reads
  TLV9061IDBVR; either part fits.
- **C0G for the filter caps** (C1, C3, C9, C16): X7R's capacitance changes with voltage, which adds distortion.
- **16 V for C7 and C5:** C7's 16 V part derates better under DC bias than a 10 V part.
- **Screw terminals:** J3, J5 and J6 are the Phoenix PT 1,5 blocks the footprints are drawn for; J6 is a single 4-way
  block.
- **0805 and 1206** passives, for an iron. R25–R28 are 0805 to fit around U2. C10/C11 sit at ≈ 0 V DC, so a 25 V X5R
  0805 part loses no capacitance to DC bias.
- **TP1** is a bare 2 mm copper pad. **Daisy sockets:** two 1×20 2.54 mm female headers, 8.5 mm tall (Sullins
  PPTC201LFBN-RC, S7018-ND).
- **JLC assembly:** the schematic has no LCSC part numbers; a JLC assembly order would need them added. Commit c8d6067
  has a set.
