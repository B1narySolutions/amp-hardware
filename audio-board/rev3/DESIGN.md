# Audio board rev 3 — design

How the board works now, and why. Rev 3 puts audio board rev 2 and power board rev 1 on one 4-layer board. `CHANGES.md`
lists the net difference from those two boards. `TEST_PLAN.md` (in this folder) is the bring-up and test procedure. Keep
this file current as the schematic and board change. Write down the design as it stands now, not the history behind it
(git has that).

The board holds a Daisy Seed3 (A1, in two 1×20 sockets), the analog input and output stages, the headphone amp, the
battery input, the 5 V distribution and the TPA3118D2 speaker amp. The schematic has two sheets:
- **Sheet 1, `seed3-carrier.kicad_sch`:** audio board rev 2's circuit, with its designators unchanged.
- **Sheet 2, `power.kicad_sch`:** power board rev 1's circuit (designed by William Anderson), with every designator +100
  (U101 TPA3118D2, U103 TPS3808, Q101 IRF4905, J101 battery jack...). The sheets join through five sheet pins (see
  "Links between the sheets").

The 5 V buck, a DFRobot DFR0571 module, stays off the board on two screw terminals. Volume, tone, input trim and mute
come from the touchscreen over the UART, so the board has no pots or encoder.

**The rule for rev 3:** the circuits are audio rev 2's and power rev 1's, changed only where the merge required it. The
four screw terminals that joined the boards are gone, Q102 protects the 5 V input, and J102's two pins are swapped for the
layout. So bring-up results from the ordered rev 2 and rev 1 boards apply here one for one, and so do rev 2's firmware
constants. Simplifications the merge only makes possible are left for later: dropping R22/R23, one battery divider
instead of two, FAULTZ to a Daisy pin.

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
J2 (SJ3-35063AG, 3.5 mm TRS) tip and ring → R3/R4 (10k each, passive stereo-to-mono sum) → summing node with R5 (470 Ω to GND)
and C3 (1 nF, RF filter) → `AUDIO_IN_2` (Daisy pin 17) directly. J2's detect switch (pins 5 and 6) is not connected.
- **No buffer and no coupling cap.** The Seed3's audio inputs are AC-coupled on the module (Seed3 datasheet, Table 1 note), and the
  source is a phone or laptop output, so nothing needs biasing or buffering. The Daisy input itself is the load that sets the level.
- **Daisy input impedance:** the TAC5242's AC input impedance is 5 kΩ ±20% at its pins (TAC5242 datasheet, ADC parameters and
  section 7.3). The Seed3 datasheet doesn't give the module pin's value, so this assumes the pin connects to the codec through its
  coupling cap with no extra series resistance. Electrosmith's own input circuits drive the pin from an op-amp through 1k or 100 Ω
  (Figures 3.2 and 3.4), which fits. TEST_PLAN measures the level with the Daisy fitted.
- **R5 sets the level, whatever the Daisy's input impedance is.** R3 ‖ R4 (5k) into R5 (470 Ω) alone is a gain of 0.086 (−21.3 dB), so
  even if the module pin added no load at all, a 2 Vrms laptop output (5.7 Vpp) would reach it at 0.17 Vrms (0.49 Vpp, ±0.24 V peak).
  The Daisy's ≈ 5 kΩ input moves that by less than 1 dB anywhere in 4–6 kΩ. R5 is also the DC return for the source's coupling caps,
  and it holds the node at GND with an empty jack or with the Daisy out.
- **R5 is 470 Ω so that a source can keep playing into the unpowered codec.** With the board off, a phone or laptop left playing into
  J2 drives the TAC5242's input while its AVDD is at 0 V. Its inputs are rated −0.3 V to AVDD + 0.3 V (TAC5242 datasheet, §6.1) and TI
  publishes no injection rating, so the signal there has to stay within ±0.3 V. With R5 at 470 Ω a 2 Vrms source reaches ±0.23 V at
  worst (codec input at 6 kΩ, 1 % resistors). At 3.3k it reached ±0.8 V and put ≈ 0.5 mA into the codec's protection diodes. The cost
  is level, which the firmware adds back (see "Level"). The TAC5242's ADC has 119 dB of dynamic range, so even a quiet phone sits
  ≈ 89 dB above its noise. R5 can go up to 560 Ω (≈ 1.2 dB louder, ±0.27 V while off); at 680 Ω the off-state peak passes 0.3 V.
- **C3** filters RF picked up on the cable, for example from the phone itself. It sees R3 ‖ R4 ‖ R5 ‖ 5k ≈ 400 Ω, so the corner is
  ≈ 400 kHz (≈ 370 kHz with the Daisy out), still far below the RF it shunts.
- **Level:** the same signal on both channels sees R3 ‖ R4 = 5k into R5 ‖ the Daisy's input. With the codec at 4k / 5k / 6k that is
  −22.2 / −22.0 / −21.9 dB, so 2 Vrms reaches the Daisy at ≈ 0.45 Vpp (−18 dBFS). Most backing tracks are close to this case, since
  bass, kick and vocals sit in the centre. One channel alone (the other driven at 0 V) sees 10k into 10k ‖ R5 ‖ 5k, a gain of 0.040
  (−28.0 dB). A quiet 0.5 Vrms phone lands around −30 dBFS, so the firmware adds gain (about 18 dB takes a 2 Vrms source to full scale)
  and trims out the ±0.2 dB spread.
- **Source load:** each channel sees ≈ 10.4k (one channel driven) to ≈ 10.9k (both driven). Phone and laptop headphone outputs drive this easily.
- **Noise:** the node sits at ≈ 400 Ω rather than at an op-amp output. Its thermal noise (≈ 2.6 nV/√Hz) is far below a backing track's level.
- **Use:** backing tracks bypass NAM. The firmware mixes `AUDIO_IN_2` in after the amp model, to both outputs.

### Headphone output (`AUDIO_OUT_1` → J4)
`AUDIO_OUT_1` (Daisy pin 18) → R10 (3.3k) / C9 (1 nF to GND) → `HP_SOURCE` → C10/C11 (4.7 µF each) → R25/R27 (10k) → U2 INL−/INR−,
with R26/R28 (10k) from each output back to its input. U2 (MAX9722AEUE+) drives J4 (`HP_L` tip, `HP_R` ring) directly.
- **What the Seed3 outputs are rated for:** 1 Vrms at 0 dBFS (Seed3 datasheet, Table 3). The datasheet gives no output impedance,
  minimum load or coupling-cap value for pins 18/19, and says only the *inputs* are AC-coupled.
  - **Line-out mode, not headphones.** The TAC5242 drives 16 Ω headphones (62.5 mW) only in its differential or pseudo-differential
    modes, set by its MD4/MD5 pins on the module. The Seed3 brings out one single-ended pin per channel at 1 Vrms, with single-ended
    AC-coupled inputs. That matches only MD5 high / MD4 low, "Single-ended output; Line-out only" (TAC5242 datasheet, Table 7-10),
    whose minimum load is 600 Ω. The module cannot drive headphones, which is why U2 is here. Electrosmith's own headphone circuit
    (Seed3 datasheet, Figure 3.9) also adds an amp (TPA6110A2).
  - **DC level: probably 0 V, not confirmed.** Figure 3.9 wires pin 18 straight across a volume pot to GND, which only works if the pin
    sits at 0 V DC, so the outputs are most likely AC-coupled on the module. TEST_PLAN measures it with the Daisy fitted.
- **No buffer between the Daisy and U2.** U2's inverting inputs are virtual grounds, so the Daisy sees R10 plus R25 ‖ R27 (5k),
  ≈ 8.3 kΩ, far above the 600 Ω line-out minimum. Electrosmith's reference circuits load the pin with 10k through a 10 µF cap (line out,
  Figure 3.3) and with a pot to GND (headphone amp, Figure 3.9).
- **R10/C9** filter the DAC's out-of-band noise before U2. With R25 ‖ R27 as the load the corner is ≈ 80 kHz (R10 ‖ 5k with 1 nF).
- **Level:** R10 and R25 ‖ R27 form a −4.4 dB divider, so full scale reaches `HP_SOURCE` at ≈ 0.60 Vrms, and U2's gain of −1
  (R26/R25 = R28/R27 = 10k/10k) puts ≈ 0.60 Vrms on each output: 22 mW into 16 Ω, 11 mW into 32 Ω.
- **Why unity gain:** U2 delivers 70 mW into 16 Ω and 130 mW into 32 Ω at 1 % THD with both channels driven in phase, which is the mono
  case here (MAX9722A datasheet, Electrical Characteristics and "Output Power"): ≈ 1.06 and 2.0 Vrms. Full scale leaves 4.9 dB of
  margin at 16 Ω and 10 dB at 32 Ω, and 11 mW is ≈ 108 dB SPL in typical 98 dB/mW headphones. The datasheet asks for 10k feedback
  resistors, since larger ones raise the output offset through the 50 nA input bias current. To lower the gain, raise R25/R27 instead.
- **Low end:** C10/C11 into R25/R27 is a 3.4 Hz high-pass. The Daisy's own output coupling cap adds a second one; its value isn't published.
- **U2, MAX9722A (DirectDrive):** an internal charge pump inverts the supply onto PVSS, so its outputs swing about 0 V with no output
  caps and the bass stays flat to a few Hz. It has built-in click-and-pop suppression, short-circuit and thermal protection, and ±8 kV
  HBM protection on its outputs. It runs from 2.4–5.5 V, so from `+5V`. The charge pump switches at 600 kHz (505–800 kHz), far above
  the audio band. PSRR is 80 dB at 217 Hz and the output noise 6 µVrms (22 Hz–22 kHz).
- **Why the MAX9722A:** it comes in a 16-pin TSSOP (0.65 mm pitch, no exposed pad), so the whole board can be soldered with an iron.
  The TPA6132A2 it replaces was a 3 × 3 mm QFN with an exposed pad. It keeps the same architecture: outputs at 0 V, no output caps,
  one 5 V supply.
- **U2 wiring** (datasheet Typical Application Circuit and Figure 7): inverting, with external gain resistors. INL+/INR+ go straight
  to SGND, as the datasheet says to when the jack's ground isn't sensed. SHDN (active low) is tied to `+5V`, so U2 is on whenever
  `+5V` is up (see "Output mute"). C13 is the flying cap (C1P/C1N), C14 holds PVSS to PGND, C12 bypasses PVDD to PGND and C15
  bypasses SVDD to SGND: 1 µF each, the datasheet's value, 0805 X7R 50 V. PVSS and SVSS are tied together at the device, as are PVDD
  and both SVDD pins.
- **Output offset:** ±2.5 mV maximum input offset at a noise gain of 2, plus 50 nA through 10k: at most ≈ ±5.5 mV at J4, ≈ 0.3 mA into
  16 Ω.
- **No click from the input caps at power-up:** `HP_SOURCE` sits at 0 V and U2's inverting inputs at SGND, so C10/C11 have nothing to
  charge to. The datasheet's advice to delay SHDN by a few RC time constants only applies to a source with a DC bias.
- **Symbol:** `seed3-carrier:MAX9722AEUE` in `seed3-carrier.kicad_sym`, drawn for this board: inputs on the left, outputs and
  charge-pump pins on the right, supplies and SHDN on top, IN+ and grounds on the bottom.

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

### Speaker send (`AUDIO_OUT_2` → U101)
`AUDIO_OUT_2` (Daisy pin 19) → R11/C16 (1k/3.3 nF, ~48 kHz low-pass) → `LINE_OUT`, with R12 (100k) to GND. `LINE_OUT`
reaches the speaker amp's IN+ (U101 pin 4) through C108. `LINE_REF`, GND through R21 (1k), reaches IN− (pin 5) through
C109. On sheet 2 the two nets are named `Line+` and `Line−`.
- **No buffer.** The reason is the same as for the headphone path: R11 plus U101's 60 kΩ input is far above the 600 Ω
  line-out minimum (see "What the Seed3 outputs are rated for"). With no `VREF` bias or coupling caps before C108,
  `LINE_OUT` doesn't drift at power-on.
- **No DC-blocking cap on this board's side: this path assumes pin 19 sits at 0 V DC.** The outputs are most likely
  AC-coupled on the module (see "DC level" under "Headphone output"). C108 blocks DC into U101 anyway, but R12 would carry
  it. If TEST_PLAN finds more than a few tens of mV at pin 19, the fix is a 10 µF cap in series between C16 and
  `LINE_OUT`.
- **R11** is the output impedance. With R21, U101 sees a 2k source into its 60 kΩ per leg (20 dB, ±20 %): ≈ 0.15 dB of loss.
  If `LINE_OUT` is shorted, the Daisy sees R11 alone: 1k, still above its 600 Ω minimum load.
- **R12** gives the Daisy's output coupling cap a DC return, so `LINE_OUT` sits at 0 V.
- **Pseudo-differential into a differential input.** The Daisy has one output pin per channel, so LINE− is the
  source-side ground through 1k, not an inverted copy of the signal. Both sheets share one ground net and the In1 plane,
  but the class D's supply current flows in that plane around U101 and J101. U101 amplifies only LINE+ − LINE−, so any
  ground difference between the Daisy's corner and U101's is rejected rather than added to the speaker signal. R21 sits
  beside R11 in the analog band, away from those currents, so LINE− senses the source's ground.
- **R21 (1k) balances the two legs.** LINE+ comes through R11 (1k), so LINE− gets the same 1k. The amp's common-mode
  rejection depends on equal source impedances. C16 makes LINE+ slightly lower impedance above ≈ 20 kHz, which only matters
  out of band.
- **Routing:** the pair runs side by side on F.Cu over the In1 plane, from C108/C109 along the power band's lower edge and
  down the right side to R11/R21. LINE_REF hops to In2 for 9 mm where the two legs swap order (see "Routing").
- **Why a separate speaker output:** muting in firmware means the speaker amp can be shut down while headphones are in,
  saving battery. Mute and unmute can ramp without clicks, and the speaker and headphones get independent levels.

### Jack ESD protection (D1–D5)
Every jack contact that carries a signal has a bidirectional ESD diode to GND, placed at the jack: D1 `GTR_TIP` (J1 tip), D2/D3
`AUX_TIP`/`AUX_RING` (J2), D4/D5 `HP_L`/`HP_R` (J4). All five are Nexperia PESD5V0S1BA (SOD-323, C19224).
- **Why:** these contacts are touched and hot-plugged. Before D1–D5 the guitar input's only protection was R2 and U1's own diodes, and
  the AUX input ran straight to the Daisy through R3/R4. U2's outputs are rated ±8 kV HBM, but a jack sees IEC 61000-4-2 discharges,
  which are harsher, so J4 gets diodes too.
- **Why this part:** bidirectional, so it never conducts on the negative half of an audio signal. 5 V working voltage: every signal on
  these contacts stays below it (the largest, a hot active guitar, is ≈ ±2.4 V where U1 clips it). 5 nA leakage, so it doesn't load
  the 1 MΩ guitar input, and 35 pF, small next to a guitar cable's few hundred pF.
- **Not protected:** the J2/J4 detect switches (pins 5/6) are isolated from the plug, so nothing reaches them.

### Output mute (STM32 watchdog)
A hung Daisy can loop its last audio buffer at full level, so every output must go silent when audio stops.
- **Headphones: no hardware mute.** U2's SHDN is tied to `+5V`. The codec mutes the headphones (see "The codec mutes"), the
  same way it mutes the speaker send. U2's own click-and-pop suppression covers its power-up and power-down.
- `SPK_EN` (Daisy pin 28) drives Q2's gate, with R17 (100k) pull-down. Q2 (2N7002) pulls `SPK_MUTE` to GND through R23
  (470 Ω), which means speaker on. R107 (10k, sheet 2) pulls `SPK_MUTE` up to `+5V_RAW`, which means muted. R108 (2.2k) and
  C124 (1 µF) carry it to U101's MUTE pin (active high).
- **Levels:** low (playing) is ≈ 0.24 V (R23 and Q2 against R107), against U101's 0.8 V VIL. High (muted) is ≈ 5 V, against
  2 V VIH and MUTE's PVCC + 0.3 V maximum. After an IWDG reset, MUTE rises through R107 + R108 (12.2 kΩ) into C124 and passes
  2 V in ≈ 5.6 ms. Both edges slew ≈ 2.3 V/ms or slower, inside the TPA3118's 10 V/ms limit for MUTE and SDZ.
- **R23** limits Q2's current if `SPK_MUTE` is ever driven hard: ≈ 11 mA from a 5 V source. On one board nothing should
  drive it, but R23 stays (see "The rule for rev 3").
- **How it works:** the firmware feeds the STM32's independent watchdog (IWDG) only from the audio callback. The IWDG runs
  on its own clock, so if the callback stops (hung firmware, stalled DMA, fault handler), it resets the STM32. During a
  reset, and while the Daisy is booting or in DFU, its pins float, and R17 holds `SPK_EN` low (speaker amp muted).
- **The codec mutes.** The STM32 clocks the TAC5242, and the TAC5242 powers down its DAC by itself when its audio clocks
  stop (TAC5242 datasheet, section 7.4.1). An IWDG reset therefore silences pins 18/19, and with them J4 and U101. The
  headphones have no amp mute. This doesn't help while the clocks keep running, such as a DMA looping a stale buffer with the
  CPU hung, which is why the IWDG has to reset the chip. The datasheet doesn't say whether the power-down clicks.
- **Why Q2 instead of driving `SPK_MUTE` from the Daisy pin:** R107 holds `SPK_MUTE` at `+5V_RAW` whenever the battery is on,
  including while the Daisy is unpowered or out of its sockets. An open-drain Q2 keeps the Daisy from being back-powered
  through it, and keeps the speaker muted unless the Daisy is running.
- **Trade-off:** an external retriggerable one-shot watching an audio-callback toggle would watch the audio from outside the
  STM32. The IWDG is inside the chip, so the mute depends on the firmware feeding it only from the audio callback. Never
  feed it from the main loop.
- **Why U2's SHDN isn't driven from the Daisy:** the Daisy can run from USB while `+5V` (U2's supply) is off (see "Running
  from USB alone"), and SHDN is rated to SVDD + 0.3 V. A Daisy pin on SHDN would need a level translator. The codec's
  power-down already covers a hung Daisy. The cost: U2 is on whenever `+5V` is, so anything on pin 18 while the Daisy boots
  reaches the headphones.

## Power section (sheet 2)
Sheet 2 is power board rev 1's circuit. `../../power-board/README.md` holds rev 1's original reasoning and the battery and
speaker details; this section is the design as it stands on rev 3.

### Battery input
- **The battery** is a Talentcell rechargeable power bank (72 W, 100 Wh). The board takes its 12 V DC output. The listing
  doesn't say whether that output is regulated, so the design assumes 9.0 V empty to 12.6 V full. Measure it.
- **J101** (Same Sky PJ-102AH, 2.0 mm pin, 5 A) sits at the rear-right corner, opening on the rear edge. J101 → F101 (5 × 20 mm
  T3.15A fuse in a Bulgin FX0457 holder) → SW101 (screw terminal to the panel switch, an NKK S1B rated 5 A) → Q101 →
  `VBAT_PROTECTED`.
- **Q101 (IRF4905 P-FET)** is the reverse-polarity protection: drain to the switch, source to the load, gate to GND through
  R101 (10k), D101 (BZT52C12, 12 V) from gate to source. With the battery the right way round the body diode lifts the
  source and Q101 turns on. D101 holds VGS to about −12 V (rated ±20 V). With the battery reversed the gate sits at the
  source and the body diode blocks.
- **`VBAT_PROTECTED`** feeds U101's PVCC through R105 (0 Ω 2512, "amp isolation"), the DFR0571 through J106, and the battery
  divider. Everything on it is after SW101, so the board draws nothing from the battery while the switch is off.
- **Overvoltage:** the board itself survives up to 24 V on J101. U101 is specified to 26 V; C111, C112 and C115 are rated
  25 V; D101 limits Q101's gate. The DFR0571's input limit is unknown.

### 5 V supply and distribution
- **The DFR0571** buck module is off the board. J106 sends it `VBAT_PROTECTED` and J107 takes its 5 V back as `+5V_DFR`. Its
  specifications (input range, output accuracy, current limit, reverse protection) couldn't be read (DFRobot's page for the
  SKU returns 404). The rest of this section assumes 5.0 V ± 5 % at up to 1.6 A, the figure in the parts order. Measure it at
  bring-up.
- **Q102 (AO3401A)** sits between `+5V_DFR` and `+5V_RAW`, gate to GND, in the same orientation as Q1. If J107 is wired
  backwards it blocks, and nothing on `+5V_RAW` sees −5 V. That protects U103, whose VDD is rated −0.3 V minimum, and the
  display on J105. It drops ≈ 45 mV at 0.75 A (60 mΩ maximum at VGS = −4.5 V, AO3401A datasheet).
- **`+5V_RAW`** feeds two filtered branches:
  - **Audio:** FB101 (220 Ω at 100 MHz, MPZ1608S221A) → `5V_IN` → Q1 → `+5V`, sheet 1's analog rail and the Daisy's VIN.
    C105 (100 nF) sits after the bead; C104 (100 µF) is optional bulk through JP102.
  - **Display:** FB102 → `+5V_DISPLAY` → J105, the display's own supply pair. C107 (100 nF) sits after the bead; C106 (100 µF)
    is optional bulk through JP104.
  - **Local parts:** C103 (10 µF) and C123 (100 nF) at Q102, plus U103 and the pull-ups R107, R109, R112, R113.
- **The jumpers are rev 1's experiments, kept for rev 3.** JP101 and JP103 bypass the beads; JP102 and JP104 connect the
  optional bulk caps. Set them from what power board rev 1's bring-up shows, and record the setting in the test log.
- **The audio rail's budget:** `+5V` must stay at 4.75 V or more, and the firmware won't start audio below 4.7 V
  (`5V_SENSE`). On the way from the DFR0571 there are two P-FETs (Q102, Q1) and FB101: about 60 mV at the audio side's
  ≈ 0.3 A plus Q102's share of the display current. A DFR0571 at 4.9 V or more is enough.

### Supervisor, shutdown and mute
- **U103** (TPS3808EG50, 4.65 V threshold, 20 ms delay with CT open) watches `+5V_RAW`. Its open-drain RESET output
  (`AMP_PG`, R109 10k pull-up) drives `AMP_SDZ` through R110 (2.2k), with R111 (100k) to GND and C125 (1 µF). U101 stays shut
  down until the 5 V has been good for 20 ms, and shuts down as soon as it sags. JP105 (left open) pulls MR low to force a
  reset, which also clears U101's fault latch.
- **MUTE:** see "Output mute". R107 pulls `SPK_MUTE` up; Q2 on sheet 1 pulls it down to play.
- **FAULTZ** (R112 10k pull-up, TP109): U101 latches its outputs off on an output short, overtemperature or too much DC at the
  output (TPA3118 datasheet, Table 4). The latch clears when SDZ goes low, by a power cycle or JP105. FAULTZ isn't tied to
  SDZ and doesn't reach the Daisy (accepted, see "Decisions").
- **Power sequence:** with the switch on, `VBAT_PROTECTED` and PVCC rise first, then the DFR0571's 5 V. U103 releases SDZ
  20 ms after `+5V_RAW` passes 4.65 V. On switch-off, `+5V_RAW` stays at or below PVCC, because the DFR0571 runs from PVCC's
  node, and U103 pulls SDZ low as it falls. So MUTE and SDZ never exceed PVCC + 0.3 V in use. On the bench they can (see
  "Decisions": no 5 V alone on J107).

### Battery level
- R102/R103 (30k/10k, 1 %) divide `VBAT_PROTECTED` by 4 from a 7.5 kΩ source onto `BATT_SENSE_CONN`. Sheet 1's R13/R22
  (10k/10k) halve that into Daisy pin 25 and load it with 20k, so pin 25 reads
  VBAT × 0.25 × 10k / (20k + 7.5k) = **VBAT / 11**: 1.15 V at 12.6 V, 1.01 V at 11.1 V, 0.82 V at 9.0 V. With all four
  resistors at 1 % the ratio is within ±2.4 %. The firmware converts with VBAT = 11 × V(pin 25).
- With C17 (100 nF) the filter corner is ≈ 320 Hz, far above battery changes; C17 also supplies the ADC's sampling charge.
- Pin 25 is the STM32's PA7, a TT_a pin rated 4.0 V absolute. Even 24 V on J101 puts only 2.2 V there. With the Daisy
  unpowered and the battery on, it sees at most 1.15 V.
- The divider sits after SW101, so it draws nothing while the amp is off.

### Speaker amp (U101, TPA3118D2)
- **Mono, PBTL.** LINP and LINN go to GND, so the device starts in mono mode. OUTPR and OUTNR are tied for the positive
  speaker terminal, and OUTNL and OUTPL for the negative one (TPA3116D2/TPA3118D2/TPA3130D2 datasheet SLOS708G, 7.4.1). ERC
  reports those ties as two output-to-output conflicts; they are excluded in the project with that reason.
- **Gain 20 dB, master:** R104 (5.6k) from GAIN/SLV to GND, nothing to GVDD (SLOS708G Table 1). Input impedance is 60 kΩ
  per leg ±20 %. Don't go above 32 dB: 36 dB drops the input impedance to 9 kΩ.
- **Inputs:** C108/C109 (1.5 µF X7R, matched) into the inputs, biased at 3 V inside the device: a 1.7 Hz high-pass.
- **Supplies:** PVCC from `VBAT_PROTECTED` through R105; C111/C112 (100 µF) bulk and C113/C114 (100 nF) at the two PVCC pin pairs.
  AVCC through R106 (10 Ω), with C115 (1 µF) and C116 (100 nF). GVDD has C110 (1 µF); PLIMIT ties to GVDD (no power limit).
  MODSEL and AM0–AM2 go to GND: BD mode, the default switching frequency.
- **Output:** bootstrap caps C117–C120 (220 nF), then the LC filter L101/L102 (10 µH, Bourns SRP1038A) with C121/C122
  (680 nF), into J102. J102 pin 2 is SPK+ and pin 1 SPK−, marked on the silkscreen. The output is bridged, so neither
  speaker wire may be grounded.
- **Levels:** the Daisy's full scale (1 Vrms, ≈ 0.98 Vrms after R11/R21) becomes ≈ 9.8 Vrms. That clips on the battery:
  ≈ 1.5 dB below full scale on a full pack, ≈ 4.5 dB near 9 V. The firmware caps the speaker level about 5 dB below full
  scale. Into 4 Ω, expect ≈ 17 W at clipping on a full pack, drawing up to ≈ 1.6 A from the battery on loud peaks.
- **Speakers:** a Jensen MOD10-50 (4 Ω) or a Skar FSX10-4 (4 Ω), one at a time (`power-board/README.md`).

## Audio 5 V (`5V_IN` → `+5V`)
`5V_IN` comes from FB101 (or JP101) on sheet 2 and goes through Q1 (AO3401A, reverse-polarity protection) onto `+5V`.
`+5V` feeds Daisy VIN (pin 39), U1, U2, `VREF` and the `5V_SENSE` divider (R18/R19). The display takes its power from J105,
not from here.
- **Why Q1 stays:** Q102 now protects all of `+5V_RAW`, so Q1 is redundant, but it stays (see "The rule for rev 3").
- **Wires on the wrong terminal:** on one board, the only signal terminal left on sheet 1 is J3 (see "Display connector").
  R8 (10k) limits the current into Daisy TX. On RX, R9 and R24 divide a 5 V wire to at most 4.78 V at pin 15 (PB7), inside
  the Seed3's 0–5 V GPIO rating.
- **Bulk at the entry:** C5 (47 µF electrolytic) and C4 (100 nF) at Q1's output. C5's ESR damps ringing between the wiring
  and the ceramics; C104/C105 sit just upstream at FB101.
- **Local decoupling:** C6 at U1 pin 5, and C12 (PVDD) and C15 (SVDD) at U2.
- **Display supply:** the display's current pulses (ESP32 Wi-Fi, backlight PWM) flow through FB102 and J105, never through Q1
  or `+5V`, and they return to J107's ground on the left edge, away from the analog band.

### Running from USB alone
The Seed3 runs from its own USB port, and the datasheet says USB and VIN can be connected together, so USB doesn't appear
to drive the VIN pin. With USB plugged in and the battery switched off (flashing or debugging on the bench), the Daisy runs
while `+5V`, `+5V_RAW` and PVCC are at 0 V. Any Daisy output that is high then pushes current into an unpowered part
through that part's input protection diodes.
- **Q1 conducts backwards** if `+5V` is lifted, because its gate is tied to GND, and so would Q102. That would only leak a
  little current toward `+5V_RAW` and the DFR0571. Nothing on the board back-powers `+5V`.
- **Display UART:** with the battery off, the display is unpowered too, and Daisy TX idles high into it. R8 (10k) limits that
  current to ≈ 0.27 mA. See "Display connector (J3)".
- **Headphone input (`5V_SENSE`):** C10/C11 pass pin 18's audio through R25/R27 to U2's inputs, which are rated only from
  SVSS − 0.3 V to SVDD + 0.3 V (MAX9722A datasheet, Absolute Maximum Ratings). U2's charge pump makes SVSS, so with `+5V`
  off both rails sit at 0 V and the inputs may only see ±0.3 V. Full scale is ±1.4 V. R10 and R25/R27 limit the current into
  U2's protection diodes to ≈ 0.07 mA (worst case), but that is still outside the rating. So the firmware has to know whether
  `+5V` is up: R18/R19 (100k/100k) divide `+5V` to ≈ 2.5 V on `5V_SENSE` (Daisy pin 22, ADC_0). While it reads low, the
  firmware keeps both outputs at digital silence (see "Firmware requirements").
  - **Why not `BATT_SENSE`:** it reads the battery, not the 5 V; a DFR0571 that fails or is unplugged would leave it reading
    normal.
  - **Why 100k/100k:** 2.5 V is well inside the ADC range and the divider draws 25 µA. The Daisy's VIN is `+5V`, so whenever
    `+5V` is up the Daisy is powered too, and the divider can't back-power it. With `+5V` off, R19 holds the pin at 0 V.
  - **No filter cap:** the source impedance is 50k, so the firmware uses a long ADC sample time.
  - **Limit: a fast power loss.** The firmware reacts within one or two audio blocks plus the codec's output delay, a few ms.
    If `+5V` collapses faster than that (the battery switched off under load), the last few ms of audio still reach U2's
    unpowered inputs, limited to ≈ 0.07 mA by R10 and R25/R27. The TEST_PLAN measures this.
- **Speaker amp inputs:** the same silence covers U101. Its inputs are rated −0.3 V to 6.3 V, absolute rather than relative
  to AVCC (SLOS708G 6.1), and full-scale negative peaks through R11 and C108 would put up to ≈ 0.8 mA into an input's
  protection until C108 charged.

## Connectors

### What each connector can see
The outside world the board is designed for, case by case. A design review checks every IC pin against these, one misuse at
a time with everything else normal, in each power state. Misuse may stop the board working, but must not damage it.

| Pin | Normal | Misuse that must not damage anything |
|---|---|---|
| J101 (12 V jack) | The power bank's 12 V output, 9.0–12.6 V, fused at 3.15 A | Reversed (Q101 blocks); a 19–24 V adapter (the board survives; the DFR0571's limit is unknown) |
| SW101 (panel switch) | The switch's two contacts, in series with the battery | — |
| J106 (to the DFR0571's input) | The module's input | Its two wires swapped: the DFR0571's input is reversed. The board's side is fine; the module's protection is unknown (accepted, see "Decisions") |
| J107 (from the DFR0571's output) | 5.0 V ± 5 % | Its two wires swapped: Q102 blocks |
| J105 (display 5 V) | The display's supply, up to ≈ 0.5 A | Shorted: limited only by the DFR0571 |
| J102 (speaker) | A 4 Ω speaker, bridged | Shorted, or one wire to GND: U101 latches off (FAULTZ low); a power cycle or JP105 clears it |
| J3.2 TX | The display's RX: high impedance, clamped to −0.5…3.8 V, 1 mA at most | A 5 V wire on TX |
| J3.3 RX | The display's TX: 0–3.3 V logic from ≈ 50 Ω | A 5 V wire on RX |
| J1 tip (guitar) | Passive pickups, 1.5 V peak (3 Vpp) from ≈ 10 kΩ, 20 Hz–20 kHz | An 18 V boost pedal at full output, 9 V peak from 1 kΩ (out of scope: may distort, must survive) |
| J2 tip/ring (AUX) | A 2 Vrms laptop, 2.83 V peak, the same signal on both | Pro line out at full level, ±5 V from 10 Ω |
| J4 tip/ring | Headphones, 16 Ω or more | — |
| J4.6 detect | Open (no plug), or switched to GND (plug in) | — |

Power states: **on** (battery switched on, Daisy running); **Daisy out**; **USB only** (Daisy on its own USB, battery switched
off, see "Running from USB alone"); **off** (everything off while a guitar or phone may still play); **reversed** (battery
reversed at J101, or J107's wires swapped). **Bench supply: never 5 V alone on J107** (see "Decisions"); bring the board up
from a current-limited 12 V supply on J101 with the DFR0571 connected, as in use. The jack pins (J1, J2, J4) are touched by
people, so each has an ESD diode (D1–D5, see "Jack ESD protection"). The speaker outputs see ESD through C121/C122 (680 nF to
GND). Every capacitor on the audio path should be C0G or film. Today C2 (X7R), C10/C11 (X5R) and C108/C109 (X7R) aren't: see
"Open items".

### Links between the sheets
These five nets were the screw-terminal contract between audio rev 2 and power rev 1 (`power-board/README.md`). On one board
they are traces, and the numbers still hold.

| Sheet 1 net | Sheet 2 net | From | Promise |
|---|---|---|---|
| `5V_IN` | `+5V_AUDIO` | FB101 / JP101 | 4.75–5.25 V (see "The audio rail's budget") |
| `BATT_SENSE_CONN` | `BAT_MON` | R102/R103 | VBAT / 4 from 7.5 kΩ, 2.3 V at most in use |
| `SPK_MUTE` | `SPK_MUTE` | R107 pull-up, Q2/R23 pull-down | ≈ 5 V muted, ≈ 0.24 V playing |
| `LINE_OUT` | `Line+` | R11 (1k) | Audio, 1 Vrms full scale, ≈ 0 V DC, into 60 kΩ |
| `LINE_REF` | `Line−` | R21 (1k) to GND | 0 V ± 10 mV, into 60 kΩ |

One ground net joins the sheets, through the planes.

### Display connector (J3)
J3 is a 3-way 3.5 mm screw terminal (Phoenix PT 1,5/3-3,5-H) on the left edge: 1 GND, 2 `UART_TX_CONN` (TX), 3
`UART_RX_CONN` (RX), marked on the silkscreen. The display takes its power from J105, beside it. R8 (10k, Daisy TX) and R9
(10k, Daisy RX) sit next to J3, in series with the UART on its way to Daisy USART1 (pins 14/15, `DISPLAY_UART_TX` /
`DISPLAY_UART_RX`). They limit current if a wire lands on the wrong terminal or the display and the Daisy power up at
different times, and add a little ESD margin.
- **J3's GND is needed:** the UART needs a common reference. The display's ground also returns with its power wire on J105,
  so some display return current comes back through J3's GND. J3, J105 and J107 sit together on the left edge, so that loop
  and its current stay at the 5 V entry, away from the analog band.
- **R8 is 10k:** with the Daisy on USB alone and the battery off, its TX idles high into an unpowered display. 10k keeps the
  current into the display's RX protection diode to ≈ 0.27 mA.
- **R9 is 10k too:** the display and the Daisy run from different supply branches, so their power-up order isn't fixed. 10k
  limits the current from a powered display into an unpowered Daisy's RX pin the same way.
- **R24 (100k) pulls `DISPLAY_UART_RX` to GND.** With R9 it divides a 5 V wire on RX to at most 4.78 V at pin 15 (PB7),
  inside the Seed3's 0–5 V GPIO rating. The display's 3.3 V high arrives at ≈ 3.0 V, well above the 0.7 × VDD (≈ 2.3 V) the
  input needs.
- **R24 also detects the display.** With the display unplugged or off, R24 holds RX low. The UART flags one break (a framing
  error) when the line drops, then waits for it to go high again, so the firmware sees one error, not a stream. A line that
  idles high means a display is connected and powered. PB7's internal pull-up has to stay off, or it fights R24.
- **Baud rate limit:** 10k with ~50 pF of cable and pin capacitance is a ≈ 0.5 µs time constant. That is fine up to 230400
  baud, but not for 921600.

### Daisy pins
Used: 14/15 (display UART), 16/17 (audio in), 18/19 (audio out), 20/40 (GND), 22 `5V_SENSE`, 23 `HP_DETECT`, 25 `BATT_SENSE`, 28 `SPK_EN`,
39 VIN. Every other pin, including `3V3_A` (21), `3V3_D` (38) and USB D−/D+ (36/37), is
marked no-connect. With the Daisy out, its sockets (A1) give probe access to every audio board net, so there are no breakout headers.
USB stays on the Daisy's own connector.

## Firmware requirements
- Run the display UART at 230400 baud or less (R8, see "Display connector (J3)"). Take volume and mute from the display over it. Ramp volume changes.
- Leave PB7's (pin 15, display RX) internal pull-up off: R24 pulls the line low. Treat a line held low as "no display", and
  restart reception after a framing error or break.
- Start the IWDG early in boot, with a timeout of about 10 ms. Feed it **only** from the audio callback.
- Send the speaker mix to output 2 and headphones to output 1.
- Read `HP_DETECT` (pin 23, PA3) with its internal pull-up enabled: **low = headphones in**. Debounce it. When headphones go
  in, ramp `AUDIO_OUT_2` down, then drive `SPK_EN` low. Reverse it when they come out: raise `SPK_EN`, then ramp
  `AUDIO_OUT_2` up.
- Add an output clamp or limiter and NaN/Inf guard at the end of the chain. Cap the speaker level about 5 dB below full scale
  (U101 clips on the battery above that).
- Save settings when they change (debounced, to spare the flash), not at shutdown. The power switch can cut the power at any
  time.
- Initialise `SPK_EN` (pin 28) as a low output. Drive it high to enable the speaker amp after the first audio callback has
  started, low when headphones are in.
- Start the codec with its output at digital silence and ramp up. U2 is always on, so the headphones hear whatever pin 18
  does from boot.
- Read `BATT_SENSE` (pin 25, ADC) and send the battery level to the display every few seconds: VBAT = 11 × V(pin 25) (see
  "Battery level"). Warn on the display when it gets low.
- Read `5V_SENSE` (pin 22, ADC_0) with the longest ADC sample time (its source impedance is 50k). It reads ≈ 2.4–2.5 V with
  `+5V` at 4.85–5.0 V.
  - **Before starting audio:** require it above 2.35 V (`+5V` ≥ 4.7 V) for at least 10 ms. Then ramp the outputs up.
  - **While running:** sample it from the audio callback on every block. Below 2.2 V (`+5V` < 4.4 V) write silence from that
    block on. Hold the outputs silent until the start-up condition above is met again.
  - This applies on USB alone on the bench too.
- Read `AUDIO_IN_2` (the AUX input, mono) and mix it in after the NAM model and cabinet EQ, with its own level control from
  the display. It goes to both outputs. It arrives ≈ 22 dB below the source, so apply gain before the mix.

## Decisions
Accepted during rev 3's design review and layout (2026-11-07), with the reason. The user delegated these calls.
- **PBTL ERC exclusions.** ERC's two U101 output-to-output conflicts (OUTPR–OUTNR, OUTPL–OUTNL) are the datasheet's PBTL
  wiring (SLOS708G 7.4.1). They are excluded in `seed3-carrier.kicad_pro` with that reason, so ERC shows 0 errors and any new
  error stands out.
- **Q102 at J107.** Added, because J107 wired backwards put −5 V on all of `+5V_RAW` (U103, the display) and Q1 only covered
  the audio branch.
- **No 5 V alone on J107, ever: bench supply on J101 only.** With PVCC at 0 V and 5 V on `+5V_RAW`, U103 releases SDZ to
  ≈ 4.9 V through R110 (≈ 2 mA into SDZ's protection diode) and R107/R108 pull MUTE to 5 V. The TPA3118 rates both at
  −0.3 V to PVCC + 0.3 V and publishes no injection rating. Normal power-up and power-down never get there (see "Power
  sequence"), so the rule is procedural; a circuit fix would change rev 1's control block. Raise it with the power board's
  designer before a rev 4.
- **FAULTZ latches until power cycle or JP105, and the Daisy can't see it.** Rev 1's choice, kept: a fault does no damage.
  Routing FAULTZ to a free Daisy pin is now possible and left for later.
- **J106 wired backwards reverses the DFR0571's input.** The board's side survives; whether the module does is unknown. Accepted
  with clear silkscreen labels.
- **J102's pins swapped** (pin 2 SPK+, pin 1 SPK−), so the speaker traces from L101/L102 don't cross. The silkscreen marks them.
- **The AUX input is 48 mm from the class D's switching nodes, short of the 50 mm the plan aimed for** (45 mm to the
  `AUDIO_IN_2` line at Daisy pin 17). That node is ≈ 400 Ω, not a high-impedance node, and runs 0.2 mm over the unbroken In1
  plane. The guitar input's 1 MΩ node is 69 mm away. Moving the class D would mean reworking the whole block for no
  measurable gain.
- **U101's and C110's ground pads join the F.Cu pour solidly** (pad-level zone connection). They are boxed in by 0.65 mm pitch
  routing and tied to ground by tracks, so the pour can't reach them with two thermal spokes. U101 is soldered with hot air or
  through its pad vias anyway.
- **The VBAT branch to J106 runs on In2** (1 mm, 0.5 oz): it carries only the DFR0571's input current, ≈ 0.75 A at most. All
  battery, PVCC and speaker current paths are on the 1 oz outer layers.
- **Five references are 0.8 mm tall** (C124, C125, R109, R111, U101) in the dense area around U101's control pins. JLC's
  recommended minimum is 1.0 mm; 0.8 mm with a 0.15 mm stroke prints.
- **The 5 V bench check order** is in TEST_PLAN.md: the DFR0571 connected, 12 V current-limited on J101, then each block.

## Open items
- **Bring up audio rev 2 and power rev 1 first,** and fold their results into rev 3 before ordering it: the Daisy outputs'
  DC level (the speaker send has no DC block on this side), the fuse rating, beads or bypass, the optional bulk caps, L101/L102's
  value, R105, C2 microphonics, and headphone clicks at boot. Set the jumpers and parts to match.
- **The DFR0571's specifications:** confirm its input range, output accuracy, current limit and input reverse protection.
- **Battery:** measure the Talentcell's 12 V output at full charge and near empty (9.0–12.6 V assumed).
- **Test the watchdog mute:** stall the audio callback in a debug build. Check that J4 and the speaker go silent and
  `SPK_MUTE` mutes within ~10 ms.
- **2N7002 gate drive:** Q2 is driven from 3.3 V logic. That should be enough for R107's 0.5 mA, but check it on the board.
- **Headphone level:** full scale is ≈ 0.60 Vrms per channel. If that's too loud, or the hiss is audible with sensitive
  headphones, raise R25 and R27 together (20k gives −6 dB) and keep R26/R28 at 10k.
- **AUX input level:** check the level with the Daisy fitted; 2 Vrms should reach ≈ 0.44–0.45 Vpp. R5 can go up to 560 Ω
  (≈ 1.2 dB louder); at 680 Ω a source playing into the unpowered codec passes ±0.3 V.
- **Hot passive pickups:** the Daisy's full scale is reached at ≈ 3.9 Vpp at J1. Play the hottest passive guitar available
  hard and confirm its peaks stay below that.
- **Polarity:** U2 inverts the signal. Decide whether the firmware negates the output.
- **Class II ceramics on the audio path:** C2 (1 µF X7R) is in series with the guitar signal into the 1 MΩ node, C10/C11
  (4.7 µF X5R) with the headphone path, and C108/C109 (1.5 µF X7R) with the speaker amp's inputs. X5R/X7R capacitance moves
  with voltage and the material is piezoelectric, so knocks can become signal. Tap the board with a guitar plugged in and
  listen. C2 can become a 100 nF C0G in the same footprint (the corner moves from 0.16 Hz to 1.6 Hz); film parts would fix
  the others.
- **USB-alone power transitions:** scope U2's input and rails while the battery is switched off and on with USB connected
  and audio playing. If U2's inputs stay outside SVSS − 0.3 V … SVDD + 0.3 V for more than a few ms at full scale, raise the
  firmware's 2.2 V threshold or shorten the audio block.
- **Soldering U2 and U101:** U2's TSSOP takes flux and a fine tip or drag soldering. U101's exposed pad takes hot air, or
  solder fed from the back through its vias (the back has a mask opening under the pad).
- **Mechanical:** the outline, jack and hole positions have no enclosure drawing yet. Recheck them against it: the front-panel
  jacks (rev 2), the battery jack, switch terminal and speaker terminal on the rear and right edges, and the 5 V and display
  terminals on the left edge. The Seed3's USB-C overhangs the left edge by 1.55 mm.
- **Front panel thickness:** under 3 mm, Neutrik's limit for the NRJ4HF's nut.
- **3D models:** J101 and L101/L102 have none (their footprints don't carry one); the 3D view shows only their pads.

## Layout

### Stackup
4 layers, 1.6 mm, JLC's standard JLC04161H-7628 stackup: 1 oz outer copper, 0.5 oz inner, 0.21 mm prepreg between each outer
layer and its neighbour, a 1.065 mm core between In1 and In2. KiCad's Python can't edit the stackup table, so it was written
into the board file to match; choose the same stackup on JLC's order page. Page numbers below refer to Eric Bogatin,
*Bogatin's Practical Guide to Prototype Breadboard and PCB Design* (Artech House, 2021).

| Layer | Use |
|---|---|
| F.Cu | Every part; every audio net; the class D's power, output and speaker paths; a GND pour around the routing |
| In1.Cu | Solid GND under the whole board. No tracks |
| In2.Cu | GND fill, with the slow and DC nets that have to cross: the `+5V_RAW` trunk, `5V_IN` into the analog band, the VBAT branch to J106, `SPK_MUTE`, display RX, and a 9 mm hop of `LINE_REF` |
| B.Cu | GND pour; a PVCC pour under the class D; `BATT_SENSE_CONN`, display TX, and rev 2's short hops |

- **In1 is the reference for everything on F.Cu,** 0.21 mm below it. Every audio net and every switching node sees an
  unbroken plane, so return currents run directly under their traces at high frequencies and spread by resistance at audio
  frequencies.
- **One GND net, no split.** A split only helps with sub-millivolt noise below 100 kHz when more than 10 A of low-frequency
  current flows in the ground plane (p. 465). Separation comes from placement (see "Isolation").
- **Why 4 layers:** the class D switches amps at ≈ 400 kHz on the same board as a 1 MΩ guitar input. A solid plane under both,
  0.21 mm away, keeps the switching loops small and their return currents local. It also gives the inner and back layers to
  the few nets that must cross, so F.Cu crossings don't cut the plane under audio traces, as rev 2's 2-layer hops did.
- **Why 1.6 mm:** the jacks, the Daisy sockets and the screw terminals take force at every plug-in.
- **No controlled impedance.** USB doesn't leave the Daisy.

### Isolation
Where the noisy parts sit relative to the audio, and what was measured (2026-11-07, read-only pcbnew script).
1. **Zones by placement.** The analog band stays at the front edge (rev 2's layout). The Daisy sits behind it, and the power
   band behind that. In the power band, the class D is in the rear-right corner, farthest from J1/U1 at the front left.
2. **High-current loops stay local.** Battery current runs J101 → F101 → SW101 → Q101 → R105 → C111/C112 → U101 → L101/L102
   → J102, all along the rear edge and the right side of the power band. Its return runs in the planes back to J101's sleeve
   at the rear-right corner. None of it passes under the Daisy or the analog band.
3. **Switching nodes are small and on F.Cu.** The OUT and bootstrap nodes stay within ≈ 12 mm of U101. Under them is In1 GND,
   then In2's GND fill and B.Cu's PVCC pour. No other signal runs through the class D area on any layer; the `+5V_RAW` trunk
   passes on In2 under C112, below the output stage.
4. **Distance from the switching nodes:** 69 mm to the guitar input (J1 tip to U1's input), 48 mm to the AUX summing parts,
   45 mm to the AUX line at Daisy pin 17 (see "Decisions").
5. **The 5 V tree:** J107 → Q102 → `+5V_RAW`. One branch goes to FB101 → Q1 → rev 2's C5 star, the analog branch plus the Daisy
   VIN branch. The other goes to FB102 → J105 for the display. Display and Daisy current never flows in the analog branch, and
   the display's return stays at the left edge.
6. **The speaker send** runs as a pair over In1 from the Daisy's corner to U101's inputs, and U101's differential input
   rejects the ground difference between the two ends.
7. **The PVCC pour on B.Cu** joins U101's two PVCC pin pairs, C111, C112 and R106 under the output stage, so neither pin pair
   depends on a long F.Cu path. In1 separates it from the switching nodes on F.Cu.
8. **Thermal:** U101's exposed pad has nine vias inside it and ten more under the body, into In1, In2 and B.Cu GND. The back has
   a mask opening under the pad, so it can be soldered from the back through the vias.

### Board outline and placement
100 × 110 mm, 2 mm corner radius. The front panel is the bottom edge. Coordinates are from the board's top-left corner (KiCad
(100, 16.5)). The analog band, the Daisy and their routing are rev 2's layout, moved 53.5 mm from the rear edge: a rev 2
position (x, y) is now (x, y + 53.5).

| Part | Position | Why |
|---|---|---|
| J1, J2, J4 | Front edge, as rev 2 | All panel jacks on one edge (rev 2's reasons) |
| A1 (Daisy) | Behind the analog band, rotated 90°, USB on the left edge | Rev 2's position. Pins 1–20 face the analog band |
| J106, J107, J105, J3 | Left edge, top to bottom, wire openings facing out | The DFR0571's input and output, the display's power and UART together, at the 5 V entry |
| J101 (12 V jack) | Rear-right corner, opening on the rear edge | Beside the class D, so battery current and its return stay in that corner |
| F101, SW101, Q101 | Along the rear edge, left of J101 | The fuse holder lies along the edge with its pins toward J101. SW101 takes the panel switch's wires on the rear edge |
| U101 (TPA3118D2) | (70, 33.5), outputs facing right | Bootstrap caps at the output pins, L101/L102 to the right, J102 on the right edge between them |
| J102 (speaker) | Right edge, pins at y 31.75 and 35.25 | Short output loop through L101/L102 and C121/C122 |
| U103, R107–R113, C108–C110, C124, C125 | Left of U101 | U101's control and input pins face this way |
| FB101, JP101, JP102, C104, C105 | Beside Q1 in the analog band's rear-right corner (rev 2's J5/J6 area) | The audio 5 V filter sits at the analog rail's entry |
| H1, H3 | As rev 2 | |
| H2, H4 | Right edge at y 55.5; rear-left corner | J101 occupies the rear-right corner |

### Routing
- **Widths:** battery, PVCC, output and speaker paths 1.5 mm (1.0 mm on the output bars between the bootstrap caps), necked to
  0.4 mm at U101's 0.65 mm pitch pins. 5 V nets 1.0 mm (0.6 mm for the display branch). Signals 0.2–0.3 mm.
- **Crossings into the analog band:** rev 2's `+5V` run to Daisy VIN still crosses the old rear edge on F.Cu, so everything from
  the power band to the left of it reaches the analog band on In2 or B.Cu. `5V_IN` hops on In2 over that run to Q1's drain,
  `SPK_MUTE` runs on In2, `BATT_SENSE_CONN` on B.Cu.
- **Display UART:** R8/R9/R24 sit next to J3. RX runs on In2 and TX on B.Cu, each between two of the Daisy's rear socket pins,
  to pins 15 and 14. The two must cross once, so they use different layers.
- **The speaker send pair** leaves C108/C109 on F.Cu, runs along the power band's lower edge and down the right side to
  R11/R21. LINE_REF hops 9 mm on In2 where the two legs swap order.
- **Rev 2's routing in the analog band is unchanged,** except the nets that went to J5/J6/J3 and the display UART, which were
  rerouted as above, and a few GND stitching vias that sat under the new routes (the In1 plane now covers them).

### U2 (TSSOP-16)
- U2's footprint is `Package_SO:TSSOP-16_4.4x5mm_P0.65mm`: 0.65 mm pitch and no exposed pad, so it's soldered with an iron (flux, a
  fine tip or drag soldering, then a check for bridges under magnification: TEST_PLAN).
- **Under the body:** the SVSS–PVSS and SVDD–PVDD links on F.Cu, the B.Cu hop for SVDD pin 11, and GND vias for PGND, SGND, INL+ and
  INR+. They're board items, not part of the footprint: move them with U2.
- **The datasheet's layout advice** (Layout and Grounding): charge-pump caps to PGND, PVDD tied to SVDD and PVSS to SVSS at the device,
  and switching traces kept away from SGND and the audio path. C13 and C14 sit on the top row's side, away from the inputs and outputs on
  the bottom row.

### Design rules
Board Setup (`seed3-carrier.kicad_pro`) holds the absolute minimums and net class defaults. `seed3-carrier.kicad_dru` adds the
per-class ranges, including the maximums. All values are within JLC's standard 4-layer limits.

| Item | Min | Default | Max |
|---|---|---|---|
| Signal track (Default class, not GND) | 0.2 mm | 0.2 mm | 0.5 mm |
| GND track | 0.2 mm | 0.5 mm | 2 mm |
| Power track (`Power` class) | 0.5 mm | 1 mm | 2 mm |
| High-current track (`HighCurrent` class) | 0.5 mm | 1.5 mm | 3 mm |
| Neck-down inside U1 / U2 / U101 / U103's courtyards | 0.3 / 0.2 / 0.3 / 0.3 mm | | |
| Via | 0.6 / 0.35 mm | | 0.8 / 0.4 mm |
| Clearance | 0.2 mm | | |
| Copper to board edge | 0.5 mm | | |

- **`Power` class:** `+5V`, `/5V_IN`, `+5V_RAW`, `+5V_DFR`, `+5V_DISPLAY`, `CAP_BANK_A`, `CAP_BANK_D`.
- **`HighCurrent` class:** `VBAT_PROTECTED`, `AMP_PVCC`, `OUT_P`, `OUT_N`, `SPK+`, `SPK−`, and the battery nets between J101,
  F101, SW101 and Q101. Sized for the 3.15 A fuse on 1 oz outer copper.
- **Thermal reliefs:** every pad joins the GND pours with 0.5 mm spokes and a 0.5 mm gap, for an iron, except U101's and C110's
  ground pads (see "Decisions"). Vias stay solid.
- **Expected DRC warnings:** 36 `silk_edge_clearance`, all from edge-mounted connectors (J1, J2, J4, J101, J102, J105, J106,
  J107, J3, SW101). Don't trim their footprints. JLC's recommended pass also flags the test points' silk circles (0.14 mm
  from their pads, JLC prefers 0.15 mm), the five 0.8 mm references, and U101's footprint silk over its own pad; all print
  fine.

## Parts sourcing
Build plan: a 4-layer JLC board, hand-soldered, U101's exposed pad with hot air or from the back. Every part comes from DigiKey.
`seed3-carrier-digikey.csv` is one build's order (DigiKey's BOM upload format, one line per part number) and
`seed3-carrier-digikey-cart.csv` the same in DigiKey's cart format. Both come from the build that was ordered for audio rev 2
and power rev 1 (`amp-digikey-order.csv`, with its stock substitutes and notes), without the four inter-board terminals,
with Q102 added and without rev 1's experiment parts, which that build's spares cover. Check stock before ordering.
- **Sheet 1's parts** carry `MPN`, `Manufacturer`, `DigiKey` and `Datasheet` fields; sheet 2's carry `MPN` and `Manufacturer`
  matching `power-board/DigiKey_Import.csv` (substitutes included).
- **U2:** the EUE suffix is the TSSOP. Don't substitute the MAX9722B: it has a fixed −2 V/V gain.
- **C0G for the filter caps** C1, C9, C16 and C3.
- **Daisy sockets:** two 1×20 2.54 mm female headers (S7018-ND).
- **The DFR0571** is in the order as an off-board part (U102 on sheet 2, no footprint).
- **The S1B panel switch** is obsolete at NKK (DigiKey still stocks it); pick another for later builds.
- **TP1 and TP101–TP109** are bare copper pads, not parts.
