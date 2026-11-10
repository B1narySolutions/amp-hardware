# Audio board rev 3 — design

How the board works now, and why. Rev 3 puts audio board rev 2 and power board rev 1 on one 4-layer board. `CHANGES.md`
lists the net difference from those two boards. `TEST_PLAN.md` (in this folder) is the bring-up and test procedure. Keep
this file current as the schematic and board change. Write down the design as it stands now, not the history behind it
(git has that).

The board holds a Daisy Seed3 (A1, in two 1×20 sockets), the analog input and output stages, the headphone amp, the
battery input, the 5 V distribution and the TPA3118D2 speaker amp. The schematic has two sheets:
- **Sheet 1, `seed3-carrier.kicad_sch`:** audio board rev 2's circuit, with its designators unchanged.
- **Sheet 2, `power.kicad_sch`:** power board rev 1's circuit (designed by William Anderson), with every designator +100
  (U101 TPA3118D2, U103 TPS3808, Q101 IRF4905, J101 battery jack...). The sheets join through six sheet pins (see
  "Links between the sheets").

The 5 V buck, a DFRobot DFR0571 module, stays off the board on two screw terminals. Volume, tone, input trim and mute
come from the touchscreen over the UART, so the board has no pots or encoder.

**The rule for rev 3:** the circuits are audio rev 2's and power rev 1's, changed only where the merge required it. The
four screw terminals that joined the boards are gone, Q102 protects the 5 V input, and J102's two pins are swapped for the
layout. So bring-up results from the ordered rev 2 and rev 1 boards apply here one for one, and so do rev 2's firmware
constants. Three simplifications the merge made possible are done, to fit the board in 100 × 100 mm (see "Decisions"): Q1
(redundant with Q102), R23 (Q2's series resistor), and the second battery divider (R13/R22, with R102 raised to 100k so pin
25 still reads VBAT / 11). F101 is an SMD fuse instead of a 5 × 20 mm holder. Three noise and fault changes followed
(2026-11-08, see "Decisions"): U2's own supply filter (R29/C21), C0G caps at the speaker amp's inputs (C108/C109), and
FAULTZ to Daisy pin 32 (R114). Three protection changes followed the schematic review (2026-11-09, see "Decisions"):
J106 is a keyed JST XH header, D102/D103 clamp U101's SDZ and MUTE to PVCC, and R30 sits in series with Daisy pin 32. U2,
the headphone amp, is a TPA6130A2 controlled over I2C instead of rev 2's MAX9722A (2026-11-09, see "Headphone output"),
since JLC assembles rev 3.

## Signal paths

U1 is a TLV9061 single op-amp (SOT-23-5), the guitar input buffer, on `+5V` (pin 5) and GND (pin 2). Its symbol,
`seed3-carrier:TLV9061DBV` in `seed3-carrier.kicad_sym`, follows the TL07x style: U1A is the op-amp and U1B the power pins.
The AUX input and both outputs connect to the Daisy with no op-amp (see "AUX input", "Headphone output" and "Speaker / line send").

### Mid-rail reference (VREF)
R6/R7 (10k/10k) from `+5V`, with C7 (47 µF): `VREF` ≈ 2.5 V. With 5k source impedance, C7 gives a ≈ 0.7 Hz corner, which keeps
noise on `+5V` (from the display) out of `VREF`. Its only load is R1.

### Guitar input (J1 → `AUDIO_IN_1`)
J1 tip → C1 (100 pF to GND, RF shunt) → FB1 (ferrite bead) → C2 (47 nF C0G) → R1 (1M to `VREF`) → R2 (1k) → C18 (100 pF to
GND) → U1A follower → R20 (470 Ω) → `AUDIO_IN_1` (Daisy pin 16). D1 and C1 sit on `GTR_TIP`, the jack side of FB1.
- J1's tip switch shorts the tip to GND when nothing is plugged in.
- **C2 (47 nF C0G)** blocks `VREF`'s DC from the guitar. C0G isn't piezoelectric, so knocks on the board don't become signal at
  this 1 MΩ node. With R1 it's a 3.4 Hz high-pass, far below a guitar's 82 Hz low E. 47 nF is the largest C0G in 0805 in stock
  (DigiKey had no 100 nF C0G 0805); 25 V is plenty for 2.5 V of bias.
- **R1** sets both the 1 MΩ guitar load and the DC bias. **R2** is the only series resistance in this path. It protects U1A's input from plug-in transients.
- **RF filtering: C1, FB1 and C18.** The display's ESP32 transmits Wi-Fi in bursts, and an op-amp input rectifies RF into an
  audible buzz at the burst rate. C1 shunts RF at the jack. FB1 (Murata BLM18HG601SN1D, a GHz-band bead: 600 Ω at 100 MHz,
  rising toward 1 GHz) blocks what's left before it reaches the board's input traces, and is a fraction of an ohm at audio
  frequencies, so it adds no noise or tone. C18 sits at U1A's pin, with R2 a low-pass at ≈ 1.6 MHz. The guitar sees it as ≈ 100 pF more cable capacitance (C1 + C18 ≈ 200 pF, against
  a typical cable's 500–1000 pF). Same part as C1 (C0G).
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
`AUDIO_OUT_1` (Daisy pin 18) → R10 (3.3k) / C9 (1 nF to GND) → `HP_SOURCE` → C10/C11 (470 nF C0G) → U2 LEFTINM/RIGHTINM.
U2's + inputs (LEFTINP/RIGHTINP) go to GND through C22/C23 (470 nF C0G). U2 (TPA6130A2RTJR) drives J4 (`HP_L` tip, `HP_R`
ring) directly. The Daisy sets U2's volume and mute over I2C (pins 12/13) and shuts it down with `HP_SD` (pin 27).
- **What the Seed3 outputs are rated for:** 1 Vrms at 0 dBFS (Seed3 datasheet, Table 3). The datasheet gives no output impedance,
  minimum load or coupling-cap value for pins 18/19, and says only the *inputs* are AC-coupled.
  - **Line-out mode, not headphones.** The TAC5242 drives 16 Ω headphones (62.5 mW) only in its differential or pseudo-differential
    modes, set by its MD4/MD5 pins on the module. The Seed3 brings out one single-ended pin per channel at 1 Vrms, with single-ended
    AC-coupled inputs. That matches only MD5 high / MD4 low, "Single-ended output; Line-out only" (TAC5242 datasheet, Table 7-10),
    whose minimum load is 600 Ω. The module cannot drive headphones, which is why U2 is here. Electrosmith's own headphone circuit
    (Seed3 datasheet, Figure 3.9) also adds an amp (TPA6110A2).
  - **DC level: probably 0 V, not confirmed.** Figure 3.9 wires pin 18 straight across a volume pot to GND, which only works if the pin
    sits at 0 V DC, so the outputs are most likely AC-coupled on the module. TEST_PLAN measures it with the Daisy fitted.
- **No buffer between the Daisy and U2.** U2's differential input impedance is 37 kΩ at its highest gain and more at lower
  settings (TPA6130A2 datasheet, 9.2.2.1 and Figure 33), so each − input loads `HP_SOURCE` with ≥ 18.5 kΩ. With both channels
  in parallel the Daisy sees R10 plus ≥ 9.2 kΩ, ≥ 12.5 kΩ in all, far above the 600 Ω line-out minimum.
- **R10/C9** filter the DAC's out-of-band noise before U2: ≈ 50–65 kHz (R10 ‖ U2's inputs, 1 nF).
- **Level and volume:** U2's gain is set over I2C in 64 audio-taper steps from −59.5 dB to +4.0 dB, with a mute bit per
  channel (datasheet Table 2). R10 against both − inputs costs ≈ 2–2.7 dB, so the Daisy's 1 Vrms full scale reaches U2 at
  ≈ 0.75 Vrms. At volume word 0x35 (+0.1 dB) that is ≈ 0.75 Vrms per output: 35 mW into 16 Ω, 18 mW into 32 Ω. Word 0x30
  (−2.1 dB) gives ≈ 0.6 Vrms, rev 2's level. The datasheet's 138 mW into 16 Ω is for out-of-phase stereo; this board drives
  both channels in phase, so cap the firmware's maximum at 0x35 until TEST_PLAN 8.8 has checked clipping into 16 Ω.
- **Low end:** each channel's two input caps in series (235 nF) with ≥ 37 kΩ (+ R10): ≈ 17 Hz at the highest gain, lower at
  lower settings. TI sizes 470 nF for ≤ 20 Hz at every gain (9.2.2.1). The Daisy's own output coupling cap adds a second
  high-pass; its value isn't published.
- **U2, TPA6130A2 (DirectPath):** an internal charge pump makes a negative rail (CPVSS), so the outputs swing about 0 V with no
  output caps. Pop and click suppression, thermal shutdown, and 8 kV HBM and IEC contact ESD protection on the outputs. It
  runs from 2.5–5.5 V, from `+5V` through R29: 4 mA playing, 1.4 mA with the outputs disabled, 0.4 µA in hardware shutdown.
  PSRR 109 dB (inputs grounded), output noise 9 µVrms A-weighted, THD+N 0.0055 % at 35 mW into 16 Ω, output offset 0.4 mV
  maximum (datasheet 7.5, 7.6). The charge pump switches at 300–500 kHz, near U101's 400 kHz (see "Speaker amp").
- **Why the TPA6130A2 (2026-11-09, user's decision):** rev 3 is assembled by JLC, so U2 no longer has to be hand-solderable,
  which was the reason for the MAX9722A's TSSOP. LCSC had 76 MAX9722AEUE+ at $5.03 and 3,842 TPA6130A2RTJR at $0.99 (C130046,
  2026-11-09). It also gives the headphones a hardware mute (see "Output mute"), volume in the amp rather than only in the
  codec, and inputs that survive the Daisy playing into them with `+5V` off (see "Running from USB alone"). Audio rev 2
  keeps the MAX9722A.
- **U2 wiring** (datasheet Figure 45 and Pin Functions): single-ended input on each − pin (`HP_SOURCE` through C10/C11), and
  each + pin AC-grounded through C22/C23 at U2, as for single-ended inputs. That makes U2 inverting, as the MAX9722A was.
  Both channels are driven, so either stereo mode or dual-mono mode (register 1) plays on both outputs. C13 is the flying
  cap (CPP/CPN), C14 holds CPVSS, C15 bypasses the charge pump's VDD (pin 20) and C12 the analog VDD (pin 12): 1 µF each,
  the datasheet's value, 0805 X7R 50 V. The exposed pad and GND pins 3, 9, 10, 13 and 19 are one ground.
- **I2C and shutdown:** address 0x60 (fixed). SDA and SCL come from Daisy pins 13 and 12 (I2C1, libDaisy D12/D11), pulled up
  to the Daisy's `3V3_D` (pin 38) by R33/R32 (2.2k: TI asks for 1–2k on a 5 V bus; ≈ 1.5 mA at 3.3 V). `HP_SD` comes from
  Daisy pin 27 (ADC_5, libDaisy D20) with R34 (100k) to GND, so U2 stays in hardware shutdown while the Daisy is out,
  booting or in reset. SD, SDA and SCL are 5 V tolerant and rated −0.3 to 7 V whatever VDD is (datasheet 7.1), so the
  Daisy can drive them with `+5V` off. Hardware shutdown clears the registers; U2 restarts muted, outputs disabled.
- **U2's supply filter (`HP_5V`):** R29 (2.2 Ω) from `+5V`, and C21 (10 µF X7R 0805) beside C12/C15: about 6–10 kHz with
  the ceramics' derating, so the charge pump's 300–500 kHz ripple reaches `+5V` about 30 dB lower. `+5V` also feeds U1, `VREF`
  and the Daisy, and less ripple there also means less to beat with U101's switching. A ferrite bead wouldn't do it: beads
  like FB101 block 100 MHz-class noise and are a few ohms at 400 kHz. R29 drops ≈ 9 mV playing quietly and up to ≈ 0.2 V
  at full scale into 16 Ω, so U2 keeps ≥ 4.5 V of its 2.5–5.5 V range.
- **Output offset:** 0.4 mV maximum: 25 µA into 16 Ω.
- **No click at power-up:** U2 starts with its outputs disabled and muted, and the firmware enables them only after U2's 5 ms
  start-up and the input caps have settled (see "Firmware requirements").
- **Symbol and footprint:** `seed3-carrier:TPA6130A2RTJ` in `seed3-carrier.kicad_sym`, drawn for this board: inputs, SD and
  I2C on the left, outputs and charge pump on the right, the two VDD pins on top, grounds and the exposed pad (pin 21) on the
  bottom. KiCad's `Package_DFN_QFN:WQFN-20-1EP_4x4mm_P0.5mm_EP2.7x2.7mm` matches TI's RTJ0020D land pattern: 0.5 mm pitch,
  2.7 mm exposed pad, and pads (0.25 × 0.83 mm at ±1.96 mm) that cover TI's 0.24 × 0.6 mm at ±1.9 mm.

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
C109. Sheet 2's labels use the same two names.
- **No buffer.** The reason is the same as for the headphone path: R11 plus U101's 60 kΩ input is far above the 600 Ω
  line-out minimum (see "What the Seed3 outputs are rated for"). With no `VREF` bias or coupling caps before C108,
  `LINE_OUT` doesn't drift at power-on.
- **No DC-blocking cap on this board's side: this path assumes pin 19 sits at 0 V DC.** The outputs are most likely
  AC-coupled on the module (see "DC level" under "Headphone output"). C108 blocks DC into U101 anyway, but R12 would carry
  it. If TEST_PLAN finds more than a few tens of mV at pin 19, the fix is a 10 µF cap in series between C16 and
  `LINE_OUT`.
- **R11** is the output impedance. With R12 (100k) in parallel with U101's 60 kΩ input (20 dB, ±20 %), it costs ≈ 0.23 dB.
  If `LINE_OUT` is shorted, the Daisy sees R11 alone: 1k, still above its 600 Ω minimum load.
- **R12** gives the Daisy's output coupling cap a DC return, so `LINE_OUT` sits at 0 V.
- **Pseudo-differential into a differential input.** The Daisy has one output pin per channel, so LINE− is the
  source-side ground through 1k, not an inverted copy of the signal. Both sheets share one ground net and the In1 plane,
  but the class D's supply current flows in that plane around U101 and J101. U101 amplifies only LINE+ − LINE−, so any
  ground difference between the Daisy's corner and U101's is rejected rather than added to the speaker signal. R21 sits
  beside R11 at the Daisy's front-right corner, away from those currents, so LINE− senses the source's ground.
- **R21 (1k) balances the two legs.** LINE+ comes through R11 (1k), so LINE− gets the same 1k. The amp's common-mode
  rejection depends on equal source impedances. C16 makes LINE+ slightly lower impedance above ≈ 20 kHz, which only matters
  out of band.
- **Routing:** R11, R12, C16 and R21 sit in a column just left of C108/C109, and the pair runs about 6 mm on F.Cu over the
  In1 plane into C108/C109 from below. `AUDIO_OUT_2` reaches R11 from Daisy pin 19 on In2, under the module (see "Routing").
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
- **Headphones: U2's SD and mute bits.** R34 holds `HP_SD` low while the Daisy is out, booting or in reset, so an IWDG
  reset shuts U2 down (outputs off, 0.4 µA). Running, the firmware mutes U2 over I2C. The codec also mutes its DAC when its
  clocks stop (see "The codec mutes").
- `SPK_EN` (Daisy pin 28) drives Q2's gate, with R17 (100k) pull-down. Q2 (2N7002) pulls `SPK_MUTE` to GND, which
  means speaker on. R107 (10k, sheet 2) pulls `SPK_MUTE` up to `+5V_RAW`, which means muted. R108 (2.2k) and
  C124 (1 µF) carry it to U101's MUTE pin (active high).
- **Levels:** low (playing) is a few mV (Q2's on-resistance against R107's 0.5 mA), against U101's 0.8 V VIL. High (muted) is ≈ 5 V, against
  2 V VIH and MUTE's PVCC + 0.3 V maximum. After an IWDG reset, MUTE rises through R107 + R108 (12.2 kΩ) into C124 and passes
  2 V in ≈ 5.6 ms. Both edges slew ≈ 2.3 V/ms or slower, inside the TPA3118's 10 V/ms limit for MUTE and SDZ.
- **D103 (BAT54H Schottky, anode on MUTE, cathode on PVCC)** holds MUTE near PVCC when PVCC falls first (see "Power
  sequence"). Reverse-biased in use; its leakage (2 µA maximum at 25 V and 25 °C, NSVBAT54HT1G) flows through R108 and Q2
  while playing, a few millivolts against the 0.8 V VIL.
- **No series resistor:** rev 2's R23 (470 Ω) limited Q2's current if a wire on the old inter-board terminal drove
  `SPK_MUTE`. On one board only R107 drives it (0.5 mA), so R23 is gone.
- **How it works:** the firmware feeds the STM32's independent watchdog (IWDG) only from the audio callback. The IWDG runs
  on its own clock, so if the callback stops (hung firmware, stalled DMA, fault handler), it resets the STM32. During a
  reset, and while the Daisy is booting or in DFU, its pins float, and R17 holds `SPK_EN` low (speaker amp muted).
- **The codec mutes.** The STM32 clocks the TAC5242, and the TAC5242 powers down its DAC by itself when its audio clocks
  stop (TAC5242 datasheet, section 7.4.1). An IWDG reset therefore silences pins 18/19, and with them J4 and U101, and
  R34 shuts U2 down as well. This doesn't help while the clocks keep running, such as a DMA looping a stale buffer with the
  CPU hung, which is why the IWDG has to reset the chip. The datasheet doesn't say whether the power-down clicks.
- **Why Q2 instead of driving `SPK_MUTE` from the Daisy pin:** R107 holds `SPK_MUTE` at `+5V_RAW` whenever the battery is on,
  including while the Daisy is unpowered or out of its sockets. An open-drain Q2 keeps the Daisy from being back-powered
  through it, and keeps the speaker muted unless the Daisy is running.
- **Trade-off:** an external retriggerable one-shot watching an audio-callback toggle would watch the audio from outside the
  STM32. The IWDG is inside the chip, so the mute depends on the firmware feeding it only from the audio callback. Never
  feed it from the main loop.
- **Why U2's SD can come from the Daisy:** SD, SDA and SCL are 5 V tolerant and rated to 7 V whatever U2's supply is, so
  the Daisy can drive them on USB alone, with `+5V` off, and no level translator is needed.

## Power section (sheet 2)
Sheet 2 is power board rev 1's circuit. `../../power-board/README.md` holds rev 1's original reasoning and the battery and
speaker details; this section is the design as it stands on rev 3.

### Battery input
- **The battery** is a Talentcell rechargeable power bank (72 W, 100 Wh). The board takes its 12 V DC output. The listing
  doesn't say whether that output is regulated, so the design assumes 9.0 V empty to 12.6 V full. Measure it.
- **J101** (Same Sky PJ-102AH, 2.0 mm pin, 5 A) sits on the rear edge, opening rearward. J101 → F101 (Bel 0683G3150-01,
  T3.15A SMD slow-blow fuse, see below) → SW101 (screw terminal to the panel switch, an NKK S1B rated 5 A) → Q101 →
  `VBAT_PROTECTED`.
- **Q101 (IRF4905 P-FET)** is the reverse-polarity protection: drain to the switch, source to the load, gate to GND through
  R101 (10k), D101 (BZT52C12, 12 V) from gate to source. With the battery the right way round the body diode lifts the
  source and Q101 turns on. D101 holds VGS to about −12 V (rated ±20 V). With the battery reversed the gate sits at the
  source and the body diode blocks.
- **`VBAT_PROTECTED`** feeds U101's PVCC through R105 (0 Ω 2512, "amp isolation"), the DFR0571 through J106, and the battery
  divider. Everything on it is after SW101, so the board draws nothing from the battery while the switch is off.
- **F101, Bel 0683G3150-01:** 3.15 A slow-blow, 4818-size square ceramic SMD fuse (12.0 × 4.65 mm), 125 V DC, interrupts
  2 kA at 125 V DC; melting I²t 16.9 A²s, 0.028 Ω cold (0.16 V at rated current); about 97 % of rating at 85 °C (0683G
  datasheet). Same rating and interrupting class as power rev 1's T3.15A 5 × 20 mm ceramic fuse (1.5 kA), without the
  36 mm holder. Switch-on charges C111/C112 and the DFR0571's input caps; the estimated surge is under 0.2 A²s, about 1 % of
  its melting I²t (TEST_PLAN measures it). Not to be run between 100 % and 210 % of rating for long (datasheet); the board
  draws at most ≈ 2.4 A on loud peaks. It is soldered, not replaceable in a holder: a blown fuse means a fault to find
  first. JLC has no stock, so it is soldered by hand and left out of the CPL. Pads are the datasheet's reflow layout.
- **Overvoltage:** the board itself survives up to 24 V on J101. U101 is specified to 26 V; C111, C112 and C115 are rated
  25 V; D101 limits Q101's gate. The DFR0571's input limit is unknown.

### 5 V supply and distribution
- **The DFR0571** buck module is off the board. J106 sends it `VBAT_PROTECTED` and J107 takes its 5 V back as `+5V_DFR`. Its
  specifications aren't on DFRobot's site (its page for the SKU returns 404). A reseller lists 8–28 V in, 5 V ± 0.1 V out,
  3 A peak and 0.5 mA with no load, and no input reverse protection; the parts order gives 1.6 A continuous. Unverified:
  TEST_PLAN measures the module before it is wired to the board. It is a non-isolated buck, so its input and output
  grounds are one node.
- **Q102 (AO3401A)** sits between `+5V_DFR` and `+5V_RAW`, gate to GND (drain to J107, source to the load). A reversed 5 V source
  on J107 then can't put −5 V on `+5V_RAW`, where U103 (VDD rated −0.3 V minimum) and the display on J105 would take it.
  With the DFR0571 wired normally its reach is narrower: the module's grounds are common, so swapping J107's two wires
  shorts the module's output rather than reversing it (see "What each connector can see"). It drops ≈ 45 mV at 0.75 A
  (60 mΩ maximum at VGS = −4.5 V, AO3401A datasheet).
- **`+5V_RAW`** feeds two filtered branches:
  - **Audio:** FB101 (220 Ω at 100 MHz, MPZ1608S221A) → `+5V`, sheet 1's analog rail and the Daisy's VIN. C105 (100 nF)
    sits after the bead; C104 (100 µF) is optional bulk through JP102.
  - **Display:** FB102 → `+5V_DISPLAY` → J105, the display's own supply pair. C107 (100 nF) sits after the bead; C106 (100 µF)
    is optional bulk through JP104.
  - **Local parts:** C103 (10 µF) and C123 (100 nF) at Q102, plus U103 and the pull-ups R107, R109, R112, R113.
- **The jumpers are rev 1's experiments, kept for rev 3.** JP101 and JP103 bypass the beads; JP102 and JP104 connect the
  optional bulk caps. Set them from what power board rev 1's bring-up shows, and record the setting in the test log.
- **The audio rail's budget:** `+5V` must stay at 4.75 V or more, and the firmware won't start audio below 4.7 V
  (`5V_SENSE`). On the way from the DFR0571 there are Q102 and FB101: about 45 mV at the audio side's ≈ 0.3 A plus
  the display current through Q102. A DFR0571 at 4.85 V or more is enough.

### Supervisor, shutdown and mute
- **U103** (TPS3808EG50, 4.65 V threshold, 20 ms delay with CT open) watches `+5V_RAW`. Its open-drain RESET output
  (`AMP_PG`, R109 10k pull-up) drives `AMP_SDZ` through R110 (2.2k), with R111 (100k) to GND and C125 (1 µF). U101 stays shut
  down until the 5 V has been good for 20 ms, and shuts down as soon as it sags. JP105 (left open) pulls MR low to force a
  reset, which also clears U101's fault latch.
- **D102 (BAT54H Schottky, anode on SDZ, cathode on PVCC)** holds SDZ near PVCC when PVCC falls first, as D103 does for
  MUTE. Its leakage into SDZ (2 µA maximum at 25 °C, tens of µA when hot) sees R110 ‖ R111 (2.15 kΩ) while U103 holds
  `AMP_PG` low: under 0.25 V, against SDZ's 0.8 V VIL.
- **MUTE:** see "Output mute". R107 pulls `SPK_MUTE` up; Q2 on sheet 1 pulls it down to play.
- **FAULTZ** (R112 10k pull-up, R114 18k to GND, TP109): U101 latches its outputs off on an output short, overtemperature or
  too much DC at the output (TPA3118 datasheet, Table 4). The latch clears when SDZ goes low, by a power cycle or JP105.
  FAULTZ reaches Daisy pin 32 (`AMP_FAULTZ`, the sixth sheet pin, then R30 on sheet 1), so the firmware can show the fault. R112/R114 divide its
  high level to `+5V_RAW` × 18/28: ≈ 3.2 V, 3.05 V at 4.75 V and 3.54 V at 5.5 V, a logic high for the 3.3 V pin and below
  its VDD + 0.3 V. When `+5V_RAW` is off, the Daisy's pin sees 0 V through R114 (on USB alone, for example). FAULTZ still
  isn't tied to SDZ: no automatic retry into a short. R30 (1k) limits the current to ≈ 3.3 mA if the firmware ever sets
  pin 32 as a high output while U101 holds FAULTZ low; with the pin an input, it carries no current and changes no level.
- **Power sequence:** with the switch on, `VBAT_PROTECTED` and PVCC rise first, then the DFR0571's 5 V. U103 releases SDZ
  20 ms after `+5V_RAW` passes 4.65 V. On switch-off, `+5V_RAW` stays at or below PVCC, because the DFR0571 runs from PVCC's
  node, and U103 pulls SDZ low as it falls. But C124 holds MUTE (R108 2.2k, 1 µF) and C125 holds SDZ ((R110 ‖ R111), 1 µF)
  for milliseconds, and PVCC falls faster: about 1.2 V/ms with 0.25 A of load on C111/C112's 200 µF. With MUTE high
  (headphones in, or the Daisy booting), MUTE and SDZ would sit volts above PVCC as it falls through 4.7 V, with C124 and
  C125 discharging into U101's protection diodes at ≈ 1 µF × 1.2 V/ms ≈ 1.2 mA each, which TI doesn't rate. D103 and D102
  take that current instead: a BAT54 drops 0.32 V at most at 1 mA (Diodes Inc. BAT54WS datasheet; onsemi's own page didn't
  download, and its listed 2 µA at 25 V and 0.8 V at 100 mA match), where U101's silicon diodes pass far less. TEST_PLAN 3C.9
  measures MUTE − PVCC and SDZ − PVCC. On the bench, 5 V alone on J107 is still ruled out (see "Decisions").

### Battery level
- R102/R103 (100k/10k, 1 %) divide `VBAT_PROTECTED` straight onto `BATT_SENSE`, Daisy pin 25: **VBAT / 11**, from a
  9.1 kΩ source. 1.15 V at 12.6 V, 1.01 V at 11.1 V, 0.82 V at 9.0 V. With both resistors at 1 % the ratio is within
  ±1.8 %. The firmware converts with VBAT = 11 × V(pin 25), the same constant as rev 2 and power rev 1's two dividers.
  It draws 115 µA at 12.6 V.
- With C17 (100 nF) at pin 25 the filter corner is ≈ 175 Hz, far above battery changes; C17 also supplies the ADC's
  sampling charge, and the 9.1 kΩ source is inside the ADC's 10 kΩ guidance (`power-board/README.md`).
- Pin 25 is the STM32's PA7, a TT_a pin rated 4.0 V absolute. Even 24 V on J101 puts only 2.2 V there. With the Daisy
  unpowered and the battery on, it sees at most 1.15 V.
- The divider sits after SW101, so it draws nothing while the amp is off.

### Speaker amp (U101, TPA3118D2)
- **Mono, PBTL.** LINP and LINN go to GND, so the device starts in mono mode. OUTPR and OUTNR are tied for the positive
  speaker terminal, and OUTNL and OUTPL for the negative one (TPA3116D2/TPA3118D2/TPA3130D2 datasheet SLOS708G, 7.4.1). ERC
  reports those ties as two output-to-output conflicts; they are excluded in the project with that reason.
- **Gain 20 dB, master:** R104 (5.6k) from GAIN/SLV to GND, nothing to GVDD (SLOS708G Table 1). Input impedance is 60 kΩ
  per leg ±20 %. Don't go above 32 dB: 36 dB drops the input impedance to 9 kΩ.
- **Inputs:** C108/C109 (470 nF C0G, 1206, matched) into the inputs, biased at 3 V inside the device: a 5.6 Hz high-pass
  (7 Hz at the input impedance's −20 %), far below the low E's 82 Hz. C0G isn't piezoelectric and doesn't lose capacitance
  with voltage, so knocks don't become signal and both legs stay matched. 470 nF is the largest C0G in 1206 in stock.
- **Supplies:** PVCC from `VBAT_PROTECTED` through R105; C111/C112 (100 µF) bulk on the B.Cu PVCC pour, and C113/C114
  (100 nF) at the two PVCC pin pairs.
  AVCC through R106 (10 Ω), with C115 (1 µF) and C116 (100 nF). GVDD has C110 (1 µF); PLIMIT ties to GVDD (no power limit).
  MODSEL goes to GND: BD mode. AM0–AM2 go to GND through JP106–JP108, solder jumpers bridged in copper on the back:
  the default switching frequency (≈ 400 kHz). U2's charge pump runs at 300–500 kHz (TPA6130A2 datasheet 7.6), so the two
  can beat into the audio band, directly or through harmonics. If a steady tone shows up with no signal, cut one jumper
  to move U101's frequency (the datasheet's AM2–AM0 table), and record the setting.
- **Output:** bootstrap caps C117–C120 (220 nF), then the LC filter L101/L102 (10 µH, Bourns SRP1038A) with C121/C122
  (680 nF), into J102. J102 pin 2 is SPK+ and pin 1 SPK−, marked on the silkscreen. The output is bridged, so neither
  speaker wire may be grounded.
- **Levels:** the Daisy's full scale (1 Vrms, ≈ 0.98 Vrms after R11/R21) becomes ≈ 9.8 Vrms. That clips on the battery:
  ≈ 1.5 dB below full scale on a full pack, ≈ 4.5 dB near 9 V. The firmware caps the speaker level about 5 dB below full
  scale. Into 4 Ω, expect ≈ 17 W at clipping on a full pack, drawing up to ≈ 1.6 A from the battery on loud peaks.
- **Speakers:** a Jensen MOD10-50 (4 Ω) or a Skar FSX10-4 (4 Ω), one at a time (`power-board/README.md`).

## Audio 5 V (`+5V`)
`+5V` comes from FB101 (or JP101) on sheet 2, through the `+5V_AUDIO` sheet pin.
`+5V` feeds Daisy VIN (pin 39), U1, U2 (through R29), `VREF` and the `5V_SENSE` divider (R18/R19). The display takes its power from J105,
not from here.
- **No Q1:** rev 2's Q1 (AO3401A) protected the old audio board's 5 V terminal against a reversed wire. Q102 protects all
  of `+5V_RAW` on one board, so Q1 is gone, and with it ≈ 20 mV of drop.
- **Wires on the wrong terminal:** on one board, the only signal terminal left on sheet 1 is J3 (see "Display connector").
  R8 (10k) limits the current into Daisy TX. On RX, R9 and R24 divide a 5 V wire to at most 4.78 V at pin 15 (PB7), inside
  the Seed3's 0–5 V GPIO rating.
- **Bulk at the entry:** C5 (47 µF electrolytic) and C4 (100 nF) after FB101. C5's ESR damps ringing between the DFR0571's
  wiring and the ceramics; C104/C105 sit at FB101.
- **Local decoupling:** C6 at U1 pin 5, and C12 (VDD, pin 12), C15 (VDD, pin 20) and C21 at U2, behind R29.
- **Display supply:** the display's current pulses (ESP32 Wi-Fi, backlight PWM) flow through FB102 and J105, never through FB101
  or `+5V`, and they return to J107's ground on the left edge, behind the input buffer (see "Isolation").

### Running from USB alone
The Seed3 runs from its own USB port, and the datasheet says USB and VIN can be connected together, so USB doesn't appear
to drive the VIN pin. With USB plugged in and the battery switched off (flashing or debugging on the bench), the Daisy runs
while `+5V`, `+5V_RAW` and PVCC are at 0 V. Any Daisy output that is high then pushes current into an unpowered part
through that part's input protection diodes.
- **Q102 conducts backwards** if `+5V_RAW` is lifted, because its gate is tied to GND. That would only leak a little
  current toward the DFR0571. Nothing on the board back-powers `+5V`.
- **Display UART:** with the battery off, the display is unpowered too, and Daisy TX idles high into it. R8 (10k) limits that
  current to ≈ 0.27 mA. See "Display connector (J3)".
- **Headphone amp:** C10/C11 pass pin 18's audio to U2's − inputs, which are rated −2.5 V to 3.6 V absolute, not relative
  to U2's supply (TPA6130A2 datasheet 7.1), so the Daisy's ±1.4 V full scale is safe with `+5V` off. The firmware still
  keeps `HP_SD` low until `+5V` is up.
- **`5V_SENSE`:** the firmware has to know whether `+5V` is up, for U101's inputs (below) and before it enables U2:
  R18/R19 (100k/100k) divide `+5V` to ≈ 2.5 V on `5V_SENSE` (Daisy pin 22, ADC_0). While it reads low, the firmware keeps
  `AUDIO_OUT_2` at digital silence and U2 shut down (see "Firmware requirements").
  - **Why not `BATT_SENSE`:** it reads the battery, not the 5 V; a DFR0571 that fails or is unplugged would leave it reading
    normal.
  - **Why 100k/100k:** 2.5 V is well inside the ADC range and the divider draws 25 µA. The Daisy's VIN is `+5V`, so whenever
    `+5V` is up the Daisy is powered too, and the divider can't back-power it. With `+5V` off, R19 holds the pin at 0 V.
  - **No filter cap:** the source impedance is 50k, so the firmware uses a long ADC sample time.
  - **Limit: a fast power loss.** The firmware reacts within one or two audio blocks plus the codec's output delay, a few ms.
    If `+5V` collapses faster than that (the battery switched off under load), the last few ms of audio still reach
    U101's unpowered inputs (next item). The TEST_PLAN measures this.
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
| J106 (to the DFR0571's input) | The module's input cable, a JST XH 2-way plug (XHP-2): pin 1 BAT+, pin 2 GND | Keyed: only the module's input cable fits, one way round, and the bare 5 V and display wires fit only the screw terminals. A cable crimped with its two wires swapped still shorts `VBAT_PROTECTED` to GND through the module's ground and J107's ground wire: F101 or the pack's own protection stops it; the module's ground track may not survive (accepted, see "Decisions") |
| J107 (from the DFR0571's output) | 5.0 V ± 0.1 V | Its two wires swapped: the module's output is shorted, and its own current limit has to hold. A reversed source that doesn't share J106's ground (a bench supply): Q102 blocks. J107's and J105's wire pairs swapped with each other: everything still works (the module feeds `+5V_RAW` through FB102, the display gets 5 V through Q102) |
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
GND). Every capacitor on the audio path is C0G: C2, C10/C11, C22/C23 and C108/C109.

### Links between the sheets
The first five nets were the screw-terminal contract between audio rev 2 and power rev 1 (`power-board/README.md`). On one
board they are traces, and the numbers still hold. `AMP_FAULTZ` is new in rev 3.

| Sheet 1 net | Sheet 2 net | From | Promise |
|---|---|---|---|
| `+5V` | `+5V_AUDIO` | FB101 / JP101 | 4.75–5.25 V (see "The audio rail's budget") |
| `BATT_SENSE` | `BATT_SENSE` | R102/R103 | VBAT / 11 from 9.1 kΩ, 1.15 V at most in use |
| `SPK_MUTE` | `SPK_MUTE` | R107 pull-up, Q2 pull-down | ≈ 5 V muted, a few mV playing |
| `LINE_OUT` | `LINE_OUT` | R11 (1k) | Audio, 1 Vrms full scale, ≈ 0 V DC, into 60 kΩ |
| `LINE_REF` | `LINE_REF` | R21 (1k) to GND | 0 V ± 10 mV, into 60 kΩ |
| `AMP_FAULTZ` | `AMP_FAULTZ` | U101 FAULTZ, R112/R114; R30 (1k) to pin 32 | ≈ 3.2 V, no fault; < 0.8 V, a latched fault; 0 V with `+5V_RAW` off |

One ground net joins the sheets, through the planes.

### Display connector (J3)
J3 is a 3-way 3.5 mm screw terminal (Phoenix PT 1,5/3-3,5-H) on the left edge: 1 GND, 2 `UART_TX_CONN` (TX), 3
`UART_RX_CONN` (RX), marked on the silkscreen. The display takes its power from J105, beside it. R8 (10k, Daisy TX) and R9
(10k, Daisy RX) sit next to J3, in series with the UART on its way to Daisy USART1 (pins 14/15, `DISPLAY_UART_TX` /
`DISPLAY_UART_RX`). They limit current if a wire lands on the wrong terminal or the display and the Daisy power up at
different times, and add a little ESD margin.
- **J3's GND is needed:** the UART needs a common reference. The display's ground also returns with its power wire on J105,
  so some display return current comes back through J3's GND. J3, J105 and J107 sit together on the left edge, so that loop
  and its current stay at the 5 V entry, behind the input buffer (see "Isolation").
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
- **C19/C20 (10 pF C0G) filter RF off the UART:** each sits on the Daisy side of R8/R9, so with the 10k it's a low-pass that
  cuts 2.4 GHz by ≈ 60 dB, keeping the display's Wi-Fi off the board's traces and the Daisy's pins. C19 loads the Daisy's own
  TX pin, so it doesn't slow TX edges; C20 adds ≈ 0.1 µs to RX.
- **Baud rate limit:** 10k with ~60 pF of cable, pin and C20 capacitance is a ≈ 0.6 µs time constant. That is fine up to
  230400 baud, but not for 921600.

### Daisy pins
Used: 14/15 (display UART), 16/17 (audio in), 18/19 (audio out), 20/40 (GND), 22 `5V_SENSE`, 23 `HP_DETECT`, 25 `BATT_SENSE`, 28 `SPK_EN`,
32 (`AMP_FAULTZ` through R30), 39 VIN; 12/13 (I2C1 to U2), 27 `HP_SD` and 38 `3V3_D` (the I2C pull-ups). Every other pin,
including `3V3_A` (21) and USB D−/D+ (36/37), is marked no-connect. With the Daisy out, its sockets (A1) give probe access to every audio board net, so there are no breakout headers.
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
- Start the codec with its output at digital silence and ramp up.
- **U2 (TPA6130A2, I2C1 at 0x60, 100 or 400 kHz):** initialise `HP_SD` (pin 27, D20) as a low output. Once `5V_SENSE` has
  met the start-up condition below, drive `HP_SD` high, wait at least 5 ms, write register 1 = 0xC0 (both outputs on,
  stereo; 0xD0 for dual mono) and register 2 = volume with the mute bits clear, ramping from a low word. Keep the volume
  word at or below 0x35 (+0.1 dB) until TEST_PLAN 8.8 has checked 16 Ω; 0x30 matches rev 2's level. Mute (register 2 bits
  7:6) before changing modes and before driving `HP_SD` low. If the I2C write fails (no ACK), keep `HP_SD` low and report it.
  U2 inverts the signal; negate it in firmware if absolute polarity matters.
- Read `BATT_SENSE` (pin 25, ADC) and send the battery level to the display every few seconds: VBAT = 11 × V(pin 25) (see
  "Battery level"). Warn on the display when it gets low.
- Read `5V_SENSE` (pin 22, ADC_0) with the longest ADC sample time (its source impedance is 50k). It reads ≈ 2.4–2.5 V with
  `+5V` at 4.85–5.0 V.
  - **Before starting audio:** require it above 2.35 V (`+5V` ≥ 4.7 V) for at least 10 ms. Then ramp the outputs up.
  - **While running:** sample it from the audio callback on every block. Below 2.2 V (`+5V` < 4.4 V) write silence from that
    block on and drive `HP_SD` low. Hold the outputs silent until the start-up condition above is met again.
  - This applies on USB alone on the bench too.
- Read `AMP_FAULTZ` (pin 32, SAI2_SD_B: libDaisy's D25, PA0) as an input with no pull: **low = speaker amp fault** (a shorted speaker wire,
  overheating, or DC at its output). Trust it only once `+5V` has been good for 50 ms (U103 holds U101 in shutdown for the
  first 20 ms). On a fault, mute the speaker send, drive `SPK_EN` low and show "speaker fault" on the display; only a
  power cycle or JP105 clears U101's latch. Never set pin 32 as an output: R30 only limits the current if it is.
- Read `AUDIO_IN_2` (the AUX input, mono) and mix it in after the NAM model and cabinet EQ, with its own level control from
  the display. It goes to both outputs. It arrives ≈ 22 dB below the source, so apply gain before the mix.

## Decisions
Accepted during rev 3's design review and layout (2026-11-07), with the reason. The user delegated these calls.
- **PBTL ERC exclusions.** ERC's two U101 output-to-output conflicts (OUTPR–OUTNR, OUTPL–OUTNL) are the datasheet's PBTL
  wiring (SLOS708G 7.4.1). They are excluded in `seed3-carrier.kicad_pro` with that reason, so ERC shows 0 errors and any new
  error stands out.
- **Q102 at J107.** Added, because a reversed 5 V source on J107 would put −5 V on all of `+5V_RAW` (U103, the display), and rev 2's
  Q1 only covered the audio branch (Q1 is now gone, see below). The design review assumed the DFR0571's own wires could do that; they can't, because its
  grounds are common (swapped J107 wires short its output instead). Q102 stays for a reversed bench supply or a module whose
  input-side ground isn't connected: one SOT-23 and ≈ 45 mV.
- **No 5 V alone on J107, ever: bench supply on J101 only.** With PVCC at 0 V and 5 V on `+5V_RAW`, U103 releases SDZ and
  R107/R108 pull MUTE high. D102 and D103 then conduct and charge PVCC through R107–R110 (12.2 kΩ per pin) to about 4.5 V
  against the battery divider's 110 kΩ. SDZ and MUTE stay within ≈ 0.3 V of PVCC, but U101 sits at its 4.5 V minimum supply
  with SDZ high and may start and stop. Without the diodes, the same ≈ 0.36 mA per pin went into U101's own protection
  diodes, which TI doesn't rate. Normal power-up and power-down never get there (see "Power sequence"), so the rule stays
  procedural.
- **FAULTZ latches until power cycle or JP105.** Rev 1's choice, kept: a fault does no damage, and an automatic retry would
  pulse a shorted speaker wire. The Daisy now sees it (pin 32), so the display can say why the speaker went silent.
- **J106 is a keyed JST XH header (2026-11-09, user's decision).** With J106 and J107 identical screw terminals side by side,
  the module's two wire pairs could go in swapped: 12 V on the module's 5 V output reaches its input through the buck's
  high-side MOSFET body diode, then J107, Q102 and all of `+5V_RAW` and `+5V` (U1, U2, U103, the Daisy, the display). The
  display's lead on J106 would put 12 V on the display. J106 is now a JST S2B-XH-A (side entry, 3 A per contact; the module
  draws ≈ 0.75 A): only the module's input cable fits it, one way round. Still possible, and accepted: J107's two wires
  swapped (shorts the module's output, whose current limit has to hold), the input cable crimped with its wires swapped
  (shorts the battery through the module's ground; F101 or the pack's protection stops it; TEST_PLAN 3A.3 and 3B.1 check
  for it), and J107 and J105 swapped with each other (harmless, see "What each connector can see").
- **D102/D103 clamp SDZ and MUTE to PVCC (2026-11-09, user's decision).** Every switch-off with the speaker muted took
  C124 and C125 into U101's unrated protection diodes (see "Power sequence"). Two SOD-323 Schottkys, beside C125's and
  C124's RC, take that current. Power rev 1 has the same weakness: its bring-up (3C.9) shows the real numbers.
- **R30 (1k) in series with Daisy pin 32 (2026-11-09, user's decision).** A firmware mistake that drives PA0 high while
  FAULTZ is low would otherwise short the STM32's output into U101's open drain.
- **U2 is a TPA6130A2 (2026-11-09, user's decision).** JLC assembles rev 3, so the hand-solderable TSSOP that chose the
  MAX9722A no longer matters, and LCSC had only 76 MAX9722As at $5 each against 3,842 TPA6130A2s at $0.99. The swap adds a
  hardware headphone mute (SD from the Daisy, R34 holding it off through a reset), I2C volume, and inputs rated to
  −2.5…3.6 V with the supply off. It costs three Daisy pins (12, 13, 27), pin 38's 3.3 V for the pull-ups, and the
  firmware has to enable U2 before the headphones play. The + inputs are AC-grounded at U2 with no resistor to match R10:
  the input-cap layout leaves no room for one, and the MAX9722A's + inputs were grounded at the amp too.
- **J102's pins swapped** (pin 2 SPK+, pin 1 SPK−), so the speaker traces from L101/L102 don't cross. The silkscreen marks them.
- **U101's, C110's and U2's ground pads join the F.Cu pour solidly** (pad-level zone connection). They are boxed in by
  0.5–0.65 mm pitch routing and tied to ground by tracks and pad vias, so the pour can't reach them with two thermal spokes.
  U101 and U2 are reflowed (or soldered with hot air) anyway.
- **U2's exposed pad has four vias** (0.6/0.35 mm) into In1, In2 and B.Cu ground, as U101's has. They sit under paste, so
  some solder may wick into them; ask JLC to plug or tent them if the order offers it.
- **The VBAT branch to J106 runs on In2** (1 mm, 0.5 oz): it carries only the DFR0571's input current, ≈ 0.75 A at most. All
  battery, PVCC and speaker current paths are on the 1 oz outer layers.
- **Nine references are 0.8 mm tall** (C113, C124, C125, D102, D103, R106, R109, R111, U101) in the dense area around
  U101's control pins, R30's beside JP105, and thirteen around U2 (U2, C3, C10–C15, C22, C23, R10, R32–R34). JLC's
  recommended minimum is 1.0 mm; 0.8 mm with a 0.15 mm stroke prints.
- **Under 100 × 100 mm (2026-11-07, user's decision).** The board is 100 × 78 mm, from 122 × 78, for JLC's 4-layer price
  break. To get there: the Daisy and the power side moved 10 mm left; F101 became an SMD fuse (Bel 0683G, same 3.15 A
  slow-blow rating and interrupting class) instead of a 36 mm 5 × 20 mm holder, which let J101 stay on the rear edge; L101
  and L102 stand upright above and below U101's outputs, with J102 on the right edge between them; and three parts the
  merge made redundant went: Q1, R23 and the second battery divider (R13/R22, R102 now 100k). The firmware's battery
  constant (×11) is unchanged. The switching nodes are 60 mm from the guitar input (66 before) and 20 mm from U2's input
  network, as before.
- **Noise and fault changes (2026-11-08, user's decision).** Three of the noise review's items, done together:
  - U2 gets its own RC supply filter (R29 2.2 Ω, C21 10 µF), to keep its charge pump off `+5V`.
  - C108/C109 are 470 nF C0G (1206) instead of 1.5 µF X7R (0805): no microphonics at the speaker amp's inputs. 1 µF C0G
    isn't made in 1206 or 1210 in stock; 470 nF moves the corner from 1.7 Hz to 5.6 Hz.
  - FAULTZ reaches Daisy pin 32 through the R112/R114 divider, so a latched speaker fault shows on the display.
  The fourth item, more bulk on PVCC, waits for bring-up (rev 1's optional bulk caps).
- **Floorplan (accepted 2026-11-08, user's decision).** The 2026-11-07 layouts stand:
  - U2's input network is 20 mm from the class D's switching nodes, over the In1 plane; U2 sits in front of the power
    section because the left column is full.
  - The display's ground terminals (J3, J105) are 26–31 mm from the guitar input's 1 MΩ node. The display current loop
    stays at the left edge, behind the input buffer.
  - About 50 references and legends are 0.8 mm tall, in the dense areas: the 5 V filter column, the columns beside the
    Daisy and around U101. 0.8 mm with a 0.15 mm stroke prints at JLC.
  - `AUDIO_OUT_2` runs 32 mm on In2 and `AUDIO_IN_2` 16 mm on B.Cu, under the Daisy.
  Bring-up's noise checks (TEST_PLAN stage 7) confirm it.
- **The 5 V bench check order** is in TEST_PLAN.md: the DFR0571 connected, 12 V current-limited on J101, then each block.

## Open items
- **AUX input at pro line level with the board off:** a ±5 V source on J2 reaches the unpowered codec at ≈ ±0.4 V, past its
  −0.3 V … AVDD + 0.3 V rating, at ≈ 0.3 mA (R3 ‖ R4 = 5k into R5). Not changed: the case is rare and the current small.
  If it matters, R5 at 330 Ω brings it to ≈ ±0.29 V for ≈ 3 dB less level (a value change only, see "AUX input").
- **Bring up audio rev 2 and power rev 1 first,** and fold their results into rev 3 before ordering it: the Daisy outputs'
  DC level (the speaker send has no DC block on this side), the fuse rating and the switch-on surge through F101, beads or bypass, the optional bulk caps, L101/L102's
  value, R105, and headphone clicks at boot. Set the jumpers and parts to match.
- **The DFR0571's specifications:** confirm the reseller's figures (8–28 V in, 5 V ± 0.1 V, 3 A peak) and its output current
  limit on the module itself.
- **No low-battery cutoff on the board.** `power-board/README.md` asks for one, but sheet 2 has none: U103 watches only
  `+5V_RAW`. As the pack runs down, the Talentcell's own protection or the DFR0571's dropout ends it. TEST_PLAN records what
  actually happens; the firmware warns from `BATT_SENSE` first.
- **Battery:** measure the Talentcell's 12 V output at full charge and near empty (9.0–12.6 V assumed).
- **Test the watchdog mute:** stall the audio callback in a debug build. Check that J4 and the speaker go silent and
  `SPK_MUTE` mutes within ~10 ms.
- **2N7002 gate drive:** Q2 is driven from 3.3 V logic. That should be enough for R107's 0.5 mA, but check it on the board.
- **Headphone level:** set by U2's volume register. Check the maximum into 16 Ω for clipping (TEST_PLAN 8.8) before raising
  the firmware's cap above word 0x35, and listen for hiss at quiet settings with sensitive headphones.
- **U2's charge pump against U101:** U2's charge pump runs at 300–500 kHz and U101 at ≈ 400 kHz, so their difference can land
  in the audio band. If a steady tone shows up on J4 or the speaker with no signal, cut one of JP106–JP108 to move U101's
  frequency (TEST_PLAN 4C.10).
- **AUX input level:** check the level with the Daisy fitted; 2 Vrms should reach ≈ 0.44–0.45 Vpp. R5 can go up to 560 Ω
  (≈ 1.2 dB louder); at 680 Ω a source playing into the unpowered codec passes ±0.3 V.
- **Hot passive pickups:** the Daisy's full scale is reached at ≈ 3.9 Vpp at J1. Play the hottest passive guitar available
  hard and confirm its peaks stay below that.
- **Soldering U2 and U101 by hand** (if not assembled by JLC): both have exposed pads. U2's QFN and U101's pad take hot air;
  U101's can also be soldered from the back through its vias (the back has a mask opening under the pad).
- **Mechanical:** the outline, jack and hole positions have no enclosure drawing yet (a combo cabinet with a 10-inch speaker
  and a large battery pack). Recheck them against it: the front-panel jacks, the battery jack and switch terminal on the rear
  edge, the speaker terminal on the right edge, and the 5 V and display terminals on the left edge. The Seed3's USB-C
  overhangs the rear edge by 1.55 mm. Keep the board off the speaker baffle, and hold the Daisy in its sockets against
  vibration (a strap or standoff).
- **Front panel thickness:** under 3 mm, Neutrik's limit for the NRJ4HF's nut.
- **3D models:** J101 and L101/L102 have none (their footprints don't carry one); the 3D view shows only their pads.

## Layout

### Stackup
4 layers, 1.6 mm, JLC's standard JLC04161H-7628 stackup: 1 oz outer copper, 0.5 oz inner, 0.21 mm prepreg between each outer
layer and its neighbour, a 1.065 mm core between In1 and In2. KiCad's Python can't edit the stackup table, so it was written
into the board file to match; choose the same stackup on JLC's order page. Black solder mask on both sides with white
silkscreen (also set in the stackup); Board Setup's minimum mask web is 0.13 mm, JLC's figure for black mask, and the
narrowest web on the board is 0.20 mm (U101's pins). Page numbers below refer to Eric Bogatin,
*Bogatin's Practical Guide to Prototype Breadboard and PCB Design* (Artech House, 2021).

| Layer | Use |
|---|---|
| F.Cu | Every part; every audio net; the class D's power, output and speaker paths; a GND pour around the routing |
| In1.Cu | Solid GND under the whole board. No tracks |
| In2.Cu | GND fill, with the nets that have to cross the Daisy: the VBAT branch to J106 (around the USB end), `+5V` to U1, R29 and R18, `HP_5V` from beside C21 to U2's VDD caps, `SPK_MUTE`, `AUDIO_OUT_2` from Daisy pin 19 to R11, and under the module `I2C_SCL` (pin 12) and `3V3_D` (pin 38) |
| B.Cu | GND pour; a PVCC pour under the class D; the `+5V_RAW` trunk (around the USB end), `+5V` down the Daisy's left side, `BATT_SENSE`, `AUDIO_IN_2`, `HP_DETECT` and `I2C_SDA` under the Daisy, four lanes (`HP_SD`, `I2C_SDA`, `I2C_SCL`, `3V3_D`) from the Daisy's right row down to U2's pull-ups, the `SPK+` branch to C121 |

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
1. **Zones by placement.** The Daisy stands upright in the middle, USB at the rear edge. Audio is on its left and in front of
   it: the input buffer and J1 at the front-left, the AUX sum and U2 in front of the Daisy, with all three jacks on the front
   edge. The power section is on its right: battery entry along the rear edge, the class D near the right edge.
2. **High-current loops stay local.** Battery current runs J101 → F101 → SW101 → Q101 → R105 → C111/C112 → U101 → L101/L102
   → J102, all along the rear edge and the right side. Its return runs in the planes back to J101's sleeve on the rear edge,
   right of the Daisy. None of it passes under the Daisy or the audio side. Only the VBAT branch to J106 (the DFR0571's input, on In2)
   and the `+5V_RAW` trunk (B.Cu) cross, around the Daisy's USB end.
3. **Switching nodes are short and on F.Cu.** The OUT and bootstrap nodes stay within ≈ 18 mm of U101 (L101 stands above
   the output pins, L102 below them). Under them is In1 GND,
   then In2's GND fill and B.Cu's PVCC pour. No other signal runs through the class D area on any layer.
4. **Distance from the switching nodes:** 60 mm to the guitar input's 1 MΩ node, 41 mm to the AUX input and summing parts,
   52 mm to `AUDIO_IN_1`, 20 mm to U2's input network (see "Open items").
5. **The 5 V tree:** J107 → Q102 → `+5V_RAW`. One branch goes to FB101 → the C5 star in the column left of the Daisy: the
   Daisy VIN branch (F.Cu, around the USB end to pin 39), and the analog branch (B.Cu down the Daisy's left side to R6, then
   In2 along its front end to U1, U2 and R18). The other goes to FB102 → J105 for the display. Display and Daisy current never flows in the analog branch, and
   the display's return stays at the left edge.
6. **The speaker send** leaves Daisy pin 19 on In2 and reaches R11 beside C108/C109, and U101's differential input rejects
   the ground difference between the two ends.
7. **The PVCC pour on B.Cu** joins U101's two PVCC pin pairs, C111, C112, R106 and TP103 around the output stage, so neither pin pair
   depends on a long F.Cu path. In1 separates it from the switching nodes on F.Cu.
8. **Thermal:** U101's exposed pad has nine vias inside it and ten more under the body, into In1, In2 and B.Cu GND. The back has
   a mask opening under the pad, so it can be soldered from the back through the vias.

### Board outline and placement
100 × 78 mm, 2 mm corner radius. The front panel is the bottom edge. Coordinates are from the board's top-left corner (KiCad
(100, 16.5)). Rev 2's input buffer, AUX and U2 blocks and power rev 1's U101 block keep their own routing; the nets
between blocks were routed for this floorplan.

| Part | Position | Why |
|---|---|---|
| A1 (Daisy) | Upright, pin 1 at (32.6, 4), USB on the rear edge | Divides the board: audio pins 16–19 at the front end of the left row, power-side pins (22, 25, 28, VIN 39) on the right row |
| J1, J2, J4 | Front edge: J1 at the left, J2 and J4 in front of the Daisy | All panel jacks on one edge (rev 2's reasons) |
| U1 and the input network | Behind J1, left of the Daisy's front end | `AUDIO_IN_1` reaches pin 16 in about 17 mm on F.Cu |
| R3–R5, C3 | Between J2 and the Daisy's front end | The AUX sum feeds pin 17 from under the module |
| U2 block | Right of the Daisy's front end, above J4 | R10 takes `AUDIO_OUT_1` from pin 18; the left column is full. U2 (rotated 90°) has its inputs up toward the four C0G caps, its outputs down toward J4, the charge-pump caps on its right and SD/SDA/SCL on its left |
| R32–R34 | Left of U2, beside C3 | The I2C pull-ups and SD pull-down, at the vias where the B.Cu lanes from the Daisy arrive |
| J106, J107, J105, J3 | Left edge, top to bottom, wire openings (J106's plug opening) facing out | The DFR0571's input and output, the display's power and UART together, at the 5 V entry |
| FB101, JP101, JP102, C104, C105, C4, C5 | Between the harness block and the Daisy (x 20–31) | The audio 5 V filter and the C5 star sit between `+5V_RAW` and both of their loads |
| SW101, F101, J101 | Rear edge, left to right (x 52–86): switch terminal, fuse, 12 V jack | The battery path runs along the edge to J101, beside the class D; F101's 10 mm pad pitch fits between them |
| Q101, D101, R101 | Under SW101 | Q101's drain on SW101, its source on `VBAT_PROTECTED` toward R105 |
| U101 (TPA3118D2) | (82, 33.5), outputs facing right | Bootstrap caps at the output pins; L101 upright above them and L102 upright below, at the right edge |
| L101, L102 | Upright at x 92, y 2.5–16.7 and 42.2–56.4 | Each on its own output pins' side, so `OUT_P` and `OUT_N` don't cross |
| J102 (speaker) | Right edge between L101 and L102, pins at y 19.4 and 22.9 | `SPK+` from L101 and `SPK−` from L102 run down and up the right edge |
| C121, C122 | Below J102 at x 96 | C122 sits on the `SPK−` track; C121 joins `SPK+` from J102 pin 2 through a short B.Cu branch and one via (it carries only the filter's ripple current) |
| C111, C112 | C111 above U101's PVCC pins, C112 below U101's AVCC parts | Both on the B.Cu PVCC pour; C113/C114 (100 nF) sit at the PVCC pins |
| R17, Q2, C17, R19, R107, R18 | Two columns right of the Daisy | Mute, battery sense and 5 V sense, each beside its Daisy pin (28, 25, 22) |
| C18 | Below R2, its pad under R2's U1 end | RF filter at U1A's + input, 2.5 mm from the pin |
| JP106–JP108 | Back, left of U101 (x 182, y 52–57) | AM2–AM0 drop through vias beside pins 13–15; the 2 mm between those pins and the `AMP_MUTE` track has no room for three jumpers on the front |
| R29, C21 | Above U2's input caps, left of FID2 | `+5V` comes up the via at R18; `HP_5V` drops through a via beside C21 and runs on In2 to C15 (pin 20) and to C12 and pin 12 |
| R114 | Beside R112 and TP109, above U101's input pins | FAULTZ drops to In2 beside it and runs 16 mm west to R30 |
| R30 | Beside JP105, right of Daisy pin 32 | In the `AMP_FAULTZ` In2 line: a via at each end, then In2 to pin 32 |
| D102 | Under R105, above U101's pins 1–2 | Anode on the SDZ track, cathode straight up into R105's PVCC pad |
| D103 | Below C124 and R106 | Anode on the MUTE track to R108, cathode on R106's PVCC track, whose via to the B.Cu PVCC pour moved 1.1 mm down |
| R12, C16, R11, R21 | Column left of C108/C109 | The speaker send's filter and LINE− reference, 6 mm from U101's input caps |
| H1–H4 | (22.3, 41.5), (96.5, 63.5), (90, 74), (4, 4) | The front-left corner is J1's; the rear-right holds L101 |

### Routing
- **Widths:** battery, PVCC, output and speaker paths 1.5 mm (1.0 mm on the output bars between the bootstrap caps), necked to
  0.4 mm at U101's 0.65 mm pitch pins. 5 V nets 1.0 mm (0.6 mm for the display branch and the `+5V` branch to U2 and R18).
  The VBAT branch to J106 is 1.0 mm on In2. Signals 0.25 mm (0.2–0.3 mm in the blocks kept from rev 2 and power rev 1).
- **Around the Daisy's USB end:** the Daisy's pins fill all four layers, and its 0.84 mm gaps pass only a signal track. So
  the three supply crossings go around the rear end, between the end pins and the board edge, one per layer: `+5V` to VIN
  on F.Cu, the VBAT branch on In2, `+5V_RAW` on B.Cu.
- **Under the Daisy:** the module stands about 8 mm off the board on its sockets, so the area between its two pin rows
  carries tracks (no parts). `AUDIO_IN_2` comes up on B.Cu from a via by R5 to pin 17. `AUDIO_IN_1` runs on F.Cu along the
  Daisy's front end and up the outside of the left pin row to pin 16. `AUDIO_OUT_1` leaves pin 18 on F.Cu and exits between
  pins 21 and 22 to R10. `AUDIO_OUT_2` leaves pin 19 on In2 and exits between pins 23 and 24. `HP_DETECT` leaves pin 23 on
  B.Cu and goes out the front end to J4. U2's control lines cross from the left row: `I2C_SDA` (pin 13) on B.Cu and
  `I2C_SCL` (pin 12) on In2, crossing each other, then through the right row's gaps on B.Cu (pins 26/27 and 25/26) to join
  `HP_SD` (pin 27) and `3V3_D` (pin 38, on In2 down the inside of the right row, out between pins 24/25) as four lanes.
- **Display UART:** R8/R9/R24 sit next to J3, C19/C20 on the Daisy side of R8/R9. TX and RX run on F.Cu to the outer side
  of pins 14 and 15; RX passes below H1.
- **The blocks kept whole keep their routing.** The nets that joined blocks were routed by hand; stitching vias that ended
  up under moved parts were removed. The new SMD parts each have a GND via at their ground pad.

### U2 (WQFN-20)
- U2's footprint is KiCad's `WQFN-20-1EP_4x4mm_P0.5mm_EP2.7x2.7mm` (TI RTJ): 0.5 mm pitch with an exposed pad. JLC places it.
- **Ground:** four vias in the exposed pad, and short stubs from GND pins 3, 9, 10, 13 and 19 into the pad.
- **The datasheet's layout advice** (Layout Guidelines): charge-pump caps close to their pins with no vias, VDD decoupled to
  its own GND pin. C15 sits right of pins 19/20, C13 below it at CPP/CPN, C14 below-right at both CPVSS pins (15, 16), and
  C12 below pin 12 behind the `HP_5V` via. The outputs leave the bottom edge on either side of C12; the inputs leave the top
  edge to C10/C11/C22/C23, with one ground via between C22 and C23 for the + inputs.

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

- **`Power` class:** `+5V`, `+5V_RAW`, `+5V_DFR`, `+5V_DISPLAY`, `CAP_BANK_A`, `CAP_BANK_D`.
- **`HighCurrent` class:** `VBAT_PROTECTED`, `AMP_PVCC`, `OUT_P`, `OUT_N`, `SPK+`, `SPK−`, and the battery nets between J101,
  F101, SW101 and Q101. Sized for the 3.15 A fuse on 1 oz outer copper.
- **Thermal reliefs:** every pad joins the GND pours with 0.5 mm spokes and a 0.5 mm gap, for an iron, except U101's, C110's
  and U2's ground pads (see "Decisions"). Vias stay solid.
- **Expected DRC warnings:** 29 `silk_edge_clearance`, all from edge-mounted connectors (J1, J2, J4, J102, J105, J106, J107,
  J3, SW101). Don't trim their footprints. JLC's recommended pass also flags the test points' silk circles (0.14 mm from
  their pads, JLC prefers 0.15 mm), the text under 1.0 mm (71 items: references and legends at 0.8 mm, all with a 0.15 mm
  stroke), and U101's footprint silk over its own pad; all print fine. On KiCad 10.0.8 DRC also reports `lib_footprint_mismatch` for the three fiducials,
  against that version's library; the board is unaffected.

## Parts sourcing
Build plan: a 4-layer JLC board with the SMD parts reflowed (JLC assembly, or a stencil and an oven); the through-hole parts
(jacks, terminals, Daisy sockets, Q101, C5, C111, C112, headers) and F101 (an SMD fuse JLC doesn't stock) are soldered by
hand, from the DigiKey order.
For a hand-soldered build every part comes from DigiKey; for JLC assembly, JLC fits the SMD parts from their `LCSC` numbers.
`seed3-carrier-digikey.csv` is one build's order (DigiKey's BOM upload format, one line per part number) and
`seed3-carrier-digikey-cart.csv` the same in DigiKey's cart format. Both come from the build that was ordered for audio rev 2
and power rev 1 (`amp-digikey-order.csv`, with its stock substitutes and notes), without the four inter-board terminals,
with Q102, C18, FB1, C19/C20, R29, C21, R114, D102/D103, R30, the SMD fuse and J106's JST XH header (with the module cable's
housing and pre-crimped leads) added, U2 a TPA6130A2 (with C22/C23, R32–R34 added, R25–R28 gone and C10/C11 470 nF C0G),
C0G C108/C109, without Q1, R13, R22 and R23, and without rev 1's experiment parts, which that build's spares cover. Check stock before ordering.
- **Passive sizes:** resistors are 0603 (R105 stays 2512 for the amp's supply current). Capacitors are 0603 up to 220 nF
  and 0805 from 680 nF: a ceramic's capacitance falls with DC voltage, more in smaller cases, so the 1–10 µF parts keep the
  0805 body. C7 stays 1210: 47 µF on `VREF` sets the 0.7 Hz filter that keeps `+5V` noise off the guitar input. All use
  KiCad's standard (reflow) footprints; 0603 still reworks with an iron.
- **JLC assembly:** every SMD part carries an `LCSC` field. Semiconductors, the beads, the inductors and the parts with no JLC
  Basic equivalent use the `MPN` itself. The resistors and most capacitors use a JLC **Basic** part (no loading fee) of the same
  value, size, tolerance and dielectric, with an equal or higher voltage rating: UNI-ROYAL 0603WAF resistors; Samsung or YAGEO
  for 100 pF, 100 nF, 220 nF (25 V, as required), 1 µF and 10 µF (25 V X5R). C10/C11, C22/C23 and C108/C109 are Murata
  GRM31C5C1E474JE01L on both orders (JLC C6049896, 546 in stock on 2026-11-08: six per board). D1–D5 are C19224, Nexperia's PESD5V0S1BA in SOD-323: the same diode as the DigiKey
  order's SOD-323F PESD5V0S1BAF. D102/D103 are onsemi NSVBAT54HT1G on both orders (JLC C179609, 63,040 in stock on 2026-11-09).
  18 Extended parts carry JLC's loading fee: C2, C3/C9, C16, C108/C109, C121/C122, C7, R105,
  FB1, FB101/FB102, D1–D5, D101, D102/D103, L101/L102, Q2, U1, U2, U101 and U103. U103 had the lowest JLC stock (10 on 2026-11-07); U2, the
  TPA6130A2RTJR, is C130046 (3,842 on 2026-11-09).
- **Assembly files:** `jlc-assembly.kicad_jobset` writes `fab/assembly/seed3-carrier_bom.csv` and `_cpl-all-pos.csv` (SMD
  parts only); `jlc_asm.py cpl` turns the latter into `_cpl.csv` with `jlc-rotations.csv` (empty until JLC's placement preview
  shows a part rotated). All placed parts are on the top side, so JLC's Economic assembly applies. Check every polarised part
  (U1, U2, U101, U103, Q2, Q102, D1–D5, D101, D102, D103) in JLC's preview before paying. The BOM's rows without a part number are the
  hand-soldered parts, the test-point pads and the off-board DFR0571 (U102): leave them unselected.
- **Edge clearance for assembly:** JLC wants placed part bodies 2.5 mm from the edge. Every placed part's courtyard clears
  it (L101's top edge is exactly 2.5 mm from the rear edge); F101, at the rear edge, is hand-soldered.
- **Sheet 1's parts** carry `MPN`, `Manufacturer`, `DigiKey` and `Datasheet` fields. Sheet 2's carry `MPN` and `Manufacturer`
  matching `power-board/DigiKey_Import.csv` (substitutes included), except the resized passives, which carry the 0603/0805
  part and its `DigiKey` and `Datasheet` fields too.
- **U2:** TPA6130A2RTJR (RTJ is the 4 × 4 mm WQFN; the YZH is a 2 × 2 mm ball-grid package that doesn't fit this footprint).
  The I2C address is fixed at 0x60.
- **C0G for the filter caps** C1, C18, C9, C16, C3, C19 and C20, and for the caps in the signal path: C2, C10/C11, C22/C23 and
  C108/C109.
- **Daisy sockets:** two 1×20 2.54 mm female headers (S7018-ND).
- **J106's mate (the DFR0571's input cable):** a JST XHP-2 housing (455-2266-ND) and one ASXHSXH22K305 lead (455-3241-ND,
  12 in of 22 AWG with an XH contact at each end). Cut the lead in half for the two wires; VIN+ goes in housing position 1
  (J106's triangle, BAT+). Mark the VIN+ wire: the lead is black.
- **The DFR0571** is in the order as an off-board part (U102 on sheet 2, no footprint).
- **The S1B panel switch** is obsolete at NKK (DigiKey still stocks it); pick another for later builds.
- **TP1 and TP101–TP109** are bare copper pads, not parts.
