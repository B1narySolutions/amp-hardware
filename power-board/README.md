# Power board

The power board's KiCad project, rev 1 (`Rev1_Power_Board.kicad_pro`).

## What the audio board needs from it

The audio board (`../audio-board/rev2/`) connects through two screw terminals, six wires in all. This is the contract
between the two boards; `../audio-board/rev2/DESIGN.md` gives the reasons ("Power board connector (J6)", "Output mute",
"Speaker send", "Display connector (J3)", "What each connector can see"). If the power board departs from a number here,
change it here and in that DESIGN.md together, and review both boards against the new number.

| Signal | Driven by | Promise |
|---|---|---|
| 5V (J6.1) | Power board | 4.75–5.25 V (5.0 V ± 5 %), never above 5.5 V |
| BAT (J6.3) | Power board | 0–3.3 V, source impedance 10 kΩ or less |
| MUTE (J6.4) | Power board pulls up, audio board pulls down | Pull-up of 4.7 kΩ or more to at most the 5 V rail; the audio board pulls it to ≈ 0.24–0.5 V to play |
| LINE+ (J5.1) | Audio board | Audio, full scale ≈ 1 Vrms (1.5 V peak), ≈ 0 V DC, from ≈ 1 kΩ (at most 1.1 kΩ) |
| LINE− (J5.2) | Audio board | The audio board's ground through ≈ 1 kΩ (0 V ± 10 mV) |
| LINE+ / LINE− load | Power board | 10 kΩ–1 MΩ per leg |

### Connections
J6 (4-way) and J5 (2-way) are 3.5 mm screw terminals on the audio board. Seen from the wire side, J6 reads 5V, GND, BAT,
MUTE from left to right (pins 1–4); J5 is 1 LINE+, 2 LINE−. The audio board's J3 (GND, TX, RX) is the UART to the
display, not a power board connection.

### 5 V supply (J6.1, J6.2)
- 4.75–5.25 V at J6, never above 5.5 V: the audio board's op-amp and headphone amp run straight from it. Its firmware
  won't start audio below 4.7 V or keep it running below 4.4 V.
- The audio board draws well under 1 A (the Daisy roughly 100–200 mA). One 5 V wire and one GND wire.
- The audio board has reverse-polarity protection (Q1), but nothing else on the power board should rely on it.

### Power switch and battery
- **The battery:** a Talentcell power bank, "72W 100Wh 12V/8300mAh 9V/11000mAh 5V/20000mAh"
  ([eBay listing](https://www.ebay.com/itm/278396464326)), a finished pack with its own charger and protection. The
  power board takes its 12 V output. The listing doesn't say whether that is regulated, so assume 9.0 V empty to 12.6 V
  full, measure it, and fuse the input.
- **Put the power switch and the low-battery cutoff on the power board.** The audio board can't turn the power off, and
  its firmware assumes the power can disappear at any time.
- **Battery level (J6.3, BAT):** a voltage proportional to the battery, scaled to 0–3.3 V, from 10 kΩ or less. The audio
  board loads it with 20 kΩ (R13 + R22) and reads V × 10k / (20k + R_source). Rev 1 uses 30k over 10k: a ratio of 0.25
  (3.15 V at 12.6 V) from 7.5 kΩ. Record the ratio and source impedance in the audio board's DESIGN.md. Switch the
  divider off with the 5 V, so it doesn't drain the battery.

### Speaker amp
- **Input (J5):** wire LINE+ to the amp's IN+ and LINE− to its IN− **only**, never to the amp's GND as well. LINE− is the
  audio board's ground through 1 kΩ, so the amp rejects any voltage between the two boards' grounds; tied to the amp's
  GND it would close a ground loop through J6 and J5.
- **Input impedance:** 10 kΩ or more per leg. The audio board drives each leg through 1 kΩ, so full scale arrives at
  ≈ 0.83 Vrms differential into 10 kΩ (−1.7 dB), and ≈ 3.0 dB lower into 5 kΩ. J5 should sit at ≈ 0 V DC (the audio
  board's TEST_PLAN 5.16).
- **Mute (J6.4):** the audio board pulls MUTE to GND through Q2 and 470 Ω to play, and leaves it open to mute. Pull it up
  with 4.7 kΩ or more to at most 5 V, so the amp is muted whenever the audio board is unpowered, booting, reset or
  unplugged. Low is ≈ 0.24 V against 10 kΩ and ≈ 0.5 V against 4.7 kΩ; the amp has to read that as "play".
- **The speakers:** 10" 4 Ω cones, one at a time. Neither speaker wire may be grounded (the output is bridged).
  - Jensen MOD10-50, 4 Ω ([Amplified Parts](https://www.amplifiedparts.com/products/speaker-jensen-mod-10-mod10-50-50w)):
    50 W, ≈ 95 dB at 1 W / 1 m, 3.08 Ω DC (distributor figures). Roughly 105–107 dB at 1 m from the amp's ≈ 17 W.
  - Skar Audio FSX10-4 ([eBay listing](https://www.ebay.com/itm/187823581724)), a "flat" pro-audio midrange: 400 W, no
    sensitivity or response figures.

#### The amp: TI TPA3118D2
How the TPA3118D2 (datasheet SLOS708G) meets each point:
- **Mute:** MUTE is active high with TTL levels, so `SPK_MUTE` wires straight to it with the pull-up above. Its levels
  follow AVCC, which is always above 5 V here. Use SDZ (active low) for the power board's own sequencing.
- **Input:** fully differential, each leg through its own coupling cap of the same type and value (the datasheet
  suggests 1.5 µF at 20 dB).
- **Gain: 20 dB, the lowest setting.** Input impedance falls from 60 kΩ at 20 dB to 9 kΩ at 36 dB, ±20 %, so 36 dB
  breaks the 10 kΩ-per-leg minimum. Full scale (≈ 0.98 Vrms after the 1 kΩ legs into 60 kΩ) becomes ≈ 9.8 Vrms, which
  already clips on the battery: ≈ 1.5 dB below full scale on a full pack, ≈ 2.5 dB at 11.1 V, ≈ 4.5 dB near 9 V. The
  firmware caps the speaker level about 5 dB below full scale.
- **Supply:** 4.5–26 V, straight from the 12 V output.
- **Output:** both channels in PBTL for the single speaker. Into 4 Ω, roughly 17 W at clipping on a full pack, 13 W at
  11.1 V and 9 W near 9 V (allowing ≈ 0.3 Ω for the switches and inductors), drawing up to ≈ 1.6 A on loud peaks.
- **Package:** HTSSOP-32 with a thermal pad. Lay the pad out with vias that can be soldered from the back, or use hot air.

### Display
Supply the display's 5 V directly from the power board, on its own wire pair, so its current pulses (Wi-Fi, backlight
PWM) never flow through the audio board's `+5V`.

### Wiring and placement
- Use ferrules or solid wire in the screw terminals. Tinned stranded wire creeps and loosens.
- Run J5 as a short twisted pair, away from the guitar input and the speaker wires.
- Keep the regulators and class D amp away from the audio board's analog circuits.
- The audio board survives 5 V landing on BAT or MUTE, and probably on LINE+ (≈ 3 mA into the codec output's
  protection). Check every wire against the silkscreen before powering up anyway.
