# Seed3 Carrier rev 2 — design

How the board works now, and why. `CHANGES.md` lists what changed from rev 1. `../TEST_PLAN.md` is the bring-up and test procedure.
Keep this file current as the schematic and board change. Write down the design as it stands now, not the history behind it (git has that).

The carrier holds a Daisy Seed3 (A1, in two 1×20 sockets), the analog input and output stages, the headphone amp and the
connectors to the power board and display. Volume, tone, input trim and mute come from the touchscreen over the UART, so the
board has no pots or encoder. If there is a master volume encoder, it goes on the touchscreen / ESP32 side.

## Signal paths

U1 is a TLV9061 single op-amp (SOT-23-5), the guitar input buffer, on `+5V` (pin 5) and GND (pin 2). Its symbol,
`seed3-carrier:TLV9061DBV` in `seed3-carrier.kicad_sym`, follows the TL07x style: U1A is the op-amp and U1B the power pins.
The AUX input and both outputs connect to the Daisy with no op-amp (see "AUX input", "Headphone output" and "Speaker / line send").

### Mid-rail reference (VREF)
R6/R7 (10k/10k) from `+5V`, with C7 (47 µF): `VREF` ≈ 2.5 V. With 5k source impedance, C7 gives a ≈ 0.7 Hz corner, which keeps
noise on `+5V` (from the display) out of `VREF`. Its only load is R1.

### Guitar input (J1 → `AUDIO_IN_1`)
J1 tip → C1 (100 pF to GND, RF shunt) → C2 (1 µF) → R1 (1M to `VREF`) → R2 (1k) → U1A follower → R20 (470 Ω) → `AUDIO_IN_1`
(Daisy pin 16).
- J1's tip switch shorts the tip to GND when nothing is plugged in.
- **R1** sets both the 1 MΩ guitar load and the DC bias. **R2** is the only series resistance in this path. It protects U1A's input from plug-in transients.
- **Unity gain, no level pot.** A pot at mid travel put about 250 kΩ of source impedance in front of U1A, which added noise and an
  ~80 kHz pole. Input trim is done in firmware.
- **Passive pickups only, no pad.** Active pickups and boost pedals are out of scope. With the module's ≈ 5 kΩ input, R20 costs
  ≈ 0.8 dB, so the Daisy's 3.6 Vpp full scale is reached at ≈ 3.9 Vpp at J1: ≈ 12 dB above a 1 Vpp hard strum on passive pickups.
- **R20 (470 Ω) limits current into the Daisy pin.** U1 runs on 5 V and can swing ≈ 4.8 Vpp, past the Daisy's 3.6 Vpp full scale and
  ±1.8 V absolute maximum. Nothing in scope gets there, but if something does (a boost pedal, a fault), R20 limits the current into
  the pin's protection to ≈ 1–2 mA.
- **DC:** pin 16 sits at `VREF` (≈ 2.5 V) through R20. The Daisy's input is AC-coupled on the module, so no DC current flows.

### AUX input (J2 → `AUDIO_IN_2`)
J2 (SJ3-35063AG, 3.5 mm TRS) tip and ring → R3/R4 (10k each, passive stereo-to-mono sum) → summing node with R5 (3.3k to GND)
and C3 (1 nF, RF filter) → `AUDIO_IN_2` (Daisy pin 17) directly. J2's detect switch (pins 5 and 6) is not connected.
- **No buffer and no coupling cap.** The Seed3's audio inputs are AC-coupled on the module (Seed3 datasheet, Table 1 note), and the
  source is a phone or laptop output, so nothing needs biasing or buffering. The Daisy input itself is the load that sets the level.
- **Daisy input impedance:** the TAC5242's AC input impedance is 5 kΩ ±20% at its pins (TAC5242 datasheet, ADC parameters and
  section 7.3). The Seed3 datasheet doesn't give the module pin's value, so this assumes the pin connects to the codec through its
  coupling cap with no extra series resistance. Electrosmith's own input circuits drive the pin from an op-amp through 1k or 100 Ω
  (Figures 3.2 and 3.4), which fits. TEST_PLAN 5.17 measures the level with the Daisy fitted.
- **R5 sets the level, whatever the Daisy's input impedance is.** R3 ‖ R4 (5k) into R5 (3.3k) alone is a gain of 0.40 (−8.0 dB), so
  even if the module pin added no load at all, a 2 Vrms laptop output (5.7 Vpp) would reach it at 0.80 Vrms (2.25 Vpp, ±1.13 V peak).
  That is under the Daisy's 3.6 Vpp full scale and its ±1.8 V absolute maximum. With R5 at 100k the same worst case was ≈ 5.4 Vpp,
  so the design relied on the unpublished ≈ 5 kΩ input to stay in range. R5 is also the DC return for the source's coupling caps, and
  it holds the node at GND with an empty jack or with the Daisy out.
- **C3** filters RF picked up on the cable, for example from the phone itself. It sees R3 ‖ R4 ‖ R5 ‖ 5k ≈ 1.4k, so the corner is
  ≈ 110 kHz (≈ 80 kHz with the Daisy out).
- **Level:** the same signal on both channels sees R3 ‖ R4 = 5k into R5 ‖ the Daisy's input. With the codec at 4k / 5k / 6k that is
  −11.5 / −10.9 / −10.5 dB, so 2 Vrms reaches the Daisy at 1.5–1.7 Vpp. Most backing tracks are close to this case, since bass, kick
  and vocals sit in the centre. One channel alone (the other driven at 0 V) sees 10k into 10k ‖ R5 ‖ 5k, a gain of 0.14 (−16.9 dB).
  A quiet 0.5 Vrms phone lands around −19 dBFS, so the firmware adds gain for phones and trims out the ±0.5 dB spread.
- **Source load:** each channel sees ≈ 12k (one channel driven) to ≈ 14k (both driven). Phone and laptop headphone outputs drive this easily.
- **Noise:** the node sits at ≈ 1.4k rather than at an op-amp output. Its thermal noise (≈ 5 nV/√Hz) is far below a backing track's level.
- **Use:** backing tracks bypass NAM. The firmware mixes `AUDIO_IN_2` in after the amp model, to both outputs.

### Headphone output (`AUDIO_OUT_1` → J4)
`AUDIO_OUT_1` (Daisy pin 18) → R10 (3.3k) / C9 (1 nF to GND) → `HP_SOURCE` → C10/C11 (4.7 µF each) → U2 INL−/INR−.
U2 (TPA6132A2RTE) drives J4 (`HP_L` tip, `HP_R` ring) directly.
- **What the Seed3 outputs are rated for:** 1 Vrms at 0 dBFS (Seed3 datasheet, Table 3). The datasheet gives no output impedance,
  minimum load or coupling-cap value for pins 18/19, and says only the *inputs* are AC-coupled.
  - **Line-out mode, not headphones.** The TAC5242 drives 16 Ω headphones (62.5 mW) only in its differential or pseudo-differential
    modes, set by its MD4/MD5 pins on the module. The Seed3 brings out one single-ended pin per channel at 1 Vrms, with single-ended
    AC-coupled inputs. That matches only MD5 high / MD4 low, "Single-ended output; Line-out only" (TAC5242 datasheet, Table 7-10),
    whose minimum load is 600 Ω. The module cannot drive headphones, which is why U2 is here. Electrosmith's own headphone circuit
    (Seed3 datasheet, Figure 3.9) also adds an amp (TPA6110A2).
  - **DC level: probably 0 V, not confirmed.** Figure 3.9 wires pin 18 straight across a volume pot to GND, which only works if the pin
    sits at 0 V DC, so the outputs are most likely AC-coupled on the module. TEST_PLAN 5.16 measures it with the Daisy fitted.
- **No buffer between the Daisy and U2.** The Daisy sees R10 plus U2's two 26.4 kΩ inputs in parallel, ≈ 16.5 kΩ, far above the 600 Ω
  line-out minimum. Electrosmith's reference circuits load the pin with 10k through a 10 µF cap (line out, Figure 3.3) and with a
  pot to GND (headphone amp, Figure 3.9).
- **R10/C9** filter the DAC's out-of-band noise before U2. With U2's 13.2 kΩ load the corner is ≈ 60 kHz (R10 ‖ 13.2 kΩ with 1 nF).
- **Level:** R10 and U2's 13.2 kΩ load form a −1.9 dB divider, so full scale reaches U2's inputs at ≈ 0.80 Vrms, and U2's −6 dB gain
  puts ≈ 0.40 Vrms on each output: 10 mW into 16 Ω, 5 mW into 32 Ω.
- **Why −6 dB, not 0 dB:** into headphone loads U2's limit is power, not voltage: 25 mW into 16 Ω and 22 mW into 32 Ω at 1 % THD
  (≈ 0.63 / 0.84 Vrms, TPA6132A2 datasheet, section 6.6). The 1.1 Vrms figure is into 100 Ω. At 0 dB, full scale (≈ 0.75 Vrms) would
  clip 16 Ω headphones and leave about 1 dB of margin at 32 Ω. At −6 dB the margin is 4 dB at 16 Ω and 6 dB at 32 Ω, and the hiss
  drops with the gain. 5 mW is ≈ 105 dB SPL in typical 98 dB/mW headphones.
- **Low end:** C10/C11 into U2's 26.4 kΩ input is a 1.3 Hz high-pass. The Daisy's own output coupling cap adds a second one; its value isn't published.
- **U2, TPA6132A2 (DirectPath):** an internal charge pump gives it a negative rail, so its outputs sit at 0 V with no output caps
  and the bass stays flat to a few Hz. It has built-in click-and-pop suppression and short-circuit and thermal protection. Its output
  swing comes from its own charge-pump rails, not VDD, so its limits (above) don't change with the supply.
  VDD is rated 2.3–5.5 V, so it runs from `+5V`.
- **U2 wiring:** single-ended inputs per the datasheet (INL+/INR+ to GND; the mono source drives both channels). Gain is −6 dB
  (G0 and G1 to GND), inverting. EN (active high) is tied to `+5V`, so U2 is on whenever `+5V` is up (see "Output mute"). C12 (2.2 µF, VDD), C15 (2.2 µF, HPVDD),
  C13 (1 µF, charge-pump flying cap) and C14 (2.2 µF, HPVSS), all 0805 X5R or better. HPVDD and HPVSS are generated inside U2:
  they get caps only (and PWR_FLAGs for ERC), never an external supply.
- **Symbol:** `seed3-carrier:TPA6132A2RTE` in `seed3-carrier.kicad_sym` is the stock KiCad symbol with the pins rearranged:
  grounded pins on the bottom, charge-pump and output pins on the right, supplies on top.

### Headphone detect (`HP_DETECT`)
J4 (Same Sky SJ3-35063AG, 3.5 mm stereo, through hole; [datasheet](https://www.sameskydevices.com/product/resource/sj3-3506x.pdf)):
pins 1/2/3 are sleeve/ring/tip on GND/`HP_R`/`HP_L`. Pins 5 and 6 are an isolated normally-open switch that closes when a plug is
inserted: pin 5 to GND, pin 6 straight to `HP_DETECT` (Daisy pin 23, PA3). TP1 sits on it. Pin 4 isn't fitted on this variant.
- **No external pull-up, series resistor or RC.** The switch is a mechanically actuated contact on this board, not on a cable, and
  isolated from the plug. The firmware enables PA3's internal pull-up and debounces it. This matches the Seed3 datasheet's own switch
  circuits (Figures 2.1 and 2.2: switch to GND, internal pull-up, "Any GPIO").
- **Low = headphones in.**
- **Footprint:** `Seed3_Carrier.pretty/Jack_3.5mm_SameSky_SJ3-35063AG_Horizontal.kicad_mod`, drawn from the datasheet's recommended
  PCB layout. The jack face sits at the board edge (X = −2.4 mm from pin 1), with the nose overhanging. J2 uses the same part and footprint.
  Every pad, peg and the face position match the recommended layout in the Same Sky SJ3-3506X datasheet (rev 1.01, page 2), checked
  2026-10-26. Pin 4 is left out because the AG variant doesn't fit it.

### Speaker send (`AUDIO_OUT_2` → J5)
`AUDIO_OUT_2` (Daisy pin 19) → R11/C16 (1k/3.3 nF, ~48 kHz low-pass) → `LINE_OUT`, with R12 (100k) to GND. `LINE_OUT` goes to
J5 pin 1 (LINE+), and J5 pin 2 (LINE−) is `LINE_REF`, GND through R21 (1k). There is no external line out: recording to a DAW goes
through the Daisy's USB-C.
- **No buffer**, for the same reason as the headphone path: R11 plus a ≥ 10k amp input is far above the 600 Ω line-out minimum (see
  "What the Seed3 outputs are rated for"). With no `VREF` bias or coupling caps in the path, `LINE_OUT` doesn't drift at power-on.
- **No DC-blocking cap: this path assumes pin 19 sits at 0 V DC.** The outputs are most likely AC-coupled on the module (see "DC level"
  under "Headphone output"), so a cap here would only add a part. If TEST_PLAN 5.16 finds more than a few tens of mV at pin 19, that DC
  reaches J5, R12 and the speaker amp, and the fix is a 10 µF cap in series between C16 and `LINE_OUT`, which needs a cut trace or a respin.
- **R11** is the output impedance and isolates the Daisy from cable capacitance. With R21, a differential input sees a 2k source:
  into 10k (with R12) it costs ≈ 1.7 dB (≈ 0.83 Vrms at full scale), and ≈ 3.0 dB into 5k. Cable capacitance adds to C16 and lowers the corner, ≈ 44 kHz with 3 m of typical
  cable. If `LINE_OUT` is shorted, the Daisy sees R11 alone: 1k, still above its 600 Ω minimum load. A lower R11 would cut that margin.
- **R12** gives the Daisy's output coupling cap a DC return, so `LINE_OUT` sits at 0 V with nothing plugged in.
- **J5** is a 2-way 3.5 mm screw terminal (KF350-3.5-2P) on the right edge: pin 1 LINE+ (`LINE_OUT`), pin 2 LINE− (`LINE_REF`),
  marked on the silkscreen. It feeds the speaker amp on the power board (or an off-the-shelf class D module while prototyping). Use a
  short twisted pair routed away from the guitar input and speaker wires.
- **Pseudo-differential output for a differential amp input.** The Daisy has one output pin per channel, so LINE− is the carrier's
  ground rather than an inverted copy of the signal. Wire LINE+ to the amp's IN+ and LINE− to its IN− **only**, never to the amp's
  GND as well. The amp then amplifies only the difference between the two wires, and any voltage between the two boards' grounds
  (the power board's supply current flowing in J6's GND wire) is rejected instead of added to the speaker signal. Tied to the amp's
  GND, LINE− would close a ground loop through J6 and J5.
- **R21 (1k) balances the two legs.** LINE+ comes through R11 (1k), so LINE− gets the same 1k to GND. The amp's common-mode rejection
  depends on both inputs seeing equal source impedances: with LINE− a hard ground, a 1k imbalance would let part of the ground noise
  through. C16 makes LINE+ slightly lower impedance above ≈ 20 kHz, which only matters out of band. With R21, LINE− is still DC-referenced
  to GND, so a shorted pair only loads the Daisy with R11 + R21 (2k).
- **Why a separate speaker output:** muting in firmware means the speaker amp can be shut down while headphones are in (saving battery),
  mute and unmute can ramp without clicks, and the speaker and headphones get independent levels.
- **Speaker wiring** is on the power board, not here: the cone's spade tabs (6.3 mm / 4.8 mm) take crimped quick-disconnects.
  Most class D amps have a bridged output, so neither speaker wire may be grounded.

### Jack ESD protection (D1–D5)
Every jack contact that carries a signal has a bidirectional ESD diode to GND, placed at the jack: D1 `GTR_TIP` (J1 tip), D2/D3
`AUX_TIP`/`AUX_RING` (J2), D4/D5 `HP_L`/`HP_R` (J4). All five are Nexperia PESD5V0S1BA (SOD-323, C19224).
- **Why:** these contacts are touched and hot-plugged. Before D1–D5 the guitar input's only protection was R2 and U1's own diodes, and
  the AUX input ran straight to the Daisy through R3/R4. U2's outputs are rated 8 kV HBM, but a jack sees IEC 61000-4-2 discharges,
  which are harsher, so J4 gets diodes too.
- **Why this part:** bidirectional, so it never conducts on the negative half of an audio signal. 5 V working voltage: every signal on
  these contacts stays below it (the largest, a hot active guitar, is ≈ ±2.4 V where U1 clips it). 5 nA leakage, so it doesn't load
  the 1 MΩ guitar input, and 35 pF, small next to a guitar cable's few hundred pF.
- **Not protected:** the J2/J4 detect switches (pins 5/6) are isolated from the plug, so nothing reaches them.

### Output mute (STM32 watchdog)
A hung Daisy can loop its last audio buffer at full level, so every output must go silent when audio stops.
- **Headphones: no hardware mute.** U2's EN is tied to `+5V`. The codec mutes the headphones (see "The codec mutes"), the same way
  it mutes the speaker send. U2's own click-and-pop suppression covers its power-up and power-down.
- `SPK_EN` (Daisy pin 28) drives Q2's gate, with R17 (100k) pull-down. Q2 (2N7002) pulls `SPK_MUTE` (J6 pin 4) to GND, which means
  speaker on. The power board pulls `SPK_MUTE` up, which means muted.
- **How it works:** the firmware feeds the STM32's independent watchdog (IWDG) only from the audio callback. The IWDG runs on its
  own clock, so if the callback stops (hung firmware, stalled DMA, fault handler), it resets the STM32. During a reset, and while the
  Daisy is booting or in DFU, its pins float, and R17 holds `SPK_EN` low (speaker amp muted).
- **The codec mutes.** The STM32 clocks the TAC5242, and the TAC5242 powers down its DAC by itself when its audio clocks stop
  (TAC5242 datasheet, section 7.4.1). An IWDG reset therefore silences pins 18/19, and with them J4 and J5. The headphones have no amp mute.
  This doesn't help while the clocks keep running, such as a DMA looping a stale buffer with the CPU hung, which is why the IWDG has
  to reset the chip. The datasheet doesn't say whether the power-down clicks; TEST_PLAN 5.16 records it.
- **Why Q2 instead of driving `SPK_MUTE` from the Daisy pin:** the power board can pull `SPK_MUTE` up to any voltage, and an unpowered
  Daisy isn't back-powered through it.
- **Trade-off:** an external retriggerable one-shot watching an audio-callback toggle would watch the audio from outside the STM32.
  The IWDG is inside the chip, so the mute depends on the firmware feeding it only from the audio callback. Never feed it from the main loop.
  The IWDG does the job with 7 fewer parts.
- **Why U2's EN isn't driven from the Daisy:** the Daisy can run from USB while `+5V` (U2's VDD) is off (see "Running from USB alone"),
  and EN is rated to VDD + 0.3 V. A Daisy pin on EN would need a level translator with supply isolation, its two decoupling caps and a
  pull-down. The codec's power-down already covers a hung Daisy. The cost: U2 is on whenever `+5V` is, so anything on pin 18 while the
  Daisy boots reaches the headphones (TEST_PLAN 7.1 records it), and U2 draws its few mA quiescent while only the speaker is in use.

## Power

`5V_IN` arrives on J6 pin 1 and goes through Q1 (AO3401A P-FET, reverse-polarity protection) onto `+5V`. `+5V` feeds Daisy VIN
(pin 39), U1, U2, `VREF` and the `5V_SENSE` divider (R18/R19). The display takes its power from the power board, not from here.
- **Why Q1:** a screw terminal has no key, so 5 V and GND can land on each other's terminals, as can swapped clip leads on a bench
  supply (TEST_PLAN 2.12 tests this). The Seed3's VIN is reverse-protected on the module, but U1 and U2 are not. Q1 drops about 50 mV at 1 A.
- **Wires on the wrong terminal:** Q1 only covers 5 V and GND swapped. If 5 V lands on a signal terminal: on `BATT_SENSE_CONN`, R13 (10k)
  limits the current into the Daisy pin to ≈ 0.2 mA; on `SPK_MUTE`, Q2 is rated 60 V; on J3, R8 and R9 (10k each) limit it; on J5's
  LINE+, R11 (1k) puts ≈ 3 mA into the codec output's protection, which it will probably survive but which is the worst case. GND sits
  between 5V and the signals on J6, so a stray strand from the 5 V wire can only reach GND. Check every terminal against its silkscreen
  label before powering up.
- **Bulk at the power entry:** C5 (47 µF low-ESR electrolytic) and C4 (100 nF) at Q1's output. C5's ESR damps the ringing between the
  wiring's inductance and the ceramics. C4 is the only ceramic at the entry, and the Seed3 datasheet recommends extra filtering on VIN.
- **Local decoupling:** C6 at U1 pin 5 and C12 at U2 VDD.
- **Display supply:** the power board feeds the display directly. Its current pulses (ESP32 Wi-Fi, backlight PWM) never flow through
  Q1 or `+5V`, the rail that feeds the analog circuits, and its current draw doesn't count against J6.

### Running from USB alone
The Seed3 runs from its own USB port, and the datasheet says USB and VIN can be connected together, so USB doesn't appear to drive the
VIN pin. With USB plugged in and the power board off (flashing or debugging on the bench), the Daisy runs while `+5V` is at 0 V. Any
Daisy output that is high then pushes current into an unpowered part on the carrier through that part's input protection diodes.
- **Q1 conducts backwards** if `+5V` is lifted, because its gate is tied to GND. That would only leak a little current to the power
  board. Nothing on the carrier back-powers `+5V`.
- **Display UART:** with the power board off, the display is unpowered too, and Daisy TX idles high into it. R8 (10k) limits that
  current to ≈ 0.27 mA. See "Display connector (J3)".
- **Headphone input (`5V_SENSE`):** C10/C11 pass pin 18's audio straight to U2's inputs, which are rated only from HPVSS − 0.3 V to
  HPVDD + 0.3 V (TPA6132A2 datasheet, section 6.1). U2's charge pump makes both rails, so with `+5V` off they sit at 0 V and the
  inputs may only see ±0.3 V. Full scale is ±1.4 V. R10 limits the current into U2's protection diodes to ≈ 0.3 mA, but that is still
  outside the rating. So the firmware has to know whether `+5V` is up: R18/R19 (100k/100k) divide `+5V` to ≈ 2.5 V on `5V_SENSE`
  (Daisy pin 22, ADC_0). While it reads low, the firmware keeps both outputs at digital silence (see "Firmware requirements").
  - **Why not `BATT_SENSE`:** a bench supply on J6 gives it no reading, so it can't tell whether `+5V` is up.
  - **Why 100k/100k:** 2.5 V is well inside the ADC range and the divider draws 25 µA. The Daisy's VIN is `+5V`, so whenever `+5V` is
    up the Daisy is powered too, and the divider can't back-power it. With `+5V` off, R19 holds the pin at 0 V.
  - **No filter cap:** the source impedance is 50k, so the firmware uses a long ADC sample time instead of a cap like C17.
  - With `+5V` up, U2's charge pump is always running (EN is tied to `+5V`), so its input rating is met whenever it is powered.
  - **Limit: a fast power loss.** The firmware reacts within one or two audio blocks plus the codec's output delay, a few ms. If `+5V`
    and U2's rails collapse faster than that (the 5 V wire pulled out of J6 under load), the last few ms of audio still reach
    U2's unpowered inputs, limited to ≈ 0.3 mA by R10. TEST_PLAN 5.18 measures this.

## Connectors

### Power board connector (J6)
J6 is a 4-way 3.5 mm screw terminal on the rear edge, made of two KF350-3.5-2P blocks slid together (LCSC has no 4-way KF350). Wires
screw in, so there's nothing to crimp and a damaged wire is quick to replace. It carries power, the battery level and the speaker mute.
The power switch is on the power board, which cuts the 5 V output itself.

| Pin | Silkscreen | Net | Direction | Daisy pin | Use |
|---|---|---|---|---|---|
| 1 | 5V | `5V_IN` | Power board → carrier | 39 (VIN) via Q1 | 5 V supply |
| 2 | GND | GND | — | 20 / 40 | Ground |
| 3 | BAT | `BATT_SENSE_CONN` | Power board → carrier | 25 (`BATT_SENSE`) | Battery voltage scaled to ≤ 3.3 V. R13 (10k) and C17 (100 nF) filter it into the ADC |
| 4 | MUTE | `SPK_MUTE` | Carrier → power board | 28 (`SPK_EN`) via Q2 | Open-drain speaker-amp mute (see "Output mute") |

- **Pin order:** seen from the wire side, the terminals read 5V, GND, BAT, MUTE from left to right. GND sits between 5V and the signals.
- **One 5 V and one GND pin:** the carrier draws well under 1 A now that the display has its own supply, and a KF350 contact is rated
  10 A. A single GND is fine because the speaker amp's input is differential and LINE− connects only to the amp's IN− (see "Speaker
  send"), so no supply current returns through J5.
- **R13 is 10k:** while the amp is off, the power board's battery divider can still hold `BATT_SENSE_CONN` near 3.3 V. Through 1k that
  would push ~3 mA into the unpowered Daisy's pin protection diodes and back-power its 3.3 V rail. 10k limits it to ~0.3 mA.
  With C17 the filter corner is ~160 Hz, far above battery changes. C17 also supplies the ADC's sampling charge.

**Power board requirements**
- Keep `BATT_SENSE_CONN` within 0–3.3 V.
- Switch the `BATT_SENSE` divider off with the 5 V output (or give it ≥ 100k source impedance), so it doesn't drain the battery or feed
  an unpowered Daisy while the amp is off.
- Pull `SPK_MUTE` up on the amp side so the amp is muted when this board is unpowered or unplugged.
- Provide the power switch and a low-battery cutoff: the carrier can no longer turn the power off itself.
- Supply the display's 5 V directly, with its own wire pair.

### Display connector (J3)
J3 is a 3-way 3.5 mm screw terminal (KF350-3.5-3P) on the rear edge next to J6: 1 GND, 2 `UART_TX_CONN` (TX), 3 `UART_RX_CONN` (RX),
marked on the silkscreen. The display takes its power from the power board, so only the UART and its ground reference come here.
R8 (10k, Daisy TX) and R9 (10k, Daisy RX) sit in series with the UART between J3 and Daisy USART1 (pins 14/15,
`DISPLAY_UART_TX`/`DISPLAY_UART_RX`). They limit current if a wire lands on the wrong terminal or the display and the Daisy power up at
different times, and add a little ESD margin.
- **J3's GND is needed:** the UART needs a common reference. The display's ground also returns to the power board with its power wire,
  so some display return current comes back through J3's GND and across to J6's. J3 and J6 sit side by side on the rear edge, so that
  current stays in the rear-right corner.
- **R8 is 10k:** with the Daisy on USB alone and the power board off (see "Running from USB alone"), its TX idles high into an
  unpowered display. 10k keeps the current into the display's RX protection diode to ≈ 0.27 mA.
- **R9 is 10k too:** the display and the Daisy both run from the power board, but they no longer share a supply rail, so their power-up
  order isn't fixed. 10k limits the current from a powered display into an unpowered Daisy's RX pin the same way.
- **Baud rate limit:** 10k with ~50 pF of cable and pin capacitance is a ≈ 0.5 µs time constant. That is fine up to 230400 baud
  (a 4.3 µs bit), but not for 921600. To go faster, lower R8 and R9 and accept more current in those cases.

### Daisy pins
Used: 14/15 (display UART), 16/17 (audio in), 18/19 (audio out), 20/40 (GND), 22 `5V_SENSE`, 23 `HP_DETECT`, 25 `BATT_SENSE`, 28 `SPK_EN`,
39 VIN. Every other pin, including `3V3_A` (21), `3V3_D` (38) and USB D−/D+ (36/37), is
marked no-connect. With the Daisy out, its sockets (A1) give probe access to every carrier net, so there are no breakout headers.
USB stays on the Daisy's own connector.

## Firmware requirements
- Run the display UART at 230400 baud or less (R8, see "Display connector (J3)"). Take volume and mute from the display over it. Ramp volume changes.
- Start the IWDG early in boot, with a timeout of about 10 ms. Feed it **only** from the audio callback.
- Send the speaker mix to output 2 and headphones to output 1.
- Read `HP_DETECT` (pin 23, PA3) with its internal pull-up enabled: **low = headphones in**. Debounce it. When headphones go in, ramp
  `AUDIO_OUT_2` down, then drive `SPK_EN` low. Reverse it when they come out: raise `SPK_EN`, then ramp `AUDIO_OUT_2` up.
- Add an output clamp or limiter and NaN/Inf guard at the end of the chain.
- Save settings when they change (debounced, to spare the flash), not at shutdown. The power switch is on the power board, so the
  power can disappear at any time.
- Initialise `SPK_EN` (pin 28) as a low output. Drive it high to enable the speaker amp after the first audio callback has started,
  low when headphones are in.
- Start the codec with its output at digital silence and ramp up. U2 is always on, so the headphones hear whatever pin 18 does from boot.
- Read `BATT_SENSE` (pin 25, ADC) and send the battery level to the display every few seconds. Warn on the display when it gets low;
  the power board cuts the power at its own low-battery threshold.
- Read `5V_SENSE` (pin 22, ADC_0) with the longest ADC sample time (its source impedance is 50k). It reads ≈ 2.4–2.5 V with `+5V`
  at 4.85–5.0 V.
  - **Before starting audio:** require it above 2.35 V (`+5V` ≥ 4.7 V) for at least 10 ms. U2's start-up time is 5 ms (TPA6132A2
    datasheet, section 6.6), so its charge pump has settled by then. Then ramp the outputs up.
  - **While running:** sample it from the audio callback on every block (ADC on DMA, so the callback only reads the last value). Below
    2.2 V (`+5V` < 4.4 V, still well above U2's 2.3 V minimum) write silence from that block on. Hold the outputs silent until the
    start-up condition above is met again. The thresholds give 0.15 V of hysteresis.
  - This applies on USB alone on the bench too.
- Read `AUDIO_IN_2` (the AUX input, mono) and mix it in after the NAM model and cabinet EQ, with its own level control from the display.
  It goes to both outputs.

## Open items
- **Test the watchdog mute:** stall the audio callback in a debug build. Check that J4 and J5 go silent and `SPK_MUTE` mutes within ~10 ms.
- **Speaker amp mute polarity:** `SPK_MUTE` floats (pulled up = muted) or is pulled low (= playing). Check that the chosen amp's
  mute/shutdown pin matches, or invert it on the power board.
- **`BATT_SENSE` divider:** the power board sets the ratio. Record it here so the firmware can convert the reading to volts.
- **J6 fit:** J6 is two KF350-3.5-2P blocks slid together on a 4-position footprint. Check that the interlocked pair keeps the 3.5 mm
  pitch across the joint before soldering, or buy a true 4-way 3.5 mm block elsewhere.
- **Wire ends:** use ferrules or solid wire in the screw terminals. Tinned stranded wire creeps under screw pressure and loosens.
- **2N7002 gate drive:** Q2 is driven from 3.3 V logic. That should be enough for the small pull-up current on `SPK_MUTE`, but check it on the board.
- **Headphone level:** check on the bench that 0.40 Vrms is loud enough with the intended headphones (TEST_PLAN 7.8). If not, moving G0
  to `+5V` (0 dB) only suits headphones of 32 Ω or more, since full scale then clips 16 Ω. Lowering R10 gains little at −6 dB (1k gives ≈ 0.46 Vrms).
- **AUX input level:** TEST_PLAN 5.17 checks the level with the Daisy fitted (the Daisy's input impedance isn't published). Then measure
  a phone and a laptop at full volume through J2: 2 Vrms should reach 1.5–1.7 Vpp, and it can't exceed 2.25 Vpp whatever the module's
  input is. If quiet phones need too much firmware gain, R5 can go up to 4.7k (≈ −9.7 dB with a 5 kΩ module input, 2.7 Vpp
  worst case). Above that the no-load worst case passes full scale.
- **Hot passive pickups:** the Daisy's full scale is reached at ≈ 3.9 Vpp at J1 (see "Guitar input"). Play the hottest passive
  guitar available hard into J1 (TEST_PLAN 5.19) and confirm its peaks stay below that.
- **Polarity:** U2 inverts the signal. Decide whether the firmware negates the output.
- **Headphone low-end corner with the Daisy fitted:** TEST_PLAN 3B.3 (Daisy out) checks C10/C11 alone (≈ 1.3 Hz). Sweep it again in
  Stage 5 with the Daisy in and record the corner.
- **Headphone noise while the Daisy boots:** U2 is always on (EN tied to `+5V`). Check TEST_PLAN 7.1 and 7.6 for clicks on J4 at
  power-up, reset and DFU entry. If they are loud, the fallback is to drive EN from the Daisy through a level translator again (git history has it).
- **USB-alone power transitions:** TEST_PLAN 5.18 scopes U2's input and rails while J6 power is removed and restored with USB
  connected and audio playing. Record how long the input stays outside HPVSS − 0.3 V … HPVDD + 0.3 V. If it is more than a few ms at
  full scale, raise the firmware's 2.2 V threshold or shorten the audio block.
- **Layout:** placement, the GND vias and the analog routing are done (see "Passive placement"). Still to route: Daisy VIN, R18,
  the power board signals (J6 to R13 and Q2, then on to the Daisy), the display UART (J3 to R8/R9, then to the Daisy) and `HP_DETECT`.
  All are DC or slow.
- **Line-out level:** with no buffer, R11 (1k) is the output impedance. Once the speaker amp is chosen, check its input impedance:
  the loss is ≈ 1.7 dB into 10k (R11 + R21) and grows below that.
- **U2 stock:** JLC had only 65 TPA6132A2RTER on 2026-10-25. Recheck before ordering (see "Parts sourcing").
- **Mechanical:** the outline, jack and hole positions are a first pass with no enclosure yet. Recheck them against the enclosure drawing.
- **Front panel thickness:** under 3 mm, Neutrik's limit for the NRJ4HF's nut. The SJ3 noses stand 3.0 mm proud of their faces, so a
  panel up to 3 mm also takes them.

## Layout

### Stackup
JLCPCB standard 4-layer, 1.6 mm (JLC04161H-7628). Outer copper 1 oz, inner 0.5 oz. Check the dielectric thicknesses on JLC's
stackup page when ordering.

This is the "ground in the middle" stackup that Bogatin recommends as the default for 4-layer boards. Page numbers below refer to
Eric Bogatin, *Bogatin's Practical Guide to Prototype Breadboard and PCB Design* (Artech House, 2021).

| Layer | Use | To next layer |
|---|---|---|
| L1 (top) | Parts, most signal routing, `+5V` and `5V_IN` as wide traces (≥ 1 mm) | 0.21 mm prepreg |
| L2 | Solid GND. No traces, no cuts | ~1.07 mm core |
| L3 | Solid GND. No traces, no cuts | 0.21 mm prepreg |
| L4 (bottom) | Remaining signals, power traces that don't fit on L1 | — |

- **Why ground in the middle:** both signal layers sit 0.21 mm from a solid GND plane. All routing can be seen and probed from the
  outside, and the symmetrical build won't warp (p. 480). The JLC build above is the book's own example (p. 475, Fig. 23.3).
- **Why no power plane:** a power plane is only needed above about 20 A (pp. 466, 479). The board draws about 1 A at most, and a 20 mil
  (0.5 mm) trace carries 3 A (p. 466). `+5V` also feeds the Daisy, which pulls digital current pulses. A full power plane would spread
  that rail under the guitar input and the analog circuits.
- **Why power is on L1/L4, not L3:** with L2 and L3 both GND, a signal that goes from L1 to L4 can return through a via between the
  two planes. A power layer in the middle would block that path (pp. 467, 479–480). Keep the power traces short and wide between the
  decoupling capacitors and the IC pins, where low inductance matters (p. 466).
- **Return vias:** next to every signal via that goes from L1 to L4, place a GND via that ties L2 to L3 (pp. 479, 483). Do the same
  where a power trace changes layers (p. 467). Keep signal-via clearance holes from merging into slots in L2/L3 (p. 478).
- **No copper pour on L1/L4:** a pour on a signal layer adds little, and a poorly stitched one increases crosstalk. It also makes the
  board harder to debug and can leave orphaned copper islands (pp. 461–464). The return path is L2/L3. Exceptions: the TPA6132A2
  exposed pad and any local GND area a part needs, each stitched to L2/L3 with vias. If JLC wants copper balanced on the outer layers
  for plating, ask them to add thieving pads (p. 464).
- **One GND net, no split.** A split only helps with sub-millivolt noise below 100 kHz when more than 10 A of low-frequency current
  flows in the ground plane (p. 465). The board stays well under that. Separate analog and digital areas by placement. At audio
  frequencies return current takes the lowest-resistance path, so placement matters more than the stackup:
  - Put J6 (power in) and J3 (display) side by side, so the display return current that comes back through J3's GND doesn't pass
    under U1, U2, J1 or J2.
  - Route U2's SGND (pin 15) straight to J4's sleeve, as the datasheet requires, and put vias under U2's exposed pad down to L2.
- **Why 1.6 mm:** the ¼" jacks, the SJ3 jacks and the Daisy sockets take force at every plug-in. It is also the cheapest thickness.
- **No controlled impedance.** USB doesn't leave the Daisy, and the module handles it itself.
- L2 and L3 each have one GND zone covering the board, inset 0.5 mm from the edge.

### Board outline and placement
90 × 56.5 mm, 2 mm corner radius. The front panel is the bottom edge (y = 56.5 mm). Coordinates are from the board's
top-left corner. The jacks set the width. Laying the Daisy flat along the rear edge, with no breakout headers, sets the depth.

| Part | Position | Why |
|---|---|---|
| J1 (guitar in), J2 (AUX), J4 (headphones) | Front edge, left to right. J1 at x ≈ 2–19 mm, J2's sleeve at x = 41.9 mm, J4's at x = 58.0 mm. All three body faces sit on the front edge | All panel jacks on one edge. Every jack mounts against the back of a flat front panel, so their faces line up, not their nose tips. J1 (Neutrik NRJ4HF) is rear-mounted: its face presses on the panel and a nut on its 8.9 mm threaded nose clamps it from the front (Ø11.2 mm panel hole). The SJ3 faces sit at the edge as drawn in the footprint, with their 3.0 mm noses into the panel holes. Inputs are on the left, outputs on the right. J2 lines its ring and tip up under the AUX block, and J4 lines its tip up under U2's OUTL |
| A1 (Daisy) | Flat along the rear edge, rotated 90°, USB on the left edge | USB stays reachable for flashing. Pins 1–20 face the front, so audio pins 16–19 face the analog band. Pins 21–40 (power, controls, `HP_DETECT`) face the rear |
| U1 (TLV9061) | At the end of the guitar row, beside J1's tip | The high-impedance guitar input stays short. U1's low-impedance output makes the long run to Daisy pin 16 |
| U2 (TPA6132A2) | Above J4, rotated 180° | OUTL and SGND drop straight down to J4's tip and sleeve |
| J6 (power board), J3 (display) | Screw terminals side by side on the rear edge, J6 against the Daisy's right end and J3 under the rear-right hole, wire openings facing out | Wires leave straight off the board. Any display return current through J3's GND flows to J6 without passing under U1, U2, J1 or J2. Daisy VIN (pin 39) is at the far left of the rear row, so run `+5V` to it under the Daisy, away from the analog section |
| J5 (speaker send) | Screw terminal on the right edge between the two right-hand holes, wire openings facing out | J5 carries LINE+ and LINE− to a differential amp input and no ground current, so it doesn't need to sit by J6. The right edge keeps the speaker wiring away from the guitar input |

### Passive placement
All parts sit on the top side, in blocks next to the pins they serve. Each filter or divider sits at its load. The long runs are
then the low-impedance ones (a source output, the DAC output, an op-amp output), and every high-impedance node is a few mm long.
The analog section fills the band between the Daisy and the front jacks, with every audio net on L1. Power, the display and the power
board controls sit in the rear-right corner beside the Daisy, as far from J1, U1 and U2 as the board allows. The power board's
regulators and class D amp are the noisiest things the carrier connects to.

- **Guitar input (most sensitive):** one straight row on L1 at the height of J1's tip: J1 tip → D1 → C1 → C2 → R2 → U1 pin 3, about
  18 mm, with no vias. D1 and C1 hang below the row, with their GND vias on the far side. R1 rises from the C2/R2 node to `VREF`, so
  the 1 MΩ node is about 4.5 mm of trace.
- **U1** (SOT-23-5, rotated −90°): + top-left (from R2), GND top-middle (via straight up), out top-right, − bottom-left, V+
  bottom-right. The follower feedback, pin 1 to pin 4, runs diagonally under the body. R20 stands just above pin 1. `AUDIO_IN_1` runs
  from R20's top pad up the left side of the AUX block to Daisy pin 16.
- **VREF:** R6, R7 and C7 form a square just above-left of R1, so `VREF` is a few mm of L1. R6's `+5V` arrives on L4.
- **AUX input:** the AUX block sits right under Daisy pins 16–17. R4 and R3 stand over J2's ring and tip, R5 sits between them, and C3
  sits on the trunk to pin 17. J2's ring and tip run straight up on L1, about 20 mm, driven by the source, so their impedance is low.
  The ≈ 2 kΩ `AUDIO_IN_2` node is about 11 mm of trace. Nothing crosses the guitar row.
- **Headphone path:** `AUDIO_OUT_1`, the DAC output, runs from pin 18 down past the AUX block and across to R10. R10, C11, C10 and C9 form a column on
  U2's input side, so `HP_SOURCE` (3.3 kΩ) is about 7 mm long.
- **U2** (rotated 180°): inputs on the right, charge pump on the left, OUTR and HPVSS on the top edge, EN, VDD, SGND and OUTL on the
  bottom edge. OUTL drops straight down on L1 to J4's tip, and SGND runs beside it to J4's sleeve, as the datasheet asks. OUTR takes
  one via to L4, with a GND return via beside it, and runs to J4's ring. J4's ring is on the left and its tip on the right, so no
  rotation puts all three outputs on L1 without a crossing. This one keeps the OUTL/SGND pair on L1.
- **Decoupling:** C6 sits right of U1, its `+5V` pad 0.8 mm from pin 5. Around U2: C13 (flying cap) left of pins 9 and 11, C14 (HPVSS)
  above pin 8, C12 (VDD and EN) just below pins 13 and 14, each within 1 mm. C15 (HPVDD) sits below-left of pin 12, 1.9 mm away,
  because HPVDD's trace has to clear C13. C12's `+5V` arrives on L4 through a via beside it.
- **Analog `+5V`:** its own branch on L4 from C5 at the power entry, down to C12 at U2, left to C6 at U1, then up to R6. It
  carries only the analog parts' current. The Daisy's and the display's current pulses never flow in it. L3 sits directly above it as
  its return path, and a GND return via sits next to each layer change.
- **Speaker send:** R11, C16 and R12 sit next to J5, and R21 next to J5's LINE− pin. `AUDIO_OUT_2`, the low-impedance DAC output,
  makes the long run from Daisy pin 19 along the bottom of the power corner (about 30 mm on L1), so the 1k `LINE_OUT` and `LINE_REF`
  stretches are only about 5 mm each.
- **Screw terminals:** J6 and J3 sit on the rear edge and J5 on the right edge, with their wire openings facing out and the screws on
  top. Each terminal's function is printed on the silkscreen next to it (5V, GND, BAT, MUTE; RX, TX, GND; LINE+, LINE−), because
  nothing else stops a wire landing on the wrong terminal.
- **ESD diodes:** each sits at its jack contact, with its GND pad dropped to L2/L3 by its own via. D2 and D3 sit above J2, D5 above J4's
  ring, D4 right of J4's tip, and D1 between J1's tip and C1. The discharge path from contact to diode to via is a few mm.
- **GND vias:** every SMD GND pad has its own 0.6/0.3 mm via, 1–1.6 mm from the pad on a short 0.4–0.5 mm stub, on the side away from
  the signal routing. There are no vias in pads, so reflow doesn't wick solder away. U2's GND pins (2, 3, 6, 7 and 10) tie into its
  exposed pad, which has four vias. SGND (pin 15) doesn't: it reaches GND only at J4's sleeve.
- **Under J6 and J3, one column per terminal:** each part sits straight below the terminal it serves, with its reference just above
  it and the terminal's function label above that. Under MUTE: Q2, with R17 below its gate. Under BAT: R13, then C17. Under GND: R19,
  then R18. Under 5V: Q1, with C4 beside it and C5 below. Under RX and TX: R9 and R8.
- **Power entry:** J6 pin 1 → Q1 → C4 and C5 on short wide traces. C5 is the `+5V` star: the analog branch leaves from its pad on L4.
- **`5V_SENSE`:** R19 (GND end up) and R18 (`+5V` end down, next to C5) stand in one column, with `5V_SENSE` between them. It goes to
  Daisy pin 22. It is a DC level, so the route isn't critical.
- **Power board signals:** R13 (`BATT_SENSE`) and Q2/R17 (`SPK_EN`) connect to Daisy pins 25 and 28 under the Daisy. The display
  UART reaches pins 14/15 the same way from R8/R9. All are slow, so L4 under the Daisy suits them.
- **`HP_DETECT` and TP1:** TP1 sits left of J4, on a short trace to J4 pin 6. The net goes to Daisy pin 23, at the right end of the rear
  row. It is a DC level, so the route isn't critical.
- **Spacing:** parts from different blocks keep at least 1 mm of copper between pads, so they can be soldered with an iron and a 0.2 mm
  trace fits between them. Inside a block, the decoupling caps sit closer on purpose: C6 and R2 at U1's pins (0.80 and 0.83 mm), C12 and
  C14 at U2 (0.60 mm), C13 and C10 at U2 (0.90 mm).
- **Mounting holes:** three M2.5 holes (non-plated, MountingHole_2.7mm_M2.5), plus J1's panel nut at the front-left corner:
  - H2 at the rear-right and H3 at the front-right corner, each 4 mm in from both edges.
  - H1 at the rear-left, in the gap between the Daisy's front socket row and J1's back face (centre 4 mm from the left edge,
    y = 27.9 mm). It supports the Daisy's end of the board when the module is pressed into its sockets or USB is plugged in.
  - All three are M2.5, so the enclosure takes one screw size.
  - The rear-left corner itself and the left edge behind the Daisy have no room for a hole.
- **Fiducials:** three global fiducials for JLC's assembly camera, 1 mm copper dots with 2 mm mask openings (Fiducial_1mm_Mask2mm),
  at FID1 beside H1, FID2 under H2 and FID3 near H3. They're asymmetric, so the camera can tell the board's orientation. Like the holes,
  they're board-only footprints: no schematic symbol, not in the BOM or the placement file.
- **Silkscreen:** references are 1.0 mm high with 0.15 mm strokes, JLC's minimum for legible text. They're horizontal, beside their
  parts, and clear of pads, vias and other labels. Under J6 and J3 the references sit in a row between the terminal labels and their
  parts. J6's own reference sits at the end of its terminal labels, next to 5V.
  The schematic's MPN fields for C10/C11 are hidden on the board.

### 3D models
- **A1** uses `3dmodels/Electrosmith_Daisy_Seed_placeholder.step` on two stock `PinSocket_1x20_P2.54mm_Vertical` models (8.5 mm), at x = 0 and 15.24.
  **J1** uses `3dmodels/Neutrik_NRJ4HF_placeholder.step`. KiCad ships no model for either part, so the board points at these
  placeholders from `make_placeholders.py`. Re-running "Update footprints from library" on A1 or J1 resets the paths to KiCad's missing models.
- **The Daisy placeholder is the original Seed's outline** (micro-USB, ~1 mm overhang, 3 mm tall). The Seed3's USB-C overhangs the
  PCB by 1.55 mm and stands 3.25 mm tall (Seed3 datasheet, page 8). Allow for that when checking the enclosure.
- **J2/J4** use `3dmodels/SameSky_SJ3-35063AG_placeholder.step`, set in the project footprint itself, so a footprint update keeps it.

### U2 exposed pad
- U2's footprint is `WQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm`. Four 0.6/0.3 mm GND vias sit in the exposed pad at ±0.4 mm from its centre,
  under the four paste windows. Solder the exposed pad (tied to GND).
- **Why not the `_ThermalVias` footprint:** it drills 0.2 mm holes, below the board's 0.3 mm minimum. U2 dissipates only tens of mW, so
  the vias are there to ground the pad to L2/L3, not for heat, and 0.3 mm holes do that within the standard rules.
- **Watch:** the vias are open, so they wick some solder from the pad during reflow. Check for voids or a floating part (TEST_PLAN 0.3).
  If it is a problem, ask JLC to tent or plug the vias from the bottom.
- **Moving U2:** the vias are board items, not part of the footprint. Move them with U2.
- The QFN needs hot air or a stencil and a hot plate rather than an iron.

### Design rules
Board Setup (`seed3-carrier.kicad_pro`) holds the absolute minimums and net class defaults. `seed3-carrier.kicad_dru` adds the
per-class ranges, including the maximums. All values are within JLC's standard 4-layer limits.

| Item | Min | Default | Max |
|---|---|---|---|
| Signal track (Default class, not GND) | 0.2 mm | 0.2 mm | 0.5 mm |
| GND track | 0.2 mm | 0.5 mm | 2 mm |
| Power track (`Power` class) | 0.5 mm | 1 mm | 2 mm |
| Power track inside U1's courtyard | 0.3 mm | 0.5 mm | 2 mm |
| Power track inside U2's courtyard | 0.2 mm | 0.25 mm | 2 mm |
| Via, Default class | 0.6 / 0.3 mm | 0.6 / 0.3 mm | 0.8 / 0.4 mm |
| Via, `Power` class | 0.6 / 0.3 mm | 0.8 / 0.4 mm | 0.8 / 0.4 mm |
| Clearance (both classes) | 0.2 mm | | |
| Copper to board edge | 0.5 mm | | |
| Hole to hole, hole clearance | 0.25 mm | | |
| Via annular ring | 0.15 mm | | |

- **`Power` class:** `+5V`, `/5V_IN` (the class also lists `/3V3_A`, which is unused on the carrier).
  GND stays in Default and mostly drops straight to L2/L3 through vias.
- **Neck-down at U1 and U2:** a 1 mm power trace cannot reach U2's 0.25 mm pads (0.5 mm pitch) or U1 pin 5 without touching the next
  pin. Inside each IC's courtyard, two rules set the default to the pad width (U2: 0.25 mm, U1: 0.5 mm), so a trace started at the pin
  begins narrow. Switch to the 1 mm preset once outside the courtyard. Anywhere else a Power trace under 0.5 mm fails DRC. Rules later in
  `seed3-carrier.kicad_dru` win, so the neck-down rules come after "Power track width".
- **Presets:** tracks 0.2, 0.25, 0.3, 0.5 and 1.0 mm; vias 0.6/0.3 and 0.8/0.4 mm.
- **Thermal reliefs:** through-hole pads join the L2/L3 GND planes with four 0.5 mm spokes and a 0.5 mm gap. SMD pads and vias,
  including U2's exposed-pad vias, stay solid. The through-hole parts are hand-soldered with an iron, and a pin tied solidly into two
  planes (jack sleeves, J3/J6 GND, the Daisy's GND pins, C5) would not heat up enough. Both GND zones use "Thermal reliefs for PTH",
  and the "Thermal reliefs on through-hole pads" rule in `seed3-carrier.kicad_dru` enforces it for any zone added later. DRC's minimum of
  2 spokes per pad passes.

## Parts sourcing
Build plan: JLC makes the 4-layer board and assembles every SMD part (Economic, top side). The through-hole parts are hand-soldered.
Every part below has its LCSC number in an `LCSC` field in the schematic, copied to the board. Stock is JLC's, checked 2026-10-25.
Basic parts have no loading fee. Each extended part adds about $3 per order (6 here, about $18, or more if C398358 turns out to be extended).

**SMD, assembled by JLC**

| LCSC | Part | Refs | Type | Stock |
|---|---|---|---|---|
| C4410 | 1k 1% 1206 (UNI-ROYAL) | R2 R11 R21 | Basic | 1.9M |
| C17710 | 470 Ω 1% 0805 (UNI-ROYAL 0805W8F4700T5E) | R20 | Basic | 2.3M (2026-10-27) |
| C19224 | PESD5V0S1BA bidirectional ESD, SOD-323 (Nexperia) | D1 D2 D3 D4 D5 | Extended | 46k (2026-10-26) |
| C26010 | 3.3k 1% 0805 (UNI-ROYAL 0805W8F3301T5E) | R5 R10 | Basic | 1.7M (2026-10-27) |
| C17900 | 100k 1% 1206 (UNI-ROYAL) | R12 R17 R18 R19 | Basic | 1.0M |
| C17927 | 1M 1% 1206 (UNI-ROYAL) | R1 | Basic | 3.8M |
| C17902 | 10k 1% 1206 (UNI-ROYAL) | R3 R4 R6 R7 R8 R9 R13 | Basic | 2.5M |
| C1790 | 100 pF 50 V C0G 0805 (Samsung CL21C101JBANNNC) | C1 | Basic | 647k (2026-10-27) |
| C1885 | 1 nF 50 V C0G 1206 (FH) | C3 C9 | Extended | 4.4k |
| C486355 | 3.3 nF 50 V C0G 0805 (FH 0805CG332J500NT) | C16 | Extended | 3.9k (2026-10-26) |
| C1848 | 1 µF 50 V X7R 1206 (Samsung) | C2 | Basic | 551k |
| C24497 | 100 nF 50 V X7R 1206 (Samsung) | C4 C6 C17 | Basic | 1.6M |
| C77101 | 47 µF 16 V X5R 1210 (Murata GRM32ER61C476KE15L) | C7 | Extended | 164k |
| C1779 | 4.7 µF 25 V X5R 0805 (Samsung CL21A475KAQNNNE) | C10 C11 | Basic | 2.0M (2026-10-27) |
| C19110 | 2.2 µF 25 V X7R 0805 (Samsung) | C12 C14 C15 | Extended | 297k |
| C28323 | 1 µF 50 V X7R 0805 (Samsung) | C13 | Basic | 1.9M |
| C15127 | AO3401A | Q1 | Basic | 642k |
| C8545 | 2N7002 | Q2 | Basic | 2.9M |
| C398358 | TLV9061IDBVR | U1 | Check | Check (LCSC lists 283k) |
| C69901 | TPA6132A2RTER | U2 | Extended | **65** |

**Through hole, hand-soldered (order from LCSC)**

| LCSC | Part | Refs | Stock |
|---|---|---|---|
| C2835642 | 47 µF 16 V radial 5 × 11 mm, 2 mm pitch, low ESR (SamYoung NXB) | C5 | 8.0k |
| C39461671 | Same Sky SJ3-35063AG | J2 J4 | 100 |
| C474892 | Cixi Kefa KF350-3.5-2P, 2-way 3.5 mm screw terminal | J5, and 2 slid together for J6 (3 per board) | 17.2k (2026-10-27) |
| C474893 | Cixi Kefa KF350-3.5-3P, 3-way 3.5 mm screw terminal | J3 | 1.5k (2026-10-27) |
| C2905423 | 1×20 2.54 mm female header, 8.5 mm | 2 per board, for the Daisy (A1) | 15.9k |
| — | Neutrik NRJ4HF | J1 | Not at LCSC: order from Mouser, DigiKey or a Neutrik distributor |

- **U2 is the stock risk.** JLC has 65 TPA6132A2RTER (the RTET reel has none). That covers this build, but order soon, or buy spares
  from DigiKey or Mouser and send them to JLC as consigned parts if the stock is gone.
- **C0G for the filter caps.** C1, C9, C16 and C3 set the RC filters. X7R would be a basic part, but its capacitance changes with voltage,
  which adds distortion. C3/C9 (C1885) and C16 (C486355) have the thinnest stock of the passives. The 50 V Yageo CC1206JRNPO9BN102 (C113881) is the
  fallback for C1885. JLC had no 3.3 nF C0G in 1206 in stock on 2026-10-26, so C16 is 0805.
- **16 V for C7 and C5:** C7's 16 V part derates better under DC bias than a 10 V part. C5 is 16 V too.
- **Screw terminals:** the footprints are KiCad's Phoenix PT 1,5/x-3,5-H, the standard 3.5 mm pattern the KF350 blocks fit. LCSC
  has no 4-way KF350 or DG350, so J6 is two 2-ways; KF350 blocks dovetail together at the same pitch.
- **R5, R10, R20, C1, C10 and C11 are 0805** because that is the size JLC stocks them in as basic parts (no loading fee). C10/C11 sit at
  ≈ 0 V DC, so a 25 V X5R part loses no capacitance to DC bias. The 2.2 µF caps (C12, C14, C15) stay extended: the only basic 2.2 µF found
  at JLC on 2026-10-27 was a 16 V 0603 (C23630), which keeps roughly half its value at 5 V.
- **TP1** is a bare 2 mm copper pad, not a part, so it has no LCSC number and nothing to order.
- **Generating the JLC BOM/CPL:** only send the SMD parts. The through-hole parts also have LCSC numbers, for ordering, so filter them
  out (or leave them unselected in JLC's BOM step) unless JLC is meant to fit them.
