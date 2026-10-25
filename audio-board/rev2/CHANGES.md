# Rev 2 changes

Changes from rev 1, with the reason for each. Keep this list current as the schematic changes.

## Done in the schematic

### Pots removed, input level set in firmware
- **Removed:** RV1 (input level), RV2 (volume), RV3 (tone), C10, C11.
- **Added:** R17 (1M) from the C3 node to VREF. It keeps the 1M guitar input load that RV1 provided.
  C3 now feeds R1 and U1A directly, so the input buffer runs at unity gain.
- **Why:** with RV1 at mid travel, U1A saw about 250 kΩ of source impedance, which added noise and an ~80 kHz pole
  (see `studies/signal-path-response`). Tone and input trim move to the touchscreen.

### Master volume encoder (added, then removed)
- **Removed (2026-10-25):** SW1 (EC11E rotary encoder with push switch), R18–R23 and C19–C21. The reference designators are
  left unused rather than renumbered.
- **Daisy pins:** pins 22, 23 and 24 (ADC_0–ADC_2) are now unused and only go to the J7 breakout, labelled `A0`, `A1`, `A2`
  (were `ENC_A`, `ENC_B`, `ENC_SW`, and before that VOLUME_POT, TONE_POT, A2).
- **Why:** the master volume encoder, if there is one, goes on the touchscreen / ESP32 side, which sends volume changes over the display UART.
  No volume control remains on this board.

### Output mute watchdog
- **Added:** U3 (SN74LVC1G123 retriggerable one-shot), R24–R26, C22, C23 and TP10 (`TP_WD_OK`).
- **How it works:** the firmware toggles `AUDIO_ALIVE` (Daisy pin 33, was D26) once per audio callback.
  Each rising edge retriggers U3, whose Q output (`WD_OK`) stays high. `WD_OK` drives U2's active-high EN pin directly
  and Q3's gate for the speaker mute (see the power board connector). If the edges stop for ~10 ms (R24 × C22), `WD_OK` falls
  and both amps mute.
- **Also muted when:** the Daisy is absent, booting, in DFU, or hung. R25 holds the trigger input low and R26 holds `WD_OK` low.
- **Superseded:** this section first used Q2 (2N7002) and R27 to drive the TPA6111A2's active-high SHUTDOWN pin through `AMP_SHUTDOWN`.
  The TPA6132A2 swap (below) removed them.
- **Why:** a hung Daisy can loop its last audio buffer at full level. Mute must not depend on the software that has failed.

### Speaker feed from AUDIO_OUT_2, headphone detect in firmware
- **Removed:** the tip-switch line out. J5's TN contact no longer drives `LINE_SEND`, and TN and RN are both no-connects.
  In rev 1, plugging in headphones lifted the tip spring and muted J2 mechanically.
- **Added:** a speaker / line-send stage driven by the Daisy's second output.
  The path is `AUDIO_OUT_2` → R28/C24 (3.3k/1nF, ~48 kHz low-pass, same as the headphone path) → C25/R29 (AC coupling, biased to VREF)
  → U1C buffer → C26 (10µF) → `LINE_SEND` → R3 → J2. J2 and R3/R4 are unchanged and remain the feed to the speaker amp.
- **Changed:** U1 is now a TLV9064 quad (SOIC-14) instead of the TLV9062 dual, using the same TL07x-style symbol.
  Units A and B are unchanged. Unit C is the speaker buffer. Unit D is the AUX input buffer (see below).
  Power moves to pin 4 (+5V) and pin 11 (GND).
- **Added:** `HP_DETECT` on Daisy pin 34 (was D27, also renamed on J7), with a 10k pull-up, 1k series resistor (R30, R31) and 100nF (C27).
  TP11 sits on the switch side (`HP_DETECT_SW`).
- **Changed:** J5 is now a Same Sky **SJ3-35063AG** (3.5 mm stereo, through hole; [datasheet](https://www.sameskydevices.com/product/resource/sj3-3506x.pdf)).
  Pins 1/2/3 are sleeve/ring/tip on GND/HP_R/HP_L. Pins 5 and 6 are an isolated normally-open switch that closes when a plug
  is inserted: pin 5 goes to GND and pin 6 to `HP_DETECT_SW`. Pin 4 isn't fitted on this variant.
  The symbol is new in `seed3-carrier.kicad_sym`, and the footprint is new in
  `Seed3_Carrier.pretty/Jack_3.5mm_SameSky_SJ3-35063AG_Horizontal.kicad_mod`, drawn from the datasheet's recommended PCB layout.
  The jack face sits at the board edge (X = −2.4 mm from pin 1), with the nose overhanging.
  DigiKey had 398 in stock when chosen.
- **Why:** muting in firmware means the speaker amp can be shut down while headphones are in (saving battery), mute and unmute can ramp
  without clicks, and the speaker and headphones get independent levels.

### Power board connector (J3 → 8-pin JST-XH)
- **Changed:** J3 is now an 8-pin JST-XH (B8B-XH-A, vertical) instead of the 2-pin 5 V header. It carries power and the control
  signals to the separate power board, which handles the battery, the power button and the speaker amp. J3 moved to a new
  "Power board connector" block at the bottom of the sheet. Q1 still provides reverse-polarity protection, now on the `5V_IN` net.

  | Pin | Net | Direction | Daisy pin | Use |
  |---|---|---|---|---|
  | 1, 2 | `5V_IN` | Power board → carrier | 39 (VIN) via Q1 | 5 V supply, two pins share the current |
  | 3, 4 | GND | — | 20 / 40 | Ground, two pins |
  | 5 | `BATT_SENSE_CONN` | Power board → carrier | 25 (`BATT_SENSE`, was A3) | Battery voltage scaled to ≤ 3.3 V. R32 (10k) and C28 (100nF) filter it into the ADC |
  | 6 | `PWR_BTN_CONN` | Power board → carrier | 26 (`PWR_BTN`, was A4) | Low while the power button is pressed. R36 (10k) pull-up to 3V3_D, R35 (1k) series, C29 (100nF) |
  | 7 | `PWR_HOLD_CONN` | Carrier → power board | 27 (`PWR_HOLD`, was A5) | High keeps the power on. R33 (1k) series, R34 (100k) pull-down so it is low while the Daisy is absent or booting |
  | 8 | `SPK_MUTE` | Carrier → power board | 28 (`SPK_EN`, was A6) | Open drain speaker-amp mute (see below) |

- **Added:** `SPK_MUTE` gate. Q3 and Q4 (2N7002) are in series from `SPK_MUTE` to GND. Q3's gate is `WD_OK` (U3 Q, the watchdog
  signal that also enables U2). Q4's gate is `SPK_EN` with R37 (100k) pull-down. `SPK_MUTE` is pulled low (speaker on) only
  when the watchdog is running **and** the firmware enables the speaker. The headphone amp (U2) follows the watchdog only.
- **Added:** FB1 (ferrite bead, 1206) and C30 (47µF, 1210) between `+5V` and J4 pin 4, which is now `DISPLAY_5V`.
  They keep the display's current pulses (ESP32 Wi-Fi, backlight PWM) off the rail that feeds the analog circuits.
- **Power board requirements:** nothing above 3.3 V on pins 5–7. Switch the `BATT_SENSE` divider off with the 5 V output
  (or give it ≥ 100k source impedance), so it doesn't drain the battery or feed an unpowered Daisy while the amp is off. Pull `SPK_MUTE` up on the amp side so the amp is muted when this
  board is unpowered or unplugged. Keep the power on for about 2 s after a button press until the Daisy raises `PWR_HOLD`, and force
  the power off when the button is held for about 5 s. The power button itself is panel mounted and wired to the power board.
- **Why:** one connector for power and signals, a clean firmware-controlled shutdown, battery level on the display, and a speaker
  mute that is independent of the headphone amp.

### Internal line out to the speaker amp (J8)
- **Added:** J8, a 2-pin JST-XH (B2B-XH-A, vertical). Pin 1 is `LINE_OUT` (J2's tip, after R3) and pin 2 is GND.
  It feeds the speaker amp, which sits on the power board (or an off-the-shelf class D module while prototyping).
  The net after R3 is now named `LINE_OUT`.
- **Kept:** J2 (1/4") as an external line out on the same net, for testing with an outside amp before the power board is ready.
- **Why:** a keyed internal header instead of a 1/4" cable between boards. Sharing R3 keeps the cable capacitance off U1C.
  Audio ground has its own pin, separate from J3's supply current. Use a short twisted pair routed away from the guitar input and speaker wires.
- **Speaker wiring** is on the power board, not here: the cone's spade tabs (6.3 mm / 4.8 mm) take crimped quick-disconnects.
  Most class D amps have a bridged output, so neither speaker wire may be grounded.

### AUX input (J9 → AUDIO_IN_2)
- **Added:** J9, a second SJ3-35063AG (3.5 mm TRS, same part and footprint as J5) for backing tracks from a phone or laptop.
  Its detect switch (pins 5 and 6) is not connected.
- **Path:** tip and ring → R40/R41 (10k each, passive stereo-to-mono sum, −6 dB) → summing node with R38 (47k to GND) and C31 (1nF, ~32 kHz RF filter)
  → C32 (1µF) → R39 (100k to VREF, ~1.6 Hz high-pass) → R42 (1k) → U1D follower → `AUDIO_IN_2` (Daisy pin 17).
  It mirrors the guitar input: biased at VREF, unity-gain buffer, Daisy input DC-coupled from a low impedance.
- **Changed:** U1D is no longer parked as a VREF follower. Its old wiring is removed, and the unit moved next to the AUX parts.
  The speaker section is now "Speaker / line send, AUX input".
- **Why:** the backing track bypasses NAM. The firmware mixes `AUDIO_IN_2` in after the amp model, to both the speaker and headphone outputs.
  R38 holds the summing node near GND when nothing is plugged in, so an empty jack stays quiet. It also gives the source's own coupling caps a DC return.
  The −6 dB from summing gives headroom for hot laptop outputs (up to 2 Vrms). The firmware can add gain for quiet phones.

### Design review fixes (2026-10-24)
**Technical**
- **R32 1k → 10k.** While the amp is off, the power board's battery divider can still hold `BATT_SENSE_CONN` near 3.3 V.
  Through 1k, that pushed ~3 mA into the unpowered Daisy's pin protection diodes and back-powered its 3.3 V rail. 10k limits it to ~0.3 mA.
  With C28 the filter corner is ~160 Hz, still far above battery changes. The power board should also switch the divider off.
- **R13/R14 100 Ω → 1k.** In rev 1 these loaded the headphone outputs for the J5 tip-switch line out. That line out is gone,
  so they only needed to bleed C14/C15 to GND (pop suppression). At 100 Ω they wasted ~10 mW per channel at full level and loaded U2 alongside 32 Ω headphones.
  (Later removed entirely by the TPA6132A2 swap.)
- **Added R43/R44 (1k)** in series with the display UART. J4 now carries `UART_TX_CONN`/`UART_RX_CONN`, and the Daisy side keeps
  `DISPLAY_UART_TX`/`DISPLAY_UART_RX`. They limit current if the cable is miswired (TX to TX) or hot-plugged, and add a little ESD margin.
  1k with ~50 pF of cable is ~50 ns, fine up to ~2 Mbaud.

**Style**
- Added voltage ratings to the bulk ceramics: C7 `47uF 10V` (VREF), C9 and C26 `10uF 16V`, C30 `47uF 16V` (5 V rails, derated for DC bias).
- TP9 renamed `TP_5V` (it is the main +5 V rail, not an amp supply).
- "Audio output" heading renamed "Headphone buffer", since the speaker path is its own section.
- Notes updated: Q1's note names `5V_IN`/J3, "Op-amp power rails" capitalisation, and the watchdog note names what each mute does (now: U2 shuts down via EN, Q3 mutes the speaker amp).
- Title block date updated to 2026-10-24. C9's labels moved below the GND wire so they don't overlap the PWR_FLAG symbols.

### Headphone amp: TPA6111A2 → TPA6132A2 (DirectPath)
- **Changed:** U2 is now a TI **TPA6132A2RTE** ([datasheet](https://www.ti.com/lit/ds/symlink/tpa6132a2.pdf), WQFN-16 3 × 3 mm with exposed pad,
  footprint `WQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm_ThermalVias`). An internal charge pump gives it a negative rail,
  so its outputs sit at 0 V and drive J5 directly.
- **Removed:** C14/C15 (470µF output caps), R13–R16, R9–R12 (gain resistors, now internal), C16 (bypass), Q2 and R27.
- **Added:** C33 (2.2µF, VDD decoupling), C34 (2.2µF, HPVDD), C35 (1µF, charge-pump flying cap), C36 (2.2µF, HPVSS), all 0805 X5R or better.
  HPVDD and HPVSS are generated inside U2. They get caps only (and PWR_FLAGs for ERC), never an external supply.
- **Wiring:** single-ended inputs per the datasheet (INL+/INR+ to GND). `HP_SOURCE` → C12/C13 (4.7µF, kept) → INL−/INR−.
  With the 19.8k internal input resistance that is a 1.7 Hz high-pass, and there is no output cap, so bass is flat down to a few Hz.
  Gain is 0 dB (G0 to +5V, G1 to GND), inverting as before. EN (active high) is `WD_OK` directly.
- **New symbol:** `seed3-carrier:TPA6132A2RTE` in `seed3-carrier.kicad_sym`. It is the stock KiCad symbol with the pins rearranged:
  grounded pins on the bottom, charge-pump and output pins on the right, supplies on top.
- **Layout:** route SGND (pin 15) straight to the J5 sleeve pin, as the datasheet requires, and keep C35/C36 tight to pins 8, 9 and 11.
  Solder the exposed pad (tied to GND). The QFN needs hot air or a stencil and a hot plate rather than an iron.
- **Why:** removes the two largest parts in the headphone section, flattens the bass, and adds built-in click-and-pop suppression.
  Its maximum output is a fixed ~1.1 Vrms (22 mW into 32 Ω) regardless of supply, which also limits how loud the headphones can get.

## Firmware changes these require
- Take volume and mute from the display over the UART instead of the volume/tone ADCs. Ramp volume changes.
- Toggle `AUDIO_ALIVE` (pin 33) once per audio callback. Initialise it as a low output.
- Send the speaker mix to output 2 and headphones to output 1. Read `HP_DETECT` (pin 34):
  **low = headphones in** (J5's normally-open switch closes to GND). Debounce it in firmware. Ramp the speaker down and shut its amp off when headphones are in.
- Add an output clamp or limiter and NaN/Inf guard at the end of the chain. Enable the STM32 internal watchdog.
- Drive `PWR_HOLD` (pin 27) high early in boot. On a `PWR_BTN` (pin 26, active low) press while running, fade out, mute,
  save settings, then drive `PWR_HOLD` low.
- Drive `SPK_EN` (pin 28) high to enable the speaker amp, low when headphones are in. The headphone amp needs no pin of its own:
  it runs whenever the watchdog sees `AUDIO_ALIVE` pulses.
- Read `BATT_SENSE` (pin 25, ADC) and send the battery level to the display. Shut down cleanly when it gets low.
- Read `AUDIO_IN_2` (the AUX input, mono) and mix it in after the NAM model and cabinet EQ, with its own level control from the display.
  It goes to both outputs, so backing tracks play through the speaker and the headphones.

## Open items
- **Check the J5 footprint** against a physical part (or a 1:1 print) before ordering boards. It was drawn by hand from the datasheet.
- **Confirm the U3 timeout:** check tw ≈ K·Rext·Cext against the SN74LVC1G123 datasheet, then measure on the board.
  The target is ~10 ms, comfortably longer than the 2 ms edge period.
- **Speaker amp mute polarity:** `SPK_MUTE` floats (pulled up = muted) or is pulled low (= playing). Check that the chosen amp's
  mute/shutdown pin matches, or invert it on the power board.
- **`BATT_SENSE` divider:** the power board sets the ratio. Record it here so the firmware can convert the reading to volts.
- **Display current:** check the display's datasheet. If it draws well over 1 A, feed it from the power board instead of J4.
- **J3 orientation:** vertical (B8B-XH-A) is drawn. Switch to the right-angle S8B-XH-A if the cable has to leave along the board.
- **2N7002 gate drive:** Q3 and Q4 are driven from 3.3 V logic. That should be enough for the small pull-up current on `SPK_MUTE`, but check it on the board.
- **Headphone level:** U2's gain is fixed at 0 dB by G0/G1. If `HP_SOURCE` at full scale clips U2's ~1.1 Vrms output, tie G0 to GND for −6 dB
  (or limit it in firmware).
- **AUX input level:** measure a phone and a laptop at full volume through J9 and check that the Daisy input doesn't clip.
  If it does, raise R40/R41.
- **Polarity:** U2 inverts the signal. Decide whether the firmware negates the output.
- **TEST_PLAN check 3B.4:** the low-end corner is ≈ 12.6 Hz, not 9 Hz.
- **Layout:** fresh board on the stackup below. Set it in Board Setup → Board Stackup before placing parts.

## Layout decisions

### Stackup (2026-10-24, revised 2026-10-25)
JLCPCB standard 4-layer, 1.6 mm (JLC04161H-7628). Outer copper 1 oz, inner 0.5 oz. Check the dielectric thicknesses
on JLC's stackup page when ordering.

This is the "ground in the middle" stackup that Bogatin recommends as the default for 4-layer boards. Page numbers below
refer to Eric Bogatin, *Bogatin's Practical Guide to Prototype Breadboard and PCB Design* (Artech House, 2021).

| Layer | Use | To next layer |
|---|---|---|
| L1 (top) | Parts, most signal routing, `+5V`, `DISPLAY_5V` and `3V3_A` as wide traces (≥ 1 mm) | 0.21 mm prepreg |
| L2 | Solid GND. No traces, no cuts | ~1.07 mm core |
| L3 | Solid GND. No traces, no cuts | 0.21 mm prepreg |
| L4 (bottom) | Remaining signals, power traces that don't fit on L1 | — |

- **Why ground in the middle:** both signal layers sit 0.21 mm from a solid GND plane. All routing can be seen and probed
  from the outside, and the symmetrical build won't warp (p. 480). The JLC build above is the book's own example (p. 475, Fig. 23.3).
- **Why no power plane:** a power plane is only needed above about 20 A (pp. 466, 479). The board draws about 1 A at most,
  and a 20 mil (0.5 mm) trace carries 3 A (p. 466). `+5V` also feeds the display, which pulls current pulses (ESP32 Wi-Fi,
  backlight PWM). A full power plane would spread that rail under the guitar input and the analog circuits.
- **Why power is on L1/L4, not L3:** with L2 and L3 both GND, a signal that goes from L1 to L4 can return through a via
  between the two planes. A power layer in the middle would block that path (pp. 467, 479–480). Keep the power traces
  short and wide between the decoupling capacitors and the IC pins, where low inductance matters (p. 466).
- **Return vias:** next to every signal via that goes from L1 to L4, place a GND via that ties L2 to L3 (pp. 479, 483).
  Do the same where a power trace changes layers (p. 467). Keep signal-via clearance holes from merging into slots
  in L2/L3 (p. 478).
- **No copper pour on L1/L4:** a pour on a signal layer adds little, and a poorly stitched one increases crosstalk. It also
  makes the board harder to debug and can leave orphaned copper islands (pp. 461–464). The return path is L2/L3.
  Exceptions: the TPA6132A2 exposed pad and any local GND area a part needs, each stitched to L2/L3 with vias.
  If JLC wants copper balanced on the outer layers for plating, ask them to add thieving pads (p. 464).
- **One GND net, no split.** A split only helps with sub-millivolt noise below 100 kHz when more than 10 A of low-frequency
  current flows in the ground plane (p. 465). The board stays well under that. Separate analog and digital areas by placement.
  At audio frequencies return current takes the lowest-resistance path, so placement matters more than the stackup:
  - Put J3 (power in) and J4 (display) close together, so the display's return current doesn't pass under U1, J1 or J9.
  - Route U2's SGND (pin 15) straight to J5's sleeve, and put vias under U2's exposed pad down to L2.
- **Why 1.6 mm:** the 1/4" jacks, the SJ3 jacks and the Daisy sockets take force at every plug-in. It is also the cheapest thickness.
- **No controlled impedance.** `USB_D+`/`USB_D−` only reach the J6/J7 breakout, and the Daisy module handles USB itself.
  The existing rules (0.6/0.3 mm vias, 0.2 mm track and clearance) are within JLC's 4-layer limits.
