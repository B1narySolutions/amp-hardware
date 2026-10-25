# Seed3 Carrier — Post-Assembly Test Plan

Bring-up and acceptance tests for one hand-assembled board built from the
`fabrication/2026-09-15-e7ddc60` package and `fabrication/seed3-carrier-BOM.csv`.

Work through the stages in order. Each stage assumes the one before it passed,
so a failure stays localized: unpowered checks first, then the board powered
**without** the Daisy, and only then with the Daisy fitted. Record results in
the log at the end (one copy per board serial).

## Circuit summary (what is being tested)

| Block | Parts | Function |
|---|---|---|
| Power input | J3, Q1 (AO3401A) | 5 V header; P-FET reverse-polarity protection onto `+5V` |
| 5 V decoupling | C8, C9, C17, C18 | Bulk/HF decoupling on `+5V` |
| Mid-rail reference | R7, R8 (10k/10k), C7 | `VREF` ≈ 2.5 V, probe at **TP5** |
| Guitar input | J1, C1, C3, RV1 (1M), R1, R5, U1A | ¼" input, tip shorted to GND when unplugged; level pot; buffer → Daisy `AUDIO_IN_1` |
| Output buffer | R2, C2, C5, R6, U1B | Daisy `AUDIO_OUT_1` → ~48 kHz RC low-pass → AC-couple → buffer → `HP_SOURCE` |
| Headphone amp | U2 (TPA6111A2), C12/C13, R9–R12, C16, C14/C15, R13–R16 | Unity-gain inverting stereo amp (mono source on both channels) → J5 |
| Line out | J5 tip-normal, R3, R4, J2 | Left HP signal routed to J2 **only when no plug is in J5** |
| Controls | RV2 (volume), RV3 (tone), C10, C11 | 3V3_A dividers into Daisy ADC0 / ADC1 |
| Display | J4 | GND / USART1 TX / USART1 RX / +5V |
| Breakout | J6, J7 | Female sockets mirroring the Daisy pins (`J6.3` = AUDIO_OUT_1, `J6.5` = AUDIO_IN_1, `J6.1`/`J7.20` = GND, `J7.19` = +5V) |
| Daisy | A1 + two 1×20 sockets | Plug-in module |

**SOIC-8 pinouts used below**

- U1 TLV9062: 1 OUTA, 2 INA−, 3 INA+, 4 V−, 5 INB+, 6 INB−, 7 OUTB, 8 V+
- U2 TPA6111A2: 1 VO1, 2 IN1−, 3 BYPASS, 4 GND, 5 SHUTDOWN, 6 IN2−, 7 VO2, 8 VDD

## Equipment

- Current-limited bench supply (0–6 V), DMM, oscilloscope (≥ 20 MHz)
- Signal generator or audio interface (sine 20 Hz – 20 kHz, ≥ 2 Vpp); a phone/laptop
  headphone output works for listening tests
- ¼" mono cable, 3.5 mm stereo cable/headphones (≈ 32 Ω), a 32 Ω dummy load
- USB cable for the Daisy, USB-serial adapter (3.3 V) for J4
- Magnifier/microscope, flux, isopropyl alcohol

## Stage 0 — Visual and mechanical inspection (unpowered, no Daisy)

| # | Check | Pass criteria |
|---|---|---|
| 0.1 | Clean flux residue; inspect every joint under magnification | No bridges (esp. U1/U2 SOIC pins, Q1), no cold/dull joints, no solder balls |
| 0.2 | IC orientation | U1 and U2 pin-1 dot matches silkscreen; U1 = TLV9062, U2 = TPA6111A2 (not swapped) |
| 0.3 | Q1 orientation and marking | SOT-23 seated on correct pads, marking matches AO3401A |
| 0.4 | Electrolytic polarity | C14, C15 `+` toward U2 outputs; C18 `+` to `+5V` |
| 0.5 | Passive values vs BOM | Spot-check R9–R12 (20k), R15/R16 (4.7 Ω), R5 (10M), R7/R8 (10k); C7/C12/C13 are the 1210 parts |
| 0.6 | Pot mounting tabs | RV1–RV3 tabs soldered in the 3 mm plated holes; bodies flat, shafts square (fit was untested before this build — note any interference) |
| 0.7 | Daisy sockets | Both A1 1×20 sockets flush and parallel; Daisy inserts with moderate force, all pins engaged, USB connector on the correct end |
| 0.8 | J6/J7 sockets, J3/J4 headers | Flush, straight, correct side of board |
| 0.9 | Jacks J1, J2, J5 | Fully seated, flush to board edge, plugs insert/eject cleanly |
| 0.10 | Enclosure fit (if available) | Jacks, pots, USB line up with panel holes |

## Stage 1 — Unpowered resistance checks (no Daisy)

Measure with the DMM; let capacitors charge before reading. Probe on IC pins or
test pads, not on connector shells.

| # | Measure | Expect | Fail indicates |
|---|---|---|---|
| 1.1 | `+5V` (TP9) → GND | Rises to > 1 kΩ (cap charging), not < 50 Ω | Short on 5 V rail — check C8/C9/C17/C18, U1.8, U2.8 |
| 1.2 | J3.1 → GND | Open / high (Q1 off, no supply) | Q1 shorted or bridged |
| 1.3 | `VREF` (TP5) → GND | ≈ 5 kΩ–10 kΩ (R7 in parallel with R8 via 5 V loads) | R7/R8 wrong or open, C7 shorted |
| 1.4 | U2.5 (SHUTDOWN) → GND | 0 Ω | SHUTDOWN not grounded |
| 1.5 | J1 tip → GND, no plug | ≈ 0 Ω (tip-normal shorts to GND) | J1 switch / footprint issue |
| 1.6 | J1 tip → GND, plug inserted (other end open) | Open | Plug not lifting the switch |
| 1.7 | J5 tip → J2 tip, no plug in J5 | ≈ 4.7 Ω + 100 Ω ≈ 105 Ω (R15 + R3) | Tip-normal or R3 open |
| 1.8 | J5 tip → J2 tip, plug in J5 | Open / high | J5 switch not breaking |
| 1.9 | J2 tip → GND | ≈ 100 kΩ (R4) in parallel with the path above | R4 missing |
| 1.10 | J5 tip → GND and J5 ring → GND | ≈ 105 Ω each (R15+R13, R16+R14) | Output network fault |
| 1.11 | RV2 / RV3 wiper → GND, sweep pot | 0 → ~10 kΩ smoothly | Pot or wiper connection |
| 1.12 | J6/J7 adjacent pins | Spot-check no shorts between neighbouring pins, esp. J7.19 (+5V) ↔ J7.18 (3V3_D) and J7.20 (GND) | Socket bridge — **5 V into 3V3_D would damage the Daisy** |

## Stage 2 — First power-up, Daisy **removed**

Supply on J3: start at 0 V, current limit **50 mA**, ramp to 5.0 V.

| # | Check | Expect |
|---|---|---|
| 2.1 | Supply current at 5.0 V | A few mA (op-amp + headphone amp quiescent + 0.25 mA divider); < 10 mA. Stop if it hits the limit |
| 2.2 | `+5V` at TP9 | 4.9–5.0 V (Q1 drop is tens of mV) |
| 2.3 | `VREF` at TP5 | 2.45–2.55 V |
| 2.4 | U1.1 (OUTA) and U1.7 (OUTB) | ≈ 2.5 V (both buffers sit at VREF) |
| 2.5 | U1.3, U1.5 | ≈ 2.5 V |
| 2.6 | U2.3 (BYPASS) | ≈ 2.5 V |
| 2.7 | U2.1 (VO1), U2.7 (VO2) | ≈ 2.5 V. If ≈ 0 V while SHUTDOWN is low, the amp is in shutdown — check SHUTDOWN polarity against the datasheet |
| 2.8 | J5 tip, J5 ring, J2 tip (DC) | ≈ 0 V (blocked by C14/C15) |
| 2.9 | J4.4 and J7.19 | +5 V; J4.1 and J7.20 are GND |
| 2.10 | Thermal | Nothing warm to the touch after 2 min |
| 2.11 | **Reverse polarity** — swap leads on J3, limit 50 mA, apply 5 V | ≈ 0 mA drawn, `+5V` stays at 0 V. Restore correct polarity and repeat 2.2 to confirm nothing was damaged |

## Stage 3 — Analog paths, Daisy **removed**

The J6 breakout reaches the Daisy-side nets with the module out, so the analog
stages can be tested on their own. Supply 5.0 V, limit 50 mA.

**3A. Input buffer (J1 → AUDIO_IN_1)**

1. Inject 1 kHz, 1 Vpp sine into J1 (tip/sleeve). Scope on `J6.5` (AUDIO_IN_1) or U1.1.
2. | # | Check | Expect |
   |---|---|---|
   | 3A.1 | RV1 fully up | 1 kHz sine riding on ≈ 2.5 V DC, amplitude ≈ input |
   | 3A.2 | Sweep RV1 | Amplitude goes smoothly from ≈ 0 to full, no crackle/dropouts |
   | 3A.3 | Unplug J1 | Output goes quiet (tip shorted to GND) |
   | 3A.4 | Raise amplitude until clipping | Clips symmetrically near the rails; record the input level |
   | 3A.5 | Sweep 20 Hz – 20 kHz | Flat within about ±1 dB |

**3B. Output buffer + headphone amp (AUDIO_OUT_1 → J5 / J2)**

1. Inject 1 kHz, 1 Vpp sine into `J6.3` (AUDIO_OUT_1), ground at `J6.1`.
   Load J5 with a 32 Ω dummy load (or headphones at low level).
2. | # | Check | Expect |
   |---|---|---|
   | 3B.1 | U1.7 (HP_SOURCE) | ≈ 1 Vpp on 2.5 V DC |
   | 3B.2 | U2.1 / U2.7 | ≈ 1 Vpp, inverted relative to U1.7, on 2.5 V DC (gain −1) |
   | 3B.3 | J5 tip and ring | Same signal, no DC, both channels equal within ~0.5 dB |
   | 3B.4 | Frequency sweep 20 Hz – 20 kHz into 32 Ω | Flat in the audio band; low end corner ≈ 9 Hz (470 µF into ~37 Ω); falls off above ≈ 48 kHz (R2/C2) |
   | 3B.5 | Listening test with headphones | Clean tone, no hum/hiss above expected level, no oscillation (check scope for HF ringing) |
   | 3B.6 | Power-on/off with headphones in | Note any pop level |

**3C. Line out switching (J5 tip-normal → J2)**

| # | Check | Expect |
|---|---|---|
| 3C.1 | No plug in J5, scope on J2 tip | Same 1 kHz signal as J5 tip (left channel), ≈ no DC |
| 3C.2 | Insert a plug into J5 | J2 goes silent (R4 holds it at 0 V) |
| 3C.3 | Remove plug | J2 signal returns |

Remove the injected signal before going on.

## Stage 4 — Power-up with Daisy fitted

1. **Power off.** Insert the Daisy, checking orientation against the silkscreen
   and that no pins are offset by one position.
2. Supply 5.0 V on J3 with the limit set to **300 mA**. Keep USB **unplugged** for this stage.

| # | Check | Expect |
|---|---|---|
| 4.1 | Supply current | Within the Daisy's normal draw (roughly 100–200 mA depending on firmware); record value |
| 4.2 | `+5V` (TP9) | ≥ 4.85 V under load |
| 4.3 | `3V3_A` (J7.1) and `3V3_D` (J7.18) | 3.3 V ± 5 % (from the Daisy regulators) |
| 4.4 | `VREF`, U1/U2 biases | Same as Stage 2 |
| 4.5 | Daisy LED / existing firmware | Boots normally |
| 4.6 | Thermal after 5 min | Nothing hot; U2 and Q1 at most warm |

Then plug in USB with J3 still powered and confirm current/voltages don't jump
unexpectedly. Check the Daisy Seed docs for your revision's VIN/USB power-path
before relying on both sources together.

## Stage 5 — Functional tests with test firmware

Flash a small bring-up program (libDaisy or Arduino/DaisyDuino) over USB that:

- passes audio input 1 straight to output 1 (and logs peak level),
- prints ADC0 (volume) and ADC1 (tone) readings over USB serial,
- echoes bytes on USART1 (J4) and sends a heartbeat string every second.

| # | Check | Expect |
|---|---|---|
| 5.1 | USB enumeration / DFU flashing | Flashes and enumerates; confirms the USB D+/D− sockets connect |
| 5.2 | Audio passthrough: 1 kHz into J1 → J5 headphones | Clean tone; RV1 changes level |
| 5.3 | Passthrough: J1 → J2 (no plug in J5) | Signal present at J2 |
| 5.4 | Noise floor: J1 unplugged, volume max | Only low-level hiss; no hum, whine, or digital noise from USB/codec; record level on the scope |
| 5.5 | Guitar test | Real guitar into J1, headphones on J5: clean signal, no clipping at normal pick strength with RV1 at mid |
| 5.6 | RV2 sweep (ADC0) | Readings go ~0 → full scale monotonically, steady when still (filtered by C10) |
| 5.7 | RV3 sweep (ADC1) | Same as 5.6 (C11) |
| 5.8 | UART on J4 with a 3.3 V USB-serial adapter (adapter TX → J4.3, RX → J4.2, GND → J4.1) | Heartbeat received; echo works. **Before connecting the real display**, confirm its TX idles at ≤ 3.3 V |
| 5.9 | Display on J4 | Powers from J4.4 (+5 V), shows data from the Daisy |
| 5.10 | Breakout spot-check | Toggle a few Daisy GPIOs (e.g. D7–D10) in firmware and confirm they appear on the matching J6 pins |

## Stage 6 — Soak and robustness

| # | Check | Expect |
|---|---|---|
| 6.1 | Run passthrough with audio for 30 min | No dropouts, resets, or drift in VREF / supply current |
| 6.2 | Plug/unplug J1, J2, J5 repeatedly while running | No resets, no lasting noise, jacks stay mechanically solid |
| 6.3 | Turn every pot end-to-end 20× | No intermittent signal, tabs and solder joints hold |
| 6.4 | Light flex/tap test on the board and Daisy | No crackle or resets (would point to a cracked joint or loose socket pin) |

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
| Supply hits current limit at power-up | Stage 1.1 short; reversed C18; U1/U2 rotated |
| No `+5V` with correct polarity | Q1 orientation/footprint; J3 pin order |
| `VREF` not ≈ 2.5 V | R7/R8 values, C7 leakage/short |
| Input works only intermittently | J1 tip-normal switch, RV1 tab/wiper joints |
| No headphone output, VO1/VO2 at 0 V | U2 SHUTDOWN (pin 5) level/polarity, U2.8 supply |
| Output only on one HP channel | That channel's C12/C13, R9–R12, C14/C15, R15/R16 |
| Line out always or never active | J5 tip-normal pin mapping (J5.TN) |
| Pots read noisy/jumpy | C10/C11, RV2/RV3 tab joints, 3V3_A |
| Daisy won't boot | Socket orientation / offset; 3V3 pins shorted at J7.18/J7.19 |

## Results log

Board serial / ID: __________  Assembled by: __________  Date: __________

Tested by: __________  Firmware commit: __________

| Stage | Result (Pass/Fail) | Measured values / notes |
|---|---|---|
| 0 Visual & mechanical | | |
| 1 Unpowered resistance | | |
| 2 Power-up, no Daisy | | I = ____ mA, +5V = ____ V, VREF = ____ V |
| 2.11 Reverse polarity | | |
| 3A Input buffer | | Clip level = ____ Vpp |
| 3B Output / HP amp | | L = ____ Vpp, R = ____ Vpp into 32 Ω |
| 3C Line out switching | | |
| 4 Power-up with Daisy | | I = ____ mA, 3V3_A = ____ V, 3V3_D = ____ V |
| 5 Firmware functional | | |
| 6 Soak & robustness | | |
| 7 Pops, hiss and mute | | SPK_EN delay = ____ s, mute time = ____ ms, HP max = ____ Vrms |

Rework performed:

Open issues:
