# Amp board — design

Why the board is the way it is. The schematic holds the circuit, the values and the part numbers, and its notes say
what each part does; this file holds the reasons, the limits and the decisions. `TEST_PLAN.md` is the bring-up
procedure. Each fact has one home; write the design as it stands, not its history (git has that).

The board holds a Daisy Seed3 (A1, in two 1×20 sockets), the analog inputs and outputs, the headphone amp, the battery
input, the 5 V distribution and the TPA3118D2 speaker amp, on one 4-layer board. The schematic has two sheets:
- **Sheet 1, `amp-board.kicad_sch`:** the audio circuit. Its designators start at 1.
- **Sheet 2, `power.kicad_sch`:** the battery input, 5 V distribution and speaker amp (first designed by William Anderson
  as a separate power board). Its designators start at 101; X101–X109 are ordered parts that aren't on the board.

The 5 V buck, a DFRobot DFR0571 module, stays off the board on J106 and J107. Volume, tone, input trim and mute come from
the touchscreen over the UART, so the board has no pots or encoder.

The circuits began as the two boards in `../legacy/`. This board is its own design and doesn't have to match them.

## Signal paths

U1 is a TLV9061 (SOT-23-5), the guitar input buffer, on `+5V`. The AUX input and both outputs connect to the Daisy with
no op-amp.

### Mid-rail reference (VREF)
R6/R7 (10k/10k) from `+5V`, with C7 (47 µF): `VREF` ≈ 2.5 V. With 5k of source impedance C7 gives a ≈ 0.7 Hz corner, which
keeps noise on `+5V` out of `VREF`. Its only load is R1.

### Guitar input (J1 → `AUDIO_IN_1`)
J1 tip → C1 (100 pF to GND) → FB1 → C2 (47 nF C0G) → R1 (1M to `VREF`) → R2 (1k) → C18 (100 pF to GND) → U1A follower →
R20 (470 Ω) → `AUDIO_IN_1` (Daisy pin 16). J1's tip switch shorts the tip to GND with nothing plugged in.
- **C2** blocks `VREF`'s DC from the guitar: a 3.4 Hz high-pass with R1. C0G isn't piezoelectric, so knocks don't become
  signal at this 1 MΩ node. 47 nF is the largest C0G in 0805.
- **R1** sets the 1 MΩ load and the DC bias. **R2** protects U1A's input from plug-in transients.
- **RF filtering.** The display's ESP32 transmits Wi-Fi in bursts, and an op-amp input rectifies RF into a buzz at the
  burst rate. C1 shunts RF at the jack; FB1 (Murata BLM18HG601SN1D, 600 Ω at 100 MHz, rising toward 1 GHz) blocks the
  rest and is a fraction of an ohm at audio; C18 with R2 is a 1.6 MHz low-pass at U1A's pin. The guitar sees C1 + C18 as
  ≈ 200 pF more cable capacitance (a cable is 500–1000 pF).
- **Unity gain, no pot.** A pot at mid travel put ≈ 250 kΩ in front of U1A (noise, and an ~80 kHz pole). Input trim is in
  firmware.
- **Passive pickups only.** With the module's ≈ 5 kΩ input, R20 costs ≈ 0.8 dB, so the Daisy's 3.6 Vpp full scale is
  reached at ≈ 3.9 Vpp at J1, ≈ 12 dB above a 1 Vpp hard strum.
- **R20 limits current into the Daisy pin** to ≈ 1–2 mA if U1 (≈ 4.8 Vpp swing on 5 V) ever exceeds the input's ±1.8 V
  absolute maximum (Seed3 datasheet, Table 1). Pin 16 sits at `VREF`; the input is AC-coupled on the module.

### AUX input (J2 → `AUDIO_IN_2`)
J2 tip and ring → R3/R4 (10k each, passive stereo-to-mono sum) → R5 (470 Ω to GND) and C3 (1 nF) → `AUDIO_IN_2` (Daisy
pin 17). J2's detect switch is not connected.
- **No buffer, no coupling cap.** The Seed3's inputs are AC-coupled on the module (Table 1 note) and the source is a
  phone or laptop output.
- **Daisy input impedance: 5 kΩ ± 20 %, assumed.** That is the TAC5242's figure at its own pins (TAC5242 datasheet, ADC
  parameters and 7.3). The Seed3 datasheet gives none for the module pin; its own input circuits drive the pin through 1k
  or 100 Ω (Figures 3.2, 3.4), which fits. TEST_PLAN measures the level.
- **R5 sets the level and protects the unpowered codec.** A source can keep playing into J2 with the board off, while the
  codec's inputs are rated −0.3 V to AVDD + 0.3 V with no injection rating (TAC5242 datasheet, 6.1). With R5 at 470 Ω a
  2 Vrms source reaches ±0.23 V at worst. 560 Ω gives ±0.27 V (≈ 1.2 dB louder); 680 Ω passes 0.3 V. R5 is also the
  source's DC return.
- **Level:** the same signal on both channels arrives at −22.2 / −22.0 / −21.9 dB for a 4k / 5k / 6k codec input
  (−21.3 dB with the Daisy out), so 2 Vrms reaches the Daisy at ≈ 0.45 Vpp (−18 dBFS). One channel alone is −28.0 dB.
  The firmware adds the gain back (≈ 18 dB takes 2 Vrms to full scale); the ADC's 119 dB range leaves room.
- **C3** filters RF from the cable: ≈ 400 kHz against the node's ≈ 400 Ω (≈ 370 kHz with the Daisy out).
- **Source load:** ≈ 10.4–10.9k per channel. **Use:** backing tracks, mixed in after the amp model, to both outputs.

### Headphone output (`AUDIO_OUT_1` → J4)
`AUDIO_OUT_1` (Daisy pin 18) → R10 (3.3k) / C9 (1 nF to GND) → `HP_SOURCE` → C10/C11 (470 nF C0G) → U2's − inputs. U2's
+ inputs go to GND through C22/C23 (470 nF C0G). U2 (TPA6130A2RTJR) drives J4 (`HP_L` tip, `HP_R` ring) directly.
- **What the Seed3 outputs are rated for:** 1 Vrms at 0 dBFS (Seed3 datasheet, Table 3). The datasheet gives no output
  impedance, minimum load, coupling or DC level for pins 18/19.
  - **Line-out only.** One single-ended pin per channel at 1 Vrms matches the TAC5242's "Single-ended output; Line-out
    only" mode (TAC5242 datasheet, Table 7-10), minimum load 600 Ω. The module can't drive headphones, hence U2.
  - **DC level: probably 0 V, not confirmed.** Seed3 Figure 3.9 wires pin 18 straight across a volume pot to GND, which
    suggests no DC on the pin. TEST_PLAN 6.16 measures it.
- **No buffer.** Each U2 − input is ≥ 18.5 kΩ (37 kΩ differential at the highest gain, TPA6130A2 datasheet 9.2.2.1), so
  the Daisy sees ≥ 12.5 kΩ.
- **R10/C9** filter the DAC's out-of-band noise: ≈ 50–65 kHz.
- **Level and volume:** U2's gain is set over I2C in 64 steps from −59.5 dB to +4.0 dB, with a mute bit per channel
  (datasheet Table 2). R10 against both inputs costs ≈ 2–2.7 dB, so full scale reaches U2 at ≈ 0.75 Vrms. Volume word
  0x35 (+0.1 dB) gives ≈ 0.75 Vrms per output: 35 mW into 16 Ω, 18 mW into 32 Ω. Word 0x30 (−2.1 dB) gives
  0.6 Vrms. Both channels play in phase, so the firmware stays at or below 0x35 until TEST_PLAN 8.8 has checked 16 Ω.
- **Low end:** ≈ 17 Hz at the highest gain (two 470 nF in series into ≥ 37 kΩ), lower at lower gains.
- **U2 (DirectPath):** an internal charge pump makes a negative rail, so the outputs sit at 0 V with no output caps
  (offset 0.4 mV maximum). 2.5–5.5 V supply; 4 mA playing, 0.4 µA in hardware shutdown; PSRR 109 dB; 9 µVrms output noise;
  pop suppression; 8 kV ESD on the outputs; minimum load 12.8 Ω. The charge pump runs at 300–500 kHz.
- **Wiring** (datasheet Figure 45): signal on each − input and each + input AC-grounded at U2, which makes U2 inverting.
  C13 is the flying cap, C14 holds CPVSS, C15 bypasses pin 20 and C12 pin 12: 1 µF X7R 50 V each, the datasheet's value.
- **I2C and shutdown:** address 0x60. SDA/SCL on Daisy pins 13/12 (I2C1), pulled up to `3V3_D` (pin 38) by R33/R32 (2.2k).
  `HP_SD` on pin 27, with R34 (100k) to GND: U2 is in hardware shutdown while the Daisy is out, booting or in reset.
  SD, SDA and SCL are rated −0.3 to 7 V whatever VDD is (datasheet 7.1), so the Daisy can drive them with `+5V` off.
  Shutdown clears the registers: U2 restarts muted with its outputs disabled.
- **Supply filter (`HP_5V`):** R29 (2.2 Ω) from `+5V` and C21 (10 µF X7R), about 6–10 kHz, so the charge pump's ripple
  reaches `+5V` about 30 dB lower. A bead wouldn't do it: beads are a few ohms at 400 kHz. R29 drops up to ≈ 0.2 V at
  full scale into 16 Ω.

### Headphone detect (`HP_DETECT`)
J4 (Same Sky SJ3-35063AG; [datasheet](https://www.sameskydevices.com/product/resource/sj3-3506x.pdf)): pins 1/2/3 are
sleeve/ring/tip. Pins 5 and 6 are an isolated switch that closes when a plug is in: pin 5 to GND, pin 6 to `HP_DETECT`
(Daisy pin 23, PA3), with TP1. **Low = headphones in.**
- **No external pull-up or RC.** The firmware enables PA3's pull-up and debounces, as in the Seed3 datasheet's switch
  circuits (Figures 2.1, 2.2).

### Speaker send (`AUDIO_OUT_2` → U101)
`AUDIO_OUT_2` (Daisy pin 19) → R11/C16 (1k/3.3 nF, ≈ 48 kHz) → `LINE_OUT`, with R12 (100k) to GND, → C108 → U101 IN+.
`LINE_REF` is GND through R21 (1k), → C109 → U101 IN−.
- **No buffer:** R11 plus U101's 60 kΩ input is far above the 600 Ω line-out minimum. R11 costs ≈ 0.23 dB. With
  `LINE_OUT` shorted the Daisy still sees 1k.
- **No DC-blocking cap on this side.** A DC level on pin 19 would damage nothing: C108 blocks it from U101, and R12 would
  carry ≈ 16 µA. It could only click when the codec starts or stops, which happens while U101 is muted. If TEST_PLAN 6.16
  finds DC and a click gets through, the fix is 10 µF in series between C16 and `LINE_OUT`.
- **R12** is the DC return for the Daisy's output coupling.
- **Pseudo-differential.** LINE− is the source-side ground through 1k, not an inverted signal. U101 amplifies only
  LINE+ − LINE−, so the ground difference between the Daisy's corner and the class D's is rejected. R21 equals R11
  because the rejection depends on equal source impedances, and it sits beside R11, away from the class D's currents.
- **Why a separate speaker output:** the speaker amp can shut down while headphones are in, mute ramps don't click, and
  the two outputs get independent levels.

### Jack ESD protection (D1–D5)
Every jack contact that carries a signal has a Nexperia PESD5V0S1BA (SOD-323) to GND at the jack: D1 `GTR_TIP`, D2/D3
`AUX_TIP`/`AUX_RING`, D4/D5 `HP_L`/`HP_R`. It is bidirectional, so it never conducts on an audio signal's negative half;
5 V working voltage; 5 nA leakage against the 1 MΩ input; 35 pF. The J2/J4 detect switches are isolated from the plug and
need none.

### Output mute (STM32 watchdog)
A hung Daisy can loop its last audio buffer at full level, so every output must go silent when audio stops.
- **How:** the firmware feeds the STM32's independent watchdog (IWDG) only from the audio callback. If the callback
  stops, the IWDG resets the STM32, and its pins float through reset, boot and DFU.
- **Speaker:** `SPK_EN` (Daisy pin 28) drives Q2's gate, with R17 (100k) to GND. Q2 (2N7002) pulls `SPK_MUTE` low to
  play; R107 (10k, sheet 2) pulls it up to `+5V_RAW` to mute. R108 (2.2k) and C124 (1 µF) carry it to U101's MUTE.
  - **Levels:** low is a few mV against U101's 0.8 V VIL; high is ≈ 5 V against 2 V VIH and MUTE's PVCC + 0.3 V maximum.
  - **Timing:** mute passes 2 V in ≈ 6.2 ms (R107 + R108 into C124); unmute falls through R108 (2.2 ms). Both edges
    slew ≈ 2.3 V/ms or slower, inside the TPA3118's 10 V/ms limit.
  - **Why Q2:** R107 holds `SPK_MUTE` at 5 V whenever the battery is on. An open-drain Q2 keeps that from back-powering
    an unpowered Daisy, and keeps the speaker muted unless the Daisy is running.
- **Headphones:** R34 holds `HP_SD` low through a reset, and the firmware mutes U2 over I2C while running.
- **The codec** powers down its DAC when its clocks stop (TAC5242 datasheet, 7.4.1), which silences both outputs after a
  reset. It doesn't help while a DMA loops a stale buffer with the CPU hung, which is why the IWDG must reset the chip.
- **Trade-off:** the watchdog is inside the chip it watches. Never feed it from the main loop.

## Power section (sheet 2)
### Battery input
- **The battery** is a Talentcell power bank (72 W, 100 Wh). The board takes its 12 V output, assumed 9.0 V empty to
  12.6 V full (unregulated or not, the listing doesn't say).
- **Path:** J101 (Same Sky PJ-102AH, 2.0 mm pin, 5 A) → F101 → SW101 (terminal to the panel switch, an NKK S1B rated 5 A)
  → Q101 → `VBAT_PROTECTED`. Everything is after SW101, so the board draws nothing with the switch off.
- **Q101 (IRF4905)** is the reverse-polarity protection: drain to the switch, source to the load, gate to GND through R101
  (10k), D101 (BZT52C12) from gate to source to hold VGS near −12 V (rated ±20 V).
- **F101 (Bel 0683G3150-01):** 3.15 A slow-blow SMD fuse, 125 V DC, 2 kA interrupting, melting I²t 16.9 A²s, 0.028 Ω cold
  (0683G datasheet). The switch-on surge into C111/C112 and the DFR0571 is estimated under 0.2 A²s. The board draws at
  most ≈ 2.4 A on peaks. It is soldered by hand (JLC has none) and isn't replaceable in a holder.
- **`VBAT_PROTECTED`** feeds U101's PVCC through R105 (0 Ω 2512), the DFR0571 through J106, and the battery divider.
- **Overvoltage:** the board survives 24 V on J101 (U101 26 V; C111, C112, C115 25 V), and the DFR0571 is rated to 28 V.

### 5 V supply and distribution
- **The DFR0571** takes `VBAT_PROTECTED` from J106 and returns 5 V on J107 as `+5V_DFR`. DFRobot's datasheet
  (2018-08-07): 8–28 V in, 5 V ± 0.1 V out, 3 A peak ("not 3 A or above for a long time"), under 50 mVpp ripple, 0.5 mA
  with no load, 0.5 MHz, not isolated, so its two grounds are one node. It asks for more than the minimum input at high
  load. It names no continuous rating (the board draws ≈ 0.75 A) and no short-circuit, overcurrent or reverse protection,
  so the design counts on none.
- **Q102 (AO3401A)** between `+5V_DFR` and `+5V_RAW`, gate to GND, blocks a reversed 5 V source on J107 from `+5V_RAW`
  (U103's VDD is rated −0.3 V minimum). It drops ≈ 45 mV at 0.75 A.
- **`+5V_RAW`** feeds two filtered branches, plus U103 and the pull-ups R107, R109, R112, R113:
  - **Audio:** FB101 (220 Ω at 100 MHz) → `+5V`, with C105; optional bulk C104 through JP102.
  - **Display:** FB102 → `+5V_DISPLAY` → J105, with C107; optional bulk C106 through JP104.
  - JP101 and JP103 bypass the beads. The jumpers are experiments: set them from bring-up.
- **Budget:** `+5V` must stay within 4.75–5.25 V. Q102 and FB101 cost about 45 mV, so a DFR0571 at 4.85 V is enough.

### Supervisor, shutdown and mute
- **U103** (TPS3808EG50, 4.65 V threshold, 20 ms delay) watches `+5V_RAW`. Its open-drain output (`AMP_PG`, R109 10k
  pull-up) drives `AMP_SDZ` through R110 (2.2k), with R111 (100k) to GND and C125 (1 µF). U101 stays shut down until the
  5 V has been good for 20 ms. JP105 pulls MR low to force a reset, which also clears U101's fault latch.
- **FAULTZ** (R112 10k pull-up, R114 18k to GND, TP109): U101 latches off on an output short, overtemperature or DC at
  the output (TPA3118 datasheet, Table 4), until SDZ goes low. The divider puts its high level at `+5V_RAW` × 18/28
  (≈ 3.2 V; 3.05–3.54 V for 4.75–5.5 V) for Daisy pin 32, reached through R30 (1k) on sheet 1. With `+5V_RAW` off the pin
  sees 0 V. R30 limits the current to ≈ 3.3 mA if the firmware ever drives pin 32 high against a fault.
- **D102, D103** (BAT54H, anode on SDZ and on MUTE, cathode on PVCC) hold SDZ and MUTE within a Schottky drop of PVCC.
  Their leakage (2 µA maximum at 25 °C) moves neither pin's low level by more than a fraction of VIL.
- **Power sequence:** PVCC rises first, then the 5 V; U103 releases SDZ 20 ms after `+5V_RAW` passes 4.65 V. At
  switch-off PVCC falls at about 1.2 V/ms while C124 and C125 hold MUTE and SDZ for milliseconds, so those pins would sit
  volts above PVCC and discharge ≈ 1.2 mA each into U101's protection diodes, which TI doesn't rate. D103 and D102 take
  that current (0.32 V at 1 mA). TEST_PLAN 3C.9 measures it.

### Battery level
R102/R103 (100k/10k, 1 %) divide `VBAT_PROTECTED` onto `BATT_SENSE` (Daisy pin 25): **VBAT / 11** within ±1.8 %, from
9.1 kΩ. 1.15 V at 12.6 V, 0.82 V at 9.0 V; 115 µA. C17 (100 nF) gives a ≈ 175 Hz corner and the ADC's sampling charge.
Pin 25 (PA7) is not 5 V tolerant; even 24 V on J101 puts only 2.2 V there.

### Speaker amp (U101, TPA3118D2)
- **Mono PBTL:** LINP and LINN to GND; OUTPR + OUTNR are SPK+, OUTPL + OUTNL are SPK− (SLOS708G, 7.4.1). MODSEL to GND
  (BD mode); PLIMIT to GVDD (no power limit).
- **Gain 20 dB, master:** R104 (5.6k) from GAIN/SLV to GND (Table 1). Input impedance 60 kΩ ± 20 % per leg. Above 32 dB
  it drops to 9 kΩ.
- **Inputs:** C108/C109 (470 nF C0G, matched): a 5.6 Hz high-pass. C0G keeps both legs matched and isn't microphonic.
- **Supplies:** PVCC through R105, with C111/C112 (100 µF) and C113/C114 (100 nF) at the pin pairs; AVCC through R106
  (10 Ω) with C115/C116; GVDD with C110.
- **Switching frequency:** AM0–AM2 to GND through JP106–JP108 (bridged in copper on the back): ≈ 400 kHz, near U2's
  charge pump. If a steady tone shows up with no signal, cut one jumper to move it (TEST_PLAN 4C.10).
- **Output:** bootstrap caps C117–C120 (220 nF), then L101/L102 (10 µH) with C121/C122 (680 nF), ≈ 61 kHz, into J102
  (pin 2 SPK+, pin 1 SPK−). The output is bridged: neither speaker wire may be grounded.
- **Levels:** full scale (≈ 0.97 Vrms after R11 into R12 and U101's input) becomes ≈ 9.7 Vrms, which clips on the battery (≈ 1.5 dB below full scale on a full pack,
  ≈ 4.5 dB near 9 V), so the firmware caps the speaker level about 5 dB down. ≈ 17 W into 4 Ω at clipping.
- **Speakers:** a Jensen MOD10-50 or a Skar FSX10-4, 4 Ω, one at a time.

## Audio 5 V (`+5V`)
`+5V` comes from FB101 through the `+5V_AUDIO` sheet pin and feeds Daisy VIN (pin 39), U1, U2 (through R29), `VREF` and
the `5V_SENSE` divider. C5 (47 µF electrolytic, whose ESR damps ringing with the DFR0571's wiring) and C4 sit at the
entry; C6 at U1; C12, C15 and C21 at U2.

### Running from USB alone
USB doesn't drive the VIN pin: on the module, USB VBUS and VIN each reach the regulators through their own diode (Seed3
datasheet, Figure 1.0). So with USB plugged in and the battery off, the Daisy runs while `+5V`, `+5V_RAW` and PVCC are at
0 V, and any Daisy pin that is high or carries audio drives an unpowered part.
- **Display UART:** TX idles high into the unpowered display through R8 (10k): ≈ 0.27 mA.
- **U2:** its inputs are rated −2.5 V to 3.6 V whatever its supply (TPA6130A2 datasheet 7.1), so full-scale audio is safe.
- **U101's inputs** are rated −0.3 V to 6.3 V, absolute (SLOS708G 6.1). Full-scale negative peaks through R11 and C108
  would put up to ≈ 0.8 mA into their protection, so the firmware keeps `AUDIO_OUT_2` silent while `+5V` is off.
- **`5V_SENSE`** tells the firmware: R18/R19 (100k/100k) put `+5V`/2 on Daisy pin 22. `BATT_SENSE` wouldn't do, since a
  failed DFR0571 leaves it normal. Its source is 50k with no filter cap, so it needs a long ADC sample time.
- **Limit:** the firmware reacts in a few ms. If `+5V` collapses faster, the last few ms of audio reach U101's inputs.

## Connectors

### What each connector can see
The outside world the board is designed for. A design review checks every IC pin against these, one misuse at a time,
in each power state. Misuse may stop the board working, but must not damage it.

| Pin | Normal | Misuse that must not damage anything |
|---|---|---|
| J101 (12 V jack) | The power bank's 12 V output, 9.0–12.6 V, fused at 3.15 A | Reversed (Q101 blocks); a 19–24 V adapter |
| SW101 (panel switch) | The switch's two contacts, in series with the battery | — |
| J106 (to the DFR0571's input) | The module's input cable, a JST XH plug: pin 1 BAT+, pin 2 GND | Keyed, so only that cable fits, one way round. A cable crimped with its wires swapped shorts `VBAT_PROTECTED` to GND through the module's ground: F101 or the pack's protection stops it; the module's ground track may not survive (accepted) |
| J107 (from the DFR0571's output) | 5.0 V ± 0.1 V | Its two wires swapped: the module's output is shorted (accepted). A reversed bench supply: Q102 blocks. J107's and J105's pairs swapped with each other: everything still works |
| J105 (display 5 V) | The display's supply, up to ≈ 0.5 A | Shorted: limited only by the DFR0571 |
| J102 (speaker) | A 4 Ω speaker, bridged | Shorted, or one wire to GND: U101 latches off |
| J3.2 TX | The display's RX: high impedance, clamped to −0.5…3.8 V, 1 mA at most | A 5 V wire on TX |
| J3.3 RX | The display's TX: 0–3.3 V logic from ≈ 50 Ω | A 5 V wire on RX |
| J1 tip (guitar) | Passive pickups, 1.5 V peak from ≈ 10 kΩ, 20 Hz–20 kHz | An 18 V boost pedal at full output, 9 V peak from 1 kΩ (may distort, must survive) |
| J2 tip/ring (AUX) | A 2 Vrms laptop, 2.83 V peak, the same signal on both | Pro line out, ±5 V from 10 Ω (see "Open items") |
| J4 tip/ring | Headphones, 16 Ω or more | — |
| J4.6 detect | Open, or switched to GND with a plug in | — |

Power states: **on**; **Daisy out**; **USB only** (see "Running from USB alone"); **off** while a guitar or phone still
plays; **reversed** (battery at J101, or J107's wires). **Never 5 V alone on J107** (see "Decisions"). The jack pins are
touched by people, so each has an ESD diode; the speaker outputs see ESD through C121/C122.

### Display connector (J3)
J3 is a 3-way screw terminal on the left edge: 1 GND, 2 TX, 3 RX. The display takes its power from J105, beside it.
- **R8, R9 (10k)** in series with TX and RX limit the current when a wire lands on the wrong terminal, or when the
  display and the Daisy power up at different times.
- **R24 (100k)** pulls RX to GND. With R9 it divides a 5 V wire on RX to at most 4.78 V (from 5.25 V) at pin 15 (PB7, a 5 V tolerant pin); the
  display's 3.3 V high arrives at ≈ 3.0 V. It also detects the display: a line held low means none. PB7's internal
  pull-up must stay off.
- **C19/C20 (10 pF C0G)** on the Daisy side of R8/R9 cut 2.4 GHz by ≈ 60 dB.
- **Baud rate:** 10k with ≈ 60 pF is ≈ 0.6 µs: fine to 230400 baud, not 921600.

## Firmware requirements
- **IWDG:** start it early in boot, ≈ 10 ms timeout, fed **only** from the audio callback.
- **Outputs:** speaker mix on output 2, headphones on output 1. Start the codec at digital silence and ramp up. End the
  chain with a limiter and a NaN/Inf guard. Cap the speaker level about 5 dB below full scale.
- **`SPK_EN` (pin 28):** a low output at start; high after the first audio callback; low while headphones are in.
- **`HP_DETECT` (pin 23, PA3):** internal pull-up on, debounced, **low = headphones in**. Going in: ramp `AUDIO_OUT_2`
  down, then `SPK_EN` low. Coming out: `SPK_EN` high, then ramp up.
- **`5V_SENSE` (pin 22):** longest ADC sample time; ≈ 2.4–2.5 V with `+5V` at 4.85–5.0 V.
  - Before starting audio, require more than 2.35 V (`+5V` ≥ 4.7 V) for 10 ms.
  - While running, sample it every block. Below 2.2 V, write silence from that block on and drive `HP_SD` low, until the
    start condition is met again. This applies on USB alone too.
- **U2 (I2C1, 0x60):** `HP_SD` (pin 27) a low output at start. Once `5V_SENSE` is good, drive it high, wait 5 ms, write
  register 1 = 0xC0 (0xD0 for dual mono) and register 2 = the volume with the mute bits clear, ramping from a low word.
  Volume word ≤ 0x35 until TEST_PLAN 8.8; Mute before changing modes and before `HP_SD` low. If a
  write gets no ACK, keep `HP_SD` low and report it. U2 inverts.
- **`AMP_FAULTZ` (pin 32, D25, PA0):** an input with no pull, **low = speaker amp fault**, valid once `+5V` has been good
  for 50 ms. On a fault: mute the speaker send, `SPK_EN` low, show it on the display. Never set pin 32 as an output.
- **`BATT_SENSE` (pin 25):** VBAT = 11 × V(pin 25); send the level to the display every few seconds and warn when low.
- **Display UART:** 230400 baud or less; PB7's pull-up off; a line held low is "no display"; restart reception after a
  framing error. Volume and mute come from the display; ramp the changes.
- **AUX:** mix `AUDIO_IN_2` in after the NAM model and cabinet EQ, with its own level and ≈ 22 dB of make-up gain.
- **Settings:** save when they change (debounced), not at shutdown. The power switch can cut the power at any time.

## Decisions
Decisions the user accepted, with the reason.
- **PBTL ERC exclusions.** ERC's two U101 output-to-output conflicts are the datasheet's PBTL wiring, excluded in
  `amp-board.kicad_pro` with that reason, so any new error stands out.
- **Q102 at J107.** A reversed 5 V source there would put −5 V on all of `+5V_RAW`. The DFR0571's own wires can't do that
  (its grounds are common), so Q102 covers a bench supply or a module with its input ground open: one SOT-23 and 45 mV.
- **No 5 V alone on J107, ever: bench supply on J101 only.** With PVCC at 0 V and 5 V on `+5V_RAW`, D102 and D103 charge
  PVCC through R107–R110 to about 4.5 V, U101's minimum supply, with SDZ high, and it may start and stop. Normal power-up
  and power-down never get there, so the rule is procedural.
- **FAULTZ latches** until a power cycle or JP105: a fault does no damage, and an automatic retry would pulse a shorted
  speaker wire. It is not tied to SDZ.
- **J106 is a keyed JST XH header.** With two identical screw terminals side by side, the module's wire
  pairs could go in swapped, putting 12 V on everything on `+5V`. Still possible and accepted: J107's wires swapped, the
  input cable crimped backwards (TEST_PLAN 3A.3 and 3B.1 check for it), and J107 and J105 swapped (harmless).
- **U2 is a TPA6130A2:** JLC assembles the board, so the package needn't be hand-solderable, and JLC's stock and price
  favoured it. It has a hardware mute, I2C volume, and inputs rated with the supply off, for Daisy pins 12, 13, 27 and
  38. The + inputs have no resistor to match R10: no room.
- **Under 100 × 100 mm,** for JLC's 4-layer price break: the board is 100 × 78 mm. That is why F101 is a soldered SMD
  fuse and not a 5 × 20 mm fuse in a holder, and why L101/L102 stand upright.
- **Floorplan.** U2's input network is 20 mm from the class D's switching nodes, because the left column is
  full. The display's ground terminals are 26–31 mm from the guitar input's 1 MΩ node. `AUDIO_OUT_2` runs 32 mm on In2
  and `AUDIO_IN_2` 16 mm on B.Cu under the Daisy. TEST_PLAN stage 7 checks the noise.
- **J102's pins swapped** (pin 2 SPK+), so the speaker traces don't cross.
- **U101's, C110's and U2's ground pads join the F.Cu pour solidly:** fine-pitch routing leaves no room for two spokes,
  and both ICs are reflowed.
- **Vias in U2's and U101's exposed pads** may wick some solder; ask JLC to plug or tent them if the order offers it.
- **The VBAT branch to J106 runs on In2** (1 mm, 0.5 oz): it carries only the DFR0571's ≈ 0.75 A.
- **0.8 mm silkscreen text** in the dense areas (JLC recommends 1.0 mm): it prints with a 0.15 mm stroke.
- **Order without waiting for the legacy boards (2026-11-10).** The board is ordered when its own open items are
  acceptable. The legacy boards' bring-up informs the next revision, not this order. The cost is a possible respin if
  they turn up a fault in a circuit this board shares.

## Open items
- **Questions this board's own bring-up answers** (the board carries the means to act on each): the Daisy outputs' DC
  level (TEST_PLAN 6.16; fix in "Speaker send"), the switch-on surge through F101 (3C), beads or bypass (JP101, JP103),
  the optional bulk caps (C104/C106 with JP102, JP104), more bulk on PVCC, L101/L102's value, and headphone clicks.
- **AUX at pro line level with the board off:** ±5 V reaches the unpowered codec at ≈ ±0.4 V and ≈ 0.3 mA, past its
  rating. Rare, and the current is small; R5 at 330 Ω fixes it for ≈ 3 dB less level.
- **The DFR0571's output current limit** is not stated. Only the accepted mistakes that short its output depend on it.
- **No low-battery cutoff.** U103 watches only the 5 V, so the pack's protection or the DFR0571's dropout ends it. The
  firmware warns from `BATT_SENSE` first. Measure the pack's real output range (9.0–12.6 V assumed).
- **Q2's gate drive:** 3.3 V against a 2.1 V maximum threshold at 250 µA (a distributor's listing; Nexperia's PDF didn't
  download), for 0.5 mA: enough on paper. TEST_PLAN 6.9 records the level.
- **Headphone level and hiss:** check 16 Ω for clipping before raising the cap above 0x35 (TEST_PLAN 8.8).
- **Hot passive pickups:** confirm the hottest guitar's peaks stay below ≈ 3.9 Vpp at J1.
- **Watchdog mute:** stall the audio callback in a debug build and time the mute (TEST_PLAN 8.6).
- **Mechanical:** no enclosure drawing yet. Recheck the outline, jacks and holes against it. The Seed3's USB-C overhangs
  the rear edge by 1.55 mm. Front panel under 3 mm (the NRJ4HF's nut). Hold the Daisy in its sockets against vibration.
- **3D models:** J101 and L101/L102 have none.

## Layout

### Stackup
4 layers, 1.6 mm, JLC's JLC04161H-7628: 1 oz outer copper, 0.5 oz inner, 0.21 mm prepreg under each outer layer. Choose
the same stackup on JLC's order page. Black mask, white silkscreen; the narrowest mask web is 0.20 mm (U101's pins).

| Layer | Use |
|---|---|
| F.Cu | Every part, every audio net, the class D's power and output paths, a GND pour |
| In1.Cu | Solid GND under the whole board. No tracks |
| In2.Cu | GND fill, with the nets that have to cross the Daisy |
| B.Cu | GND pour, a PVCC pour under the class D, and the `+5V_RAW` trunk |

- **In1 is the reference for everything on F.Cu,** 0.21 mm below it: every audio net and switching node sees an unbroken
  plane. That is why the board has 4 layers.
- **One GND net, no split.** Separation comes from placement.

### Isolation
1. **Zones.** The Daisy stands upright in the middle, USB at the rear. Audio is on its left and in front of it, with all
   three jacks on the front edge. The battery entry runs along the rear edge and the class D sits at the right edge.
2. **High-current loops stay local:** J101 → F101 → SW101 → Q101 → R105 → U101 → L101/L102 → J102, with the return in the
   planes to J101. None of it passes under the Daisy or the audio side.
3. **Switching nodes** stay on F.Cu within ≈ 18 mm of U101, over In1.
4. **Distances from the switching nodes:** 60 mm to the guitar input's 1 MΩ node, 52 mm to `AUDIO_IN_1`, 41 mm to the
   AUX parts, 20 mm to U2's input network.
5. **The 5 V tree:** J107 → Q102 → `+5V_RAW`, then FB101 → the C5 star (one branch to Daisy VIN, one to U1, U2 and R18)
   and FB102 → J105. Display and Daisy current never flows in the analog branch, and the display's return stays at the
   left edge with J3, J105 and J107.
6. **Thermal:** U101's pad has nine vias and ten more under the body, with a mask opening on the back.

### Outline, placement and routing
- **100 × 78 mm,** 2 mm corner radius; the front panel is the bottom edge. Jacks on the front edge; the 5 V and display
  terminals together on the left edge; the battery entry along the rear edge; the speaker terminal on the right edge.
- **U2:** inputs toward its four C0G caps, outputs toward J4, charge-pump caps at their pins with no vias (TPA6130A2
  Layout Guidelines).
- **Widths:** battery, PVCC, output and speaker paths 1.5 mm; 5 V nets 1.0 mm (0.6 mm on the smaller branches); signals
  0.2–0.3 mm.
- **Around the Daisy's USB end:** its pins fill all four layers, so the three supply crossings go around the rear end,
  one per layer: `+5V` to VIN on F.Cu, the VBAT branch on In2, `+5V_RAW` on B.Cu.
- **Under the Daisy:** the module stands 8 mm off the board, so tracks (no parts) run between its pin rows.

### Design rules
`amp-board.kicad_pro` holds the minimums and net classes; `amp-board.kicad_dru` adds the per-class ranges. All are
within JLC's standard 4-layer limits.

- **`Power`:** the 5 V nets. **`HighCurrent`:** the battery, PVCC, output and speaker nets, sized for the 3.15 A fuse.
- **Thermal reliefs** on every GND pad, for an iron, except those in "Decisions".

## Parts sourcing
The schematic's fields are the only record of the part numbers (`../CLAUDE.md`, "Where each fact lives").
- **Build:** JLC assembles the SMD parts, all on top. The through-hole parts and F101 are soldered by hand from the
  DigiKey order. Check every polarised part in JLC's preview before paying.
- **Passive sizes:** resistors 0603 (R105 2512). Capacitors 0603 up to 220 nF and 0805 from 680 nF, since a ceramic
  loses capacitance with DC voltage, more in smaller cases. The C0G parts are larger for their value (C2 0805, the
  470 nF parts 1206), and C7 is 1210.
- **C0G** for every capacitor on the audio path (C2, C10/C11, C22/C23, C108/C109) and the filter caps (C1, C3, C9, C16,
  C18–C20).
- **J106's mate** (X103, X104): one lead cut in half, crimped into the housing. VIN+ goes in position 1 (J106's
  triangle). Mark it: both wires are black.
