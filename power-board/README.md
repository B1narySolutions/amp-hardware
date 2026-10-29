# Power board

This directory is where we will put the KiCad project for the power board.

## What the audio board needs from it

The audio board (the Seed3 carrier, `../audio-board/rev2/`) connects to the power board through two screw terminals, six wires in all. This list
collects everything the carrier expects from the power board. `../audio-board/rev2/DESIGN.md` gives the reasons ("Power board
connector (J6)", "Output mute", "Speaker send", "Display connector (J3)"). `../interfaces/carrier-power.py` encodes the same
numbers as a contract that both boards' circuit-check specs load: the carrier takes its J6/J5 assumptions from it and
checks the signals it drives against it, and the power board's spec will do the same once it has a schematic. If the
power board's design departs from any of them, change the contract and rerun `tools/kicad/circuit_verify.py` on both
boards.

### Connections

| Carrier terminal | Pins (silkscreen) | What the power board does with it |
|---|---|---|
| J6, power | 1 5V, 2 GND, 3 BAT, 4 MUTE | Sends 5 V and the battery level to the carrier, and gets the speaker mute back |
| J5, speaker send | 1 LINE+, 2 LINE− | Feeds the speaker amp's differential input |

Both are 3.5 mm screw terminals on the carrier, J6 4-way and J5 2-way. Seen from the wire side, J6 reads 5V, GND, BAT, MUTE from
left to right.

The carrier's third screw terminal, J3 (1 GND, 2 TX, 3 RX), is not a power board connection. It is the UART link between the Seed3
and the display's ESP32-S3, wired straight to the display. The power board only supplies the display's power (see "Display").

### 5 V supply (J6.1, J6.2)
- 5.0 V ± 5 % (4.75–5.25 V) at J6, never above 5.5 V: the carrier's op-amp (U1) and headphone amp (U2) run straight from it.
  The carrier's Q1 drops tens of mV, and its firmware won't start audio below 4.7 V or keep it running below 4.4 V.
- The carrier draws well under 1 A. The Daisy takes roughly 100–200 mA.
- One 5 V wire and one GND wire on J6 (a KF350 contact is rated 10 A). The display's ground returns with its own power pair, though
  some of its return current comes back through the display UART's GND (J3) and across to J6, which sit side by side on the carrier.
- The carrier has reverse-polarity protection (Q1), but nothing else on the power board should rely on it.

### Power switch and battery
- Put the power switch and the low-battery cutoff on the power board. The carrier can't turn the power off itself, and its firmware
  assumes the power can disappear at any time.
- **Battery level (J6.3, BAT):** a voltage proportional to the battery, scaled to 0–3.3 V.
  - Keep its source impedance at 10 kΩ or less. The carrier loads BAT with 20 kΩ (its R13 + R22) and reads
    V × 10k / (20k + R_source), where V is the divider's open-circuit output. With a stiff source that is half of BAT.
  - Record the divider's ratio and source impedance in the carrier's DESIGN.md ("Open items"), so the firmware can convert the
    reading to volts.
  - Switch the divider off with the 5 V output, so it doesn't drain the battery while the amp is off.

### Speaker amp
- **Input (J5):** wire LINE+ to the amp's IN+ and LINE− to its IN− **only**, never to the amp's GND as well. LINE− is the carrier's
  ground through 1 kΩ, so the amp rejects any voltage between the two boards' grounds. Tied to the amp's GND, LINE− would close a
  ground loop through J6 and J5.
- **Input impedance:** 10 kΩ or more per leg. The carrier drives each leg through 1 kΩ, so full scale arrives at ≈ 0.83 Vrms
  differential into 10 kΩ (−1.7 dB), and ≈ 3.0 dB lower into 5 kΩ. Choose the amp's gain for that level. J5 should sit at ≈ 0 V DC
  (the carrier's TEST_PLAN 5.16 confirms it).
- **Mute (J6.4, MUTE):** the carrier pulls MUTE to GND through Q2 and a 470 Ω resistor to let the speaker play, and leaves it open to
  mute. So:
  - Pull MUTE up on the power board, with 4.7 kΩ or more to at most 5 V. The amp is then muted whenever the carrier is unpowered,
    booting, reset or unplugged.
  - Low (speaker on) is ≈ 0.24 V against a 10 kΩ pull-up and ≈ 0.5 V against 4.7 kΩ. The amp's mute or shutdown input has to read that
    as "play" and a pulled-up line as "mute". If the chosen amp's pin works the other way, invert it on the power board.
- **Speakers:** the speaker wiring is on the power board. The cone's spade tabs (6.3 mm / 4.8 mm) take crimped quick-disconnects. Most
  class D amps have a bridged output, so neither speaker wire may be grounded.

### Display
- Supply the display's 5 V directly from the power board, with its own wire pair, so its current pulses (ESP32-S3 Wi-Fi, backlight PWM)
  never flow through the carrier's `+5V`.

### Wiring and placement
- Use ferrules or solid wire in the screw terminals. Tinned stranded wire creeps under screw pressure and loosens.
- Run J5 as a short twisted pair, away from the guitar input and the speaker wires.
- Keep the power board's regulators and class D amp away from the carrier's audio section. The carrier's J6 is on its rear
  edge and J5 on its right edge, away from the front-edge jacks.
- The carrier is designed to survive 5 V landing on BAT or MUTE, and probably on LINE+ (it puts ≈ 3 mA into the codec output's
  protection). Check every wire against the silkscreen label before powering up anyway.
