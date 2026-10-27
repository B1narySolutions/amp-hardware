# Seed3 Carrier — Post-Assembly Test Plan

Bring-up and acceptance tests for one hand-assembled **rev 2** board built from the rev 2 schematic
(`rev2/seed3-carrier.kicad_sch`), its fabrication package and its BOM. Record the package name in the log.
`rev2/DESIGN.md` describes the design and the reasons for it, and `rev2/CHANGES.md` lists what changed from rev 1.

Work through the stages in order. Each stage assumes the one before it passed,
so a failure stays localized: unpowered checks first, then the board powered
**without** the Daisy, and only then with the Daisy fitted. Record results in
the log at the end (one copy per board serial).

## Circuit summary (what is being tested)

| Block | Parts | Function |
|---|---|---|
| Power input | J6 (8-pin JST-XH), Q1 (AO3401A) | `5V_IN` on J6.1/J6.2, GND on J6.3/J6.4; P-FET reverse-polarity protection onto `+5V`, probe at C5 `+` |
| 5 V decoupling | C6, C4, C5, C12 | Bulk/HF decoupling on `+5V` (C12 at U2 VDD) |
| Power board signals | R13/C17, R16/C18, R14/R15, Q2/R17 | J6.5 `BATT_SENSE_CONN` → Daisy pin 25; J6.6 `PWR_BTN_CONN` → pin 26 (active low, STM32 internal pull-up); pin 27 `PWR_HOLD` → J6.7 (100k pull-down); pin 28 `SPK_EN` → Q2 → J6.8 `SPK_MUTE` (open drain, low = speaker on) |
| Display supply | FB1, C8 | Ferrite + 47 µF filter from `+5V` to `DISPLAY_5V` (J3.4) |
| Mid-rail reference | R7, R6 (10k/10k), C7 | `VREF` ≈ 2.5 V, probe at C7 |
| Guitar input | J1, C1, C2, R1 (1M), R2, U1A, R20 | ¼" input, tip shorted to GND when unplugged; 1 MΩ load; unity-gain buffer → R20 (470 Ω series) → Daisy `AUDIO_IN_1`. U1 is clean to ≈ 4.8 Vpp; the Daisy's full scale is 3.6 Vpp |
| AUX input | J2, R3/R4, R5, C3 | 3.5 mm TRS, passive stereo-to-mono sum, ~110 kHz RF filter, straight into Daisy `AUDIO_IN_2` (no buffer). R5 (3.3k) sets the level: ≈ −11 dB with the same signal on both channels and the Daisy's ≈ 5k input, never more than −8 dB |
| Headphone filter | R10, C9 | Daisy `AUDIO_OUT_1` (expected to be AC-coupled on the module; 5.16 checks) → ~60 kHz RC low-pass → `HP_SOURCE`, driving U2 directly |
| Headphone amp | U2 (TPA6132A2), C10/C11, C12–C15 | DirectPath stereo amp, −6 dB inverting (mono source on both channels), outputs at 0 V straight to J4 (`HP_L` tip, `HP_R` ring). EN tied to `+5V`: U2 is on whenever `+5V` is up |
| Headphone detect | J4.5/J4.6, TP1 | Normally-open switch closes to GND on plug insertion → `HP_DETECT` (Daisy pin 34, wired directly; STM32 internal pull-up, enabled by the firmware). **Low = headphones in.** Probe at **TP1** (`TP_HP_DET`) |
| Jack ESD | D1–D5 (PESD5V0S1BA) | Bidirectional ESD diode from each jack signal contact to GND: J1 tip, J2 tip/ring, J4 tip/ring |
| Speaker send | R11, C16, R12 | Daisy `AUDIO_OUT_2` → ~48 kHz low-pass (R11/C16, no buffer) → `LINE_OUT` on J5 (internal, to the speaker amp) |
| `+5V` sense | R18, R19 (100k/100k) | `+5V` divided to ≈ 2.5 V → `5V_SENSE` (Daisy pin 22, ADC_0). The firmware keeps both outputs silent while it reads low (USB alone) |
| Display | J3, R8, R9 | GND / `UART_TX_CONN` / `UART_RX_CONN` / `DISPLAY_5V`; series resistors to Daisy USART1 (R8 10k on TX, R9 1k on RX) |
| Daisy | A1 + two 1×20 sockets | Plug-in module. R17 holds `SPK_EN` low (speaker muted) while it is absent, booting or reset. The firmware feeds the STM32 IWDG only from the audio callback; a reset stops the codec's clocks, which silences J4 and J5 |

**Pinouts used below**

- U1 TLV9061 (SOT-23-5): 1 OUT, 2 V−, 3 IN+, 4 IN−, 5 V+
- U2 TPA6132A2 (WQFN-16): 1 INL−, 2 INL+, 3 INR+, 4 INR−, 5 OUTR, 6 G0, 7 G1, 8 HPVSS, 9 CPN, 10 PGND, 11 CPP, 12 HPVDD, 13 EN, 14 VDD, 15 SGND, 16 OUTL, EP GND.
  INL+/INR+, G0, G1, PGND, SGND and EP to GND; EN and VDD to `+5V`
- Q1 AO3401A, Q2 2N7002 (SOT-23): 1 G, 2 S, 3 D
- J6: 1–2 `5V_IN`, 3–4 GND, 5 `BATT_SENSE_CONN`, 6 `PWR_BTN_CONN`, 7 `PWR_HOLD_CONN`, 8 `SPK_MUTE`
- J4 / J2 (SJ3-35063AG): 1 sleeve, 2 ring, 3 tip, 5 detect common, 6 detect NO (J2's 5/6 not connected)
- A1 (Daisy sockets, `A1.n` = Daisy pin n): 14 USART1 TX, 15 USART1 RX, 16 `AUDIO_IN_1`, 17 `AUDIO_IN_2`, 18 `AUDIO_OUT_1`,
  19 `AUDIO_OUT_2`, 20 GND, 22 `5V_SENSE`, 25 `BATT_SENSE`, 26 `PWR_BTN`, 27 `PWR_HOLD`, 28 `SPK_EN`, 34 `HP_DETECT`,
  39 `+5V`, 40 GND. All other Daisy pins are not connected on the carrier. Probe the sockets while the Daisy is out. With it fitted
  they are covered, so the checks name a carrier part on the same net instead

## Equipment

- Current-limited bench supply (0–6 V), DMM, oscilloscope (≥ 20 MHz)
- Signal generator or audio interface (sine 20 Hz – 20 kHz, ≥ 2 Vpp); a phone/laptop
  headphone output works for listening tests
- ¼" mono cable, 3.5 mm stereo (TRS) cable, 3.5 mm mono (TS) plug, headphones (≈ 32 Ω), 32 Ω and 16 Ω dummy loads (one per channel)
- 8-pin JST-XH pigtail with flying leads for J6, 2-pin JST-XH pigtail for J5
- 10k resistor and clip leads to pull `SPK_MUTE` (J6.8) up to 3.3 V
- USB cable for the Daisy, USB-serial adapter (3.3 V) for J3
- Magnifier/microscope, flux, isopropyl alcohol; hot air for U2 rework

## Stage 0 — Visual and mechanical inspection (unpowered, no Daisy)

| # | Check | Pass criteria |
|---|---|---|
| 0.1 | Clean flux residue; inspect every joint under magnification | No bridges (esp. U1 SOT-23-5 pins, U2 QFN pins, Q1, Q2, the SOD-323 ESD diodes D1–D5), no cold/dull joints, no solder balls |
| 0.2 | IC orientation | U1 and U2 pin-1 marks match silkscreen; U1 = TLV9061, U2 = TPA6132A2 |
| 0.3 | U2 (WQFN-16) | Even fillets on all 16 side pads; part flat, not tilted or floating on the exposed pad; exposed pad soldered (solder visible in the thermal vias from the bottom) |
| 0.4 | Q1 and Q2 | Both SOT-23: confirm markings match AO3401A (Q1) and 2N7002 (Q2) — not swapped; seated on correct pads |
| 0.5 | Electrolytic polarity | C5 `+` to `+5V` |
| 0.6 | Passive values vs BOM | Spot-check R1 (1M), R3/R4/R6/R7/R8/R13 (10k), R12/R15/R17/R18/R19 (100k), R5/R10 (3.3k), R20 (470), R2/R9/R11/R14/R16 (1k); C7/C8 are the 1210 parts, C1, C10/C11 and C12–C16 the 0805 parts (R5/R10/R20 are 0805 too); FB1 is the 1206 bead, not a resistor |
| 0.7 | J6, J5 (JST-XH) | Seated flat; key orientation matches the power-board cable |
| 0.8 | Daisy sockets | Both A1 1×20 sockets flush and parallel; Daisy inserts with moderate force, all pins engaged, USB connector on the correct end |
| 0.9 | J3 header | Flush, straight, correct side of board |
| 0.10 | Jacks J1, J4, J2 | Fully seated, flush to board edge, plugs insert/eject cleanly. J2/J4 noses overhang the edge as drawn; note any footprint mismatch (the J2/J4 footprint was checked against the datasheet only) |
| 0.11 | Enclosure fit (if available) | Jacks, USB and J3/J5/J6 cables line up with panel holes and cable routes |

## Stage 1 — Unpowered resistance checks (no Daisy)

Measure with the DMM; let capacitors charge before reading. Probe on IC pins,
test pads or the Daisy sockets (A1), not on connector shells.

| # | Measure | Expect | Fail indicates |
|---|---|---|---|
| 1.1 | `+5V` (C5 `+`) → GND | Rises to > 1 kΩ (caps charging), not < 50 Ω | Short on 5 V rail — check C4/C5/C6/C12, U1.5, and U2.14 (VDD) bridged to U2.15 (SGND) |
| 1.2 | J6.1 → GND | High; diode mode shows Q1's body diode into the `+5V` rail, not a short | Q1 shorted or bridged |
| 1.3 | J6.1 ↔ J6.2, J6.3/J6.4 → GND | ≈ 0 Ω | J6 joint open |
| 1.4 | `VREF` (C7) → GND | 5–10 kΩ (R7, in parallel with R6 through the unpowered `+5V` rail) | < 1 kΩ = C7 shorted; > 10 kΩ = R7 open or wrong |
| 1.5 | `DISPLAY_5V` (J3.4) → C5 `+` | < 1 Ω (FB1) | FB1 open or missing |
| 1.6 | HPVDD (C15) → `+5V` (C5 `+`) | High (no short) | U2.13 (EN, on `+5V`) bridged to U2.12 (HPVDD) |
| 1.7 | A1.33 and A1.38 → GND and → `+5V` | Open (not connected on the carrier) | Stray copper or a socket bridge |
| 1.8 | U2 pin bridges: J4 tip → GND, J4 ring → GND, J4 ring → `+5V` | High (no short), not < 100 Ω | QFN bridge: OUTL (16)/SGND (15), OUTR (5)/G0 (6) or INR− (4) |
| 1.9 | J1 tip → GND, no plug | ≈ 0 Ω (tip-normal shorts to GND) | J1 switch / footprint issue |
| 1.10 | J1 tip → GND, plug inserted (other end open) | Open once C1 and C2 charge (both block DC); not ≈ 0 Ω | ≈ 0 Ω = plug not lifting the switch |
| 1.11 | J2 tip → ring | ≈ 20 kΩ (R3 + R4) | R3/R4 open |
| 1.12 | J2 tip → GND | ≈ 13.3 kΩ (R3 + R5) | ≈ 10 kΩ = R5 or C3 shorted; ≈ 110 kΩ = 100k fitted for R5 |
| 1.13 | TP1 (`HP_DETECT`) → GND, no plug in J4 | Open | J4 detect switch closed or bridged |
| 1.14 | TP1 → GND, plug in J4 | ≈ 0 Ω | J4 detect switch not closing (check pins 5/6 mapping) |
| 1.15 | TP1 → A1.34 (`HP_DETECT`) | < 1 Ω (direct trace) | Open trace or J4 pin 6 joint |
| 1.16 | J5.1 → GND; J5.2 → GND | ≈ 100 kΩ (R12); ≈ 0 Ω | R12 missing; J5 joints |
| 1.17 | J5.1 → A1.19 (`AUDIO_OUT_2`) | ≈ 1 kΩ (R11) | R11 open or wrong value |
| 1.18 | J6.5 → A1.25; J6.6 → A1.26 | ≈ 10 kΩ (R13); ≈ 1 kΩ (R16) | Power-board signal resistors |
| 1.19 | J6.7 → A1.27; J6.7 → GND | ≈ 1 kΩ (R14); ≈ 100 kΩ (R15) | `PWR_HOLD` network |
| 1.20 | A1.28 (`SPK_EN`) → GND; J6.8 → GND | ≈ 100 kΩ (R17); open (Q2 off) | R17 missing; Q2 shorted or swapped with Q1 |
| 1.21 | J3.2 → A1.14; J3.3 → A1.15 | ≈ 10 kΩ (R8), ≈ 1 kΩ (R9) | UART series resistors |
| 1.21a | A1.22 (`5V_SENSE`) → GND | Below 100 kΩ (R19, with R18 through the `+5V` loads); not ≈ 0 Ω | R18/R19 missing or shorted |
| 1.21b | A1.16 (`AUDIO_IN_1`) → U1.1 | ≈ 470 Ω (R20) | Open = R20 open; ≈ 0 Ω = shorted |
| 1.21c | ESD diodes: J1 tip, J2 tip, J2 ring, J4 tip, J4 ring → GND, in DMM diode mode both ways | No conduction below ≈ 5 V either way (bidirectional TVS; the meter reads open) | A reading = D1–D5 shorted, fitted wrong, or a solder bridge |
| 1.22 | Daisy socket (A1) adjacent pins | Spot-check no shorts between neighbouring pins, esp. A1.39 (+5V) ↔ A1.38 (3V3_D) and A1.40 (GND) | Socket bridge — **5 V into 3V3_D would damage the Daisy** |

## Stage 2 — First power-up, Daisy **removed**

Supply on J6 (+ to J6.1/J6.2, − to J6.3/J6.4): start at 0 V, current limit **50 mA**, ramp to 5.0 V.
U2's EN is tied to `+5V`, so U2 turns on with the supply.

| # | Check | Expect |
|---|---|---|
| 2.1 | Supply current at 5.0 V | A few mA (TLV9061 quiescent + 0.25 mA divider + U2 quiescent and charge pump); < 15 mA. Stop if it hits the limit |
| 2.2 | `+5V` at C5 `+` | 4.9–5.0 V (Q1 drop is tens of mV) |
| 2.3 | `VREF` at C7 | 2.45–2.55 V |
| 2.4 | U1.1 (output); A1.16 | ≈ 2.5 V (the buffer sits at VREF); ≈ 2.5 V at A1.16 too (through R20) |
| 2.5 | U1.3 (IN+) | ≈ 2.5 V |
| 2.6 | U2 charge pump | HPVDD (C15) positive and HPVSS (C14) roughly equal and negative; record both. ≈ 0 V on either = charge-pump fault (C13, pins 8/9/11) |
| 2.7 | J4 tip and ring (DC) | Within ±5 mV of 0 V (DirectPath, no output caps) |
| 2.8 | J5.1 (DC) | ≈ 0 V (R12 to GND) |
| 2.9 | J3.4 (`DISPLAY_5V`) and A1.39 | +5 V; J3.1 and A1.40 are GND. A1.22 (`5V_SENSE`) ≈ 2.5 V (R18/R19) |
| 2.10 | J6.8 (`SPK_MUTE`) with 10k pull-up to 3.3 V | ≈ 3.3 V (Q2 off = speaker muted while the Daisy is absent) |
| 2.11 | Thermal | Nothing warm to the touch after 2 min, U2 included |
| 2.12 | **Reverse polarity** — swap leads on J6, limit 50 mA, apply 5 V | ≈ 0 mA drawn, `+5V` stays at 0 V. Restore correct polarity and repeat 2.2 to confirm nothing was damaged |

## Stage 3 — Analog paths, Daisy **removed**

With the module out, its sockets (A1) reach the Daisy-side nets, so the analog
stages can be tested on their own. Supply 5.0 V, limit 50 mA.

**3A. Guitar input buffer (J1 → AUDIO_IN_1)**

1. Inject 1 kHz, 1 Vpp sine into J1 (tip/sleeve). Scope on `A1.16` (AUDIO_IN_1) or U1.1.
2. | # | Check | Expect |
   |---|---|---|
   | 3A.1 | Output level | U1.1: 1 kHz sine riding on ≈ 2.5 V DC, amplitude ≈ input (unity gain). A1.16: the same through R20 (no Daisy load) |
   | 3A.2 | Input load: add 1 MΩ in series with the generator | Output drops to ≈ half (≈ 1 MΩ input impedance, R1) |
   | 3A.3 | Unplug J1 | Output goes quiet (tip shorted to GND) |
   | 3A.4 | Raise amplitude until clipping | Clips symmetrically near the rails: ≈ 4.8 Vpp at U1.1 and A1.16 (no Daisy load); record the input level |
   | 3A.5 | Sweep 20 Hz – 20 kHz | Flat within about ±1 dB |

**3B. Headphone filter + headphone amp (AUDIO_OUT_1 → J4)**

1. Inject 1 kHz, 1 Vpp sine into `A1.18` (AUDIO_OUT_1), ground at `A1.20`.
   Load J4 tip and ring with 32 Ω each (or headphones at low level).
2. | # | Check | Expect |
   |---|---|---|
   | 3B.1 | C9 (`HP_SOURCE`) | ≈ 0.80 Vpp centred on 0 V (R10 into U2's two 26.4 kΩ inputs, −1.9 dB). Set the generator's DC offset to 0 V |
   | 3B.2 | J4 tip and ring | ≈ 0.40 Vpp centred on 0 V, inverted relative to `HP_SOURCE` (−6 dB, G0 and G1 low); both channels equal within ~0.5 dB |
   | 3B.3 | Frequency sweep 20 Hz – 20 kHz into 32 Ω | Flat in the audio band; low-end corner ≈ 1.3 Hz (C10/C11 into U2's 26.4 kΩ input); falls off above ≈ 60 kHz (R10/C9 with U2's input load) |
   | 3B.4 | Listening test with headphones | Clean tone, no hum/hiss above expected level, no oscillation (check scope for HF ringing on the outputs and on HPVSS) |
   | 3B.5 | Power-on/off with headphones in | Note any pop level (U2 has built-in pop suppression; Stage 7 is the full test) |

**3C. Speaker send (AUDIO_OUT_2 → J5)**

1. Inject 1 kHz, 1 Vpp sine into `A1.19` (AUDIO_OUT_2), ground at `A1.20`.
2. | # | Check | Expect |
   |---|---|---|
   | 3C.1 | J5.1, nothing plugged in | ≈ 1 Vpp centred on 0 V (R11 into R12, −0.1 dB), same phase as the input. Set the generator's DC offset to 0 V |
   | 3C.2 | Load J5 with 10 kΩ | ≈ 0.90 Vpp (R11 into 10k ‖ R12, −0.9 dB) |
   | 3C.3 | Frequency sweep 20 Hz – 20 kHz | Flat in the audio band; falls off above ≈ 48 kHz (R11/C16) |
   | 3C.4 | Insert and remove a plug in J4 | J5 unchanged (rev 2 has no tip-switch; speaker muting is in firmware) |

**3D. AUX input (J2 → AUDIO_IN_2)**

With the Daisy out, only R5 loads the summing node, so these levels are higher than in use. 5.17 checks the real level with the Daisy fitted.

1. Inject 1 kHz, 1 Vpp sine into J2 with a TRS cable, same signal on tip and ring. Scope on `A1.17` (AUDIO_IN_2) or C3.
2. | # | Check | Expect |
   |---|---|---|
   | 3D.1 | Tip and ring driven together | ≈ 0.40 Vpp centred on 0 V (R3‖R4 into R5, −8 dB) |
   | 3D.2 | Tip only, ring grounded (TS plug) | ≈ 0.20 Vpp |
   | 3D.3 | Unplug J2 | Output goes quiet (R5 holds the summing node at GND) |
   | 3D.4 | Sweep 20 Hz – 20 kHz (tip and ring driven) | Flat, ≈ −0.3 dB at 20 kHz (C3 with no Daisy load, ~80 kHz pole; ~110 kHz with the Daisy fitted) |

Remove the injected signal before going on.

## Stage 4 — Power-up with Daisy fitted

1. **Power off.** Insert the Daisy, checking orientation against the silkscreen
   and that no pins are offset by one position.
2. Supply 5.0 V on J6 with the limit set to **300 mA**. Keep USB **unplugged** for this stage.
   Keep the 10k pull-up from J6.8 to 3.3 V.

| # | Check | Expect |
|---|---|---|
| 4.1 | Supply current | Within the Daisy's normal draw (roughly 100–200 mA depending on firmware); record value |
| 4.2 | `+5V` (C5 `+`) | ≥ 4.85 V under load |
| 4.3 | `3V3_D` (Daisy pin 38, probed on top of the module) | 3.3 V ± 5 % (from the Daisy regulator) |
| 4.4 | `VREF`, U1 biases | Same as Stage 2 |
| 4.5 | `HP_DETECT` (TP1) with a plug in J4 | ≈ 0 V. With J4 empty it floats until the firmware enables the internal pull-up, so that case is checked in 5.7 |
| 4.6 | Hold the Daisy in reset (RESET button held) | J4 quiet (headphones on), Q2 pin 1 (`SPK_EN`) 0 V, J6.8 ≈ 3.3 V (muted), J6.7 (`PWR_HOLD_CONN`) 0 V |
| 4.7 | Daisy LED / existing firmware | Boots normally |
| 4.8 | Thermal after 5 min | Nothing hot; Q1 and U2 at most warm |
| 4.9 | Back-power: J6 supply **off**, 3.3 V on J6.5 (`BATT_SENSE_CONN`) | ≤ 0.3 mA drawn (R13); record `3V3_D`. More means the Daisy is being back-powered |

Then plug in USB with J6 still powered and confirm current/voltages don't jump
unexpectedly. Check the Daisy Seed docs for your revision's VIN/USB power-path
before relying on both sources together.

## Stage 5 — Functional tests with test firmware

Flash a small bring-up program (libDaisy or Arduino/DaisyDuino) over USB that:

- passes audio input 1 to outputs 1 and 2, mixes input 2 (AUX) into both, and logs peak levels,
- drives `PWR_HOLD` high at boot,
- lets `SPK_EN` be toggled from USB serial,
- prints `HP_DETECT`, `PWR_BTN` and the `BATT_SENSE` and `5V_SENSE` ADC readings over USB serial,
- keeps both outputs at digital silence while `5V_SENSE` reads low,
- echoes bytes on USART1 (J3) and sends a heartbeat string every second.

Keep the 10k pull-up from J6.8 to 3.3 V unless the power board is connected.

| # | Check | Expect |
|---|---|---|
| 5.1 | USB enumeration / DFU flashing | Flashes and enumerates; confirms the USB D+/D− sockets connect |
| 5.2 | Audio passthrough: 1 kHz into J1 → J4 headphones | Clean tone on both channels |
| 5.3 | Passthrough: J1 → J5 | Signal present (output 2) |
| 5.4 | Noise floor: J1 unplugged, firmware gain max | Only low-level hiss; no hum, whine, or digital noise from USB/codec; record level on the scope at J4 and J5 |
| 5.5 | Guitar test | Real guitar into J1, headphones on J4: clean signal, no clipping at normal pick strength; record the peak level the firmware logs |
| 5.6 | AUX: phone/laptop into J2 at full volume | Heard on J4 and J5; record the logged peak and whether input 2 clips |
| 5.7 | `HP_DETECT` | Prints high with J4 empty (internal pull-up), low with a plug in; TP1 ≈ 3.3 V empty, ≈ 0 V with a plug in. No chatter after debounce |
| 5.8 | Headphones through a reset: 1 kHz into J1, headphones on J4, hold RESET, then release | J4 goes silent while RESET is held (codec clocks stopped) and the tone returns after boot. Note any click at each step |
| 5.9 | `SPK_EN` toggled high/low | Q2 pin 1 follows; J6.8 < 0.1 V while high (Q2 on, speaker playing), ≈ 3.3 V while low. Record the low level (Q2 gate drive from 3.3 V) |
| 5.10 | `PWR_BTN`: short J6.6 to GND, release | Prints low while shorted, high released (internal pull-up) |
| 5.11 | `PWR_HOLD` | J6.7 ≈ 3.3 V after boot |
| 5.12 | `BATT_SENSE`: known voltage (e.g. 1.65 V) on J6.5 | ADC reading matches within a few % |
| 5.13 | UART on J3 with a 3.3 V USB-serial adapter (adapter TX → J3.3, RX → J3.2, GND → J3.1) | Heartbeat received; echo works. **Before connecting the real display**, confirm its TX idles at ≤ 3.3 V |
| 5.14 | Display on J3 | Powers from J3.4 (`DISPLAY_5V`), shows data from the Daisy. Scope `+5V` at C5 with Wi-Fi/backlight active: ripple much lower than at J3.4 (FB1/C8) |
| 5.15 | USB alone: J6 supply **off**, display unplugged, Daisy on USB, 1 kHz into J1, `PWR_HOLD` and `SPK_EN` driven high | `+5V` (C5 `+`) ≈ 0 V and `5V_SENSE` prints ≈ 0 V. A1.18 (`AUDIO_OUT_1`, on top of the module) and C9 carry no signal: the firmware keeps the outputs silent. Then power J6: `5V_SENSE` prints ≈ 2.5 V and the tone returns on J4 without a click. Record all of it |
| 5.16 | Output DC with the codec running: firmware outputs digital silence, nothing plugged into J5. Measure DC at A1.18 and A1.19 (on top of the module) and at J5.1 (`LINE_OUT`). Then hold RESET (clocks stop, codec powers down) and release, watching J5.1 on the scope | All three within ±20 mV of 0 V, which confirms the Seed3 outputs are AC-coupled on the module. More than a few tens of mV at A1.19 or J5.1: the speaker send needs a 10 µF DC-blocking cap in series (see DESIGN.md "Speaker send"). Record any step or pop on J5.1 at reset and release |
| 5.17 | AUX level with the Daisy fitted: 1 kHz, 1 Vpp into J2, same signal on tip and ring, then tip only with ring grounded. Scope A1.17 (on top of the module) and read the firmware's input-2 peak | Tip and ring: 0.27–0.30 Vpp (−11.5 to −10.5 dB, the Daisy's input at 4–6 kΩ). Tip only: ≈ 0.13–0.15 Vpp. Record both. ≈ 0.40 Vpp means the module adds almost no load; much lower means its input is below 4 kΩ (see DESIGN.md "AUX input") |
| 5.18 | `+5V` transitions on USB: Daisy on USB, J6 powered, display connected, full-scale 1 kHz to J4 (32 Ω load). Scope `+5V` (C5 `+`), HPVDD (C15), HPVSS (C14) and U2's INL− (C10, U2 side). Remove J6 power, then restore it. Repeat with the display unplugged | Power off: INL− goes silent before HPVDD/HPVSS collapse, or stays outside HPVSS − 0.3 V … HPVDD + 0.3 V for no more than a few ms. Record the time. Power on: audio returns ≥ 10 ms after HPVDD/HPVSS settle, with no click on J4 |
| 5.19 | Hot passive pickups: the hottest passive guitar available into J1, played as hard as possible | Record the logged peak. It should stay below full scale (≈ 3.9 Vpp at J1). Active pickups are out of scope |

## Stage 6 — Soak and robustness

| # | Check | Expect |
|---|---|---|
| 6.1 | Run passthrough with audio for 30 min | No dropouts, resets, or drift in VREF / supply current |
| 6.2 | Plug/unplug J1, J4, J2 repeatedly while running | No resets, no lasting noise, jacks stay mechanically solid; `HP_DETECT` reports every J4 change |
| 6.3 | Wiggle the J6, J3 and J5 cables while running | No crackle, dropouts or resets |
| 6.4 | Full-level 1 kHz into 32 Ω on J4 for 10 min | U2 at most warm; no shutdown or distortion change |
| 6.5 | Light flex/tap test on the board and Daisy | No crackle or resets (would point to a cracked joint or loose socket pin) |

## Stage 7 — Pops, hiss and mute (rev 2)

Rev 2 only. Needs the product firmware (volume ramps, headphone detect, `PWR_HOLD` shutdown, `SPK_EN` delay) and an
audio interface on the laptop. Record J4 (into a 32 Ω load or EarPods) and J5 (`LINE_OUT`) into the interface, and look at each
recording for spikes. Pass means no audible click and no spike more than ~10 dB above the recording's noise floor.
On the bench, pull J6.8 (`SPK_MUTE`) up to 3.3 V with 10k so it can be probed without the power board.

| # | Check | Expect |
|---|---|---|
| 7.1 | Power-on pop: record J4 and J5, then power the board | No click on either output. U2 turns on with `+5V`, before the Daisy boots, so listen for anything on J4 while the codec starts up |
| 7.2 | Speaker power-on: scope `+5V` (C5 `+`), `SPK_EN` (Q2 pin 1) and J5.1 (`LINE_OUT`) at power-on, J5 open and then into the speaker amp | `SPK_EN` goes high after audio starts. `LINE_OUT` stays near 0 V (no bias network to settle). Record any step at the Daisy's output, and listen for a thump from the speaker |
| 7.3 | Power-off pop: record J4 and J5, press the power button for a clean shutdown | Audio fades out, then silence. No click when `PWR_HOLD` drops |
| 7.4 | Hard power cut: record J4 and J5, unplug J6 while playing | Note the result. A small click is acceptable here, a loud bang is not |
| 7.5 | Headphone plug-in and removal while playing a 1 kHz tone | `SPK_EN` goes low while headphones are in and high again when they come out. No click on J4 or J5 |
| 7.6 | Watchdog mute: debug build that stops the audio callback on a USB serial command | J4 and J5 go silent (codec DAC power-down) and `SPK_MUTE` goes to muted within ~10–20 ms. The Daisy resets and boots back into silence. Record any click on J4 |
| 7.7 | Hiss with EarPods: J1 unplugged, firmware volume at a quiet listening level, then at max | No hiss audible at a normal listening level (U2 already runs at −6 dB). Record whether hiss is audible at max |
| 7.8 | Maximum level: full-scale 1 kHz into a 32 Ω load on J4 | ≈ 0.40 Vrms per channel (1 Vrms Daisy full scale, −1.9 dB at R10, −6 dB in U2), no clipping: U2's 1 % THD limit is ≈ 0.84 Vrms into 32 Ω and ≈ 0.63 Vrms into 16 Ω. Repeat into 16 Ω. Listening check with the intended headphones: loud enough with margin (if not, see DESIGN.md "Headphone level") |

## Fault-finding hints

| Symptom | Look at first |
|---|---|
| Supply hits current limit at power-up | Stage 1.1 short; reversed C5; U1/U2 rotated; U2 pins bridged |
| No `+5V` with correct polarity | Q1 orientation/footprint; Q1 and Q2 swapped; J6 pin order / cable |
| `VREF` not ≈ 2.5 V | R6/R7 values, C7 leakage/short |
| Input works only intermittently | J1 tip-normal switch, C2/R2 joints |
| No headphone output | U2.13 (EN) and U2.14 (VDD) at `+5V`; U2 side pads and exposed pad joints |
| HPVDD/HPVSS ≈ 0 V with EN high | C13 (flying cap), C14/C15, U2 pins 8/9/11/12 |
| DC or hum on J4 outputs | U2 SGND (pin 15) / exposed pad to GND; INL+/INR+ (pins 2/3) grounded |
| Output only on one HP channel | That channel's C10/C11, U2 pin 1/4 (input) or 16/5 (output) joints, J4 tip/ring pins |
| Speaker output (J5) dead | R11, C16 (shorted?), R12; `AUDIO_OUT_2` from firmware |
| AUX input dead, quiet or too loud | J2 pins, R3/R4, R5 value (3.3k: a 100k fitted by mistake is ≈ 5 dB louder), C3 shorted; `AUDIO_IN_2` trace to A1.17 |
| `HP_DETECT` stuck or inverted | J4 pins 5/6 mapping, TP1 → A1.34 trace, firmware pull-up on pin 34 (PG9) |
| Speaker amp never unmutes / never mutes | Q2 orientation or swapped with Q1; R17; `SPK_MUTE` polarity on the power board |
| Daisy won't boot | Socket orientation / offset; `3V3_D` and `+5V` shorted at A1.38/A1.39 |
| Daisy partly alive with J6 off | Back-powering through J6.5–J6.7: check R13/R16/R14 values and the power board's divider |

## Results log

Board serial / ID: __________  Assembled by: __________  Date: __________

Fab package: __________  Tested by: __________  Firmware commit: __________

| Stage | Result (Pass/Fail) | Measured values / notes |
|---|---|---|
| 0 Visual & mechanical | | |
| 1 Unpowered resistance | | |
| 2 Power-up, no Daisy | | I = ____ mA, +5V = ____ V, VREF = ____ V, HPVDD = ____ V, HPVSS = ____ V |
| 2.12 Reverse polarity | | |
| 3A Guitar input buffer | | Clip level = ____ Vpp |
| 3B Headphone filter / amp | | L = ____ Vpp, R = ____ Vpp into 32 Ω, DC offset L/R = ____ / ____ mV |
| 3C Speaker send | | J5 = ____ Vpp |
| 3D AUX input | | Tip+ring = ____ Vpp |
| 4 Power-up with Daisy | | I = ____ mA, 3V3_A = ____ V, 3V3_D = ____ V, back-power I = ____ mA |
| 5 Firmware functional | | SPK_MUTE low = ____ V, AUX peak = ____ |
| 6 Soak & robustness | | |
| 7 Pops, hiss and mute | | SPK_EN delay = ____ s, mute time = ____ ms, HP max = ____ Vrms |

Rework performed:

Open issues:
