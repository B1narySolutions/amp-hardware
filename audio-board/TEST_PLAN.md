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
| Power input | J3 (8-pin JST-XH), Q1 (AO3401A) | `5V_IN` on J3.1/J3.2, GND on J3.3/J3.4; P-FET reverse-polarity protection onto `+5V`, probe at C18 `+` |
| 5 V decoupling | C8, C17, C18, C33 | Bulk/HF decoupling on `+5V` (C33 at U2 VDD) |
| Power board signals | R32/C28, R35/C29, R33/R34, Q4/R37 | J3.5 `BATT_SENSE_CONN` → Daisy pin 25; J3.6 `PWR_BTN_CONN` → pin 26 (active low, STM32 internal pull-up); pin 27 `PWR_HOLD` → J3.7 (100k pull-down); pin 28 `SPK_EN` → Q4 → J3.8 `SPK_MUTE` (open drain, low = speaker on) |
| Display supply | FB1, C30 | Ferrite + 47 µF filter from `+5V` to `DISPLAY_5V` (J4.4) |
| Mid-rail reference | R7, R8 (10k/10k), C7 | `VREF` ≈ 2.5 V, probe at C7 |
| Guitar input | J1, C1, C3, R17 (1M), R1, U1A | ¼" input, tip shorted to GND when unplugged; 1 MΩ load; unity-gain buffer → Daisy `AUDIO_IN_1` |
| AUX input | J9, R40/R41, R38, C31 | 3.5 mm TRS, passive stereo-to-mono sum, ~65 kHz RF filter, straight into Daisy `AUDIO_IN_2` (no buffer). The Daisy's ≈ 5k input sets the level (≈ −6 dB with the same signal on both channels) |
| Headphone filter | R2, C2 | Daisy `AUDIO_OUT_1` (expected to be AC-coupled on the module; 5.16 checks) → ~64 kHz RC low-pass → `HP_SOURCE`, driving U2 directly |
| Headphone amp | U2 (TPA6132A2), C12/C13, C33–C36 | DirectPath stereo amp, 0 dB inverting (mono source on both channels), outputs at 0 V straight to J5 (`HP_L` tip, `HP_R` ring). EN tied to `+5V`: U2 is on whenever `+5V` is up |
| Headphone detect | J5.5/J5.6, TP11 | Normally-open switch closes to GND on plug insertion → `HP_DETECT` (Daisy pin 34, wired directly; STM32 internal pull-up, enabled by the firmware). **Low = headphones in.** Probe at **TP11** (`TP_HP_DET`) |
| Speaker / line send | R28, C24, R4 | Daisy `AUDIO_OUT_2` → ~48 kHz low-pass (R28/C24, no buffer) → `LINE_OUT` on J2 (¼" external) and J8 (internal, to the speaker amp) |
| Display | J4, R43, R44 | GND / `UART_TX_CONN` / `UART_RX_CONN` / `DISPLAY_5V`; series resistors to Daisy USART1 (R43 10k on TX, R44 1k on RX) |
| Daisy | A1 + two 1×20 sockets | Plug-in module. R37 holds `SPK_EN` low (speaker muted) while it is absent, booting or reset. The firmware feeds the STM32 IWDG only from the audio callback; a reset stops the codec's clocks, which silences J5 and J2 |

**Pinouts used below**

- U1 TLV9061 (SOT-23-5): 1 OUT, 2 V−, 3 IN+, 4 IN−, 5 V+
- U2 TPA6132A2 (WQFN-16): 1 INL−, 2 INL+, 3 INR+, 4 INR−, 5 OUTR, 6 G0, 7 G1, 8 HPVSS, 9 CPN, 10 PGND, 11 CPP, 12 HPVDD, 13 EN, 14 VDD, 15 SGND, 16 OUTL, EP GND.
  INL+/INR+, G1, PGND, SGND and EP to GND; G0, EN and VDD to `+5V`
- Q1 AO3401A, Q4 2N7002 (SOT-23): 1 G, 2 S, 3 D
- J3: 1–2 `5V_IN`, 3–4 GND, 5 `BATT_SENSE_CONN`, 6 `PWR_BTN_CONN`, 7 `PWR_HOLD_CONN`, 8 `SPK_MUTE`
- J5 / J9 (SJ3-35063AG): 1 sleeve, 2 ring, 3 tip, 5 detect common, 6 detect NO (J9's 5/6 not connected)
- A1 (Daisy sockets, `A1.n` = Daisy pin n): 14 USART1 TX, 15 USART1 RX, 16 `AUDIO_IN_1`, 17 `AUDIO_IN_2`, 18 `AUDIO_OUT_1`,
  19 `AUDIO_OUT_2`, 20 GND, 25 `BATT_SENSE`, 26 `PWR_BTN`, 27 `PWR_HOLD`, 28 `SPK_EN`, 34 `HP_DETECT`,
  39 `+5V`, 40 GND. All other Daisy pins are not connected on the carrier. Probe the sockets while the Daisy is out. With it fitted
  they are covered, so the checks name a carrier part on the same net instead

## Equipment

- Current-limited bench supply (0–6 V), DMM, oscilloscope (≥ 20 MHz)
- Signal generator or audio interface (sine 20 Hz – 20 kHz, ≥ 2 Vpp); a phone/laptop
  headphone output works for listening tests
- ¼" mono cable, 3.5 mm stereo (TRS) cable, 3.5 mm mono (TS) plug, headphones (≈ 32 Ω), a 32 Ω dummy load (one per channel)
- 8-pin JST-XH pigtail with flying leads for J3, 2-pin JST-XH pigtail for J8
- 10k resistor and clip leads to pull `SPK_MUTE` (J3.8) up to 3.3 V
- USB cable for the Daisy, USB-serial adapter (3.3 V) for J4
- Magnifier/microscope, flux, isopropyl alcohol; hot air for U2 rework

## Stage 0 — Visual and mechanical inspection (unpowered, no Daisy)

| # | Check | Pass criteria |
|---|---|---|
| 0.1 | Clean flux residue; inspect every joint under magnification | No bridges (esp. U1 SOT-23-5 pins, U2 QFN pins, Q1, Q4), no cold/dull joints, no solder balls |
| 0.2 | IC orientation | U1 and U2 pin-1 marks match silkscreen; U1 = TLV9061, U2 = TPA6132A2 |
| 0.3 | U2 (WQFN-16) | Even fillets on all 16 side pads; part flat, not tilted or floating on the exposed pad; exposed pad soldered (solder visible in the thermal vias from the bottom) |
| 0.4 | Q1 and Q4 | Both SOT-23: confirm markings match AO3401A (Q1) and 2N7002 (Q4) — not swapped; seated on correct pads |
| 0.5 | Electrolytic polarity | C18 `+` to `+5V` |
| 0.6 | Passive values vs BOM | Spot-check R17 (1M), R7/R8/R32/R40/R41/R43 (10k), R4/R34/R37/R38 (100k); C7/C12/C13/C30 are the 1210 parts, C33–C36 the 0805 parts; FB1 is the 1206 bead, not a resistor |
| 0.7 | J3, J8 (JST-XH) | Seated flat; key orientation matches the power-board cable |
| 0.8 | Daisy sockets | Both A1 1×20 sockets flush and parallel; Daisy inserts with moderate force, all pins engaged, USB connector on the correct end |
| 0.9 | J4 header | Flush, straight, correct side of board |
| 0.10 | Jacks J1, J2, J5, J9 | Fully seated, flush to board edge, plugs insert/eject cleanly. J5/J9 noses overhang the edge as drawn; note any footprint mismatch (J5/J9 footprint was hand-drawn) |
| 0.11 | Enclosure fit (if available) | Jacks, USB and J3/J4/J8 cables line up with panel holes and cable routes |

## Stage 1 — Unpowered resistance checks (no Daisy)

Measure with the DMM; let capacitors charge before reading. Probe on IC pins,
test pads or the Daisy sockets (A1), not on connector shells.

| # | Measure | Expect | Fail indicates |
|---|---|---|---|
| 1.1 | `+5V` (C18 `+`) → GND | Rises to > 1 kΩ (caps charging), not < 50 Ω | Short on 5 V rail — check C8/C17/C18/C33, U1.5, U2.14, U2.6 |
| 1.2 | J3.1 → GND | High; diode mode shows Q1's body diode into the `+5V` rail, not a short | Q1 shorted or bridged |
| 1.3 | J3.1 ↔ J3.2, J3.3/J3.4 → GND | ≈ 0 Ω | J3 joint open |
| 1.4 | `VREF` (C7) → GND | ≈ 5 kΩ (R7 in parallel with R8 via 5 V loads) | R7/R8 wrong or open, C7 shorted |
| 1.5 | `DISPLAY_5V` (J4.4) → C18 `+` | < 1 Ω (FB1) | FB1 open or missing |
| 1.6 | HPVDD (C34) → `+5V` (C18 `+`) | High (no short) | U2.13 (EN, on `+5V`) bridged to U2.12 (HPVDD) |
| 1.7 | A1.33 and A1.38 → GND and → `+5V` | Open (not connected on the carrier) | Stray copper or a socket bridge |
| 1.8 | U2 pin bridges: J5 tip → GND, J5 ring → GND, J5 ring → `+5V` | High (no short), not < 100 Ω | QFN bridge: OUTL (16)/SGND (15), OUTR (5)/G0 (6) or INR− (4) |
| 1.9 | J1 tip → GND, no plug | ≈ 0 Ω (tip-normal shorts to GND) | J1 switch / footprint issue |
| 1.10 | J1 tip → GND, plug inserted (other end open) | ≈ 1 MΩ (R17 via VREF) once C3 charges; not ≈ 0 Ω | Plug not lifting the switch |
| 1.11 | J9 tip → ring | ≈ 20 kΩ (R40 + R41) | R40/R41 open |
| 1.12 | J9 tip → GND | ≈ 110 kΩ (R40 + R38) | ≈ 10 kΩ = R38 or C31 shorted; ≈ 14.7 kΩ = 4.7k fitted for R38 |
| 1.13 | TP11 (`HP_DETECT`) → GND, no plug in J5 | Open | J5 detect switch closed or bridged |
| 1.14 | TP11 → GND, plug in J5 | ≈ 0 Ω | J5 detect switch not closing (check pins 5/6 mapping) |
| 1.15 | TP11 → A1.34 (`HP_DETECT`) | < 1 Ω (direct trace) | Open trace or J5 pin 6 joint |
| 1.16 | J2 tip → GND; J2 tip ↔ J8.1; J8.2 → GND | ≈ 100 kΩ (R4); ≈ 0 Ω; ≈ 0 Ω | R4 missing; J8 joints |
| 1.17 | J2 tip → A1.19 (`AUDIO_OUT_2`) | ≈ 3.3 kΩ (R28) | R28 open or wrong value |
| 1.18 | J3.5 → A1.25; J3.6 → A1.26 | ≈ 10 kΩ (R32); ≈ 1 kΩ (R35) | Power-board signal resistors |
| 1.19 | J3.7 → A1.27; J3.7 → GND | ≈ 1 kΩ (R33); ≈ 100 kΩ (R34) | `PWR_HOLD` network |
| 1.20 | A1.28 (`SPK_EN`) → GND; J3.8 → GND | ≈ 100 kΩ (R37); open (Q4 off) | R37 missing; Q4 shorted or swapped with Q1 |
| 1.21 | J4.2 → A1.14; J4.3 → A1.15 | ≈ 10 kΩ (R43), ≈ 1 kΩ (R44) | UART series resistors |
| 1.22 | Daisy socket (A1) adjacent pins | Spot-check no shorts between neighbouring pins, esp. A1.39 (+5V) ↔ A1.38 (3V3_D) and A1.40 (GND) | Socket bridge — **5 V into 3V3_D would damage the Daisy** |

## Stage 2 — First power-up, Daisy **removed**

Supply on J3 (+ to J3.1/J3.2, − to J3.3/J3.4): start at 0 V, current limit **50 mA**, ramp to 5.0 V.
U2's EN is tied to `+5V`, so U2 turns on with the supply.

| # | Check | Expect |
|---|---|---|
| 2.1 | Supply current at 5.0 V | A few mA (TLV9061 quiescent + 0.25 mA divider + U2 quiescent and charge pump); < 15 mA. Stop if it hits the limit |
| 2.2 | `+5V` at C18 `+` | 4.9–5.0 V (Q1 drop is tens of mV) |
| 2.3 | `VREF` at C7 | 2.45–2.55 V |
| 2.4 | U1.1 (output) | ≈ 2.5 V (the buffer sits at VREF) |
| 2.5 | U1.3 (IN+) | ≈ 2.5 V |
| 2.6 | U2 charge pump | HPVDD (C34) positive and HPVSS (C36) roughly equal and negative; record both. ≈ 0 V on either = charge-pump fault (C35, pins 8/9/11) |
| 2.7 | J5 tip and ring (DC) | Within ±5 mV of 0 V (DirectPath, no output caps) |
| 2.8 | J2 tip / J8.1 (DC) | ≈ 0 V (R4 to GND) |
| 2.9 | J4.4 (`DISPLAY_5V`) and A1.39 | +5 V; J4.1 and A1.40 are GND |
| 2.10 | J3.8 (`SPK_MUTE`) with 10k pull-up to 3.3 V | ≈ 3.3 V (Q4 off = speaker muted while the Daisy is absent) |
| 2.11 | Thermal | Nothing warm to the touch after 2 min, U2 included |
| 2.12 | **Reverse polarity** — swap leads on J3, limit 50 mA, apply 5 V | ≈ 0 mA drawn, `+5V` stays at 0 V. Restore correct polarity and repeat 2.2 to confirm nothing was damaged |

## Stage 3 — Analog paths, Daisy **removed**

With the module out, its sockets (A1) reach the Daisy-side nets, so the analog
stages can be tested on their own. Supply 5.0 V, limit 50 mA.

**3A. Guitar input buffer (J1 → AUDIO_IN_1)**

1. Inject 1 kHz, 1 Vpp sine into J1 (tip/sleeve). Scope on `A1.16` (AUDIO_IN_1) or U1.1.
2. | # | Check | Expect |
   |---|---|---|
   | 3A.1 | Output level | 1 kHz sine riding on ≈ 2.5 V DC, amplitude ≈ input (unity gain, no level pot) |
   | 3A.2 | Input load: add 1 MΩ in series with the generator | Output drops to ≈ half (≈ 1 MΩ input impedance, R17) |
   | 3A.3 | Unplug J1 | Output goes quiet (tip shorted to GND) |
   | 3A.4 | Raise amplitude until clipping | Clips symmetrically near the rails (≈ 4.8 Vpp); record the input level |
   | 3A.5 | Sweep 20 Hz – 20 kHz | Flat within about ±1 dB |

**3B. Headphone filter + headphone amp (AUDIO_OUT_1 → J5)**

1. Inject 1 kHz, 1 Vpp sine into `A1.18` (AUDIO_OUT_1), ground at `A1.20`.
   Load J5 tip and ring with 32 Ω each (or headphones at low level).
2. | # | Check | Expect |
   |---|---|---|
   | 3B.1 | C2 (`HP_SOURCE`) | ≈ 0.75 Vpp centred on 0 V (R2 into U2's two 19.8 kΩ inputs, −2.5 dB). Set the generator's DC offset to 0 V |
   | 3B.2 | J5 tip and ring | ≈ 0.75 Vpp centred on 0 V, inverted relative to `HP_SOURCE` (0 dB, G0 high / G1 low); both channels equal within ~0.5 dB |
   | 3B.3 | Frequency sweep 20 Hz – 20 kHz into 32 Ω | Flat in the audio band; low-end corner ≈ 1.7 Hz (C12/C13 into U2's 19.8 kΩ input); falls off above ≈ 64 kHz (R2/C2 with U2's input load) |
   | 3B.4 | Listening test with headphones | Clean tone, no hum/hiss above expected level, no oscillation (check scope for HF ringing on the outputs and on HPVSS) |
   | 3B.5 | Power-on/off with headphones in | Note any pop level (U2 has built-in pop suppression; Stage 7 is the full test) |

**3C. Speaker / line send (AUDIO_OUT_2 → J2 / J8)**

1. Inject 1 kHz, 1 Vpp sine into `A1.19` (AUDIO_OUT_2), ground at `A1.20`.
2. | # | Check | Expect |
   |---|---|---|
   | 3C.1 | J2 tip and J8.1, nothing plugged in | ≈ 1 Vpp centred on 0 V (R28 into R4, −0.3 dB), same phase as the input, identical on both. Set the generator's DC offset to 0 V |
   | 3C.2 | Load J2 with 10 kΩ | ≈ 0.74 Vpp (R28 into 10k ‖ R4, −2.6 dB) |
   | 3C.3 | Frequency sweep 20 Hz – 20 kHz | Flat in the audio band; falls off above ≈ 48 kHz (R28/C24) |
   | 3C.4 | Insert and remove a plug in J5 | J2/J8 unchanged (rev 2 has no tip-switch; speaker muting is in firmware) |

**3D. AUX input (J9 → AUDIO_IN_2)**

With the Daisy out, only R38 loads the summing node, so these levels are higher than in use. 5.17 checks the real level with the Daisy fitted.

1. Inject 1 kHz, 1 Vpp sine into J9 with a TRS cable, same signal on tip and ring. Scope on `A1.17` (AUDIO_IN_2) or C31.
2. | # | Check | Expect |
   |---|---|---|
   | 3D.1 | Tip and ring driven together | ≈ 0.95 Vpp centred on 0 V (R40‖R41 into R38) |
   | 3D.2 | Tip only, ring grounded (TS plug) | ≈ 0.48 Vpp |
   | 3D.3 | Unplug J9 | Output goes quiet (R38 holds the summing node at GND) |
   | 3D.4 | Sweep 20 Hz – 20 kHz (tip and ring driven) | Flat, ≈ −1.3 dB at 20 kHz (C31 with no Daisy load, ~33 kHz pole; ~65 kHz with the Daisy fitted) |

Remove the injected signal before going on.

## Stage 4 — Power-up with Daisy fitted

1. **Power off.** Insert the Daisy, checking orientation against the silkscreen
   and that no pins are offset by one position.
2. Supply 5.0 V on J3 with the limit set to **300 mA**. Keep USB **unplugged** for this stage.
   Keep the 10k pull-up from J3.8 to 3.3 V.

| # | Check | Expect |
|---|---|---|
| 4.1 | Supply current | Within the Daisy's normal draw (roughly 100–200 mA depending on firmware); record value |
| 4.2 | `+5V` (C18 `+`) | ≥ 4.85 V under load |
| 4.3 | `3V3_D` (Daisy pin 38, probed on top of the module) | 3.3 V ± 5 % (from the Daisy regulator) |
| 4.4 | `VREF`, U1 biases | Same as Stage 2 |
| 4.5 | `HP_DETECT` (TP11) with a plug in J5 | ≈ 0 V. With J5 empty it floats until the firmware enables the internal pull-up, so that case is checked in 5.7 |
| 4.6 | Hold the Daisy in reset (RESET button held) | J5 quiet (headphones on), Q4 pin 1 (`SPK_EN`) 0 V, J3.8 ≈ 3.3 V (muted), J3.7 (`PWR_HOLD_CONN`) 0 V |
| 4.7 | Daisy LED / existing firmware | Boots normally |
| 4.8 | Thermal after 5 min | Nothing hot; Q1 and U2 at most warm |
| 4.9 | Back-power: J3 supply **off**, 3.3 V on J3.5 (`BATT_SENSE_CONN`) | ≤ 0.3 mA drawn (R32); record `3V3_D`. More means the Daisy is being back-powered |

Then plug in USB with J3 still powered and confirm current/voltages don't jump
unexpectedly. Check the Daisy Seed docs for your revision's VIN/USB power-path
before relying on both sources together.

## Stage 5 — Functional tests with test firmware

Flash a small bring-up program (libDaisy or Arduino/DaisyDuino) over USB that:

- passes audio input 1 to outputs 1 and 2, mixes input 2 (AUX) into both, and logs peak levels,
- drives `PWR_HOLD` high at boot,
- lets `SPK_EN` be toggled from USB serial,
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
| 5.7 | `HP_DETECT` | Prints high with J5 empty (internal pull-up), low with a plug in; TP11 ≈ 3.3 V empty, ≈ 0 V with a plug in. No chatter after debounce |
| 5.8 | Headphones through a reset: 1 kHz into J1, headphones on J5, hold RESET, then release | J5 goes silent while RESET is held (codec clocks stopped) and the tone returns after boot. Note any click at each step |
| 5.9 | `SPK_EN` toggled high/low | Q4 pin 1 follows; J3.8 < 0.1 V while high (Q4 on, speaker playing), ≈ 3.3 V while low. Record the low level (Q4 gate drive from 3.3 V) |
| 5.10 | `PWR_BTN`: short J3.6 to GND, release | Prints low while shorted, high released (internal pull-up) |
| 5.11 | `PWR_HOLD` | J3.7 ≈ 3.3 V after boot |
| 5.12 | `BATT_SENSE`: known voltage (e.g. 1.65 V) on J3.5 | ADC reading matches within a few % |
| 5.13 | UART on J4 with a 3.3 V USB-serial adapter (adapter TX → J4.3, RX → J4.2, GND → J4.1) | Heartbeat received; echo works. **Before connecting the real display**, confirm its TX idles at ≤ 3.3 V |
| 5.14 | Display on J4 | Powers from J4.4 (`DISPLAY_5V`), shows data from the Daisy. Scope `+5V` at C18 with Wi-Fi/backlight active: ripple much lower than at J4.4 (FB1/C30) |
| 5.15 | Back-power from USB: J3 supply **off**, display unplugged, Daisy on USB, `PWR_HOLD` and `SPK_EN` driven high | `+5V` (C18 `+`) ≈ 0 V. Record it |
| 5.16 | Output DC with the codec running: firmware outputs digital silence, nothing plugged into J2/J8. Measure DC at A1.18 and A1.19 (on top of the module) and at J2 tip (`LINE_OUT`). Then hold RESET (clocks stop, codec powers down) and release, watching J2 tip on the scope | All three within ±20 mV of 0 V, which confirms the Seed3 outputs are AC-coupled on the module. More than a few tens of mV at A1.19 or J2: fit a 10 µF series cap after R28 (see DESIGN.md "Speaker / line send"). Record any step or pop on J2 at reset and release |
| 5.17 | AUX level with the Daisy fitted: 1 kHz, 1 Vpp into J9, same signal on tip and ring, then tip only with ring grounded. Scope A1.17 (on top of the module) and read the firmware's input-2 peak | Tip and ring: 0.44–0.55 Vpp (−7.0 to −5.5 dB, the Daisy's input at 4–6 kΩ). Tip only: ≈ 0.22–0.27 Vpp. Record both. Much lower means the module input is lower than 4 kΩ: lower R40/R41 (see DESIGN.md "AUX input") |

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
| 7.1 | Power-on pop: record J5 and J2, then power the board | No click on either output. U2 turns on with `+5V`, before the Daisy boots, so listen for anything on J5 while the codec starts up |
| 7.2 | Speaker power-on: scope `+5V` (C18 `+`), `SPK_EN` (Q4 pin 1) and J8.1 (`LINE_OUT`) at power-on, J8 open and then into the speaker amp | `SPK_EN` goes high after audio starts. `LINE_OUT` stays near 0 V (no bias network to settle). Record any step at the Daisy's output, and listen for a thump from the speaker |
| 7.3 | Power-off pop: record J5 and J2, press the power button for a clean shutdown | Audio fades out, then silence. No click when `PWR_HOLD` drops |
| 7.4 | Hard power cut: record J5 and J2, unplug J3 while playing | Note the result. A small click is acceptable here, a loud bang is not |
| 7.5 | Headphone plug-in and removal while playing a 1 kHz tone | J2 dips briefly at each plug-in and removal, then carries on (it stays live with headphones in). `SPK_EN` goes low while headphones are in. No click on either output |
| 7.6 | Watchdog mute: debug build that stops the audio callback on a USB serial command | J5 and J2 go silent (codec DAC power-down) and `SPK_MUTE` goes to muted within ~10–20 ms. The Daisy resets and boots back into silence. Record any click on J5 |
| 7.7 | Hiss with EarPods: J1 unplugged, firmware volume at a quiet listening level, then at max | No hiss audible at a normal listening level. If it is, tie U2 G0 to GND (−6 dB) and repeat 7.7 and 7.8 |
| 7.8 | Maximum level: full-scale 1 kHz into a 32 Ω load on J5 | ≈ 0.75 Vrms per channel (1 Vrms Daisy full scale, −2.5 dB at R2), no clipping. U2 clips at ≈ 1.1 Vrms, so full scale can't reach it. Listening check with ATH-M40x-class headphones: loud enough with margin |

## Fault-finding hints

| Symptom | Look at first |
|---|---|
| Supply hits current limit at power-up | Stage 1.1 short; reversed C18; U1/U2 rotated; U2 pins bridged |
| No `+5V` with correct polarity | Q1 orientation/footprint; Q1 and Q4 swapped; J3 pin order / cable |
| `VREF` not ≈ 2.5 V | R7/R8 values, C7 leakage/short |
| Input works only intermittently | J1 tip-normal switch, C3/R1 joints |
| No headphone output | U2.13 (EN) and U2.14 (VDD) at `+5V`; U2 side pads and exposed pad joints |
| HPVDD/HPVSS ≈ 0 V with EN high | C35 (flying cap), C34/C36, U2 pins 8/9/11/12 |
| DC or hum on J5 outputs | U2 SGND (pin 15) / exposed pad to GND; INL+/INR+ (pins 2/3) grounded |
| Output only on one HP channel | That channel's C12/C13, U2 pin 1/4 (input) or 16/5 (output) joints, J5 tip/ring pins |
| Speaker output (J2/J8) dead | R28, C24 (shorted?), R4; `AUDIO_OUT_2` from firmware |
| AUX input dead or quiet | J9 pins, R40/R41, R38 (4.7k fitted instead of 100k?), C31 shorted; `AUDIO_IN_2` trace to A1.17 |
| `HP_DETECT` stuck or inverted | J5 pins 5/6 mapping, TP11 → A1.34 trace, firmware pull-up on pin 34 (PG9) |
| Speaker amp never unmutes / never mutes | Q4 orientation or swapped with Q1; R37; `SPK_MUTE` polarity on the power board |
| Daisy won't boot | Socket orientation / offset; `3V3_D` and `+5V` shorted at A1.38/A1.39 |
| Daisy partly alive with J3 off | Back-powering through J3.5–J3.7: check R32/R35/R33 values and the power board's divider |

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
| 3C Speaker / line send | | J2 = ____ Vpp |
| 3D AUX input | | Tip+ring = ____ Vpp |
| 4 Power-up with Daisy | | I = ____ mA, 3V3_A = ____ V, 3V3_D = ____ V, back-power I = ____ mA |
| 5 Firmware functional | | SPK_MUTE low = ____ V, AUX peak = ____ |
| 6 Soak & robustness | | |
| 7 Pops, hiss and mute | | SPK_EN delay = ____ s, mute time = ____ ms, HP max = ____ Vrms |

Rework performed:

Open issues:
