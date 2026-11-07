# Audio board rev 3 — Post-Assembly Test Plan

Bring-up and acceptance tests for one hand-assembled **rev 3** board: audio board rev 2 and power board rev 1 on one 4-layer
board, built from the rev 3 schematic (`seed3-carrier.kicad_sch`, with the power sheet `power.kicad_sch` as sheet 2), its
fabrication package (`fab/B1NARY_SOLUTIONS_gerber.zip`) and its order (`seed3-carrier-digikey.csv`). Record the package name
in the log. Every expected number was computed from the rev 3 netlist (KiCad 10 export, commit 9a68f75) and the parts'
datasheets, with the working shown so it can be redone after a change. `DESIGN.md` describes the design and the reasons for
it, `CHANGES.md` lists what changed from audio rev 2 and power rev 1, and `../TEST_PLAN.md` is rev 2's plan, which this one
follows. Stage 1A keeps rev 2's item numbers so results compare across revisions.

Work through the stages in order and stop at the first failure. Each stage assumes the one before it passed, so a failure
stays localized: unpowered checks first, then the battery side alone, then the 5 V rails with the DFR0571, the analog paths
and the speaker amp **without** the Daisy, and only then with the Daisy fitted. Record results in the log at the end (one
copy per board serial). DESIGN.md "Open items" has audio rev 2 and power rev 1 brought up first: set this board's jumpers and
experiment parts from their results, and record the settings in the log.

## Powering rule: 12 V on J101, never 5 V alone on J107

Every powered stage runs from a current-limited 12 V bench supply on J101 (centre positive), with the DFR0571 wired to J106
and J107 as in use. Stage 2 and step 5.9 leave the DFR0571 disconnected, with nothing on J106 or J107, to check the battery
side on its own. **Never power the board from 5 V on J107 alone**, whether from a bench supply or from a DFR0571 fed from
anything but J106.

Why: U103 and the MUTE pull-up R107 run from `+5V_RAW`, while U101's PVCC comes from the battery. With `+5V_RAW` up and PVCC
at 0 V, U103 releases SDZ to ≈ 4.46 V (5.0 V × R111 / (R109 + R110 + R111)) and R107/R108 pull MUTE to 5 V, but the
TPA3118D2 rates both pins at −0.3 V to PVCC + 0.3 V (SLOS708G, 6.1) and publishes no injection rating. Fed from J101 the
order is safe: PVCC rises with the battery, and the DFR0571, a buck running from `VBAT_PROTECTED`, can't hold `+5V_RAW` above
it (3C.1 and 3C.9 check both edges). DESIGN.md "Decisions" records the rule.

The same applies to anything else that could lift `+5V_RAW` while the battery is off:
- **R105** (0 Ω, "amp isolation") stays fitted whenever U101 is. Without it PVCC sits at 0 V while `+5V_RAW` is up.
- **The Daisy on USB:** Q1 conducts backwards if `+5V` is lifted (its gate is at GND), and FB101 joins `5V_IN` to `+5V_RAW`.
  Step 5.0 checks that the Seed3 doesn't drive its VIN pin from USB before USB is ever used with the battery off.
- **The display:** if it has a USB port of its own, don't plug it into a computer while it is wired to J105 and the battery
  is off. Its 5 V would reach `+5V_RAW` through FB102.
- **Jumpers:** change JP101–JP104 only with the power off (JP102/JP104 would connect an uncharged 100 µF to a live rail).
  JP105 is shorted live on purpose in 3C.8 and 4C.7.

## Circuit summary (what is being tested)

**Power section (sheet 2)**

| Block | Parts | Function |
|---|---|---|
| Battery input | J101 (PJ-102AH), F101 (T3.15A 5 × 20 mm in an FX0457 holder), SW101 (terminal for the S1B panel switch), Q101 (IRF4905), R101, D101 (BZT52C12) | 9.0–12.6 V from the Talentcell pack → fuse → switch → Q101 → `VBAT_PROTECTED`, probe at **TP101**. Q101 is the reverse-polarity protection: the body diode lifts the source, R101 pulls the gate to GND, D101 holds VGS near −12 V |
| Battery level | R102/R103 (30k/10k), R13/R22 (10k/10k), C17 | `VBAT_PROTECTED` ÷ 4 from 7.5 kΩ → `BATT_SENSE_CONN` → halved again → Daisy pin 25: **VBAT = 11 × V(pin 25)**, ±2.4 % with 1 % parts. Switched by SW101 |
| 5 V buck (off-board) | J106, DFR0571, J107, Q102 (AO3401A), C103, C123 | J106 sends `VBAT_PROTECTED` to the module; its 5 V comes back on J107 as `+5V_DFR` and through Q102 (reverse protection, gate to GND) onto `+5V_RAW`, probe at **TP106** |
| Audio 5 V | FB101 (bypass JP101), C105, C104 (DNP, through JP102), Q1 (AO3401A), C4, C5 | `+5V_RAW` → bead → `5V_IN` → Q1 (reverse protection, kept from rev 2) → `+5V`, probe at C5 `+` |
| Display 5 V | FB102 (bypass JP103), C107, C106 (DNP, through JP104), J105 | `+5V_RAW` → bead → `+5V_DISPLAY` → J105, the display's own supply pair |
| Supervisor | U103 (TPS3808EG50), R109/R110/R111/C125, R113, JP105 | Holds U101's SDZ (**TP104**) low until `+5V_RAW` has been above 4.65 V for 20 ms (CT open), and pulls it low as soon as it sags. JP105 (normally open) forces a reset, which also clears U101's fault latch |
| Speaker mute | R107 (10k to `+5V_RAW`), R108/C124, Q2/R23/R17 | `SPK_MUTE` pulled up = U101 muted (MUTE high: outputs Hi-Z). `SPK_EN` (Daisy pin 28) high turns Q2 on and pulls it to ≈ 0.22 V = play. R17 keeps it muted while the Daisy is absent, booting or reset |
| Speaker amp | U101 (TPA3118D2), R104, R105, R106, C108–C116, C117–C120, R112 | Mono PBTL (LINP/LINN to GND), 20 dB master (R104 5.6k, 60 kΩ input per leg ±20 %), BD modulation at 400 kHz (MODSEL, AM0–AM2 to GND), no power limit (PLIMIT to GVDD). Inputs from `LINE_OUT`/`LINE_REF` through C108/C109, biased at 3 V inside. PVCC (**TP103**) from `VBAT_PROTECTED` through R105, AVCC through R106. FAULTZ (**TP109**, R112 pull-up) goes low on a latched fault |
| Speaker output | L101/L102 (10 µH), C121/C122 (680 nF), J102 | LC filter into J102: **pin 2 SPK+, pin 1 SPK−** (swapped from power rev 1). Bridged: neither terminal may touch GND |

**Audio section (sheet 1, rev 2's circuit)**

| Block | Parts | Function |
|---|---|---|
| 5 V decoupling | C6, C4, C5, C12, C15 | Bulk/HF decoupling on `+5V` (C12 at U2 PVDD, C15 at U2 SVDD) |
| Mid-rail reference | R7, R6 (10k/10k), C7 | `VREF` ≈ 2.5 V, probe at C7 |
| Guitar input | J1, C1, C2, R1 (1M), R2, U1A, R20 | ¼" input, tip shorted to GND when unplugged; 1 MΩ load; unity-gain buffer → R20 (470 Ω series) → Daisy `AUDIO_IN_1`. U1 is clean to ≈ 4.8 Vpp; the Daisy's full scale is 3.6 Vpp |
| AUX input | J2, R3/R4, R5, C3 | 3.5 mm TRS, passive stereo-to-mono sum, ~110 kHz RF filter, straight into Daisy `AUDIO_IN_2` (no buffer). R5 (470 Ω) sets the level: ≈ −22 dB with the same signal on both channels and the Daisy's ≈ 5k input, never more than −21.3 dB |
| Headphone filter | R10, C9 | Daisy `AUDIO_OUT_1` → ~80 kHz RC low-pass → `HP_SOURCE`, driving U2 directly |
| Headphone amp | U2 (MAX9722A), R25–R28, C10/C11, C12–C15 | DirectDrive stereo amp, inverting at a gain of −1, outputs at 0 V straight to J4 (`HP_L` tip, `HP_R` ring). SHDN tied to `+5V`: U2 is on whenever `+5V` is up |
| Headphone detect | J4.5/J4.6, TP1 | Normally-open switch closes to GND on plug insertion → `HP_DETECT` (Daisy pin 23, STM32 internal pull-up). **Low = headphones in.** Probe at **TP1** |
| Jack ESD | D1–D5 (PESD5V0S1BA) | Bidirectional ESD diode from each jack signal contact to GND |
| Speaker send | R11, C16, R12, R21 | Daisy `AUDIO_OUT_2` → ~48 kHz low-pass (R11/C16) → `LINE_OUT` → C108 → U101 IN+; `LINE_REF` (R21, 1k to GND) → C109 → IN−. R12 is `LINE_OUT`'s DC return |
| `+5V` sense | R18, R19 (100k/100k) | `+5V` divided to ≈ 2.5 V → `5V_SENSE` (Daisy pin 22). The firmware keeps both outputs silent while it reads low |
| Display UART | J3, R8, R9, R24 | GND / `UART_TX_CONN` / `UART_RX_CONN`; R8/R9 10k in series, R24 100k holds RX low with no display. The display is powered from J105 |
| Daisy | A1 + two 1×20 sockets | Plug-in module. R17 holds `SPK_EN` low (speaker muted) while it is absent, booting or reset. The firmware feeds the IWDG only from the audio callback; a reset stops the codec's clocks, which silences J4 and the speaker |

**Pinouts used below**

- U101 TPA3118D2 (HTSSOP-32, exposed pad = GND): 1 MODSEL (GND), 2 SDZ, 3 FAULTZ, 4 RINP, 5 RINN, 6 PLIMIT, 7 GVDD, 8 GAIN/SLV,
  9 GND, 10 LINP (GND), 11 LINN (GND), 12 MUTE, 13–15 AM2/AM1/AM0 (GND), 16 SYNC (not connected), 17 AVCC, 18/19 PVCC, 20 BSNL,
  21 OUTNL, 22 GND, 23 OUTPL, 24 BSPL, 25 GND, 26 BSNR, 27 OUTNR, 28 GND, 29 OUTPR, 30 BSPR, 31/32 PVCC. `OUT_P` = pins 27 + 29
  (→ L101 → SPK+), `OUT_N` = pins 21 + 23 (→ L102 → SPK−)
- U103 TPS3808EG50 (SOT-23-6): 1 RESET (`AMP_PG`), 2 GND, 3 MR (`AMP_MR`, 90 kΩ internal pull-up), 4 CT (open: 20 ms), 5 SENSE
  and 6 VDD (both `+5V_RAW`)
- Q101 IRF4905 (TO-220): 1 G, 2 D (SW101.2), 3 S (`VBAT_PROTECTED`). D101 (SOD-123): cathode on `VBAT_PROTECTED`, anode on
  Q101's gate
- Q1, Q102 AO3401A, Q2 2N7002 (SOT-23): 1 G, 2 S, 3 D. Q1: G GND, S `+5V`, D `5V_IN`. Q102: G GND, S `+5V_RAW`, D `+5V_DFR`
- U1 TLV9061 (SOT-23-5): 1 OUT, 2 V−, 3 IN+, 4 IN−, 5 V+
- U2 MAX9722A (TSSOP-16): 1 INL+, 2 SHDN, 3 PVDD, 4 C1P, 5 PGND, 6 C1N, 7 PVSS, 8 SGND, 9 INR+, 10 INR−, 11 SVDD, 12 OUTR, 13 SVSS,
  14 OUTL, 15 SVDD, 16 INL−. INL+, INR+, PGND and SGND to GND; SHDN, PVDD and SVDD to `+5V`; PVSS tied to SVSS
- J101: 1 centre pin (+), 2 sleeve (GND), 3 switched contact (not connected). SW101: 1 from F101, 2 to Q101's drain
- Left edge, rear to front: J106 (1 `VBAT_PROTECTED` "BAT+", 2 GND), J107 (1 `+5V_DFR` "5V", 2 GND), J105 (1 `+5V_DISPLAY`
  "DISP", 2 GND), J3 (1 GND, 2 `UART_TX_CONN` TX, 3 `UART_RX_CONN` RX). J106 and J107, side by side, are the DFR0571's
  input and return.
- J102 (right edge): 1 SPK−, 2 SPK+
- JP101: 1 `+5V_RAW`, 2 `5V_IN`. JP102: 1 `5V_IN`, 2 C104 `+`. JP103: 1 `+5V_RAW`, 2 `+5V_DISPLAY`. JP104: 1 `+5V_DISPLAY`,
  2 C106 `+`. JP105: 1 `AMP_MR`, 2 GND
- DFR0571 (U102, off-board): VIN+, GND, 5V OUT, GND. It isn't isolated: its two GND pads are one node
- J4 / J2 (SJ3-35063AG): 1 sleeve, 2 ring, 3 tip, 5 detect common, 6 detect NO (J2's 5/6 not connected)
- A1 (Daisy sockets, `A1.n` = Daisy pin n): 14 USART1 TX, 15 USART1 RX, 16 `AUDIO_IN_1`, 17 `AUDIO_IN_2`, 18 `AUDIO_OUT_1`,
  19 `AUDIO_OUT_2`, 20 GND, 22 `5V_SENSE`, 23 `HP_DETECT`, 25 `BATT_SENSE`, 28 `SPK_EN`, 39 `+5V` (VIN), 40 GND. All other
  Daisy pins are not connected. Probe the sockets while the Daisy is out; with it fitted the checks name a part on the same net
- Test points: TP1 `HP_DETECT`, TP101 `VBAT_PROTECTED`, TP103 `AMP_PVCC`, TP104 `AMP_SDZ`, TP106 `+5V_RAW`, TP109 `AMP_FAULTZ`;
  TP102, TP105, TP107, TP108 GND
- Other probe points: `BATT_SENSE_CONN` at R13 pad 1; `5V_IN` at C105 pad 1; `AMP_AVCC` at C115 pad 1; GVDD at C110 pad 1;
  `AMP_GAIN` at R104 pad 1; `AMP_PG` at R110 pad 1; `AMP_MR` at JP105 pin 1; `SPK_MUTE` at R107 pad 2; U101's MUTE at C124
  pad 1; `LINE_OUT`/`LINE_REF` at C108/C109 pad 1 and U101's inputs at their pad 2; `OUT_P`/`OUT_N` at L101/L102 pad 1; the
  bootstrap pins at C117–C120 pad 1 (`BSPR`, `BSNR`, `BSPL`, `BSNL`; pad 2 is the output); Q101's gate at R101 pad 1

**Options and experiments.** Power rev 1's jumpers and experiment parts are kept. Bring up with the defaults below, then
record every setting in the log, since some readings depend on them.

| Option | Default for bring-up | Readings it moves |
|---|---|---|
| JP101 / JP103 (bead bypass) | Open (beads in) | 1.34 only detects a missing bead with these open |
| JP102 / JP104 (optional bulk) | Open; C104 and C106 are DNP | None until C104/C106 are fitted (3D.2) |
| JP105 (manual reset) | Open (shunted only in 3B and to clear a fault) | Shunted: SDZ held low, `AMP_MR` → GND 0 Ω, TP106 → GND ≈ 9 kΩ |
| F101 | T3.15A (0001.2509); spares T2A, T2.5A, T4A, T5A | None |
| R105 | 0 Ω RC2512JK-070RL (2 A); spare CRCW2512 0 Ω | None |
| R106 (AVCC filter) | 10 Ω; spares 4.7 Ω, 22 Ω | 1.31: TP103 → C115 pad 1 |
| C108/C109 | 1.5 µF; spare pair 2.2 µF | 4C.4: input corner 1.8 Hz → 1.2 Hz |
| C121/C122 | 680 nF; spare pair 470 nF | 4C.4: filter corner 61 kHz → 73 kHz |
| L101/L102 | 10 µH; spare pairs 6.8 µH, 15 µH | 4C.3/4C.4: corner 74 / 50 kHz, ripple up / down |

## Equipment

- Current-limited bench supply, 0–15 V, at least 2.5 A, whose limit holds at 20 mA; a lead with a 5.5 × 2.1 mm barrel plug
  (centre +) for J101 with its two wires free so they can be swapped (2.13)
- A second supply channel, 0–6 V, limit 10 mA, whose output floats (not joined to the first channel's − or to earth), for
  A1.28 and 2.14
- DMM with diode mode, oscilloscope (≥ 20 MHz, 4 channels; 2 with A − B math at the least)
- 4 Ω dummy load, 25 W or more (50 W preferred)
- The DFR0571 with four wires (ferrules), the S1B panel switch wired to SW101 (or a wire link), a 47 Ω 1 W resistor (3A.2),
  the four 2.54 mm shunts
- Signal generator or audio interface (sine 20 Hz – 20 kHz, ≥ 2 Vpp); a phone/laptop headphone output works for listening tests
- ¼" mono cable, 3.5 mm stereo (TRS) cable, 3.5 mm mono (TS) plug, headphones (≈ 32 Ω), 32 Ω and 16 Ω dummy loads (one per channel)
- A 1 kΩ resistor and clip leads to pull A1.28 (`SPK_EN`) to 3.3 V with the Daisy out
- USB cable for the Daisy, USB-serial adapter (3.3 V) for J3, the display and its J105 power lead
- A 4 Ω speaker (Jensen MOD10-50 or Skar FSX10-4) with crimped quick-disconnects, and a microphone (or phone) for the speaker
  pop tests
- The Talentcell battery (Stage 7)
- Magnifier/microscope, flux, isopropyl alcohol, solder wick, a needle probe; hot air for U101's exposed pad

## Stage 0 — Visual and mechanical inspection (unpowered, no Daisy, no DFR0571)

| # | Check | Pass criteria |
|---|---|---|
| 0.1 | Clean flux residue; inspect every joint under magnification | No bridges (esp. U1, U2, U101, U103, Q1, Q2, Q102, D1–D5, D101), no cold/dull joints, no solder balls |
| 0.2 | IC orientation and type | U1, U2, U101 and U103 pin-1 marks match the silkscreen; U1 = TLV9061, U2 = MAX9722AEUE+, U101 = TPA3118D2, U103 = TPS3808EG50. A rotated U101 can't be found by resistance: check it here |
| 0.3 | U2 (TSSOP-16) | All 16 pins soldered with visible fillets and the part flat on the board; no bridge between neighbouring pins (0.65 mm pitch) |
| 0.4 | U101 (HTSSOP-32, 0.65 mm) | All 32 pins with fillets, part flat. Exposed pad soldered: solder visible in the back-side mask opening and its vias, none squeezed out toward the pins. No bridge between neighbours. The bridges that do damage at first power are 5–6 (RINN to PLIMIT/GVDD: 6.4–7.4 V on an input rated 6.3 V), 19–20 and 30–31 (PVCC on a bootstrap pin); 15–16 (SYNC to GND) can only be seen |
| 0.5 | Q1, Q102 and Q2 | All SOT-23: Q1 and Q102 are AO3401A, Q2 is 2N7002, not swapped (Q2 in Q102's place leaves `+5V_RAW` dead; an AO3401A in Q2's place holds `SPK_MUTE` near 1 V). Seated on the correct pads |
| 0.6 | Q101 and D101 | Q101 is the IRF4905, legs in the holes the silkscreen marks, tab facing as drawn. D101's cathode band on the side the silkscreen marks (cathode on `VBAT_PROTECTED`) |
| 0.7 | Polarised parts | C5 `+` to `+5V`. C111 and C112 `+` to PVCC (fitted backwards they fail at first power). C104 and C106 not fitted (DNP) |
| 0.8 | Passive values vs BOM | Sheet 1 as rev 2: R1 (1M), R3/R4/R6/R7/R8/R9/R13/R22 and R25–R28 (10k), R12/R17/R18/R19/R24 (100k), R10 (3.3k), R5/R20/R23 (470), R2/R11/R21 (1k); C7 is the 1210 part, C1, C10/C11 and C12–C16 the 0805 parts. Sheet 2: R101/R103/R107/R109/R112/R113 (10k), R102 (30k), R104 (5.6k), R106 (10 Ω, marked 10R0, not 1002), R108/R110 (2.2k), R111 (100k), R105 (0 Ω 2512). The swaps that matter: R102/R103 (battery reading ×3), a 10k for R106 (AVCC starved), R104 (gain). Ceramic caps aren't marked: fit C108/C109 (1.5 µF), C121/C122 (680 nF), C117–C120 (220 nF), C110 (1 µF 0805) and C103 (10 µF 1206) straight from their tapes |
| 0.9 | F101 | A T3.15A 5 × 20 mm fuse in the FX0457 holder, clips tight. Record the fuse fitted |
| 0.10 | Screw terminals J3, J102, J105, J106, J107, SW101 | Seated flat, wire openings facing the board edge, screws turn freely |
| 0.11 | Silkscreen legends | GND/TX/RX (J3), BAT+/GND (J106, to the DFR0571's input), 5V/GND (J107, from its output), DISP/GND (J105, the display's supply), SPK+/SPK− (J102, SPK+ on pin 2, toward the rear), 12V IN (J101); each test point's net beside its reference (VBAT, PVCC, SDZ, FAULT, 5V RAW, HP DET, GND) |
| 0.12 | Jumper headers | JP101–JP105 fitted, all shunts off |
| 0.13 | Daisy sockets | Both A1 1×20 sockets flush and parallel; Daisy inserts with moderate force, all pins engaged, USB connector on the correct end |
| 0.14 | Jacks J1, J4, J2 and J101 | Fully seated, flush to the board edge, plugs insert/eject cleanly |
| 0.15 | Enclosure fit (if available) | Front jacks, USB, J101, the switch, J102 and the left-edge terminals line up with panel holes and cable routes |

## Stage 1 — Unpowered resistance checks (no Daisy, no DFR0571)

Nothing on any terminal, the panel switch off, every shunt off, Daisy out. Measure with the DMM, red lead on the first point
named and black on the second, and let capacitors charge before reading. Probe on IC pins, test points, pads or the Daisy
sockets (A1), not on connector shells.

The numbers are the resistor network with every IC and diode open, from the netlist. Where an unpowered IC pin or a diode sits
in a parallel path the reading can be lower, by an amount that depends on the meter's test voltage, and the table gives the
lower bound. One diode matters most: with the red lead on the `+5V_RAW` side, Q1's body diode puts the `+5V` loads (18.2 kΩ)
in parallel. `VBAT_PROTECTED` carries 200 µF (C111/C112), so its readings take about half a minute to settle.

**1A. Audio section (rev 2's checks, same numbers where the circuit allows)**

| # | Measure | Expect | A wrong reading means |
|---|---|---|---|
| 1.1 | `+5V` (C5 `+`) → GND | Rises to ≈ 18 kΩ (R6 + R7 ∥ R18 + R19 = 18.2 kΩ, less with U1/U2's supply pins); never below 50 Ω | Short on the 5 V rail: C4/C5/C6/C12/C15, U1.5, U2.2 (SHDN) bridged to U2.1 (INL+, GND) |
| 1.2 | C105 pad 1 (`5V_IN`) → C5 `+` in diode mode, then reversed | ≈ 0.4–0.7 V (Q1's body diode); reversed: OL | ≈ 0 both ways: Q1 shorted; OL both ways: Q1 missing, rotated or swapped with Q2 |
| 1.3 | J3.1, J101 sleeve (pin 2), J105.2, J106.2, J107.2, TP102, TP105, TP107, TP108 → A1.40 | < 1 Ω each | Open joint |
| 1.4 | `VREF` (C7) → GND | ≈ 9.5 kΩ (R7 ∥ (R6 + R18 + R19)); down to ≈ 5 kΩ with U1/U2's supply pins | < 1 kΩ = C7 shorted; > 10 kΩ = R7 open or wrong |
| 1.5 | J3.2 → GND; J3.3 → GND | Open; ≈ 110 kΩ (R9 + R24) | UART pins shorted to GND; ≈ 100 kΩ = R9 shorted, open = R9 or R24 open |
| 1.6 | PVSS (C14 pad 1) → GND and → `+5V` (C5 `+`) | High (no short) | C14 shorted; U2.7 (PVSS) bridged to U2.8 (SGND) |
| 1.6a | U2 charge-pump pins: C13 pad 1 (C1P) → C13 pad 2 (C1N), → `+5V` and → GND; C13 pad 2 → GND and → C14 pad 1 (PVSS) | High (no short) on all five | C13 shorted; U2 pins 3–4, 4–5, 5–6 or 6–7 bridged |
| 1.7 | A1.33 and A1.38 → GND and → `+5V` | Open | Stray copper or a socket bridge |
| 1.8 | J4 tip → GND, J4 ring → GND, J4 ring → `+5V`, J4 tip → J4 ring | High (no short), not < 100 Ω | U2 bridge: OUTR (12) to SVDD (11), an output to SVSS (13), or OUTR (12) to OUTL (14) |
| 1.8a | J4 tip → C10 pad 2; J4 ring → C11 pad 2 | ≈ 20 kΩ (R26 + R25; R28 + R27) | A gain resistor missing, open or the wrong value |
| 1.9 | J1 tip → GND, no plug | ≈ 0 Ω (tip-normal shorts to GND) | J1 switch / footprint issue |
| 1.10 | J1 tip → GND, plug inserted (other end open) | Open once C1 and C2 charge; not ≈ 0 Ω | ≈ 0 Ω = plug not lifting the switch |
| 1.11 | J2 tip → ring | ≈ 20 kΩ (R3 + R4) | R3/R4 open |
| 1.12 | J2 tip → GND | ≈ 10.5 kΩ (R3 + R5) | ≈ 10.0 kΩ = R5 or C3 shorted; ≈ 13.3 kΩ = a 3.3k fitted for R5 |
| 1.13 | TP1 (`HP_DETECT`) → GND, no plug in J4 | Open | J4 detect switch closed or bridged |
| 1.14 | TP1 → GND, plug in J4 | ≈ 0 Ω | J4 detect switch not closing (check pins 5/6 mapping) |
| 1.15 | TP1 → A1.23 | < 1 Ω (direct trace) | Open trace or J4 pin 6 joint |
| 1.16 | C108 pad 1 (`LINE_OUT`) → GND; C109 pad 1 (`LINE_REF`) → GND | ≈ 100 kΩ (R12); ≈ 1 kΩ (R21) | R12 or R21 missing or wrong |
| 1.17 | C108 pad 1 → A1.19 (`AUDIO_OUT_2`) | ≈ 1 kΩ (R11) | R11 open or wrong value |
| 1.18 | R13 pad 1 (`BATT_SENSE_CONN`) → GND; A1.25 → GND (once C17 charges) | ≈ 6.7 kΩ (R103 ∥ (R13 + R22)); ≈ 6.7 kΩ (R22 ∥ (R13 + R103)) | 10k / 10k = R13 open; 10k / 20k = R22 open; 20k / 10k = R103 open; 12k / 8k = R102 and R103 swapped |
| 1.19 | A1.26, A1.27 → anything | Open | Stray bridge |
| 1.20 | A1.28 (`SPK_EN`) → GND; R107 pad 2 (`SPK_MUTE`) → GND; R23 pad 1 → Q2 pin 3 | ≈ 100 kΩ (R17); ≈ 122 kΩ (R107, then R109 + R110 + R111), down to ≈ 26 kΩ with Q1's body diode, never below 10 kΩ; ≈ 470 Ω (R23) | R17 missing; below 10 kΩ = Q2 shorted, or an AO3401A fitted as Q2 (its body diode conducts); R23 open |
| 1.21 | J3.2 → A1.14; J3.3 → A1.15; A1.15 → GND | ≈ 10 kΩ (R8), ≈ 10 kΩ (R9), ≈ 100 kΩ (R24) | UART series resistors, RX pull-down |
| 1.21a | A1.22 (`5V_SENSE`) → GND | ≈ 55 kΩ (R19 ∥ (R18 + R6 + R7)), less with U1/U2; not ≈ 0 Ω | R18/R19 missing or shorted |
| 1.21b | A1.16 (`AUDIO_IN_1`) → U1.1 | ≈ 470 Ω (R20) | Open = R20 open; ≈ 0 Ω = shorted |
| 1.21c | ESD diodes: J1 tip, J2 tip, J2 ring, J4 tip, J4 ring → GND, diode mode both ways | No conduction below ≈ 5 V either way (the meter reads open) | D1–D5 shorted, fitted wrong, or a solder bridge |
| 1.22 | Daisy socket (A1) adjacent pins: A1.17 (`AUDIO_IN_2`) → A1.18 (`AUDIO_OUT_1`); A1.18 → A1.19 (`AUDIO_OUT_2`); then spot-check the rest | Open on both (C9–C11 block DC on `AUDIO_OUT_1`); no shorts between other neighbouring pins, esp. A1.39 (`+5V`) ↔ A1.38 (3V3_D) and A1.40 (GND) | Socket bridge. A1.17–A1.18 loads the DAC output below its 600 Ω minimum (R5); A1.18–A1.19 ties the two DAC outputs together; **A1.39–A1.38 puts 5 V into 3V3_D and would damage the Daisy** |

**1B. Power section**

| # | Measure | Expect | A wrong reading means |
|---|---|---|---|
| 1.23 | J101 pin 1 (its solder joint) → SW101.1 | < 1 Ω (F101) | Fuse missing, blown or loose in its clips |
| 1.24 | SW101.1 → SW101.2 with the panel switch wired: off, then on | Open; < 1 Ω | Switch wiring, terminal joints |
| 1.25 | SW101.2 (Q101 drain) → TP101 in diode mode, then reversed | ≈ 0.4–0.7 V (Q101's body diode); reversed: OL | ≈ 0 both ways: Q101 shorted (no reverse protection); OL both ways: Q101 missing or its legs in the wrong holes |
| 1.26 | GND → R101 pad 1 (Q101 gate) | ≈ 10 kΩ (R101) | Open = R101 missing (Q101 would stay off and run on its body diode); ≈ 0 = gate bridged to GND |
| 1.27 | R101 pad 1 → TP101 in diode mode, then reversed | ≈ 0.6–0.8 V (D101 forward); reversed: OL (a 12 V zener) | The two readings swapped: D101 backwards (it would hold VGS at −0.7 V and leave Q101 off); ≈ 0 both ways: Q101's gate and source bridged |
| 1.28 | R101 pad 1 → SW101.2 (gate–drain) | Not a short | Q101's G and D legs bridged |
| 1.29 | TP101 → GND | Climbs over ≈ 30 s to ≈ 37 kΩ (R102 + R103 ∥ (R13 + R22)), lower if U101's PVCC pins conduct; never below 50 Ω | Short on the battery rail: C111/C112 (reversed?), C113/C114, U101's PVCC pins to its pad |
| 1.30 | TP101 → R13 pad 1 | ≈ 30 kΩ (R102) | ≈ 10 kΩ = R102/R103 swapped; open = R102 missing |
| 1.31 | TP101 → TP103; TP103 → C115 pad 1 | < 1 Ω (R105); ≈ 10 Ω (R106) | R105 missing (PVCC would stay at 0 V: see "Powering rule"); ≈ 10 kΩ = a 10k fitted for R106 |
| 1.32 | J107.1 → TP106 in diode mode, then reversed | ≈ 0.4–0.7 V (Q102's body diode); reversed: OL | ≈ 0 both ways: Q102 shorted (no reverse protection: don't run 2.14); OL both ways: Q102 missing or rotated; the two readings swapped: a 2N7002 fitted as Q102 |
| 1.33 | Q102 pin 1 → GND | < 1 Ω | Q102's gate not at GND: it would pass `+5V_RAW` on its body diode only |
| 1.34 | TP106 → C105 pad 1; TP106 → J105.1 (JP101 and JP103 open) | < 1 Ω each (FB101, FB102) | Open = a bead missing or cracked. With JP101/JP103 shunted these read 0 Ω whatever the beads are |
| 1.35 | TP106 (`+5V_RAW`) → GND | ≈ 112 kΩ (R109 + R110 + R111), down to ≈ 16 kΩ with Q1's body diode; never below 1 kΩ | Short on `+5V_RAW`: C103, C123, C105, C107, U103; ≈ 9 kΩ = a shunt left on JP105 |
| 1.36 | R107 pad 2 → TP106; C124 pad 1 → R107 pad 2 | ≈ 10 kΩ (R107); ≈ 2.2 kΩ (R108) | R107/R108 open, or swapped with each other |
| 1.37 | TP104 → TP106; R110 pad 1 → TP106 | ≈ 12.2 kΩ (R110 + R109); ≈ 10 kΩ (R109) | Open = R109 or R110 open; ≈ 2.2 kΩ on the second = R109 and R110 swapped |
| 1.38 | TP104 (SDZ) → GND | ≈ 100 kΩ (R111), down to ≈ 23 kΩ with Q1's body diode; never below 10 kΩ | ≈ 0 = U101 pins 1–2 (MODSEL, SDZ) bridged or C125 shorted |
| 1.39 | TP109 → TP106 | ≈ 10 kΩ (R112) | R112 open |
| 1.40 | JP105 pin 1 → TP106 | ≈ 9 kΩ (R113 ∥ U103's internal 90 kΩ MR pull-up) | Open/high = R113 open |
| 1.41 | J102.1 → J102.2; J102.1 → GND; J102.2 → GND | Open once C121/C122 charge (the outputs are bridged: no DC path); not a short | ≈ 0 between them = `OUT_P` and `OUT_N` joined (U101's output pins, L101/L102 pads); to GND = C121/C122 shorted or an output pin bridged to GND |
| 1.42 | J102.2 → L101 pad 1; J102.1 → L102 pad 1 | < 1 Ω (L101, L102) | Inductor joint open |

**1C. U101 and U103 neighbouring pins**

Pairs of adjacent pins on different nets. An unpowered U101 conducts between some pins through its own protection, so "not a
short" means above 100 Ω.

| # | Measure | Expect | A wrong reading means |
|---|---|---|---|
| 1.43 | TP104 → TP109 (U101 pins 2–3) | ≈ 22 kΩ (R110 + R109 + R112) | ≈ 0 = SDZ–FAULTZ bridged |
| 1.44 | TP109 → C108 pad 2 (3–4); C108 pad 2 → C109 pad 2 (4–5) | Not a short | FAULTZ–RINP or RINP–RINN bridged |
| 1.45 | C109 pad 2 → C110 pad 1 (5–6) | Not a short | RINN–PLIMIT bridged: GVDD (6.4–7.4 V) on an input rated 6.3 V. **Fix before power** |
| 1.46 | C110 pad 1 → R104 pad 1 (7–8) | Starts near 5.6 kΩ and climbs (C110 charging through R104) | ≈ 0 = GVDD–GAIN bridged |
| 1.47 | R104 pad 1 → GND (8–9) | ≈ 5.6 kΩ (R104) | ≈ 0 = GAIN–GND bridged; 2.2 kΩ or 10 kΩ = the wrong part (another gain or slave mode) |
| 1.48 | C124 pad 1 (MUTE) → GND (11–12–13) | ≈ 124 kΩ (R108 + R107, then R109–R111), down to ≈ 28 kΩ with Q1's body diode; never below 10 kΩ | ≈ 0 = MUTE bridged to LINN or AM2 (both GND): the speaker would never mute |
| 1.49 | U101 pin 16 (SYNC) → GND, needle probe on the pin | Open | SYNC bridged to AM0 |
| 1.50 | TP103 → C120 pad 1 (19–20); TP103 → C117 pad 1 (30–31) | Not a short | PVCC on a bootstrap pin |
| 1.51 | C117, C118, C119, C120: pad 1 → pad 2 each (bootstrap–output: 29–30, 26–27, 23–24, 20–21) | Not a short | A bootstrap cap shorted or its two pins bridged |
| 1.52 | C119 pad 1 → GND (24–25); C118 pad 1 → GND (25–26) | Not a short | Bootstrap pin bridged to GND |
| 1.53 | L101 pad 1 (`OUT_P`) → GND; L102 pad 1 (`OUT_N`) → GND (21–22, 22–23, 27–28, 28–29 and the exposed pad) | Not a short | An output bridged to GND (U101 would latch off when first unmuted) |
| 1.54 | R110 pad 1 (`AMP_PG`) → GND (U103 pins 1–2); JP105 pin 1 → GND (U103 pins 2–3) | ≈ 102 kΩ (R110 + R111), down to ≈ 22 kΩ; ≈ 121 kΩ (R113 ∥ 90 kΩ, then R109–R111), down to ≈ 25 kΩ | ≈ 0 = RESET or MR bridged to GND (U101 would never start) |

## Stage 2 — Battery side, DFR0571 disconnected

Left out: the Daisy, the DFR0571 (nothing on J106 or J107), the display (J105, J3), any load on J102, every shunt
(JP101–JP105). R105 fitted, the panel switch wired to SW101 (or a wire link for "on"). With no 5 V, U103 and the pull-ups
R107/R109/R112 sit at 0 V, so U101 stays in shutdown with SDZ and MUTE at 0 V, inside its rating. The battery path, Q101, the
battery divider and PVCC are checked without risking the DFR0571 or anything on 5 V. This is the only stage, with 5.9, that
runs the amp unpowered: the battery side up, 5 V off. Never the other way round.

Bench supply on J101 (centre +), set to 12.0 V, current limit **20 mA**. Expected draw is under 1 mA: the battery divider takes
12.0 V / 36.7 kΩ = 0.33 mA, U101 in shutdown < 50 µA (SLOS708G, ICC(SD) at 12 V), R101/D101 under 0.1 mA (D101 only conducts
near its 12 V knee), plus C111/C112 leakage. 20 mA is the lowest limit most supplies hold, and far below anything that heats a
part. Switch on at SW101, then turn the supply on.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 2.1 | Supply current at 12.0 V | < 1 mA (above). Stop if it hits the limit | At the limit: a short on `VBAT_PROTECTED`/PVCC (1.29), C111/C112 reversed. A few mA: U101 not in shutdown (2.6), a lower-voltage zener for D101 |
| 2.2 | TP101, TP103, C115 pad 1 (AVCC) | All within 10 mV of the supply at J101 | ≈ 0.5 V low: Q101 running on its body diode (D101 reversed, R101 open, gate bridged to source). TP103 at 0 V: R105 missing, **stop** ("Powering rule") |
| 2.3 | R101 pad 1 → TP101 (Q101's VGS) | −9 to −12 V: R101 pulls the gate to GND, and D101, near its knee, may hold it a few volts short of 12 V | ≈ −0.6 V = D101 reversed; ≈ 0 V = R101 open |
| 2.4 | R13 pad 1 (`BATT_SENSE_CONN`); A1.25 | 2.15–2.22 V; 1.065–1.117 V. A1.25 = TP101 / 11 (VBAT × 0.25 from 7.5 kΩ into R13 + R22, halved), ±2.4 % with 1 % parts | A1.25 ≈ 3.3 V = R102/R103 swapped; ≈ 3.0 V = R22 open; ≈ 2.4 V = R103 open; 0 V = R102 or R13 open |
| 2.5 | TP106 (`+5V_RAW`), J107.1, C5 `+` (`+5V`) | < 50 mV | Higher: something on the battery side feeds the 5 V nets (U101's SDZ, MUTE or FAULTZ pin back through R107–R112). **Stop** |
| 2.6 | TP104 (SDZ), C124 pad 1 (MUTE), TP109 (FAULTZ) | < 50 mV each: their pull-ups run from `+5V_RAW`. U101 in shutdown, MUTE and SDZ inside −0.3 V … PVCC + 0.3 V | |
| 2.7 | C110 pad 1 (GVDD); C108 pad 2 and C109 pad 2 (U101's inputs) | Record. SLOS708G doesn't say whether GVDD or the inputs' 3 V bias run in shutdown | |
| 2.8 | J102.1 and J102.2 → GND, DMM and scope | ≈ 0 V, no switching (outputs Hi-Z in shutdown) | Switching: U101 not in shutdown (2.6) |
| 2.9 | J106.1 → J106.2 | = TP101, pin 1 positive | J106 joints |
| 2.10 | Battery range: set 9.0 V, then 12.6 V | A1.25: 0.80–0.84 V, then 1.12–1.17 V (VBAT / 11). TP101 within 10 mV of the supply each time; the divider draws 0.25 mA, then 0.34 mA | TP101 low at 9 V: Q101 not fully on (2.3) |
| 2.11 | Thermal | Nothing warm to the touch after 2 min | |
| 2.12 | Switch off at SW101 | Current drops to ≈ 0; TP101 decays over ≈ 30 s (C111/C112 into the divider, τ ≈ 7 s) | Current stays: SW101 wiring |
| 2.13 | **Reverse polarity at J101:** supply off, swap its two wires (− to the centre pin), limit 20 mA, 12.0 V, switch on | ≈ 0 mA; TP101 ≈ 0 V: Q101's body diode blocks and its gate gets no drive. Restore the polarity and repeat 2.2 and 2.4 | Current flows: Q101 shorted or fitted wrong (1.25) |
| 2.14 | **Reverse 5 V on J107 (Q102):** keep 12.0 V on J101, correct polarity. The second, floating supply at 5.0 V, limit 10 mA: + to J107.2, − to J107.1 | ≈ 0 mA from the second supply; TP106 stays within 50 mV of 0 V; TP104 and C124 pad 1 stay at 0 V. Remove it | Current, or TP106 negative: Q102 shorted or the wrong part. Remove the supply at once |

What 2.14 risks: if Q102 is wrong (1.32 should have caught it), −5 V reaches `+5V_RAW`, and U103 (VDD rated −0.3 V minimum)
clamps it through its own diode at the 10 mA limit. The 12 V on J101 means that even this supply connected the wrong way round
(+5 V on J107.1) leaves U101's MUTE and SDZ inside PVCC + 0.3 V. Don't use the DFR0571 for this test: its input and output GND
are one node, so with J106 wired, J107's wires swapped short its output to GND (3B.1).

## Stage 3 — The DFR0571 and the 5 V rails, Daisy removed

**3A. The DFR0571 on its own (off the board)**

Before it goes near the board: U1 and U2 are rated 5.5 V, U103 6 V, and the 5 V contract (`power-board/README.md`) is
4.75–5.25 V. DFRobot's figures, as resellers list them (DFRobot's own page doesn't load): 8–28 V in, 5 V ± 0.1 V out, 0.5 mA
no-load input current, under 50 mVpp ripple at full load.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 3A.1 | 12.0 V into its VIN+/GND, limit 50 mA, output open | Output 4.90–5.10 V; input current ≈ 0.5 mA. Record both | Above 5.25 V: don't connect it |
| 3A.2 | Repeat at 9.0 V and 12.6 V in, then with the 47 Ω 1 W resistor on the output (≈ 0.1 A) | 4.90–5.10 V each time | Sags at 9 V: record it (DFRobot: raise the minimum input at high load) |
| 3A.3 | Fit and label its four wires: VIN+ → J106.1 (BAT+), GND → J106.2, 5V → J107.1, GND → J107.2. Check them with the module powered as in 3A.1 | The 5V wire reads +5 V against either GND wire | |

**3B. On the board, U101 held in shutdown**

Left out: the Daisy, the display (J105, J3), any load on J102, shunts on JP101–JP104. Put a shunt on JP105 (borrow one from
JP101–JP104): it holds U103's MR low, so SDZ stays low and U101 stays in shutdown while the 5 V rails are checked.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 3B.1 | Supply off. Wire the DFR0571 to J106 and J107. Then TP101 → GND; J107.1 → GND; TP101 → J107.1 | Not below 1 kΩ (TP101 climbs as in 1.29, with the module's input in parallel); not a short (> 100 Ω); not a short | TP101 → GND ≈ 0: J106's wires swapped. The module's two GNDs are one node, so `VBAT_PROTECTED` would reach GND through J107's ground wire, a dead short at power-up. J107.1 → GND ≈ 0: J107's wires swapped (the module's output shorted to GND). TP101 → J107.1 ≈ 0: both swapped |
| 3B.2 | Supply 12.0 V on J101, limit **50 mA**; switch on | ≈ 5–12 mA. 5 V side ≈ 7.4 mA typical, 15 mA at most: U2 5.5 mA (13 mA max), U1 ≈ 0.5 mA, the `VREF` and `5V_SENSE` dividers 0.28 mA, R109 and R113 into U103 and JP105 1.1 mA. Through the buck that is ≈ 3.5–8 mA at 12 V, plus its own 0.5 mA, the battery divider's 0.33 mA and U101's shutdown current. Stop if it hits the limit | At the limit: a short on `+5V_RAW` or `+5V` (1.1, 1.35), the DFR0571's wiring (3B.1), C5 reversed, U1/U2 rotated |
| 3B.3 | TP106 (`+5V_RAW`) | 4.90–5.10 V, as 3A.1 | |
| 3B.4 | J107.1 − TP106 (Q102's drop) | < 10 mV | 0.4–0.7 V: Q102's channel is off (gate not at GND, rotated), and `+5V_RAW` sits near U103's 4.65 V threshold |
| 3B.5 | C105 pad 1 (`5V_IN`); J105.1 (`+5V_DISPLAY`) | Within 5 mV of TP106 (FB101, FB102) | 0 V: a bead open (1.34) |
| 3B.6 | `+5V` (C5 `+`) | Within 10 mV of `5V_IN` (Q1 on) | ≈ 0.5 V low: Q1 on its body diode (gate not at GND, or swapped with Q2) |
| 3B.7 | `VREF` (C7); A1.22 (`5V_SENSE`) | Half of C5 `+` within ±1 %: 2.42–2.58 V for 4.90–5.10 V; the same | R6/R7, R18/R19 values |
| 3B.8 | U1.1, A1.16 (through R20), U1.3 | ≈ `VREF` | U1 rotated or not powered (U1.5) |
| 3B.9 | U2 charge pump: PVSS (C14 pad 1) | ≈ −4.3 to −5.0 V, roughly `+5V` inverted; record it | ≈ 0 V = charge-pump fault (C13, pins 4/6/7) |
| 3B.10 | J4 tip and ring (DC) | Within ±10 mV of 0 V (worst-case offset ≈ ±5.5 mV) | |
| 3B.11 | C108 pad 1 (`LINE_OUT`), C109 pad 1 (`LINE_REF`) | ≈ 0 V (R12, R21) | |
| 3B.12 | A1.39; J3.1 and A1.40 | `+5V`; GND | |
| 3B.13 | R107 pad 2 (`SPK_MUTE`), C124 pad 1 (MUTE) | Within 50 mV of TP106: Q2 off (R17 holds A1.28 low with the Daisy out), U101 muted. Both below PVCC + 0.3 V | ≈ 0.22 V: Q2 on (Q2 shorted, A1.28 not low); ≈ 0: MUTE bridged to GND (1.48) |
| 3B.14 | JP105 pin 1; R110 pad 1 (`AMP_PG`); TP104 (SDZ) | 0 V; < 0.4 V (U103's RESET held low by MR); < 0.4 V: U101 in shutdown | |
| 3B.15 | TP109 (FAULTZ) | ≈ TP106 (no fault); record it | |
| 3B.16 | TP101, TP103; A1.25 | = the supply; 1.065–1.117 V, as 2.4 | |
| 3B.17 | **5 V on a signal terminal:** a second supply at 5.0 V, limit 50 mA, on J3.3 | A1.15 ≈ 4.55 V (R9/R24). Remove it | More: R24 open |
| 3B.18 | Thermal | Nothing warm to the touch after 2 min, U2 included | |

**3C. U101 enabled, muted**

Supply off. Park the JP105 shunt on one pin of its header (JP105 open). Limit **70 mA**: 3B's ≤ 12 mA plus U101's quiescent
current, 20 mA typical and 35 mA at most at 12 V (SLOS708G, no load or filter), plus about 50 %.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 3C.1 | **Power-on sequence:** scope TP103 (PVCC), TP106 (`+5V_RAW`), TP104 (SDZ) and C124 pad 1 (MUTE). Supply at 12.0 V, trigger on TP106, switch on at SW101 | PVCC rises first. `+5V_RAW` follows once the DFR0571 starts. SDZ stays low until ≈ 20 ms after `+5V_RAW` passes 4.65 V (U103, CT open), then rises with τ ≈ 11 ms ((R109 + R110) ∥ R111 into C125), crossing 2 V ≈ 6.5 ms later. MUTE follows `+5V_RAW` with τ ≈ 12 ms (R107 + R108 into C124). SDZ and MUTE stay below PVCC + 0.3 V throughout and change slower than 10 V/ms (SLOS708G's limit; here ≤ 0.4 V/ms) | SDZ rising with `+5V_RAW`: U103's delay missing (wrong part, CT not open). SDZ or MUTE above PVCC + 0.3 V at any time: **stop** and record it |
| 3C.2 | Supply current at 12.0 V | 3B.2's value, less ≈ 0.5 mA (JP105 open), plus U101's 20 mA typical (35 mA max; muted it may draw less). Record it; < 50 mA | More: U101 switching despite MUTE (3C.7), a fault |
| 3C.3 | TP104 (SDZ); R110 pad 1 (`AMP_PG`) | 4.0–4.56 V: R111 / (R109 + R110 + R111) × `+5V_RAW` = 4.37–4.56 V for 4.90–5.10 V, less up to 0.5 V from U101's SDZ input current (≤ 50 µA, SLOS708G) through ≈ 11 kΩ. `AMP_PG` ≈ 0.1 V above SDZ | ≈ 0: U103 holding RESET (TP106 below 4.65 V, JP105 still shunted, U103 pins 1–2 or 2–3 bridged) |
| 3C.4 | TP109 (FAULTZ) | ≈ TP106 (no fault) | < 0.8 V = a latched fault. Over-current: an output shorted (1.41, 1.53). DC detect: C108/C109 or the input pins (3C.6). Over-temperature: the exposed pad. Find it, then clear with JP105 (3C.8) |
| 3C.5 | C110 pad 1 (GVDD) | 6.4–7.4 V (SLOS708G) | ≈ 0: U101 not running (SDZ, AVCC at C115) |
| 3C.6 | C108 pad 2, C109 pad 2 (U101's inputs) | ≈ 3 V each (biased inside U101), within ≈ 0.1 V of each other; record both | One at 0 V: its cap shorted, or the pin bridged (1.44, 1.45) |
| 3C.7 | J102.1, J102.2 (scope and DMM) | No switching: MUTE is high, so the outputs are Hi-Z. Record the DC | Switching: MUTE not reaching U101 pin 12 (R108, C124 joints) |
| 3C.8 | **JP105 manual reset:** short JP105 for ≈ 1 s with the shunt, watching TP104 and TP109 | SDZ falls below 0.8 V within ≈ 4 ms (C125 through R110, τ ≈ 2.2 ms) and rises again ≈ 26 ms after the shunt comes off (20 ms + 6.5 ms). TP109 stays high | SDZ doesn't move: MR not reaching U103 pin 3 |
| 3C.9 | **Power-off sequence:** same probes, trigger on TP103 falling, switch off at SW101 | `+5V_RAW` holds while PVCC falls, then falls with it once the DFR0571 drops out. SDZ goes low within ≈ 4 ms of `+5V_RAW` passing 4.65 V. MUTE (lagging `+5V_RAW` through R107 + R108 and C124) and SDZ never above PVCC + 0.3 V. Record the times and the largest MUTE − PVCC | MUTE or SDZ above PVCC + 0.3 V: record by how much and for how long, and raise it (DESIGN.md "Power sequence") |
| 3C.10 | Thermal after 5 min | U101 at most warm (muted); Q101, Q102 and the DFR0571 cool | |

**3D. 5 V filter options**

Power off for every jumper change. Record each configuration tested in the log. The display's share of these tests is 6.14.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 3D.1 | Shunt JP101 and JP103 (beads bypassed); repeat 3B.5 and 3C.2 | The same readings: at a few mA the beads drop well under 1 mV | |
| 3D.2 | C104/C106 are DNP. If they're fitted for the bulk experiment (`+` toward JP102/JP104): shunt JP102/JP104 and repeat 3C.1 | `+5V_RAW` still rises monotonically and the DFR0571 starts first time; SDZ's delay unchanged. Record the rise time with and without | DFR0571 hiccups into the extra 200 µF: record it |

Return the jumpers to the defaults (or to what rev 1's bring-up chose) before going on.

## Stage 4 — Analog paths and speaker amp, Daisy removed

With the module out, its sockets (A1) reach the Daisy-side nets, so the analog stages can be tested on their own. Supply
12.0 V on J101 with the DFR0571, limit **70 mA** for 4A, 4B and 4D (4C sets its own). R17 keeps the speaker muted throughout,
except in 4C.

**4A. Guitar input buffer (J1 → AUDIO_IN_1)**

1. Inject 1 kHz, 1 Vpp sine into J1 (tip/sleeve). Scope on `A1.16` (AUDIO_IN_1) or U1.1.
2. | # | Check | Expect |
   |---|---|---|
   | 4A.1 | Output level | U1.1: 1 kHz sine riding on ≈ 2.5 V DC, amplitude ≈ input (unity gain). A1.16: the same through R20 (no Daisy load) |
   | 4A.2 | Input load: add 1 MΩ in series with the generator | Output drops to ≈ half (≈ 1 MΩ input impedance, R1) |
   | 4A.3 | Unplug J1 | Output goes quiet (tip shorted to GND) |
   | 4A.4 | Raise amplitude until clipping | Clips symmetrically near the rails: ≈ 4.8 Vpp at U1.1 and A1.16 (no Daisy load); record the input level |
   | 4A.5 | Sweep 20 Hz – 20 kHz | Flat within about ±1 dB |

**4B. Headphone filter + headphone amp (AUDIO_OUT_1 → J4)**

1. Inject 1 kHz, 1 Vpp sine into `A1.18` (AUDIO_OUT_1), ground at `A1.20`.
   Load J4 tip and ring with 32 Ω each (or headphones at low level).
2. | # | Check | Expect |
   |---|---|---|
   | 4B.1 | C9 (`HP_SOURCE`) | ≈ 0.60 Vpp centred on 0 V (R10 into R25 ‖ R27, −4.4 dB). Set the generator's DC offset to 0 V |
   | 4B.2 | J4 tip and ring | ≈ 0.60 Vpp centred on 0 V, inverted relative to `HP_SOURCE` (gain −1); both channels equal within ~0.5 dB |
   | 4B.3 | Frequency sweep 20 Hz – 20 kHz into 32 Ω | Flat in the audio band; low-end corner ≈ 3.4 Hz (C10/C11 into R25/R27); falls off above ≈ 80 kHz (R10/C9 with R25 ‖ R27 as the load) |
   | 4B.4 | Listening test with headphones | Clean tone, no hum/hiss above expected level, no oscillation (check scope for HF ringing on the outputs and on PVSS) |
   | 4B.5 | Power-on/off with headphones in | Note any pop level (U2 has built-in pop suppression; Stage 8 is the full test) |

**4C. Speaker send and speaker amp (AUDIO_OUT_2 → U101 → J102)**

Power off and connect the 4 Ω dummy load to J102. Inject 1 kHz into `A1.19` (AUDIO_OUT_2), ground at `A1.20`, generator DC
offset 0 V. Measure J102 with two scope probes, their grounds on TP105 or TP107 and **never on J102**, CH1 on J102.2 (SPK+),
CH2 on J102.1 (SPK−), and read CH1 − CH2; or read a true-RMS DMM across the load. Both terminals sit at ≈ 6 V while U101
plays, so grounding either one shorts an output and latches U101 off. To unmute without the Daisy, pull A1.28 (`SPK_EN`) to
3.3 V through 1 kΩ from the second supply (limit 10 mA); leave it open to mute. Limit **200 mA** unless an item says otherwise.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 4C.1 | Muted (A1.28 open), 0.1 Vrms (0.28 Vpp) in. C108 pad 1 (`LINE_OUT`), C109 pad 1 (`LINE_REF`), J102 | ≈ 0.097 Vrms, in phase (R11 into R12 ∥ U101's 60 kΩ ±20 %: −0.2 dB); ≈ 0; J102 silent, no switching | `LINE_OUT` low: R11, C16 or R12 (1.16, 1.17) |
| 4C.2 | Unmute: A1.28 to 3.3 V through 1 kΩ | R107 pad 2 and C124 pad 1 ≈ 0.22 V (R23 against R107's 10k). J102 ≈ 0.97 Vrms differential (0.87–1.09 Vrms: 20 dB ± 1 dB, SLOS708G with R104 = 5.6 kΩ), SPK+ in phase with A1.19. Gain = V(J102) / V(C108 pad 1 − C109 pad 1) = 19–21 dB. Record the supply current | No output with MUTE low: SDZ (3C.3), FAULTZ (3C.4), L101/L102. ≈ 26 or 32 dB: R104 wrong. MUTE not low: Q2, R23, the 1 kΩ pull-up |
| 4C.3 | Generator off, still unmuted | J102.1 and J102.2 each ≈ 6.0 V DC (PVCC / 2, BD modulation) with ≈ 0.3 Vpp of 400 kHz (376–424 kHz) on each, common to both (at idle each 10 µH carries ≈ 0.75 App of ripple, PVCC × 0.25 / (L × 400 kHz), into its 680 nF); the difference within ±15 mV DC (SLOS708G). Record the idle supply current (SLOS708G's 20 mA is without the output filter) | 500 kHz or 1.2 MHz: an AM pin not at GND. One leg off 6 V: a PBTL tie or an output pin open |
| 4C.4 | Sweep 20 Hz – 20 kHz at 0.1 Vrms | Within 0.1 dB of 1 kHz at 20 Hz (C108/C109 into 60 kΩ: 1.8 Hz). −0.4 dB at 10 kHz and ≈ −1.4 dB at 20 kHz (R11/C16 −0.7 dB; L101/C121 and L102/C122 into 4 Ω, 61 kHz, −0.8 dB) | Peaking near the top: a filter cap missing or the wrong value |
| 4C.5 | Mute timing: scope A1.28, C124 pad 1 and J102; connect and remove the 3.3 V | Unmute ≈ 6 ms after A1.28 rises (C124 falls through R108, τ ≈ 2.7 ms, to 0.8 V); mute ≈ 6 ms after it falls (C124 rises through R107 + R108, τ ≈ 12 ms, to 2 V). Record any click | |
| 4C.6 | Maximum output: limit **2.5 A**, a few seconds at a time. Raise the input until the output clips | Clips at ≈ 11 V peak (≈ 7.9 Vrms, ≈ 15.5 W into 4 Ω, allowing ≈ 0.3 Ω for the switches and inductors) at ≈ 0.81 Vrms in, drawing ≈ 1.5 A from the supply. Full scale (1 Vrms in) clips: the firmware caps the speaker ≈ 5 dB below it. Record the input, output and current | Clipping much earlier: TP103 sagging (R105, Q101, F101, the supply lead), R104 |
| 4C.7 | **Speaker short:** back to 0.1 Vrms in, limit 500 mA. Short J102.1 to J102.2 with a wire for ≈ 1 s | TP109 drops below 0.8 V and J102 goes silent (outputs Hi-Z, latched). Remove the short: still silent, TP109 still low. Wait 2 s, then short JP105 for ≈ 1 s: the tone returns ≈ 30 ms after release and TP109 goes high. Repeat, clearing it by switching off at SW101 for 5 s instead | No latch: U101's protection isn't reporting (TP109, R112). The tone returns without JP105: SDZ toggling (TP104) |
| 4C.8 | Insert and remove a plug in J4 | J102 unchanged (no hardware link; muting the speaker is the firmware's job) | |
| 4C.9 | Thermal after 5 min at 0.1 Vrms in | U101 at most warm; L101/L102 cool | |

What 4C.7 risks: it relies on U101's over-current protection (SLOS708G Table 4: latched, outputs Hi-Z), which DESIGN.md "What
each connector can see" lists as designed-for misuse; the low level and the 500 mA limit keep the energy small.

Power off before disconnecting the load.

**4D. AUX input (J2 → AUDIO_IN_2)**

With the Daisy out, only R5 loads the summing node, so these levels are slightly higher than in use. 6.17 checks the real level with
the Daisy fitted.

1. Inject 1 kHz, 2 Vpp sine into J2 with a TRS cable, same signal on tip and ring. Scope on `A1.17` (AUDIO_IN_2) or C3.
2. | # | Check | Expect |
   |---|---|---|
   | 4D.1 | Tip and ring driven together | ≈ 0.17 Vpp centred on 0 V (R3‖R4 into R5, −21.3 dB) |
   | 4D.2 | Tip only, ring grounded (TS plug) | ≈ 0.09 Vpp |
   | 4D.3 | Unplug J2 | Output goes quiet (R5 holds the summing node at GND) |
   | 4D.4 | Sweep 20 Hz – 20 kHz (tip and ring driven) | Flat (C3's pole is ≈ 370 kHz with no Daisy load, ≈ 400 kHz with the Daisy fitted) |

Remove the injected signal and the A1.28 pull-up before going on.

## Stage 5 — Power-up with Daisy fitted

**5.0 Before fitting it:** power the Daisy on its own from USB, nothing else connected, and measure VIN (pin 39) to GND
(pin 40). Expect < 0.5 V: USB doesn't drive VIN (the Seed3 datasheet allows USB and VIN together). Record it. If it reads
near 5 V, USB alone would lift `+5V` and, through Q1 (gate at GND) and FB101, `+5V_RAW`, putting U101's SDZ and MUTE above
PVCC + 0.3 V: then plug in USB on this board only while the battery is on, and skip the battery-off parts of 6.15 and 6.18.

1. **Power off.** Insert the Daisy, checking orientation against the silkscreen
   and that no pins are offset by one position.
2. Supply 12.0 V on J101 with the DFR0571, limit **300 mA**: 3C's < 50 mA plus the Daisy's 100–200 mA at 5 V (≈ 50–100 mA
   at 12 V through the buck), with room for start-up. Keep USB **unplugged** for this stage.

| # | Check | Expect |
|---|---|---|
| 5.1 | Supply current | 3C.2 plus ≈ 50–100 mA (the Daisy, depending on firmware); record value |
| 5.2 | TP106; `+5V` (C5 `+`) | 4.90–5.10 V; ≥ 4.85 V, within 30 mV of TP106 (Q102, FB101 and Q1 at ≈ 0.2 A) |
| 5.3 | `3V3_D` (Daisy pin 38, probed on top of the module) | 3.3 V ± 5 % (from the Daisy regulator) |
| 5.4 | `VREF`, U1 biases, A1.25 | Same as Stage 3 |
| 5.5 | `HP_DETECT` (TP1) with a plug in J4 | ≈ 0 V. With J4 empty it floats until the firmware enables the internal pull-up, so that case is checked in 6.7 |
| 5.6 | Hold the Daisy in reset (RESET button held) | J4 quiet (headphones on), Q2 pin 1 (`SPK_EN`) 0 V, R107 pad 2 and C124 pad 1 ≈ TP106 (muted), J102 not switching |
| 5.7 | Daisy LED / existing firmware | Boots normally |
| 5.8 | Thermal after 5 min | Nothing hot; Q1, Q102, U2 and U101 at most warm |
| 5.9 | **Back-power, DFR0571 disconnected:** switch off, take the DFR0571's wires out of J106 and J107 (nothing on J107), limit 20 mA, 12.6 V, switch on | Current as 2.1 (< 1 mA); A1.25 ≈ 1.15 V (VBAT / 11) into the unpowered Daisy; TP106 and `+5V` < 50 mV; record `3V3_D`, which should stay near 0 V. More current, or `3V3_D` rising, means pin 25 back-powers the Daisy. Switch off, rewire the DFR0571 and repeat 3B.1 |

Then plug in USB with the board powered from J101 and confirm current/voltages don't jump
unexpectedly. Check the Daisy Seed docs for your revision's VIN/USB power-path
before relying on both sources together.

## Stage 6 — Functional tests with test firmware

Flash a small bring-up program (libDaisy or Arduino/DaisyDuino) over USB that:

- passes audio input 1 to outputs 1 and 2, mixes input 2 (AUX) into both, and logs peak levels,
- lets `SPK_EN` be toggled and the speaker level be set from USB serial, capped ≈ 5 dB below full scale,
- prints `HP_DETECT`, the `BATT_SENSE` and `5V_SENSE` ADC readings and VBAT = 11 × V(pin 25) over USB serial,
- keeps both outputs at digital silence while `5V_SENSE` reads low,
- echoes bytes on USART1 (J3) and sends a heartbeat string every second.

The firmware requirements in `DESIGN.md` apply. Supply 12.0 V on J101 with the DFR0571, limit 300 mA; raise it to 2.5 A
before the display (6.14) or a loud speaker test (6.20, 6.21). Speaker tests go into the 4 Ω dummy load until 6.21.

| # | Check | Expect |
|---|---|---|
| 6.1 | USB enumeration / DFU flashing | Flashes and enumerates; confirms the USB D+/D− sockets connect |
| 6.2 | Audio passthrough: 1 kHz into J1 → J4 headphones | Clean tone on both channels |
| 6.3 | Passthrough: J1 → J102 (dummy load, low level, `SPK_EN` high) | Signal present across J102 (differential) |
| 6.4 | Noise floor: J1 unplugged, firmware gain max | Only low-level hiss; no hum, whine, or digital noise from USB/codec; record level on the scope at J4 and across J102 |
| 6.5 | Guitar test | Real guitar into J1, headphones on J4: clean signal, no clipping at normal pick strength; record the peak level the firmware logs |
| 6.6 | AUX: phone/laptop into J2 at full volume | Heard on J4 and the speaker output; record the logged peak and whether input 2 clips |
| 6.7 | `HP_DETECT` | Prints high with J4 empty (internal pull-up), low with a plug in; TP1 ≈ 3.3 V empty, ≈ 0 V with a plug in. No chatter after debounce |
| 6.8 | Headphones through a reset: 1 kHz into J1, headphones on J4, hold RESET, then release | J4 goes silent while RESET is held (codec clocks stopped) and the tone returns after boot. Note any click at each step |
| 6.9 | `SPK_EN` toggled high/low | Q2 pin 1 follows. R107 pad 2 ≈ 0.22 V while high (0.22–0.23 V: R23 against R107's 10k to `+5V_RAW`), ≈ TP106 while low; C124 pad 1 follows within ≈ 6 ms. Record the high-state reading (Q2's gate drive from 3.3 V) |
| 6.10 | Settings survive a hard power cut: change a setting on the display, wait for the debounce, pull the J101 plug, restore it | The setting is kept |
| 6.11 | Wiring check before connecting the display and the speaker | J3 GND/TX/RX as labelled; J105 (DISP/GND) to the display's supply; J106/J107 as 3A.3; J102: speaker + to pin 2 (SPK+), − to pin 1, neither wire to GND or the chassis; the panel switch on SW101 |
| 6.12 | `BATT_SENSE`: J101 at 9.0, 11.1 and 12.6 V, measuring TP101 each time | A1.25 and the ADC read TP101 / 11 (0.818, 1.009, 1.145 V) within ±2.4 %; the printed VBAT within ≈ 3 % of TP101 |
| 6.13 | UART on J3 with a 3.3 V USB-serial adapter (adapter TX → J3.3, RX → J3.2, GND → J3.1) | Heartbeat received; echo works. Unplug the adapter: the firmware reports no display (R24 holds RX low), and recovers when it is plugged back in. **Before connecting the real display**, confirm its TX idles at ≤ 3.3 V |
| 6.14 | Display on J3, powered from J105 (limit 2.5 A) | Shows data from the Daisy; record its supply current. Scope TP106, J105.1 and `+5V` (C5 `+`) with Wi-Fi and the backlight active: the display's current pulses show on J105.1 and TP106, and much less on `+5V`. Record the ripple on each and the noise floor at J4 and across J102 with the beads in (JP101/JP103 open), then bypassed, and, if C104/C106 are fitted, with JP102/JP104 shunted. Power off for each change; record each configuration |
| 6.15 | USB alone (only if 5.0 read < 0.5 V): battery off at SW101, display unplugged, Daisy on USB, 1 kHz into J1, `SPK_EN` driven high | `+5V` (C5 `+`), TP106 and TP104 ≈ 0 V; `5V_SENSE` prints ≈ 0 V. A1.18 (`AUDIO_OUT_1`, on top of the module), C9 and C108 pad 1 carry no signal: the firmware keeps the outputs silent, which protects U2's inputs and U101's (rated −0.3 V…6.3 V). If `+5V` or TP106 rises above 0.5 V, unplug USB at once. Then switch on at SW101: `5V_SENSE` prints ≈ 2.5 V and the tone returns on J4 without a click. Record all of it |
| 6.16 | Output DC with the codec running: firmware outputs digital silence. Measure DC at A1.18 and A1.19 (on top of the module) and at C108 pad 1 (`LINE_OUT`). Then, speaker unmuted, hold RESET and release, watching C108 pad 1 and J102 | All three within ±20 mV of 0 V, which confirms the Seed3 outputs are AC-coupled. C108 keeps DC at pin 19 out of U101, but R12 carries it: more than a few tens of mV, see DESIGN.md "Speaker send" (a 10 µF cap in series). Record any step on `LINE_OUT` and any thump on J102 at reset and release |
| 6.17 | AUX level with the Daisy fitted: 1 kHz, 2 Vpp into J2, same signal on tip and ring, then tip only with ring grounded. Scope A1.17 (on top of the module) and read the firmware's input-2 peak | Tip and ring: 0.155–0.160 Vpp (−22.2 to −21.9 dB, the Daisy's input at 4–6 kΩ). Tip only: ≈ 0.08 Vpp. Record both. ≈ 0.17 Vpp means the module adds almost no load; much lower means its input is well below 4 kΩ (see DESIGN.md "AUX input") |
| 6.18 | `+5V` transitions on USB (only if 5.0 read < 0.5 V): Daisy on USB, battery on, full-scale 1 kHz to J4 (32 Ω load). Scope `+5V` (C5 `+`), PVSS (C14 pad 1) and U2's INL− (R25's U2 side). Switch off at SW101, then on | Power off: INL− goes silent before `+5V`/PVSS collapse, or stays outside PVSS − 0.3 V … `+5V` + 0.3 V for no more than a few ms. Record the time. Power on: audio returns ≥ 10 ms after `+5V` and PVSS settle, with no click on J4 |
| 6.19 | Hot passive pickups: the hottest passive guitar available into J1, played as hard as possible | Record the logged peak. It should stay below full scale (≈ 3.9 Vpp at J1). Active pickups are out of scope |
| 6.20 | Speaker level cap: firmware full-scale 1 kHz to the speaker output, dummy load, at 12.0 V and then 9.0 V on J101 | ≈ 5.5 Vrms (≈ 7.5 W: full scale ≈ 9.7 Vrms, less 5 dB), no clipping at either voltage (at 9.0 V U101 clips at ≈ 8.4 V peak; the capped output peaks at ≈ 7.7 V). Record both |
| 6.21 | Speaker on J102 (+ tab to pin 2, SPK+) | Guitar through the speaker at a moderate level: clean, no hum or whine at idle, no rattle. Record the speaker used |
| 6.22 | Low battery: speaker muted (headphones in), display unplugged. Lower J101 from 12.0 V to 6.0 V over about a minute, then back | Record VBAT (TP101) where TP106 falls below 4.9 V (the DFR0571 drops out; DFRobot lists 8 V as its minimum), where SDZ goes low (TP106 < 4.65 V, U103), where the firmware goes silent (`5V_SENSE` < 2.2 V), and the printed VBAT. Back at 12 V: U101 restarts (SDZ ≈ 26 ms after TP106 passes 4.65 V) and the Daisy recovers or resets cleanly. The board has no battery cutoff of its own: the pack's protection and these thresholds are all there is |

## Stage 7 — Soak and robustness

| # | Check | Expect |
|---|---|---|
| 7.1 | Run passthrough with audio for 30 min from the Talentcell battery (record its voltage at the start and end) | No dropouts, resets, or drift in `VREF`, TP106 or the printed VBAT |
| 7.2 | Plug/unplug J1, J4, J2 repeatedly while running | No resets, no lasting noise, jacks stay mechanically solid; `HP_DETECT` reports every J4 change |
| 7.3 | Wiggle the J3, J105, J106, J107 and J102 wires, the switch wires and the J101 plug while running | No crackle, dropouts or resets. A loose DFR0571 wire can only drop the 5 V, never leave it up without the battery, since the module runs from J106 |
| 7.4 | Full-level 1 kHz into 32 Ω on J4 for 10 min | U2 at most warm; no shutdown or distortion change |
| 7.5 | Light flex/tap test on the board and Daisy, guitar plugged in, listening on J4 and the speaker | No crackle or resets (would point to a cracked joint or loose socket pin). Record any knock heard through C2 or C108/C109 (class II ceramics, DESIGN.md "Open items") |
| 7.6 | Board off, a phone or laptop at full volume into J2. Scope A1.17 (on top of the module) | At most ≈ 0.46 Vpp (±0.23 V) for a 2 Vrms source: the unpowered codec's input stays within its ±0.3 V rating. Record the peak |
| 7.7 | Speaker for 30 min: music at the capped level into the speaker, or 1 kHz at ≈ 2 W into the dummy load | No thermal shutdown (TP109 stays high); record U101's case temperature; L101/L102 warm at most; Q101, F101 and the DFR0571 cool |
| 7.8 | With the battery: switch on at SW101 20 times, and plug the battery into J101 (switch on) 10 times | F101 survives every inrush (record the fuse value); U101 starts each time (TP109 high); record any spark at the switch or the jack |

## Stage 8 — Pops, hiss and mute

Needs the product firmware (volume ramps, headphone detect, settings saved on change, `SPK_EN` delay) and an audio interface on
the laptop. Record J4 (into a 32 Ω load or EarPods) into the interface, and the speaker with a microphone or as J102's
differential voltage on the scope. **Never connect the interface to J102:** both terminals sit at ≈ 6 V. Look at each
recording for spikes. Pass means no audible click and no spike more than ~10 dB above the recording's noise floor.

| # | Check | Expect |
|---|---|---|
| 8.1 | Power-on pop: record J4 and the speaker, then switch on at SW101 | No click on either output. U2 turns on with `+5V`, before the Daisy boots, so listen for anything on J4 while the codec starts up |
| 8.2 | Speaker power-on: scope TP106, TP104 (SDZ), Q2 pin 1 (`SPK_EN`), C124 pad 1 (MUTE) and J102 (differential) at power-on, into the speaker | SDZ rises ≈ 26 ms after TP106 passes 4.65 V while MUTE is still high. C108/C109 charge to U101's 3 V bias through its 60 kΩ inputs (τ ≈ 90 ms) while muted. `SPK_EN` goes high after audio starts and MUTE falls ≈ 6 ms later. Record any step on J102 at unmute, and listen for a thump |
| 8.3 | Power-off pop: record J4 and the speaker, switch off at SW101 | Note the result. The speaker stays unmuted until `+5V_RAW` falls below 4.65 V (U103) or the firmware sees `5V_SENSE` low, which happens only once the DFR0571 drops out, after PVCC has already sagged (3C.9 has the timing) |
| 8.4 | Hard power cut: record J4 and the speaker, pull the J101 plug while playing | Note the result. A small click is acceptable here, a loud bang is not |
| 8.5 | Headphone plug-in and removal while playing a 1 kHz tone | `SPK_EN` goes low while headphones are in and high again when they come out. No click on J4 or the speaker |
| 8.6 | Watchdog mute: debug build that stops the audio callback on a USB serial command | J4 and the speaker go silent (codec DAC power-down), and C124 pad 1 (MUTE) is above 2 V within ~10–20 ms (IWDG ≈ 10 ms, then ≈ 6 ms for C124). The Daisy resets and boots back into silence. Record any click on J4 and the speaker |
| 8.7 | Hiss with EarPods: J1 unplugged, firmware volume at a quiet listening level, then at max | No hiss audible at a normal listening level (U2 runs at a gain of −1; DESIGN.md "Open items" says how to lower it). Record whether hiss is audible at max |
| 8.8 | Maximum headphone level: full-scale 1 kHz into a 32 Ω load on J4 | ≈ 0.60 Vrms per channel (1 Vrms Daisy full scale, −4.4 dB at R10 into R25 ‖ R27, gain −1 in U2), no clipping: U2's 1 % THD limit is ≈ 2.0 Vrms into 32 Ω and ≈ 1.06 Vrms into 16 Ω. Repeat into 16 Ω. Listening check with the intended headphones: loud enough with margin |
| 8.9 | Speaker hiss: J1 unplugged, speaker level at the cap, ear near the cone | Record whether hiss or whine is audible, and the noise across J102 on the scope (SLOS708G: 65 µV A-weighted at 20 dB) |

## Fault-finding hints

| Symptom | Look at first |
|---|---|
| Supply hits the current limit in Stage 2 | 1.29 short; C111/C112 reversed; U101's PVCC pins bridged to its exposed pad |
| `VBAT_PROTECTED` ≈ 0.5 V below the supply | Q101 on its body diode: D101 reversed, R101 open, Q101's legs (2.3) |
| Supply hits the limit in Stage 3B | `+5V_RAW` or `+5V` short (1.1, 1.35); the DFR0571's wires (3B.1); C5 reversed; U1/U2 rotated; U2 pins bridged |
| No `+5V_RAW` | The DFR0571 (3A), J107's wiring, Q102 (orientation, gate at GND, swapped with Q2) |
| `+5V_RAW` fine, no `+5V` | FB101 (1.34), Q1 orientation or swapped with Q2 |
| `VREF` not ≈ 2.5 V | R6/R7 values, C7 leakage/short |
| SDZ stays low | `+5V_RAW` below 4.65 V; a shunt left on JP105; U103 pins 1–2 or 2–3 bridged; R109/R110 open |
| FAULTZ low | A latched fault. Over-current: J102 shorted or a wire to GND, C121/C122, an output pin. DC detect: C108/C109, the input pins. Over-temperature: U101's exposed pad. Clear with JP105 or a power cycle |
| Speaker silent, FAULTZ high | MUTE high (Q2, R23, `SPK_EN`, R108/C124); SDZ (TP104); L101/L102; J102 wiring |
| Speaker level wrong or distorted | R104 (gain), C108/C109, R11/R12; TP103 sagging under load (R105, F101, Q101, the supply lead) |
| Speaker never mutes | MUTE bridged to GND (U101 pins 11–13); Q2 shorted, or an AO3401A fitted as Q2 |
| Battery reading wrong | R102/R103 swapped (reads ≈ 3× high); R13/R22; C17 |
| Input works only intermittently | J1 tip-normal switch, C2/R2 joints |
| No headphone output | U2.2 (SHDN), U2.3 (PVDD) and U2.11/U2.15 (SVDD) at `+5V`; U2's pin joints |
| PVSS ≈ 0 V with SHDN high | C13 (flying cap), C14, U2 pins 4/6/7/13 |
| DC or hum on J4 outputs | U2 SGND (pin 8) and PGND (pin 5) to GND; INL+/INR+ (pins 1/9) grounded; R25–R28 values |
| Output only on one HP channel | That channel's C10/C11 and R25–R28, U2 pin 16/10 (input) or 14/12 (output) joints, J4 tip/ring pins |
| AUX input dead, quiet or too loud | J2 pins, R3/R4, R5 value (470 Ω: a 3.3k fitted by mistake is ≈ 11 dB louder), C3 shorted; `AUDIO_IN_2` trace to A1.17 |
| `HP_DETECT` stuck or inverted | J4 pins 5/6 mapping, TP1 → A1.23 trace, firmware pull-up on pin 23 (PA3) |
| Daisy won't boot | Socket orientation / offset; `3V3_D` and `+5V` shorted at A1.38/A1.39 |
| Daisy partly alive with the battery off | Back-powering: pin 25 (5.9), J3 (R8/R9 values, a display powered from elsewhere), USB (5.0) |
| Thump at power-off | 8.3: U101 plays on until the 5 V drops. `BATT_SENSE` falls before the 5 V does, so the firmware can see the switch-off first |

## Results log

Board serial / ID: __________  Assembled by: __________  Date: __________

Fab package: __________  Tested by: __________  Firmware commit: __________

DFR0571 (marking / serial): __________  Battery 12 V output: full ______ V, near empty ______ V

**Options fitted on this board** (note in the stage rows if a setting changed between stages)

| Option | Setting |
|---|---|
| JP101 (FB101 bypass) / JP103 (FB102 bypass) | |
| C104 + JP102 / C106 + JP104 (optional bulk) | |
| F101 fuse | |
| R105 part | |
| R106 value | |
| C108/C109 value | |
| C121/C122 value | |
| L101/L102 value | |

| Stage | Result (Pass/Fail) | Measured values / notes |
|---|---|---|
| 0 Visual & mechanical | | |
| 1 Unpowered resistance | | TP101 → GND = ____ kΩ, R13 pad 1 → GND = ____ kΩ, TP106 → GND = ____ kΩ |
| 2 Battery side | | I = ____ mA at 12.0 V, TP101 = ____ V, VGS = ____ V, A1.25 = ____ V |
| 2.13 / 2.14 Reverse J101 / J107 | | I = ____ mA / ____ mA |
| 3A DFR0571 alone | | Vout = ____ V (12 V in), ____ V (9 V in), ____ V (0.1 A); Iin = ____ mA |
| 3B 5 V rails | | I = ____ mA, TP106 = ____ V, Q102 drop = ____ mV, +5V = ____ V, VREF = ____ V, PVSS = ____ V |
| 3C U101 enabled | | I = ____ mA, SDZ = ____ V, GVDD = ____ V, inputs = ____ / ____ V, SDZ delay = ____ ms |
| 3C.9 Power-off | | Largest MUTE − PVCC = ____ V, SDZ − PVCC = ____ V |
| 3D Filter options | | |
| 4A Guitar input buffer | | Clip level = ____ Vpp |
| 4B Headphone filter / amp | | L = ____ Vpp, R = ____ Vpp into 32 Ω, DC offset L/R = ____ / ____ mV |
| 4C Speaker amp | | Gain = ____ dB, idle I = ____ mA, f_sw = ____ kHz, offset = ____ mV, clip = ____ V pk at ____ A, fault latch and JP105 clear OK |
| 4D AUX input | | Tip+ring = ____ Vpp |
| 5 Power-up with Daisy | | 5.0 VIN on USB = ____ V, I = ____ mA, 3V3_D = ____ V, back-power I = ____ mA |
| 6 Firmware functional | | SPK_MUTE high-state = ____ V, VBAT error = ____ %, AUX peak = ____, display I = ____ mA, DFR0571 drop-out at VBAT = ____ V, SDZ off at VBAT = ____ V |
| 7 Soak & robustness | | U101 = ____ °C after 30 min, fuse survived ____ starts |
| 8 Pops, hiss and mute | | SPK_EN delay = ____ s, mute time = ____ ms, HP max = ____ Vrms |

Rework performed:

Open issues:
