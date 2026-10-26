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
- **Daisy pins:** pins 22, 23 and 24 (ADC_0–ADC_2) are now unused and marked no-connect (they went to the J7 breakout, labelled `A0`, `A1`, `A2`, until J6/J7 were removed)
  (were `ENC_A`, `ENC_B`, `ENC_SW`, and before that VOLUME_POT, TONE_POT, A2).
- **Why:** the master volume encoder, if there is one, goes on the touchscreen / ESP32 side, which sends volume changes over the display UART.
  No volume control remains on this board.

### Output mute (STM32 internal watchdog)
- **Now:** `HP_EN` (Daisy pin 33, was `AUDIO_ALIVE`, and before that D26) drives U2's active-high EN pin directly.
  R26 (100k) pulls it low. The speaker mute is Q4 alone (see the power board connector).
- **How it works:** the firmware feeds the STM32's independent watchdog (IWDG) only from the audio callback. The IWDG runs on its
  own clock, so if the callback stops (hung firmware, stalled DMA, fault handler), it resets the STM32. During a reset, and while the
  Daisy is absent, booting or in DFU, its pins float: R26 holds `HP_EN` low (U2 off) and R37 holds `SPK_EN` low (speaker amp muted).
- **Removed (2026-10-25):** U3 (SN74LVC1G123 retriggerable one-shot), R24, R25, C22, C23 and Q3. The reference designators are
  left unused rather than renumbered. In the first version of this section, the firmware toggled `AUDIO_ALIVE` once per callback,
  and U3's Q output (`WD_OK`) stayed high while the edges kept coming. It drove U2's EN and Q3's gate in series with Q4.
- **Trade-off:** U3 watched the audio edges directly, outside the STM32. The IWDG is inside the chip, so the mute depends on the
  firmware feeding it only from the audio callback. Never feed it from the main loop.
- **Superseded:** this section first used Q2 (2N7002) and R27 to drive the TPA6111A2's active-high SHUTDOWN pin through `AMP_SHUTDOWN`.
  The TPA6132A2 swap (below) removed them.
- **Why:** a hung Daisy can loop its last audio buffer at full level, so both amps must mute when audio stops.
  The IWDG covers that with 7 fewer parts.

### Speaker feed from AUDIO_OUT_2, headphone detect in firmware
- **Removed:** the tip-switch line out. J5's TN contact no longer drives `LINE_SEND`, and TN and RN are both no-connects.
  In rev 1, plugging in headphones lifted the tip spring and muted J2 mechanically.
- **Added:** a speaker / line-send stage driven by the Daisy's second output.
  The path is `AUDIO_OUT_2` → R28/C24 (3.3k/1nF, ~48 kHz low-pass, same as the headphone path) → C25/R29 (AC coupling, biased to VREF)
  → U1C buffer → C26 (10µF) → `LINE_SEND` → R3 → J2. J2 and R3/R4 are unchanged and remain the feed to the speaker amp.
- **Changed:** U1 is now a TLV9064 quad (SOIC-14) instead of the TLV9062 dual, using the same TL07x-style symbol.
  Unit A is unchanged. Unit B is unused (see "Headphone buffer removed"). Unit C is the speaker buffer. Unit D is the AUX input buffer (see below).
  Power moves to pin 4 (+5V) and pin 11 (GND).
- **Added:** `HP_DETECT` on Daisy pin 34 (was D27). TP11 sits on it. (R30, R31 and C27 were removed later, see "Small-signal cleanup".)
- **Changed:** J5 is now a Same Sky **SJ3-35063AG** (3.5 mm stereo, through hole; [datasheet](https://www.sameskydevices.com/product/resource/sj3-3506x.pdf)).
  Pins 1/2/3 are sleeve/ring/tip on GND/HP_R/HP_L. Pins 5 and 6 are an isolated normally-open switch that closes when a plug
  is inserted: pin 5 goes to GND and pin 6 to `HP_DETECT`. Pin 4 isn't fitted on this variant.
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
  | 6 | `PWR_BTN_CONN` | Power board → carrier | 26 (`PWR_BTN`, was A4) | Low while the power button is pressed. R35 (1k) series, C29 (100nF), STM32 internal pull-up |
  | 7 | `PWR_HOLD_CONN` | Carrier → power board | 27 (`PWR_HOLD`, was A5) | High keeps the power on. R33 (1k) series, R34 (100k) pull-down so it is low while the Daisy is absent or booting |
  | 8 | `SPK_MUTE` | Carrier → power board | 28 (`SPK_EN`, was A6) | Open drain speaker-amp mute (see below) |

- **Added:** `SPK_MUTE` gate. Q4 (2N7002) pulls `SPK_MUTE` to GND. Its gate is `SPK_EN` with R37 (100k) pull-down, so
  `SPK_MUTE` is pulled low (speaker on) only while the firmware drives `SPK_EN` high. During a watchdog reset the pin floats and
  the speaker amp mutes. The headphone amp (U2) has its own enable, `HP_EN`.
  (Q3 was in series with Q4, gated by the old `WD_OK` watchdog signal. It was removed on 2026-10-25, see "Output mute".)
- **Added:** FB1 (ferrite bead, 1206) and C30 (47µF, 1210) between `+5V` and J4 pin 4, which is now `DISPLAY_5V`.
  They keep the display's current pulses (ESP32 Wi-Fi, backlight PWM) off the rail that feeds the analog circuits.
- **Power board requirements:** nothing above 3.3 V on pins 5–7. Give `PWR_BTN_CONN` its own pull-up (≤ 3.3 V) if the power board reads the button:
  the carrier only has the STM32's internal pull-up, which is off while the Daisy is unpowered or booting. Switch the `BATT_SENSE` divider off with the 5 V output
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
  → C32 (1µF) → R39 (100k to VREF, ~1.6 Hz high-pass) → U1D follower → `AUDIO_IN_2` (Daisy pin 17).
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
  footprint `WQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm`). An internal charge pump gives it a negative rail,
  so its outputs sit at 0 V and drive J5 directly.
- **Removed:** C14/C15 (470µF output caps), R13–R16, R9–R12 (gain resistors, now internal), C16 (bypass), Q2 and R27.
- **Added:** C33 (2.2µF, VDD decoupling), C34 (2.2µF, HPVDD), C35 (1µF, charge-pump flying cap), C36 (2.2µF, HPVSS), all 0805 X5R or better.
  HPVDD and HPVSS are generated inside U2. They get caps only (and PWR_FLAGs for ERC), never an external supply.
- **Wiring:** single-ended inputs per the datasheet (INL+/INR+ to GND). `HP_SOURCE` → C12/C13 (4.7µF, kept) → INL−/INR−.
  With the 19.8k internal input resistance that is a 1.7 Hz high-pass, and there is no output cap, so bass is flat down to a few Hz.
  Gain is 0 dB (G0 to +5V, G1 to GND), inverting as before. EN (active high) is `HP_EN` directly (was `WD_OK`).
- **New symbol:** `seed3-carrier:TPA6132A2RTE` in `seed3-carrier.kicad_sym`. It is the stock KiCad symbol with the pins rearranged:
  grounded pins on the bottom, charge-pump and output pins on the right, supplies on top.
- **Layout:** route SGND (pin 15) straight to the J5 sleeve pin, as the datasheet requires, and keep C35/C36 tight to pins 8, 9 and 11.
  Solder the exposed pad (tied to GND). The QFN needs hot air or a stencil and a hot plate rather than an iron.
- **Why:** removes the two largest parts in the headphone section, flattens the bass, and adds built-in click-and-pop suppression.
  Its maximum output is a fixed ~1.1 Vrms (22 mW into 32 Ω) regardless of supply, which also limits how loud the headphones can get.

### Test points and C9 removed (2026-10-25)
- **Removed:** TP5 (`TP_VREF`), TP9 (`TP_5V`), TP10 (`TP_HP_EN`) and C9 (10 µF on `+5V`), from the schematic and the board.
  The reference designators are left unused rather than renumbered.
- **Why the test points went:** each one duplicated a pad that is easy to probe. TEST_PLAN.md now uses C18 `+` for `+5V`,
  C7 for `VREF` and R26's `HP_EN` end for `HP_EN`.
- **Why C9 went:** it sat on the same node as C18 (47 µF bulk) and C17 (100 nF). C18 stays, because its ESR damps the ringing
  between the harness inductance and the ceramics. U1 and U2 keep their own decoupling (C8, C33).

### Headphone buffer removed (2026-10-25)
- **Removed:** C5 (1 µF) and R6 (1M). The reference designators are left unused rather than renumbered.
- **Changed:** `HP_SOURCE` is now the R2/C2 node, so the Daisy drives C12/C13 and U2 through R2. U1B no longer drives `HP_SOURCE`.
  It is parked as a follower: pin 5 to `VREF`, pins 6 and 7 tied (net `Net-(U1B--)`), so its output sits at 2.5 V and doesn't oscillate.
- **Why it is safe:** the Seed3 outputs are AC-coupled, 1 Vrms at 0 dBFS (Daisy Seed3 datasheet, Table 3), and its TAC5242 codec can drive 16 Ω headphones.
  Electrosmith's own reference circuits load the pin directly with 10k (line out), 15k (instrument out) and a pot plus 22k into a headphone amp (Figure 3.9).
  Here the Daisy sees R2 plus U2's two 19.8 kΩ inputs in parallel, ≈ 13 kΩ.
- **Effects:** R2 and U2's 9.9 kΩ load form a −2.5 dB divider, so full scale reaches U2 at ≈ 0.75 Vrms (≈ 17 mW into 32 Ω), below its ~1.1 Vrms clip point.
  The R2/C2 corner moves from ≈ 48 kHz to ≈ 64 kHz (R2 ‖ 9.9 kΩ with 1 nF). The low-end corner is now C12/C13 into U2 plus the Daisy's own
  output coupling cap, whose value isn't published.

### Small-signal cleanup (2026-10-25)
- **Removed:** R5, R42, R30, R31, C27 and R36. The reference designators are left unused rather than renumbered.
- **R5 (10M, `VREF` → U1A+):** R17 already biases U1A+ to `VREF` through R1, so R5 only sat in parallel with that path. It lowered the
  guitar input load from 1 MΩ to ≈ 0.91 MΩ. It was also the only 10M part, an extended one.
- **R42 (1k into U1D+):** the AUX path already has ≈ 5k in series (R40 ‖ R41) and C31 to GND ahead of C32, so it added no protection or filtering.
  C32/R39 now go straight to U1 pin 12.
- **R30, R31, C27 (`HP_DETECT`):** J5's detect switch is an isolated, mechanically actuated contact on this board, not on a cable. J5 pin 6 now goes
  straight to Daisy pin 34 (PG9), and the `HP_DETECT_SW` net is merged into `HP_DETECT`. The firmware enables the internal pull-up and debounces.
  This matches the Seed3 datasheet's own switch circuits (Figures 2.1 and 2.2: switch to GND, internal pull-up, "Any GPIO").
- **R36 (`PWR_BTN` pull-up):** replaced by the STM32's internal pull-up on pin 26 (PA6). R35 and C29 stay, since that line runs off the board
  to a panel button. With a ≈ 40k internal pull-up, C29 gives a ≈ 4 ms release time, fine for a button. The power board must provide its own pull-up
  if it reads the button (see "Power board requirements").
- **Daisy pin 38 (`3V3_D`)** fed only R30 and R36, so it is now marked no-connect.
- **Kept C17:** it was on the removal list while C9 was still fitted. With C9 gone it is the only ceramic at the power entry, beside C18's electrolytic,
  and the Seed3 datasheet recommends extra filtering on VIN, so it stays.

## Firmware changes these require
- Take volume and mute from the display over the UART instead of the volume/tone ADCs. Ramp volume changes.
- Start the STM32 independent watchdog (IWDG) early in boot, with a timeout of about 10 ms. Feed it **only** from the audio callback.
- Send the speaker mix to output 2 and headphones to output 1. Read `HP_DETECT` (pin 34, PG9) with its internal pull-up enabled:
  **low = headphones in** (J5's normally-open switch closes to GND). Debounce it in firmware. Ramp the speaker down and shut its amp off when headphones are in.
- Add an output clamp or limiter and NaN/Inf guard at the end of the chain.
- Drive `PWR_HOLD` (pin 27) high early in boot. Enable the internal pull-up on `PWR_BTN` (pin 26, PA6). On a press (active low) while running, fade out, mute,
  save settings, then drive `PWR_HOLD` low.
- Drive `SPK_EN` (pin 28) high to enable the speaker amp, low when headphones are in. At power-on, wait about 0.5 s after audio
  starts before raising it, so C26 and the speaker amp's input caps settle and don't pop the speaker. Drive `HP_EN` (pin 33) high
  to run the headphone amp, after the first audio callback has started. Initialise both as low outputs.
- Read `BATT_SENSE` (pin 25, ADC) and send the battery level to the display. Shut down cleanly when it gets low.
- Read `AUDIO_IN_2` (the AUX input, mono) and mix it in after the NAM model and cabinet EQ, with its own level control from the display.
  It goes to both outputs, so backing tracks play through the speaker and the headphones.

## Open items
- **Check the J5 footprint** against a physical part (or a 1:1 print) before ordering boards. It was drawn by hand from the datasheet.
- **Test the watchdog mute:** stall the audio callback in a debug build. Check `HP_EN` (at R26) and `SPK_MUTE` that both amps mute within ~10 ms.
  The target is ~10 ms, comfortably longer than the 2 ms edge period.
- **Speaker amp mute polarity:** `SPK_MUTE` floats (pulled up = muted) or is pulled low (= playing). Check that the chosen amp's
  mute/shutdown pin matches, or invert it on the power board.
- **`BATT_SENSE` divider:** the power board sets the ratio. Record it here so the firmware can convert the reading to volts.
- **Display current:** check the display's datasheet. If it draws well over 1 A, feed it from the power board instead of J4.
- **J3 orientation:** vertical (B8B-XH-A) is drawn. Switch to the right-angle S8B-XH-A if the cable has to leave along the board.
- **2N7002 gate drive:** Q4 is driven from 3.3 V logic. That should be enough for the small pull-up current on `SPK_MUTE`, but check it on the board.
- **Headphone level:** U2's gain is fixed at 0 dB by G0/G1. Full scale reaches U2 at ≈ 0.75 Vrms, below its ~1.1 Vrms clip point.
  Check on the bench that this is loud enough. If not, lower R2 (1k with C2 at 3.3 nF keeps the corner near 50 kHz).
- **AUX input level:** measure a phone and a laptop at full volume through J9 and check that the Daisy input doesn't clip.
  If it does, raise R40/R41.
- **Polarity:** U2 inverts the signal. Decide whether the firmware negates the output.
- **Headphone low-end corner with the Daisy fitted:** TEST_PLAN 3B.4 (Daisy out) checks C12/C13 alone (≈ 1.7 Hz). With the Daisy in, its own output
  coupling cap adds a second high-pass. Sweep it in Stage 5 and record the corner.
- **Layout:** every part is placed (see "Board outline and placement" and "Passive placement" below). Next is routing.
- **U2 stock:** JLC had only 65 TPA6132A2RTER on 2026-10-25. Recheck before ordering (see "Parts sourcing").
- **Mechanical:** the outline and jack positions are a first pass with no enclosure yet. Recheck them against the enclosure drawing.

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
- **No controlled impedance.** `USB_D+`/`USB_D−` no longer leave the Daisy (the J6/J7 breakout is gone), and the module handles USB itself.
  The rules (0.6/0.3 mm vias, 0.2 mm track and clearance) are within JLC's 4-layer limits. See "Design rules" below.

### Board outline and placement (2026-10-25)
90 × 56.5 mm, 2 mm corner radius, three M3 holes (non-plated): rear right, and one on each side just behind the ¼" jacks.
The jack nuts hold the front of the board to the panel. The front panel is the bottom edge (y = 56.5 mm).
Coordinates below are from the board's top-left corner.
The first version was 90 × 80 mm with the Daisy upright. Laying the Daisy flat along the rear edge removed 18 mm of depth
and the empty area beside it, giving 90 × 62 mm. Removing J6/J7 then freed another 5.5 mm (see below). The jacks set the width.

| Part | Position | Why |
|---|---|---|
| J1 (guitar in), J9 (AUX), J5 (headphones), J2 (line out) | Front edge, left to right | All panel jacks on one edge. The ¼" bodies sit flush with the edge and the threaded noses overhang. The SJ3 faces sit at the edge as drawn in the footprint. Inputs are on the left, outputs on the right |
| A1 (Daisy) | Flat along the rear edge, rotated 90°, USB on the left edge | USB stays reachable for flashing. Pins 1–20 face the front, so audio pins 16–19 face U1. Pins 21–40 (power, controls, `HP_EN`, `HP_DETECT`) face the rear |
| U1 (TLV9064) | Between the input jacks and Daisy pins 16–19 | Short input and output paths for all four buffers |
| U2 (TPA6132A2) | Next to J5 | Short SGND and output runs to J5 |
| J3 (power board), J4 (display) | J3 at the rear right beside the Daisy, J4 on the right edge under the rear-right hole, with pin 4 (`DISPLAY_5V`) at the bottom | The display's return current flows between J4 and J3 without passing under U1, J1 or J9. Daisy VIN (pin 39) is at the far left of the rear row, so run `+5V` to it under the Daisy, away from the analog section |
| J8 (internal line out) | Right side, just above J2 | Same net as J2. The speaker-amp cable stays away from the guitar input |

L2 and L3 each have one GND zone covering the board, inset 0.5 mm from the edge.

### Passive placement (2026-10-25)
All parts sit on the top side, in blocks next to the pins they serve. The analog section fills the band between the Daisy and
the front jacks. Power, the display and the power board controls sit in the rear-right corner beside the Daisy.

- **U1** is rotated so its pins 1–7 face the jacks and pins 8–14 face the Daisy, with a row of parts and labels between them.
- **Guitar input (most sensitive):** J1 tip → C1 → C3 → R17 → R1 → U1 pin 3 is one row about 15 mm long, with no
  node longer than 7 mm. Route it all on L1 with no vias, and keep other signals off L1 next to it.
- **AUX input:** R40/R41, R38, C31 and C32 form a block above J1. Only R39 sits at U1 pin 12. J9's tip and ring reach
  the block on L4. They are driven by the source (a phone or laptop output), so the long run is harmless, and L2/L3 shield them from the guitar row on L1.
- **Headphone and speaker filters:** R2/C2 sit below U1 pin 5. R28/C24/C25/R29 sit above pin 10, with C26 and R3
  to the right of pin 8. Route `AUDIO_OUT_1` from the Daisy on L4 where it crosses other paths. It is a DAC output, so it is low impedance.
- **Decoupling:** C8 is right under U1 pin 4 (V+). C33 (VDD), C34 (HPVDD), C35 (flying cap) and C36 (HPVSS) surround U2 within
  3 mm of their pins. U2 is rotated so its inputs face C12/C13, the charge pump faces away from J5, and OUTR drops straight to J5's ring.
  OUTL and SGND leave from the top edge. Take them to J5's tip and sleeve together on L4, so the output and its return run side by side.
- **VREF:** R7, R8 and C7 sit below U1, near the middle of the VREF loads (R17, R29, R39, U1 pin 5). C7 holds the node at low
  impedance, so the VREF trace can run on L4.
- **Power entry:** Q1 sits between J3 pins 1–2 and Daisy VIN. Bulk C18 (47 µF) and C17 (100 nF) sit at Q1's output.
- **Power board signals:** the series resistors R32, R35 and R33 sit in a row under J3 pins 5–7. Q4 and R37 sit under pin 8, and R34 sits above pin 7.
  The Daisy-side parts (C28, C29) sit just below them. Their nets reach Daisy pins 25–28, 33 and 34 under the Daisy.
- **Display:** FB1 sits beside J4 pin 4 and C30 just below J4. R43/R44 sit to their left, so the UART traces to J4 pins 2/3 pass between R37 and FB1 or drop to L4.
- **Test points:** TP11 (`HP_DETECT`) is by J5. TP5, TP9 and TP10 were removed (see "Test points and C9 removed").
- **Spacing:** parts from different blocks keep at least 1 mm of copper between pads, so they can be soldered with an iron and
  a 0.2 mm trace fits between them. The exceptions are on purpose: C8 and R1 at U1's pins (0.73–0.93 mm) and C35 at U2 (0.90 mm).
- **Silkscreen:** passive references are 0.8 mm. A few are placed by hand so none reads as a neighbour's label.
  The schematic's MPN fields for C12/C13 are hidden on the board.

### J6/J7 breakout headers removed (2026-10-25)
- **Removed:** J6 and J7 (1×20 female sockets that mirrored every Daisy pin), their 40 net labels and the "Seed3 breakout headers"
  heading in the schematic, and both footprints on the board.
- **Daisy pins:** the 24 pins that only went to the breakouts are now marked no-connect: D0–D12 (pins 1–13), A0–A2 (22–24), A7–A11
  (29–32, 35), `USB_D−`/`USB_D+` (36, 37) and `3V3_A` (21). Every other Daisy pin is wired as before. `3V3_D` (38) is now no-connect too, since R30 and R36 were removed (see "Small-signal cleanup").
- **Probing:** with the Daisy out, its own sockets (A1) give the same access. TEST_PLAN.md now uses `A1.n`, or a carrier part on the same
  net where the Daisy is fitted. The breakout spot-check (old 5.15) is gone. USB stays on the Daisy's own connector.
- **Board shrunk to 90 × 56.5 mm (was 90 × 62):** the Daisy moved 5.4 mm into J7's strip along the rear edge, and the front section (jacks,
  analog parts, J8 and the side holes) moved 5.5 mm toward it. That leaves a ~4.5 mm routing channel under the Daisy's front row, where its
  audio pins are. The power entry and power-board controls stay put. To make room, the display group was repacked: J4 is on the right edge
  under the rear-right hole, with FB1, C30, R43 and R44 beside it. The spacing rule (≥ 1 mm copper between different-net pads) still holds,
  apart from the same deliberate exceptions at U1/U2. Going shallower would mean breaking that rule in the rear-right corner.

### Parts sourcing: LCSC numbers (2026-10-25)
Build plan: JLC makes the 4-layer board and assembles every SMD part (Economic, top side). The through-hole parts are hand-soldered.
Every part below has its LCSC number in an `LCSC` field in the schematic, copied to the board. Stock is JLC's, checked 2026-10-25.
Basic parts have no loading fee. Each extended part adds about $3 per order (10 here, about $30).

**SMD, assembled by JLC**

| LCSC | Part | Refs | Type | Stock |
|---|---|---|---|---|
| C4410 | 1k 1% 1206 (UNI-ROYAL) | R1 R33 R35 R43 R44 | Basic | 1.9M |
| C26032 | 3.3k 1% 1206 (UNI-ROYAL) | R2 R28 | Extended | 357k |
| C17901 | 100 Ω 1% 1206 (UNI-ROYAL) | R3 | Basic | 2.5M |
| C17900 | 100k 1% 1206 (UNI-ROYAL) | R4 R26 R34 R37 R39 | Basic | 1.0M |
| C17927 | 1M 1% 1206 (UNI-ROYAL) | R17 R29 | Basic | 3.8M |
| C17902 | 10k 1% 1206 (UNI-ROYAL) | R7 R8 R32 R40 R41 | Basic | 2.5M |
| C25833 | 47k 1% 1206 (UNI-ROYAL) | R38 | Extended | 141k |
| C107179 | 100 pF 50 V C0G 1206 (Yageo) | C1 | Extended | 74k |
| C1885 | 1 nF 50 V C0G 1206 (FH) | C2 C24 C31 | Extended | 4.4k |
| C1848 | 1 µF 50 V X7R 1206 (Samsung) | C3 C25 C32 | Basic | 551k |
| C24497 | 100 nF 50 V X7R 1206 (Samsung) | C8 C17 C28 C29 | Basic | 1.6M |
| C13585 | 10 µF 50 V X5R 1206 (Samsung) | C26 | Basic | 2.6M |
| C77101 | 47 µF 16 V X5R 1210 (Murata GRM32ER61C476KE15L) | C7 C30 | Extended | 164k |
| C86052 | 4.7 µF 50 V X7R 1210 (Murata GRM32ER71H475KA88L) | C12 C13 | Extended | 53k |
| C19110 | 2.2 µF 25 V X7R 0805 (Samsung) | C33 C34 C36 | Extended | 297k |
| C28323 | 1 µF 50 V X7R 0805 (Samsung) | C35 | Basic | 1.9M |
| C357023 | 600 Ω@100 MHz, 3 A, 40 mΩ 1206 bead (TAI-TECH HCB3216KF-601T30) | FB1 | Extended | 272k |
| C15127 | AO3401A | Q1 | Basic | 642k |
| C8545 | 2N7002 | Q4 | Basic | 2.9M |
| C388176 | TLV9064IDR | U1 | Extended | 6.1k |
| C69901 | TPA6132A2RTER | U2 | Extended | **65** |

**Through hole, hand-soldered (order from LCSC)**

| LCSC | Part | Refs | Stock |
|---|---|---|---|
| C2835642 | 47 µF 16 V radial 5 × 11 mm, 2 mm pitch, low ESR (SamYoung NXB) | C18 | 8.0k |
| C39461671 | Same Sky SJ3-35063AG | J5 J9 | 100 |
| C157972 | JST B8B-XH-A | J3 | 4.8k |
| C158012 | JST B2B-XH-A | J8 | 425k |
| C53055674 | 1×4 2.54 mm pin header | J4 | 47k |
| C2905423 | 1×20 2.54 mm female header, 8.5 mm | 2 per board, for the Daisy (A1) | 15.9k |
| — | Neutrik NRJ4HF | J1 J2 | Not at LCSC: order from Mouser, DigiKey or a Neutrik distributor |

- **U2 is the stock risk.** JLC has 65 TPA6132A2RTER (the RTET reel has none). That covers this build, but order soon, or buy
  spares from DigiKey or Mouser and send them to JLC as consigned parts if the stock is gone.
- **C0G for the filter caps.** C1, C2, C24 and C31 set the RC filters. X7R would be a basic part, but its capacitance changes with voltage,
  which adds distortion. C2/C24/C31 (C1885) have the thinnest stock of the passives. The 50 V Yageo CC1206JRNPO9BN102 (C113881) is the fallback.
- **Voltage ratings above the schematic's:** C7 (47 µF, schematic says 10 V) shares C30's 16 V part, which also derates better under DC bias.
  C18 is 16 V rather than 10 V. C26 is 50 V. Same footprints, same or better behaviour.
- **Generating the JLC BOM/CPL:** only send the SMD parts. The through-hole parts also have LCSC numbers, for ordering, so filter them out
  (or leave them unselected in JLC's BOM step) unless JLC is meant to fit them.

### U2 exposed-pad vias (2026-10-25)
- **Changed:** U2's footprint is now `WQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm` (was the `_ThermalVias` variant).
  Four 0.6/0.3 mm GND vias sit in the exposed pad at ±0.4 mm from its centre, under the four paste windows.
- **Why:** the `_ThermalVias` footprint drills 0.2 mm holes, below the board's 0.3 mm minimum. U2 dissipates only tens of mW,
  so the vias are there to ground the pad to L2/L3, not for heat, and 0.3 mm holes do that within the standard rules.
- **Watch:** the vias are open, so they wick some solder from the pad during reflow. Check for voids or a floating part (TEST_PLAN 0.3).
  If it is a problem, ask JLC to tent or plug the vias from the bottom.
- **Moving U2:** the vias are board items, not part of the footprint. Move them with U2.

### Design rules (2026-10-25)
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

- **`Power` class:** `+5V`, `/5V_IN`, `/DISPLAY_5V`, `/3V3_A`, `/3V3_D` (both unused on the carrier now). GND stays in Default and mostly drops straight to L2/L3 through vias.
- **Neck-down at U1 and U2 (2026-10-25):** a 1 mm power trace cannot reach U2's 0.25 mm pads (0.5 mm pitch) or U1 pin 4 without touching
  the next pin. Inside each IC's courtyard, two rules set the default to the pad width (U2: 0.25 mm, U1: 0.5 mm), so a trace started
  at the pin begins narrow. Switch to the 1 mm preset once outside the courtyard. Anywhere else a Power trace under 0.5 mm fails DRC.
  Rules later in `seed3-carrier.kicad_dru` win, so the neck-down rules come after "Power track width".
- **Presets:** tracks 0.2, 0.25, 0.3, 0.5 and 1.0 mm; vias 0.6/0.3 and 0.8/0.4 mm.
- **Thermal reliefs (2026-10-25):** through-hole pads join the L2/L3 GND planes with four 0.5 mm spokes and a 0.5 mm gap.
  SMD pads and vias, including U2's exposed-pad vias, stay solid. The through-hole parts are hand-soldered with an iron, and a pin tied solidly
  into two planes (jack sleeves, J3/J4/J8 GND, the Daisy's GND pins, C18) would not heat up enough. Both GND zones use
  "Thermal reliefs for PTH", and the "Thermal reliefs on through-hole pads" rule in `seed3-carrier.kicad_dru` enforces it for
  any zone added later. DRC's minimum of 2 spokes per pad passes.
- **Was:** the minimum track width was 0.3 mm while the Default class used 0.2 mm, so every default track failed DRC. The minimum is now 0.2 mm.
