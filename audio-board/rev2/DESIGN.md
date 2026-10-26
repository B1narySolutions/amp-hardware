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
R7/R8 (10k/10k) from `+5V`, with C7 (47 µF): `VREF` ≈ 2.5 V. With 5k source impedance, C7 gives a ≈ 0.7 Hz corner, which keeps
noise on `+5V` (from the display) out of `VREF`. Its only load is R17.

### Guitar input (J1 → `AUDIO_IN_1`)
J1 tip → C1 (100 pF to GND, RF shunt) → C3 (1 µF) → R17 (1M to `VREF`) → R1 (1k) → U1A follower → `AUDIO_IN_1` (Daisy pin 16).
- J1's tip switch shorts the tip to GND when nothing is plugged in.
- **R17** sets both the 1 MΩ guitar load and the DC bias. **R1** is the only series resistance in this path. It protects U1A's input from plug-in transients.
- **Unity gain, no level pot.** A pot at mid travel put about 250 kΩ of source impedance in front of U1A, which added noise and an
  ~80 kHz pole. Input trim is done in firmware.

### AUX input (J9 → `AUDIO_IN_2`)
J9 (SJ3-35063AG, 3.5 mm TRS) tip and ring → R40/R41 (10k each, passive stereo-to-mono sum) → summing node with R38 (100k to GND)
and C31 (1 nF, RF filter) → `AUDIO_IN_2` (Daisy pin 17) directly. J9's detect switch (pins 5 and 6) is not connected.
- **No buffer and no coupling cap.** The Seed3's audio inputs are AC-coupled on the module (Seed3 datasheet, Table 1 note), and the
  source is a phone or laptop output, so nothing needs biasing or buffering. The Daisy input itself is the load that sets the level.
- **Daisy input impedance:** the TAC5242's AC input impedance is 5 kΩ ±20% at its pins (TAC5242 datasheet, ADC parameters and
  section 7.3). The Seed3 datasheet doesn't give the module pin's value, so this assumes the pin connects to the codec through its
  coupling cap with no extra series resistance. Electrosmith's own input circuits drive the pin from an op-amp through 1k or 100 Ω
  (Figures 3.2 and 3.4), which fits. TEST_PLAN 5.17 measures the level with the Daisy fitted.
- **R38** gives the source's own coupling caps a DC return and holds the summing node at GND when the Daisy is out. At 100k it barely
  affects the level. An empty jack stays quiet because the node then sits at the Daisy's ≈ 5k.
- **C31** filters RF picked up on the cable, for example from the phone itself. It sees R40 ‖ R41 ‖ R38 ‖ 5k ≈ 2.4k, so the corner is
  ≈ 65 kHz.
- **Level:** the same signal on both channels sees R40 ‖ R41 = 5k into the Daisy's input ‖ R38. With the codec at 4k / 5k / 6k that is
  −7.0 / −6.2 / −5.5 dB. Most backing tracks are close to this case, since bass, kick and vocals sit in the centre. One channel alone
  (the other driven at 0 V) sees 10k into 5k ‖ 10k ‖ 100k, a gain of 0.24 (−12.3 dB). A 2 Vrms laptop output (5.7 Vpp) then reaches the
  Daisy at 2.5–3.0 Vpp, under its 3.6 Vpp full scale and its ±1.8 V absolute maximum. The firmware can add gain for quiet phones and
  trims out the ±0.8 dB spread.
- **Source load:** each channel sees ≈ 13k (one channel driven) to ≈ 19k (both driven). Phone and laptop headphone outputs drive this easily.
- **Noise:** the node sits at ≈ 2.4k rather than at an op-amp output. Its thermal noise (≈ 6 nV/√Hz) is far below a backing track's level.
- **Use:** backing tracks bypass NAM. The firmware mixes `AUDIO_IN_2` in after the amp model, to both outputs.

### Headphone output (`AUDIO_OUT_1` → J5)
`AUDIO_OUT_1` (Daisy pin 18) → R2 (3.3k) / C2 (1 nF to GND) → `HP_SOURCE` → C12/C13 (4.7 µF each) → U2 INL−/INR−.
U2 (TPA6132A2RTE) drives J5 (`HP_L` tip, `HP_R` ring) directly.
- **What the Seed3 outputs are rated for:** 1 Vrms at 0 dBFS (Seed3 datasheet, Table 3). The datasheet gives no output impedance,
  minimum load or coupling-cap value for pins 18/19, and says only the *inputs* are AC-coupled.
  - **Line-out mode, not headphones.** The TAC5242 drives 16 Ω headphones (62.5 mW) only in its differential or pseudo-differential
    modes, set by its MD4/MD5 pins on the module. The Seed3 brings out one single-ended pin per channel at 1 Vrms, with single-ended
    AC-coupled inputs. That matches only MD5 high / MD4 low, "Single-ended output; Line-out only" (TAC5242 datasheet, Table 7-10),
    whose minimum load is 600 Ω. The module cannot drive headphones, which is why U2 is here. Electrosmith's own headphone circuit
    (Seed3 datasheet, Figure 3.9) also adds an amp (TPA6110A2).
  - **DC level: probably 0 V, not confirmed.** Figure 3.9 wires pin 18 straight across a volume pot to GND, which only works if the pin
    sits at 0 V DC, so the outputs are most likely AC-coupled on the module. TEST_PLAN 5.16 measures it with the Daisy fitted.
- **No buffer between the Daisy and U2.** The Daisy sees R2 plus U2's two 19.8 kΩ inputs in parallel, ≈ 13 kΩ, far above the 600 Ω
  line-out minimum. Electrosmith's reference circuits load the pin with 10k through a 10 µF cap (line out, Figure 3.3) and with a
  pot to GND (headphone amp, Figure 3.9).
- **R2/C2** filter the DAC's out-of-band noise before U2. With U2's 9.9 kΩ load the corner is ≈ 64 kHz (R2 ‖ 9.9 kΩ with 1 nF).
- **Level:** R2 and U2's 9.9 kΩ load form a −2.5 dB divider, so full scale reaches U2 at ≈ 0.75 Vrms (≈ 17 mW into 32 Ω).
  That is below U2's fixed ~1.1 Vrms maximum output, so full scale can't clip it.
- **Low end:** C12/C13 into U2's 19.8 kΩ input is a 1.7 Hz high-pass. The Daisy's own output coupling cap adds a second one; its value isn't published.
- **U2, TPA6132A2 (DirectPath):** an internal charge pump gives it a negative rail, so its outputs sit at 0 V with no output caps
  and the bass stays flat to a few Hz. It has built-in click-and-pop suppression and short-circuit and thermal protection. Its maximum
  output is a fixed ~1.1 Vrms (22 mW into 32 Ω) regardless of supply, which also limits how loud the headphones can get.
  VDD is rated 2.3–5.5 V, so it runs from `+5V`.
- **U2 wiring:** single-ended inputs per the datasheet (INL+/INR+ to GND; the mono source drives both channels). Gain is 0 dB
  (G0 to `+5V`, G1 to GND), inverting. EN (active high) is `U2_EN`, driven from `HP_EN` by U4 (see "Output mute"). C33 (2.2 µF, VDD), C34 (2.2 µF, HPVDD),
  C35 (1 µF, charge-pump flying cap) and C36 (2.2 µF, HPVSS), all 0805 X5R or better. HPVDD and HPVSS are generated inside U2:
  they get caps only (and PWR_FLAGs for ERC), never an external supply.
- **Symbol:** `seed3-carrier:TPA6132A2RTE` in `seed3-carrier.kicad_sym` is the stock KiCad symbol with the pins rearranged:
  grounded pins on the bottom, charge-pump and output pins on the right, supplies on top.

### Headphone detect (`HP_DETECT`)
J5 (Same Sky SJ3-35063AG, 3.5 mm stereo, through hole; [datasheet](https://www.sameskydevices.com/product/resource/sj3-3506x.pdf)):
pins 1/2/3 are sleeve/ring/tip on GND/`HP_R`/`HP_L`. Pins 5 and 6 are an isolated normally-open switch that closes when a plug is
inserted: pin 5 to GND, pin 6 straight to `HP_DETECT` (Daisy pin 34, PG9). TP11 sits on it. Pin 4 isn't fitted on this variant.
TN and RN are no-connects.
- **No external pull-up, series resistor or RC.** The switch is a mechanically actuated contact on this board, not on a cable, and
  isolated from the plug. The firmware enables PG9's internal pull-up and debounces it. This matches the Seed3 datasheet's own switch
  circuits (Figures 2.1 and 2.2: switch to GND, internal pull-up, "Any GPIO").
- **Low = headphones in.**
- **Footprint:** `Seed3_Carrier.pretty/Jack_3.5mm_SameSky_SJ3-35063AG_Horizontal.kicad_mod`, drawn from the datasheet's recommended
  PCB layout. The jack face sits at the board edge (X = −2.4 mm from pin 1), with the nose overhanging. J9 uses the same part and footprint.

### Speaker / line send (`AUDIO_OUT_2` → J2, J8)
`AUDIO_OUT_2` (Daisy pin 19) → R28/C24 (3.3k/1 nF, ~48 kHz low-pass) → `LINE_OUT`, with R4 (100k) to GND. `LINE_OUT` goes to
J2 (¼", external) and J8 (internal, to the speaker amp).
- **No buffer**, for the same reason as the headphone path: R28 plus a ≥ 10k amp input is far above the 600 Ω line-out minimum (see
  "What the Seed3 outputs are rated for"). With no `VREF` bias or coupling caps in the path, `LINE_OUT` doesn't drift at power-on.
- **This path assumes pin 19 sits at 0 V DC.** With no cap of our own, any DC offset at the pin would reach J2, J8 and R4. If TEST_PLAN
  5.16 finds more than a few tens of mV, fit a series cap after R28 (10 µF; with R4 and a 10k load the corner stays under 3 Hz).
- **R28** is the output impedance and isolates the Daisy from cable capacitance. Into a 10k input it costs ≈ 2.6 dB (≈ 0.74 Vrms at
  full scale). Cable capacitance adds to C24 and lowers the corner, ≈ 37 kHz with 3 m of typical cable.
- **R4** gives the Daisy's output coupling cap a DC return, so `LINE_OUT` sits at 0 V with nothing plugged in.
- **J8** is a 2-pin JST-XH (B2B-XH-A, vertical): pin 1 `LINE_OUT`, pin 2 GND. It feeds the speaker amp on the power board (or an
  off-the-shelf class D module while prototyping). A keyed internal header instead of a ¼" cable between boards. Audio ground has its
  own pin, separate from J3's supply current. Use a short twisted pair routed away from the guitar input and speaker wires.
- **J2** is the external line out: for an outside amp, or to record into a DAW while monitoring on headphones. It stays live when
  headphones are in (only the speaker amp is muted, through `SPK_EN`).
- **Why a separate speaker output:** muting in firmware means the speaker amp can be shut down while headphones are in (saving battery),
  mute and unmute can ramp without clicks, and the speaker and headphones get independent levels.
- **Speaker wiring** is on the power board, not here: the cone's spade tabs (6.3 mm / 4.8 mm) take crimped quick-disconnects.
  Most class D amps have a bridged output, so neither speaker wire may be grounded.

### Output mute (STM32 watchdog)
A hung Daisy can loop its last audio buffer at full level, so both amps must mute when audio stops.
- `HP_EN` (Daisy pin 33) drives U2's EN through U4, a TXU0101 single-bit level translator: A from `HP_EN`, VCCA and OE from the
  Daisy's `3V3_D` (pin 38), VCCB from `+5V`, BY to `U2_EN`. C37 (100 nF) decouples VCCA and C38 (100 nF) decouples VCCB.
  R26 (100k) pulls `U2_EN` low.
- **Why U4:** the Daisy and U2 are on different supplies (see "Running from USB alone"). U4's output can only swing to VCCB, which is
  U2's own VDD, so EN can't exceed its VDD + 0.3 V rating. If either supply is off, U4's output goes high-impedance (TI's "VCC isolation"
  and Ioff features) and R26 holds EN low. U4's A input has a 5 MΩ internal pull-down, so a floating Daisy pin reads low.
  The datasheet specifies the Ioff and VCC isolation behaviour, so both power-up orders are covered.
- `SPK_EN` (Daisy pin 28) drives Q4's gate, with R37 (100k) pull-down. Q4 (2N7002) pulls `SPK_MUTE` (J3.8) to GND, which means
  speaker on. The power board pulls `SPK_MUTE` up, which means muted.
- **How it works:** the firmware feeds the STM32's independent watchdog (IWDG) only from the audio callback. The IWDG runs on its
  own clock, so if the callback stops (hung firmware, stalled DMA, fault handler), it resets the STM32. During a reset, and while the
  Daisy is booting or in DFU, its pins float: U4's internal pull-down holds its output low (U2 off) and R37 holds `SPK_EN` low (speaker amp
  muted). With the Daisy absent, U4 has no VCCA, its output goes high-impedance, and R26 holds `U2_EN` low.
- **The codec mutes too.** The STM32 clocks the TAC5242, and the TAC5242 powers down its DAC by itself when its audio clocks stop
  (TAC5242 datasheet, section 7.4.1). An IWDG reset therefore also silences pins 18/19, including J2, which has no amp to mute.
  This doesn't help while the clocks keep running, such as a DMA looping a stale buffer with the CPU hung, which is why the IWDG has
  to reset the chip. The datasheet doesn't say whether the power-down clicks; TEST_PLAN 5.16 records it.
- **Why Q4 instead of driving `SPK_MUTE` from the Daisy pin:** the power board can pull `SPK_MUTE` up to any voltage, and an unpowered
  Daisy isn't back-powered through it.
- **Trade-off:** an external retriggerable one-shot watching an audio-callback toggle would watch the audio from outside the STM32.
  The IWDG is inside the chip, so the mute depends on the firmware feeding it only from the audio callback. Never feed it from the main loop.
  The IWDG does the job with 7 fewer parts.

## Power

`5V_IN` arrives on J3 pins 1–2 and goes through Q1 (AO3401A P-FET, reverse-polarity protection) onto `+5V`. `+5V` feeds Daisy VIN
(pin 39), U1, U2, `VREF`, and the display through FB1.
- **Why Q1 with a keyed connector:** the JST-XH key stops the plug going in backwards, but not a hand-crimped harness with 5 V and GND
  swapped, or swapped clip leads on a bench supply (TEST_PLAN 2.16 tests this). The Seed3's VIN is reverse-protected on the module, but
  U1, U2 and the display are not. Q1 drops about 50 mV at 1 A.
- **Mirrored harness:** with this pinout, a harness wired end-to-end mirrored puts the power board's signals on `5V_IN`/GND and 5 V/GND
  onto pins 5–8. Q1 can't catch that. The keying and a careful look at the first harness do. R33 limits the current into the Daisy pin if it happens.
- **Bulk at the power entry:** C18 (47 µF low-ESR electrolytic) and C17 (100 nF) at Q1's output. C18's ESR damps the ringing between the
  harness inductance and the ceramics. C17 is the only ceramic at the entry, and the Seed3 datasheet recommends extra filtering on VIN.
- **Local decoupling:** C8 at U1 pin 5 and C33 at U2 VDD.
- **Display supply:** FB1 (600 Ω @ 100 MHz bead, 1206) and C30 (47 µF, 1210) between `+5V` and J4 pin 4 (`DISPLAY_5V`). They keep
  the display's current pulses (ESP32 Wi-Fi, backlight PWM) off the rail that feeds the analog circuits.

### Running from USB alone
The Seed3 runs from its own USB port, and the datasheet says USB and VIN can be connected together, so USB doesn't appear to drive the
VIN pin. With USB plugged in and the power board off (flashing or debugging on the bench), the Daisy runs while `+5V` is at 0 V. Any
Daisy output that is high then pushes current into an unpowered part on the carrier through that part's input protection diodes.
- **`HP_EN`:** U2's EN is rated to VDD + 0.3 V, so with VDD at 0 V it must stay at 0 V. U4 sits between the Daisy and EN. With VCCB
  (`+5V`) off, its output goes high-impedance, its A input draws at most a few µA (Ioff), and R26 holds EN at 0 V. No current flows
  from `HP_EN` into U2.
- **Q1 conducts backwards** if `+5V` is lifted, because its gate is tied to GND. The UART current through R43 (below) can lift `+5V` very
  slightly through the display. That only leaks a little current to the power board. It would matter if anything back-powered `+5V` hard.
- **Display UART:** Daisy TX idles high into an unpowered display. R43 (10k) limits that current to ≈ 0.27 mA. See "Display connector (J4)".
- **`PWR_HOLD`** goes to the power board through R33 (1k). The power board has to tolerate 3.3 V on that pin while it is off.

## Connectors

### Power board connector (J3)
J3 is an 8-pin JST-XH (B8B-XH-A, vertical). It carries power and the control signals to the separate power board, which handles
the battery, the power button and the speaker amp. One connector gives power, a clean firmware-controlled shutdown, the battery level
on the display, and a speaker mute that is independent of the headphone amp.

| Pin | Net | Direction | Daisy pin | Use |
|---|---|---|---|---|
| 1, 2 | `5V_IN` | Power board → carrier | 39 (VIN) via Q1 | 5 V supply, two pins share the current |
| 3, 4 | GND | — | 20 / 40 | Ground, two pins |
| 5 | `BATT_SENSE_CONN` | Power board → carrier | 25 (`BATT_SENSE`) | Battery voltage scaled to ≤ 3.3 V. R32 (10k) and C28 (100 nF) filter it into the ADC |
| 6 | `PWR_BTN_CONN` | Power board → carrier | 26 (`PWR_BTN`) | Low while the power button is pressed. R35 (1k) series, C29 (100 nF), STM32 internal pull-up |
| 7 | `PWR_HOLD_CONN` | Carrier → power board | 27 (`PWR_HOLD`) | High keeps the power on. R33 (1k) series, R34 (100k) pull-down so it is low while the Daisy is absent or booting |
| 8 | `SPK_MUTE` | Carrier → power board | 28 (`SPK_EN`) via Q4 | Open-drain speaker-amp mute (see "Output mute") |

- **R32 is 10k:** while the amp is off, the power board's battery divider can still hold `BATT_SENSE_CONN` near 3.3 V. Through 1k that
  would push ~3 mA into the unpowered Daisy's pin protection diodes and back-power its 3.3 V rail. 10k limits it to ~0.3 mA.
  With C28 the filter corner is ~160 Hz, far above battery changes. C28 also supplies the ADC's sampling charge.
- **`PWR_BTN`:** the STM32's internal pull-up (pin 26, PA6, ≈ 40k) replaces an external one. R35 and C29 stay, because the line runs
  off the board to a panel button. With C29, the release time is ≈ 4 ms, fine for a button.

**Power board requirements**
- Nothing above 3.3 V on pins 5–7.
- Give `PWR_BTN_CONN` its own pull-up (≤ 3.3 V) if the power board reads the button. The carrier only has the STM32's internal
  pull-up, which is off while the Daisy is unpowered or booting.
- Switch the `BATT_SENSE` divider off with the 5 V output (or give it ≥ 100k source impedance), so it doesn't drain the battery or feed
  an unpowered Daisy while the amp is off.
- Pull `SPK_MUTE` up on the amp side so the amp is muted when this board is unpowered or unplugged.
- Keep the power on for about 2 s after a button press until the Daisy raises `PWR_HOLD`, and force the power off when the button is held for about 5 s.
- The power button is panel mounted and wired to the power board.

### Display connector (J4)
J4 is a 1×4 2.54 mm header: 1 GND, 2 `UART_TX_CONN`, 3 `UART_RX_CONN`, 4 `DISPLAY_5V`. R43 (10k, Daisy TX) and R44 (1k, Daisy RX)
sit in series with the UART between J4 and Daisy USART1 (pins 14/15, `DISPLAY_UART_TX`/`DISPLAY_UART_RX`). They limit current if the
cable is miswired (TX to TX) or hot-plugged, and add a little ESD margin.
- **R43 is 10k** because the display is powered from the carrier's `+5V`. With the Daisy on USB alone (see "Running from USB alone"),
  its TX idles high into an unpowered display. 10k keeps the current into the display's RX protection diode to ≈ 0.27 mA.
- **Baud rate limit:** R43 with ~50 pF of cable and pin capacitance is a ≈ 0.5 µs time constant. That is fine up to 230400 baud
  (a 4.3 µs bit), but not for 921600. To go faster, lower R43 and accept more current into an unpowered display.
- **R44 stays 1k.** The display only drives it while the carrier is powered, and then the Daisy is powered too.

### Daisy pins
Used: 14/15 (display UART), 16/17 (audio in), 18/19 (audio out), 20/40 (GND), 25 `BATT_SENSE`, 26 `PWR_BTN`, 27 `PWR_HOLD`,
28 `SPK_EN`, 33 `HP_EN`, 34 `HP_DETECT`, 38 `3V3_D` (U4's VCCA and OE only, a few µA), 39 VIN. Every other pin, including `3V3_A` (21) and USB D−/D+ (36/37), is
marked no-connect. With the Daisy out, its sockets (A1) give probe access to every carrier net, so there are no breakout headers.
USB stays on the Daisy's own connector.

## Firmware requirements
- Run the display UART at 230400 baud or less (R43, see "Display connector (J4)"). Take volume and mute from the display over it. Ramp volume changes.
- Start the IWDG early in boot, with a timeout of about 10 ms. Feed it **only** from the audio callback.
- Send the speaker mix to output 2 and headphones to output 1.
- Read `HP_DETECT` (pin 34, PG9) with its internal pull-up enabled: **low = headphones in**. Debounce it. When headphones go in, ramp
  `AUDIO_OUT_2` down, drive `SPK_EN` low, then ramp `AUDIO_OUT_2` back up so J2 stays live for recording. Reverse it when they come out.
- Add an output clamp or limiter and NaN/Inf guard at the end of the chain.
- Drive `PWR_HOLD` (pin 27) high early in boot. Enable the internal pull-up on `PWR_BTN` (pin 26, PA6). On a press (active low) while
  running, fade out, mute, save settings, then drive `PWR_HOLD` low.
- Initialise `SPK_EN` (pin 28) and `HP_EN` (pin 33) as low outputs. Drive `HP_EN` high after the first audio callback has started.
  Drive `SPK_EN` high to enable the speaker amp (after the first audio callback, like `HP_EN`), low when headphones are in.
- Read `BATT_SENSE` (pin 25, ADC) and send the battery level to the display. Shut down cleanly when it gets low.
- Read `AUDIO_IN_2` (the AUX input, mono) and mix it in after the NAM model and cabinet EQ, with its own level control from the display.
  It goes to both outputs.

## Open items
- **Check the J5/J9 footprint** against a physical part (or a 1:1 print) before ordering boards. It was drawn by hand from the datasheet.
- **Test the watchdog mute:** stall the audio callback in a debug build. Check that `U2_EN` (at R26) and `SPK_MUTE` both mute within ~10 ms.
- **Speaker amp mute polarity:** `SPK_MUTE` floats (pulled up = muted) or is pulled low (= playing). Check that the chosen amp's
  mute/shutdown pin matches, or invert it on the power board.
- **`BATT_SENSE` divider:** the power board sets the ratio. Record it here so the firmware can convert the reading to volts.
- **Display current:** check the display's datasheet. If it draws well over 1 A, feed it from the power board instead of J4.
- **J3 orientation:** vertical (B8B-XH-A) is drawn. Switch to the right-angle S8B-XH-A if the cable has to leave along the board.
- **2N7002 gate drive:** Q4 is driven from 3.3 V logic. That should be enough for the small pull-up current on `SPK_MUTE`, but check it on the board.
- **Headphone level:** check on the bench that 0.75 Vrms is loud enough. If not, lower R2 (1k with C2 at 3.3 nF keeps the corner near 50 kHz).
- **AUX input level:** TEST_PLAN 5.17 checks the level with the Daisy fitted (the Daisy's input impedance isn't published). Then measure
  a phone and a laptop at full volume through J9. 2 Vrms should reach 2.5–3.0 Vpp, under full scale. If it clips, add a resistor from
  the summing node to GND (10k gives ≈ −8 dB). If quiet phones need too much firmware gain, lower R40/R41 (4.7k each gives ≈ −3.5 dB).
- **Guitar input level:** U1A is unity gain and can swing ≈ ±2.4 V, beyond the Daisy's 3.6 Vpp full scale and ±1.8 V absolute maximum.
  Passive pickups fit, but active pickups or a boost pedal may not. Firmware trim comes after the ADC, so it can't help. Decide the
  maximum supported input, and whether a pad or clamp is needed.
- **Polarity:** U2 inverts the signal. Decide whether the firmware negates the output.
- **Headphone low-end corner with the Daisy fitted:** TEST_PLAN 3B.4 (Daisy out) checks C12/C13 alone (≈ 1.7 Hz). Sweep it again in
  Stage 5 with the Daisy in and record the corner.
- **Layout:** every part is placed. Next is routing.
- **Line-out level:** with no buffer, R28 is the output impedance. Check on the bench that the speaker amp and an interface see enough
  level. If not, lower R28 (1k with C24 at 3.3 nF keeps the corner near 48 kHz).
- **U2 stock:** JLC had only 65 TPA6132A2RTER on 2026-10-25. Recheck before ordering (see "Parts sourcing").
- **Mechanical:** the outline and jack positions are a first pass with no enclosure yet. Recheck them against the enclosure drawing.

## Layout

### Stackup
JLCPCB standard 4-layer, 1.6 mm (JLC04161H-7628). Outer copper 1 oz, inner 0.5 oz. Check the dielectric thicknesses on JLC's
stackup page when ordering.

This is the "ground in the middle" stackup that Bogatin recommends as the default for 4-layer boards. Page numbers below refer to
Eric Bogatin, *Bogatin's Practical Guide to Prototype Breadboard and PCB Design* (Artech House, 2021).

| Layer | Use | To next layer |
|---|---|---|
| L1 (top) | Parts, most signal routing, `+5V` and `DISPLAY_5V` as wide traces (≥ 1 mm) | 0.21 mm prepreg |
| L2 | Solid GND. No traces, no cuts | ~1.07 mm core |
| L3 | Solid GND. No traces, no cuts | 0.21 mm prepreg |
| L4 (bottom) | Remaining signals, power traces that don't fit on L1 | — |

- **Why ground in the middle:** both signal layers sit 0.21 mm from a solid GND plane. All routing can be seen and probed from the
  outside, and the symmetrical build won't warp (p. 480). The JLC build above is the book's own example (p. 475, Fig. 23.3).
- **Why no power plane:** a power plane is only needed above about 20 A (pp. 466, 479). The board draws about 1 A at most, and a 20 mil
  (0.5 mm) trace carries 3 A (p. 466). `+5V` also feeds the display, which pulls current pulses (ESP32 Wi-Fi, backlight PWM). A full
  power plane would spread that rail under the guitar input and the analog circuits.
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
  - Put J3 (power in) and J4 (display) close together, so the display's return current doesn't pass under U1, J1 or J9.
  - Route U2's SGND (pin 15) straight to J5's sleeve, as the datasheet requires, and put vias under U2's exposed pad down to L2.
- **Why 1.6 mm:** the ¼" jacks, the SJ3 jacks and the Daisy sockets take force at every plug-in. It is also the cheapest thickness.
- **No controlled impedance.** USB doesn't leave the Daisy, and the module handles it itself.
- L2 and L3 each have one GND zone covering the board, inset 0.5 mm from the edge.

### Board outline and placement
90 × 56.5 mm, 2 mm corner radius, three M3 holes (non-plated): rear right, and one on each side just behind the ¼" jacks. The jack
nuts hold the front of the board to the panel. The front panel is the bottom edge (y = 56.5 mm). Coordinates are from the board's
top-left corner. The jacks set the width. Laying the Daisy flat along the rear edge, with no breakout headers, sets the depth.

| Part | Position | Why |
|---|---|---|
| J1 (guitar in), J9 (AUX), J5 (headphones), J2 (line out) | Front edge, left to right | All panel jacks on one edge. The ¼" bodies sit flush with the edge and the threaded noses overhang. The SJ3 faces sit at the edge as drawn in the footprint. Inputs are on the left, outputs on the right |
| A1 (Daisy) | Flat along the rear edge, rotated 90°, USB on the left edge | USB stays reachable for flashing. Pins 1–20 face the front, so audio pins 16–19 face U1. Pins 21–40 (power, controls, `HP_EN`, `HP_DETECT`) face the rear. A ~4.5 mm routing channel runs under its front row, where the audio pins are |
| U1 (TLV9061) | At the end of the guitar row, below Daisy pin 16 | Short guitar input path |
| U2 (TPA6132A2) | Next to J5 | Short SGND and output runs to J5 |
| J3 (power board), J4 (display) | J3 at the rear right beside the Daisy, J4 on the right edge under the rear-right hole, with pin 4 (`DISPLAY_5V`) at the bottom | The display's return current flows between J4 and J3 without passing under U1, J1 or J9. Daisy VIN (pin 39) is at the far left of the rear row, so run `+5V` to it under the Daisy, away from the analog section |
| J8 (internal line out) | Right side, just above J2 | Same net as J2. The speaker-amp cable stays away from the guitar input |

### Passive placement
All parts sit on the top side, in blocks next to the pins they serve. The analog section fills the band between the Daisy and the
front jacks. Power, the display and the power board controls sit in the rear-right corner beside the Daisy.

- **U1** (SOT-23-5) sits unrotated at the end of the guitar row: pin 3 (+) is 0.8 mm from R1, pin 1 (out) faces up toward Daisy pin 16,
  and pin 2 (GND) takes a via to L2/L3. The follower feedback, pin 4 to pin 1, wraps around the right side of the body.
- **Guitar input (most sensitive):** J1 tip → C1 → C3 → R17 → R1 → U1 pin 3 is one row about 15 mm long, with no node longer than 7 mm.
  Route it all on L1 with no vias, and keep other signals off L1 next to it.
- **AUX input:** R40/R41, R38 and C31 form a block above J1. `AUDIO_IN_2` runs from that block straight to Daisy pin 17, clear of U1.
  J9's tip and ring reach the block on L4. They are driven by the source (a phone or laptop output), so the long run is harmless, and
  L2/L3 shield them from the guitar row on L1.
- **Headphone and speaker filters:** R2/C2 sit below-right of U1. R28/C24 sit above J8, with R4 beside J8 pin 1. `AUDIO_OUT_2` runs
  from Daisy pin 19 to R28 as the low-impedance DAC output, so only the short R28 → J8 stretch is at 3.3k.
  Route `AUDIO_OUT_1` from the Daisy on L4 where it crosses other paths. It is a DAC output, so it is low impedance.
- **Decoupling:** C8 sits just right of U1 pin 5 (V+), 0.6 mm away, with its GND end away from the IC. C33 (VDD), C34 (HPVDD), C35 (flying cap) and C36 (HPVSS) surround U2 within 3 mm
  of their pins. U2 is rotated so its inputs face C12/C13, the charge pump faces away from J5, and OUTR drops straight to J5's ring.
  OUTL and SGND leave from the top edge. Take them to J5's tip and sleeve together on L4, so the output and its return run side by side.
- **VREF:** R7, R8 and C7 sit below U1, near the middle of the `VREF` loads. C7 holds the node at low impedance, so the `VREF` trace can run on L4.
- **Power entry:** Q1 sits between J3 pins 1–2 and Daisy VIN. C18 and C17 sit at Q1's output.
- **`HP_EN`:** U4 sits above C33, with C37 to its left (at VCCA) and C38 above it (at VCCB). R26 stands to its right. `HP_EN` and
  `3V3_D` come from the Daisy's rear row (pins 33 and 38) under the Daisy. Keep the `3V3_D` trace away from the `+5V` trace at pins 38/39.
  `U2_EN` runs from U4 pin 4 down past C33 to U2 pin 13 (EN).
- **Power board signals:** the series resistors R32, R35 and R33 sit in a row under J3 pins 5–7. Q4 and R37 sit under pin 8, and R34
  sits above pin 7. C28 and C29 sit just below them. Their nets reach Daisy pins 25–28, 33 and 34 under the Daisy.
- **Display:** FB1 sits beside J4 pin 4 and C30 just below J4. R43/R44 sit to their left, so the UART traces to J4 pins 2/3 pass
  between R37 and FB1 or drop to L4.
- **Test point:** TP11 (`HP_DETECT`) is by J5. Other nets are probed on part pads (see TEST_PLAN.md).
- **Spacing:** parts from different blocks keep at least 1 mm of copper between pads, so they can be soldered with an iron and a 0.2 mm
  trace fits between them. The exceptions are on purpose: C8 and R1 at U1's pins (0.58 and 0.80 mm) and C35 at U2 (0.90 mm). Making the
  board shallower would mean breaking this rule in the rear-right corner.
- **Silkscreen:** passive references are 0.8 mm. A few are placed by hand so none reads as a neighbour's label. The schematic's MPN
  fields for C12/C13 are hidden on the board.

### 3D models
- **A1** uses `3dmodels/Electrosmith_Daisy_Seed_placeholder.step` on two stock `PinSocket_1x20_P2.54mm_Vertical` models (8.5 mm), at x = 0 and 15.24.
  **J1/J2** use `3dmodels/Neutrik_NRJ4HF_placeholder.step`. KiCad ships no model for either part, so the board points at these
  placeholders from `make_placeholders.py`. Re-running "Update footprints from library" on A1, J1 or J2 resets the paths to KiCad's missing models.
- **The Daisy placeholder is the original Seed's outline** (micro-USB, ~1 mm overhang, 3 mm tall). The Seed3's USB-C overhangs the
  PCB by 1.55 mm and stands 3.25 mm tall (Seed3 datasheet, page 8). Allow for that when checking the enclosure.
- **J5/J9** use `3dmodels/SameSky_SJ3-35063AG_placeholder.step`, set in the project footprint itself, so a footprint update keeps it.

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

- **`Power` class:** `+5V`, `/5V_IN`, `/DISPLAY_5V` (the class also lists `/3V3_A`, which is unused on the carrier, and `/3V3_D`, which only feeds U4).
  GND stays in Default and mostly drops straight to L2/L3 through vias.
- **Neck-down at U1 and U2:** a 1 mm power trace cannot reach U2's 0.25 mm pads (0.5 mm pitch) or U1 pin 5 without touching the next
  pin. Inside each IC's courtyard, two rules set the default to the pad width (U2: 0.25 mm, U1: 0.5 mm), so a trace started at the pin
  begins narrow. Switch to the 1 mm preset once outside the courtyard. Anywhere else a Power trace under 0.5 mm fails DRC. Rules later in
  `seed3-carrier.kicad_dru` win, so the neck-down rules come after "Power track width".
- **Presets:** tracks 0.2, 0.25, 0.3, 0.5 and 1.0 mm; vias 0.6/0.3 and 0.8/0.4 mm.
- **Thermal reliefs:** through-hole pads join the L2/L3 GND planes with four 0.5 mm spokes and a 0.5 mm gap. SMD pads and vias,
  including U2's exposed-pad vias, stay solid. The through-hole parts are hand-soldered with an iron, and a pin tied solidly into two
  planes (jack sleeves, J3/J4/J8 GND, the Daisy's GND pins, C18) would not heat up enough. Both GND zones use "Thermal reliefs for PTH",
  and the "Thermal reliefs on through-hole pads" rule in `seed3-carrier.kicad_dru` enforces it for any zone added later. DRC's minimum of
  2 spokes per pad passes.

## Parts sourcing
Build plan: JLC makes the 4-layer board and assembles every SMD part (Economic, top side). The through-hole parts are hand-soldered.
Every part below has its LCSC number in an `LCSC` field in the schematic, copied to the board. Stock is JLC's, checked 2026-10-25.
Basic parts have no loading fee. Each extended part adds about $3 per order (10 here, about $30, or more if C398358 turns out to be extended).

**SMD, assembled by JLC**

| LCSC | Part | Refs | Type | Stock |
|---|---|---|---|---|
| C4410 | 1k 1% 1206 (UNI-ROYAL) | R1 R33 R35 R44 | Basic | 1.9M |
| C26032 | 3.3k 1% 1206 (UNI-ROYAL) | R2 R28 | Extended | 357k |
| C17900 | 100k 1% 1206 (UNI-ROYAL) | R4 R26 R34 R37 R38 | Basic | 1.0M |
| C17927 | 1M 1% 1206 (UNI-ROYAL) | R17 | Basic | 3.8M |
| C17902 | 10k 1% 1206 (UNI-ROYAL) | R7 R8 R32 R40 R41 R43 | Basic | 2.5M |
| C107179 | 100 pF 50 V C0G 1206 (Yageo) | C1 | Extended | 74k |
| C1885 | 1 nF 50 V C0G 1206 (FH) | C2 C24 C31 | Extended | 4.4k |
| C1848 | 1 µF 50 V X7R 1206 (Samsung) | C3 | Basic | 551k |
| C24497 | 100 nF 50 V X7R 1206 (Samsung) | C8 C17 C28 C29 C37 C38 | Basic | 1.6M |
| C77101 | 47 µF 16 V X5R 1210 (Murata GRM32ER61C476KE15L) | C7 C30 | Extended | 164k |
| C86052 | 4.7 µF 50 V X7R 1210 (Murata GRM32ER71H475KA88L) | C12 C13 | Extended | 53k |
| C19110 | 2.2 µF 25 V X7R 0805 (Samsung) | C33 C34 C36 | Extended | 297k |
| C28323 | 1 µF 50 V X7R 0805 (Samsung) | C35 | Basic | 1.9M |
| C357023 | 600 Ω@100 MHz, 3 A, 40 mΩ 1206 bead (TAI-TECH HCB3216KF-601T30) | FB1 | Extended | 272k |
| C15127 | AO3401A | Q1 | Basic | 642k |
| C8545 | 2N7002 | Q4 | Basic | 2.9M |
| C398358 | TLV9061IDBVR | U1 | Check | Check (LCSC lists 283k) |
| C69901 | TPA6132A2RTER | U2 | Extended | **65** |
| C7136368 | TXU0101DBVR (TI) | U4 | Extended | 5.1k |

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

- **U2 is the stock risk.** JLC has 65 TPA6132A2RTER (the RTET reel has none). That covers this build, but order soon, or buy spares
  from DigiKey or Mouser and send them to JLC as consigned parts if the stock is gone.
- **C0G for the filter caps.** C1, C2, C24 and C31 set the RC filters. X7R would be a basic part, but its capacitance changes with voltage,
  which adds distortion. C2/C24/C31 (C1885) have the thinnest stock of the passives. The 50 V Yageo CC1206JRNPO9BN102 (C113881) is the fallback.
- **Voltage ratings above the schematic's:** C7 (47 µF, schematic says 10 V) shares C30's 16 V part, which also derates better under
  DC bias. C18 is 16 V rather than 10 V. Same footprints, same or better behaviour.
- **Generating the JLC BOM/CPL:** only send the SMD parts. The through-hole parts also have LCSC numbers, for ordering, so filter them
  out (or leave them unselected in JLC's BOM step) unless JLC is meant to fit them.
