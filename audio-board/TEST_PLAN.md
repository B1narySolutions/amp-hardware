# Seed3 Carrier — Post-Assembly Test Plan

Bring-up and acceptance tests for one hand-assembled **rev 2** board built from the rev 2 schematic
(`rev2/seed3-carrier.kicad_sch`), its fabrication package and its BOM. Record the package name in the log.
`rev2/CHANGES.md` lists what changed from rev 1 and why.

Work through the stages in order. Each stage assumes the one before it passed,
so a failure stays localized: unpowered checks first, then the board powered
**without** the Daisy, and only then with the Daisy fitted. Record results in
the log at the end (one copy per board serial).

## Circuit summary (what is being tested)

| Block | Parts | Function |
|---|---|---|
| Power input | J3 (8-pin JST-XH), Q1 (AO3401A) | `5V_IN` on J3.1/J3.2, GND on J3.3/J3.4; P-FET reverse-polarity protection onto `+5V`, probe at **TP9** (`TP_5V`) |
| 5 V decoupling | C8, C9, C17, C18, C33 | Bulk/HF decoupling on `+5V` (C33 at U2 VDD) |
| Power board signals | R32/C28, R35/R36/C29, R33/R34, Q4/R37 | J3.5 `BATT_SENSE_CONN` → Daisy pin 25; J3.6 `PWR_BTN_CONN` → pin 26 (active low, 10k pull-up to 3V3_D); pin 27 `PWR_HOLD` → J3.7 (100k pull-down); pin 28 `SPK_EN` → Q4 → J3.8 `SPK_MUTE` (open drain, low = speaker on) |
| Display supply | FB1, C30 | Ferrite + 47 µF filter from `+5V` to `DISPLAY_5V` (J4.4) |
| Mid-rail reference | R7, R8 (10k/10k), C7 | `VREF` ≈ 2.5 V, probe at **TP5** (`TP_VREF`) |
| Guitar input | J1, C1, C3, R17 (1M), R1, R5, U1A | ¼" input, tip shorted to GND when unplugged; 1 MΩ load; unity-gain buffer → Daisy `AUDIO_IN_1` |
| AUX input | J9, R40/R41, R38, C31, C32, R39, R42, U1D | 3.5 mm TRS, passive stereo-to-mono sum, ~32 kHz RF filter, biased to VREF; unity-gain buffer → Daisy `AUDIO_IN_2` |
| Headphone buffer | R2, C2, C5, R6, U1B | Daisy `AUDIO_OUT_1` → ~48 kHz RC low-pass → AC-couple → buffer → `HP_SOURCE` |
| Headphone amp | U2 (TPA6132A2), C12/C13, C33–C36 | DirectPath stereo amp, 0 dB inverting (mono source on both channels), outputs at 0 V straight to J5 (`HP_L` tip, `HP_R` ring). EN = `HP_EN` (Daisy pin 33), R26 pull-down, probe at **TP10** (`TP_HP_EN`) |
| Headphone detect | J5.5/J5.6, R30, R31, C27 | Normally-open switch closes to GND on plug insertion → `HP_DETECT` (Daisy pin 34, 10k pull-up to 3V3_D). **Low = headphones in.** Switch side at **TP11** (`TP_HP_DET`) |
| Speaker / line send | R28, C24, C25, R29, U1C, C26, R3, R4 | Daisy `AUDIO_OUT_2` → ~48 kHz low-pass → AC-couple → buffer → C26 → `LINE_SEND` → R3 → `LINE_OUT` on J2 (¼" external) and J8 (internal, to the speaker amp) |
| Display | J4, R43, R44 | GND / `UART_TX_CONN` / `UART_RX_CONN` / `DISPLAY_5V`; 1k series resistors to Daisy USART1 |
| Breakout | J6, J7 | Female sockets mirroring the Daisy pins (see pinouts below) |
| Daisy | A1 + two 1×20 sockets | Plug-in module. Mute while absent, booting or reset comes from R26 (`HP_EN` low) and R37 (`SPK_EN` low); the firmware feeds the STM32 IWDG only from the audio callback |

**Pinouts used below**

- U1 TLV9064 (SOIC-14): 1 OUTA, 2 INA−, 3 INA+, 4 V+, 5 INB+, 6 INB−, 7 OUTB, 8 OUTC, 9 INC−, 10 INC+, 11 V−, 12 IND+, 13 IND−, 14 OUTD
- U2 TPA6132A2 (WQFN-16): 1 INL−, 2 INL+, 3 INR+, 4 INR−, 5 OUTR, 6 G0, 7 G1, 8 HPVSS, 9 CPN, 10 PGND, 11 CPP, 12 HPVDD, 13 EN, 14 VDD, 15 SGND, 16 OUTL, EP GND.
  INL+/INR+, G1, PGND, SGND and EP to GND; G0 and VDD to `+5V`
- Q1 AO3401A, Q4 2N7002 (SOT-23): 1 G, 2 S, 3 D
- J3: 1–2 `5V_IN`, 3–4 GND, 5 `BATT_SENSE_CONN`, 6 `PWR_BTN_CONN`, 7 `PWR_HOLD_CONN`, 8 `SPK_MUTE`
- J5 / J9 (SJ3-35063AG): 1 sleeve, 2 ring, 3 tip, 5 detect common, 6 detect NO (J9's 5/6 not connected)
- J6: 1 GND, 2 `AUDIO_OUT_2`, 3 `AUDIO_OUT_1`, 4 `AUDIO_IN_2`, 5 `AUDIO_IN_1`, 6 USART1 RX, 7 USART1 TX, 10–13 D10–D7
- J7: 1 `3V3_A`, 5 `BATT_SENSE`, 6 `PWR_BTN`, 7 `PWR_HOLD`, 8 `SPK_EN`, 13 `HP_EN`, 14 `HP_DETECT`, 18 `3V3_D`, 19 `+5V`, 20 GND

## Equipment

- Current-limited bench supply (0–6 V), DMM, oscilloscope (≥ 20 MHz)
- Signal generator or audio interface (sine 20 Hz – 20 kHz, ≥ 2 Vpp); a phone/laptop
  headphone output works for listening tests
- ¼" mono cable, 3.5 mm stereo (TRS) cable, 3.5 mm mono (TS) plug, headphones (≈ 32 Ω), a 32 Ω dummy load (one per channel)
- 8-pin JST-XH pigtail with flying leads for J3, 2-pin JST-XH pigtail for J8
- 10k resistors and clip leads: one to pull `HP_EN` up while the Daisy is out, one to pull `SPK_MUTE` (J3.8) up to 3.3 V
- USB cable for the Daisy, USB-serial adapter (3.3 V) for J4
- Magnifier/microscope, flux, isopropyl alcohol; hot air for U2 rework

## Stage 0 — Visual and mechanical inspection (unpowered, no Daisy)

| # | Check | Pass criteria |
|---|---|---|
| 0.1 | Clean flux residue; inspect every joint under magnification | No bridges (esp. U1 SOIC-14 pins, U2 QFN pins, Q1, Q4), no cold/dull joints, no solder balls |
| 0.2 | IC orientation | U1 and U2 pin-1 marks match silkscreen; U1 = TLV9064, U2 = TPA6132A2 |
| 0.3 | U2 (WQFN-16) | Even fillets on all 16 side pads; part flat, not tilted or floating on the exposed pad; exposed pad soldered (solder visible in the thermal vias from the bottom) |
| 0.4 | Q1 and Q4 | Both SOT-23: confirm markings match AO3401A (Q1) and 2N7002 (Q4) — not swapped; seated on correct pads |
| 0.5 | Electrolytic polarity | C18 `+` to `+5V` |
| 0.6 | Passive values vs BOM | Spot-check R17/R6/R29 (1M), R5 (10M), R7/R8/R30/R32/R36/R40/R41 (10k), R26/R34/R37/R39 (100k), R38 (47k); C7/C12/C13/C30 are the 1210 parts, C33–C36 the 0805 parts; FB1 is the 1206 bead, not a resistor |
| 0.7 | J3, J8 (JST-XH) | Seated flat; key orientation matches the power-board cable |
| 0.8 | Daisy sockets | Both A1 1×20 sockets flush and parallel; Daisy inserts with moderate force, all pins engaged, USB connector on the correct end |
| 0.9 | J6/J7 sockets, J4 header | Flush, straight, correct side of board |
| 0.10 | Jacks J1, J2, J5, J9 | Fully seated, flush to board edge, plugs insert/eject cleanly. J5/J9 noses overhang the edge as drawn; note any footprint mismatch (J5/J9 footprint was hand-drawn) |
| 0.11 | Enclosure fit (if available) | Jacks, USB and J3/J4/J8 cables line up with panel holes and cable routes |

## Stage 1 — Unpowered resistance checks (no Daisy)

Measure with the DMM; let capacitors charge before reading. Probe on IC pins,
test pads or J6/J7 sockets, not on connector shells.

| # | Measure | Expect | Fail indicates |
|---|---|---|---|
| 1.1 | `+5V` (TP9) → GND | Rises to > 1 kΩ (caps charging), not < 50 Ω | Short on 5 V rail — check C8/C9/C17/C18/C33, U1.4, U2.14, U2.6 |
| 1.2 | J3.1 → GND | High; diode mode shows Q1's body diode into the `+5V` rail, not a short | Q1 shorted or bridged |
| 1.3 | J3.1 ↔ J3.2, J3.3/J3.4 → GND | ≈ 0 Ω | J3 joint open |
| 1.4 | `VREF` (TP5) → GND | ≈ 5 kΩ (R7 in parallel with R8 via 5 V loads) | R7/R8 wrong or open, C7 shorted |
| 1.5 | `DISPLAY_5V` (J4.4) → TP9 | < 1 Ω (FB1) | FB1 open or missing |
| 1.6 | TP10 (`HP_EN`) → GND | ≈ 100 kΩ (R26) | R26 missing; < 1 kΩ = U2.13 bridged to GND/neighbour |
| 1.7 | TP10 → TP9, TP10 → J5 tip | High (no short) | U2.13 (EN) bridged to U2.14 (VDD) or U2.12 |
| 1.8 | U2 pin bridges: J5 tip → GND, J5 ring → GND, J5 ring → TP9 | High (no short), not < 100 Ω | QFN bridge: OUTL (16)/SGND (15), OUTR (5)/G0 (6) or INR− (4) |
| 1.9 | J1 tip → GND, no plug | ≈ 0 Ω (tip-normal shorts to GND) | J1 switch / footprint issue |
| 1.10 | J1 tip → GND, plug inserted (other end open) | ≈ 1 MΩ (R17 via VREF) once C3 charges; not ≈ 0 Ω | Plug not lifting the switch |
| 1.11 | J9 tip → ring | ≈ 20 kΩ (R40 + R41) | R40/R41 open |
| 1.12 | J9 tip → GND | ≈ 57 kΩ (R40 + R38) | R38 missing or C31 shorted |
| 1.13 | TP11 (`HP_DETECT_SW`) → GND, no plug in J5 | Open | J5 detect switch closed or bridged |
| 1.14 | TP11 → GND, plug in J5 | ≈ 0 Ω | J5 detect switch not closing (check pins 5/6 mapping) |
| 1.15 | TP11 → J7.14 (`HP_DETECT`); J7.14 → J7.18 (`3V3_D`) | ≈ 1 kΩ (R31); ≈ 10 kΩ (R30) | R30/R31 wrong or open |
| 1.16 | J2 tip → GND; J2 tip ↔ J8.1; J8.2 → GND | ≈ 100 kΩ (R4); ≈ 0 Ω; ≈ 0 Ω | R4 missing; J8 joints |
| 1.17 | J2 tip → C26 (`LINE_SEND` side) | ≈ 100 Ω (R3) | R3 open |
| 1.18 | J3.5 → J7.5; J3.6 → J7.6; J7.6 → J7.18 | ≈ 10 kΩ (R32); ≈ 1 kΩ (R35); ≈ 10 kΩ (R36) | Power-board signal resistors |
| 1.19 | J3.7 → J7.7; J3.7 → GND | ≈ 1 kΩ (R33); ≈ 100 kΩ (R34) | `PWR_HOLD` network |
| 1.20 | J7.8 (`SPK_EN`) → GND; J3.8 → GND | ≈ 100 kΩ (R37); open (Q4 off) | R37 missing; Q4 shorted or swapped with Q1 |
| 1.21 | J4.2 → J6.7; J4.3 → J6.6 | ≈ 1 kΩ each (R43, R44) | UART series resistors |
| 1.22 | J6/J7 adjacent pins | Spot-check no shorts between neighbouring pins, esp. J7.19 (+5V) ↔ J7.18 (3V3_D) and J7.20 (GND) | Socket bridge — **5 V into 3V3_D would damage the Daisy** |

## Stage 2 — First power-up, Daisy **removed**

Supply on J3 (+ to J3.1/J3.2, − to J3.3/J3.4): start at 0 V, current limit **50 mA**, ramp to 5.0 V.
With the Daisy out, R26 holds `HP_EN` low, so U2 starts in shutdown.

| # | Check | Expect |
|---|---|---|
| 2.1 | Supply current at 5.0 V | A few mA (TLV9064 quiescent + 0.25 mA divider; U2 off); < 10 mA. Stop if it hits the limit |
| 2.2 | `+5V` at TP9 | 4.9–5.0 V (Q1 drop is tens of mV) |
| 2.3 | `VREF` at TP5 | 2.45–2.55 V |
| 2.4 | U1.1, U1.7, U1.8, U1.14 (all four outputs) | ≈ 2.5 V (all buffers sit at VREF) |
| 2.5 | U1.3, U1.5, U1.10, U1.12 | ≈ 2.5 V |
| 2.6 | TP10 (`HP_EN`) | 0 V (R26) |
| 2.7 | J5 tip and ring (DC), U2 off | ≈ 0 V |
| 2.8 | J2 tip / J8.1 (DC) | ≈ 0 V (blocked by C26) |
| 2.9 | J4.4 (`DISPLAY_5V`) and J7.19 | +5 V; J4.1 and J7.20 are GND |
| 2.10 | J7.1 (`3V3_A`), J7.18 (`3V3_D`) | ≈ 0 V (nothing on the carrier back-feeds the Daisy rails) |
| 2.11 | J3.8 (`SPK_MUTE`) with 10k pull-up to 3.3 V | ≈ 3.3 V (Q4 off = speaker muted while the Daisy is absent) |
| 2.12 | Enable U2: 10k from TP10 to TP9 | Current rises by a few mA (U2 quiescent + charge pump); TP10 ≈ 4.5 V |
| 2.13 | U2 charge pump, enabled | HPVDD (C34) positive and HPVSS (C36) roughly equal and negative; record both. ≈ 0 V on either = charge-pump fault (C35, pins 8/9/11) |
| 2.14 | J5 tip and ring (DC), U2 enabled | Within ±5 mV of 0 V (DirectPath, no output caps) |
| 2.15 | Thermal | Nothing warm to the touch after 2 min, U2 included |
| 2.16 | **Reverse polarity** — swap leads on J3, limit 50 mA, apply 5 V | ≈ 0 mA drawn, `+5V` stays at 0 V. Restore correct polarity and repeat 2.2 to confirm nothing was damaged |

## Stage 3 — Analog paths, Daisy **removed**

The J6 breakout reaches the Daisy-side nets with the module out, so the analog
stages can be tested on their own. Supply 5.0 V, limit 50 mA. Keep the 10k from
TP10 to TP9 for 3B (U2 enabled).

**3A. Guitar input buffer (J1 → AUDIO_IN_1)**

1. Inject 1 kHz, 1 Vpp sine into J1 (tip/sleeve). Scope on `J6.5` (AUDIO_IN_1) or U1.1.
2. | # | Check | Expect |
   |---|---|---|
   | 3A.1 | Output level | 1 kHz sine riding on ≈ 2.5 V DC, amplitude ≈ input (unity gain, no level pot) |
   | 3A.2 | Input load: add 1 MΩ in series with the generator | Output drops to ≈ half (≈ 1 MΩ input impedance, R17) |
   | 3A.3 | Unplug J1 | Output goes quiet (tip shorted to GND) |
   | 3A.4 | Raise amplitude until clipping | Clips symmetrically near the rails (≈ 4.8 Vpp); record the input level |
   | 3A.5 | Sweep 20 Hz – 20 kHz | Flat within about ±1 dB |

**3B. Headphone buffer + headphone amp (AUDIO_OUT_1 → J5)**

1. Inject 1 kHz, 1 Vpp sine into `J6.3` (AUDIO_OUT_1), ground at `J6.1`.
   Load J5 tip and ring with 32 Ω each (or headphones at low level).
2. | # | Check | Expect |
   |---|---|---|
   | 3B.1 | U1.7 (`HP_SOURCE`) | ≈ 1 Vpp on 2.5 V DC |
   | 3B.2 | J5 tip and ring | ≈ 1 Vpp centred on 0 V, inverted relative to U1.7 (0 dB, G0 high / G1 low); both channels equal within ~0.5 dB |
   | 3B.3 | Remove the TP10 pull-up | Both outputs go silent within a few ms (U2 shutdown); refit it |
   | 3B.4 | Frequency sweep 20 Hz – 20 kHz into 32 Ω | Flat in the audio band; low-end corner ≈ 1.7 Hz (C12/C13 into U2's 19.8 kΩ input); falls off above ≈ 48 kHz (R2/C2) |
   | 3B.5 | Listening test with headphones | Clean tone, no hum/hiss above expected level, no oscillation (check scope for HF ringing on the outputs and on HPVSS) |
   | 3B.6 | Power-on/off with headphones in | Note any pop level (U2 has built-in pop suppression; Stage 7 is the full test) |

**3C. Speaker / line send (AUDIO_OUT_2 → J2 / J8)**

1. Inject 1 kHz, 1 Vpp sine into `J6.2` (AUDIO_OUT_2), ground at `J6.1`.
2. | # | Check | Expect |
   |---|---|---|
   | 3C.1 | U1.8 (OUTC) | ≈ 1 Vpp on 2.5 V DC |
   | 3C.2 | J2 tip and J8.1 | ≈ 1 Vpp centred on 0 V, same phase as the input, identical on both |
   | 3C.3 | Frequency sweep 20 Hz – 20 kHz | Flat in the audio band; falls off above ≈ 48 kHz (R28/C24) |
   | 3C.4 | Insert and remove a plug in J5 | J2/J8 unchanged (rev 2 has no tip-switch; speaker muting is in firmware) |

**3D. AUX input (J9 → AUDIO_IN_2)**

1. Inject 1 kHz, 1 Vpp sine into J9 with a TRS cable, same signal on tip and ring. Scope on `J6.4` (AUDIO_IN_2) or U1.14.
2. | # | Check | Expect |
   |---|---|---|
   | 3D.1 | Tip and ring driven together | ≈ 0.9 Vpp on 2.5 V DC (R40‖R41 into R38) |
   | 3D.2 | Tip only, ring grounded (TS plug) | ≈ 0.45 Vpp (−6 dB mono sum) |
   | 3D.3 | Unplug J9 | Output goes quiet (R38 holds the summing node at GND) |
   | 3D.4 | Sweep 20 Hz – 20 kHz (tip and ring driven) | Flat to ≈ 10 kHz, ≈ −1.5 dB at 20 kHz (C31, ~32 kHz pole) |
   | 3D.5 | Raise amplitude until clipping (tip and ring driven) | Clips near the rails; record the input level. Compare with a laptop at full volume (up to 2 Vrms ≈ 5.7 Vpp) |

Remove the injected signal and the TP10 pull-up before going on.

## Stage 4 — Power-up with Daisy fitted

1. **Power off.** Insert the Daisy, checking orientation against the silkscreen
   and that no pins are offset by one position.
2. Supply 5.0 V on J3 with the limit set to **300 mA**. Keep USB **unplugged** for this stage.
   Keep the 10k pull-up from J3.8 to 3.3 V.

| # | Check | Expect |
|---|---|---|
| 4.1 | Supply current | Within the Daisy's normal draw (roughly 100–200 mA depending on firmware); record value |
| 4.2 | `+5V` (TP9) | ≥ 4.85 V under load |
| 4.3 | `3V3_A` (J7.1) and `3V3_D` (J7.18) | 3.3 V ± 5 % (from the Daisy regulators) |
| 4.4 | `VREF`, U1 biases | Same as Stage 2 |
| 4.5 | `HP_DETECT` (J7.14) | ≈ 3.3 V with no plug in J5; ≈ 0 V with a plug in |
| 4.6 | Hold the Daisy in reset (RESET button held) | TP10 (`HP_EN`) 0 V, J7.8 (`SPK_EN`) 0 V, J3.8 ≈ 3.3 V (muted), J3.7 (`PWR_HOLD_CONN`) 0 V |
| 4.7 | Daisy LED / existing firmware | Boots normally |
| 4.8 | Thermal after 5 min | Nothing hot; Q1 and U2 at most warm |
| 4.9 | Back-power: J3 supply **off**, 3.3 V on J3.5 (`BATT_SENSE_CONN`) | ≤ 0.3 mA drawn (R32); record `3V3_D`. More means the Daisy is being back-powered |

Then plug in USB with J3 still powered and confirm current/voltages don't jump
unexpectedly. Check the Daisy Seed docs for your revision's VIN/USB power-path
before relying on both sources together.

## Stage 5 — Functional tests with test firmware

Flash a small bring-up program (libDaisy or Arduino/DaisyDuino) over USB that:

- passes audio input 1 to outputs 1 and 2, mixes input 2 (AUX) into both, and logs peak levels,
- drives `PWR_HOLD` high at boot and `HP_EN` high after the first audio callback,
- lets `SPK_EN` and `HP_EN` be toggled from USB serial,
- prints `HP_DETECT`, `PWR_BTN` and the `BATT_SENSE` ADC reading over USB serial,
- echoes bytes on USART1 (J4) and sends a heartbeat string every second.

Keep the 10k pull-up from J3.8 to 3.3 V unless the power board is connected.

| # | Check | Expect |
|---|---|---|
| 5.1 | USB enumeration / DFU flashing | Flashes and enumerates; confirms the USB D+/D− sockets connect |
| 5.2 | Audio passthrough: 1 kHz into J1 → J5 headphones | Clean tone on both channels |
| 5.3 | Passthrough: J1 → J2 and J8 | Signal present on both (output 2) |
| 5.4 | Noise floor: J1 unplugged, firmware gain max | Only low-level hiss; no hum, whine, or digital noise from USB/codec; record level on the scope at J5 and J2 |
| 5.5 | Guitar test | Real guitar into J1, headphones on J5: clean signal, no clipping at normal pick strength; record the peak level the firmware logs |
| 5.6 | AUX: phone/laptop into J9 at full volume | Heard on J5 and J2; record the logged peak and whether input 2 clips |
| 5.7 | `HP_DETECT` | Prints high with J5 empty, low with a plug in; TP11 ≈ 0 V with a plug in. No chatter after debounce |
| 5.8 | `HP_EN` toggled low/high | TP10 follows; J5 silent while low |
| 5.9 | `SPK_EN` toggled high/low | J7.8 follows; J3.8 < 0.1 V while high (Q4 on, speaker playing), ≈ 3.3 V while low. Record the low level (Q4 gate drive from 3.3 V) |
| 5.10 | `PWR_BTN`: short J3.6 to GND, release | Prints low while shorted, high released (R36) |
| 5.11 | `PWR_HOLD` | J3.7 ≈ 3.3 V after boot |
| 5.12 | `BATT_SENSE`: known voltage (e.g. 1.65 V) on J3.5 | ADC reading matches within a few % |
| 5.13 | UART on J4 with a 3.3 V USB-serial adapter (adapter TX → J4.3, RX → J4.2, GND → J4.1) | Heartbeat received; echo works. **Before connecting the real display**, confirm its TX idles at ≤ 3.3 V |
| 5.14 | Display on J4 | Powers from J4.4 (`DISPLAY_5V`), shows data from the Daisy. Scope TP9 with Wi-Fi/backlight active: ripple much lower than at J4.4 (FB1/C30) |
| 5.15 | Breakout spot-check | Toggle Daisy GPIOs D7–D10 in firmware and confirm they appear on J6.13–J6.10 |

## Stage 6 — Soak and robustness

| # | Check | Expect |
|---|---|---|
| 6.1 | Run passthrough with audio for 30 min | No dropouts, resets, or drift in VREF / supply current |
| 6.2 | Plug/unplug J1, J2, J5, J9 repeatedly while running | No resets, no lasting noise, jacks stay mechanically solid; `HP_DETECT` reports every J5 change |
| 6.3 | Wiggle the J3, J4 and J8 cables while running | No crackle, dropouts or resets |
| 6.4 | Full-level 1 kHz into 32 Ω on J5 for 10 min | U2 at most warm; no shutdown or distortion change |
| 6.5 | Light flex/tap test on the board and Daisy | No crackle or resets (would point to a cracked joint or loose socket pin) |

## Stage 7 — Pops, hiss and mute (rev 2)

Rev 2 only. Needs the product firmware (volume ramps, headphone detect, `PWR_HOLD` shutdown, `SPK_EN` delay) and an
audio interface on the laptop. Record J5 (into a 32 Ω load or EarPods) and J2 into the interface, and look at each
recording for spikes. Pass means no audible click and no spike more than ~10 dB above the recording's noise floor.
On the bench, pull J3.8 (`SPK_MUTE`) up to 3.3 V with 10k so it can be probed without the power board.

| # | Check | Expect |
|---|---|---|
| 7.1 | Power-on pop: record J5 and J2, then power the board | No click on either output. Headphones come on only after audio starts (`HP_EN`, TP10, goes high after boot) |
| 7.2 | Speaker enable delay: scope `+5V` (TP_5V) and `SPK_EN` (J7.8) at power-on | `SPK_EN` goes high ≥ 0.5 s after `+5V`, so C26 and the speaker amp's caps settle first |
| 7.3 | Power-off pop: record J5 and J2, press the power button for a clean shutdown | Audio fades out, then silence. No click when `PWR_HOLD` drops |
| 7.4 | Hard power cut: record J5 and J2, unplug J3 while playing | Note the result. A small click is acceptable here, a loud bang is not |
| 7.5 | Headphone plug-in and removal while playing a 1 kHz tone | J2 ramps down when a plug goes into J5 and back up when it's removed. No click on either output. `SPK_EN` follows |
| 7.6 | Watchdog mute: debug build that stops the audio callback on a USB serial command | TP10 (`HP_EN`) and `SPK_MUTE` both go to the muted state within ~10–20 ms. The Daisy resets and boots back into silence |
| 7.7 | Hiss with EarPods: J1 unplugged, firmware volume at a quiet listening level, then at max | No hiss audible at a normal listening level. If it is, tie U2 G0 to GND (−6 dB) and repeat 7.7 and 7.8 |
| 7.8 | Maximum level: full-scale 1 kHz into a 32 Ω load on J5 | ≈ 1.1 Vrms per channel without clipping (record the clip point). Listening check with ATH-M40x-class headphones: loud enough with margin |

## Fault-finding hints

| Symptom | Look at first |
|---|---|
| Supply hits current limit at power-up | Stage 1.1 short; reversed C18; U1/U2 rotated; U2 pins bridged |
| No `+5V` with correct polarity | Q1 orientation/footprint; Q1 and Q4 swapped; J3 pin order / cable |
| `VREF` not ≈ 2.5 V | R7/R8 values, C7 leakage/short |
| Input works only intermittently | J1 tip-normal switch, C3/R1 joints |
| No headphone output | TP10 (`HP_EN`) level; R26 value; U2.14 supply; U2 side pads and exposed pad joints |
| HPVDD/HPVSS ≈ 0 V with EN high | C35 (flying cap), C34/C36, U2 pins 8/9/11/12 |
| DC or hum on J5 outputs | U2 SGND (pin 15) / exposed pad to GND; INL+/INR+ (pins 2/3) grounded |
| Output only on one HP channel | That channel's C12/C13, U2 pin 1/4 (input) or 16/5 (output) joints, J5 tip/ring pins |
| Speaker output (J2/J8) dead | U1C (pins 8–10), C25/R29, C26, R3; `AUDIO_OUT_2` from firmware |
| AUX input dead or quiet | J9 pins, R40/R41, C32, R42, U1D (pins 12–14) |
| `HP_DETECT` stuck or inverted | J5 pins 5/6 mapping, R30/R31, TP11, C27 |
| Speaker amp never unmutes / never mutes | Q4 orientation or swapped with Q1; R37; `SPK_MUTE` polarity on the power board |
| Daisy won't boot | Socket orientation / offset; 3V3 pins shorted at J7.18/J7.19 |
| Daisy partly alive with J3 off | Back-powering through J3.5–J3.7: check R32/R35/R33 values and the power board's divider |

## Results log

Board serial / ID: __________  Assembled by: __________  Date: __________

Fab package: __________  Tested by: __________  Firmware commit: __________

| Stage | Result (Pass/Fail) | Measured values / notes |
|---|---|---|
| 0 Visual & mechanical | | |
| 1 Unpowered resistance | | |
| 2 Power-up, no Daisy | | I = ____ mA (U2 on: ____ mA), +5V = ____ V, VREF = ____ V, HPVDD = ____ V, HPVSS = ____ V |
| 2.16 Reverse polarity | | |
| 3A Guitar input buffer | | Clip level = ____ Vpp |
| 3B Headphone buffer / amp | | L = ____ Vpp, R = ____ Vpp into 32 Ω, DC offset L/R = ____ / ____ mV |
| 3C Speaker / line send | | J2 = ____ Vpp |
| 3D AUX input | | Tip+ring = ____ Vpp, clip level = ____ Vpp |
| 4 Power-up with Daisy | | I = ____ mA, 3V3_A = ____ V, 3V3_D = ____ V, back-power I = ____ mA |
| 5 Firmware functional | | SPK_MUTE low = ____ V, AUX peak = ____ |
| 6 Soak & robustness | | |
| 7 Pops, hiss and mute | | SPK_EN delay = ____ s, mute time = ____ ms, HP max = ____ Vrms |

Rework performed:

Open issues:
