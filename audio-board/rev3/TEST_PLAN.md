# Audio board rev 3 — Post-Assembly Test Plan

Bring-up and acceptance tests for one hand-assembled **rev 3** board, built from `seed3-carrier.kicad_sch` (sheet 2 is
`power.kicad_sch`), `fab/B1NARY_SOLUTIONS_gerber.zip` and `seed3-carrier-digikey.csv`. Record the package name in the log.
Expected numbers come from the rev 3 netlist and the parts' datasheets. `DESIGN.md` has the design and its reasons,
`CHANGES.md` the differences from audio rev 2 and power rev 1, and `../TEST_PLAN.md` is rev 2's plan. Stage 1A keeps rev 2's
item numbers so results compare across revisions.

Work through the stages in order and stop at the first failure: each stage assumes the one before it passed. Record results
in the log at the end (one copy per board serial). DESIGN.md "Open items" has audio rev 2 and power rev 1 brought up first:
set this board's jumpers and experiment parts from their results, and record the settings in the log.

## Powering rule: 12 V on J101, never 5 V alone on J107

Every powered stage runs from a current-limited 12 V bench supply on J101 (centre positive), with the DFR0571 wired to J106
and J107 as in use. Stage 2 and step 5.9 leave the DFR0571 disconnected, with nothing on J106 or J107. **Never power the
board from 5 V on J107 alone**, whether from a bench supply or from a DFR0571 fed from anything but J106. The reason is in
DESIGN.md "Decisions"; 3C.1 and 3C.9 check both edges of the normal sequence.

The same applies to anything else that could lift `+5V_RAW` while the battery is off:
- **R105** (0 Ω) stays fitted whenever U101 is. Without it PVCC sits at 0 V while `+5V_RAW` is up.
- **The Daisy on USB:** `+5V` and `+5V_RAW` are one node at DC (FB101). The Seed3 doesn't drive its VIN pin from USB
  (Seed3 datasheet Figure 1.0); step 5.0 confirms it on this module before USB is used with the battery off.
- **The display:** if it has a USB port of its own, don't plug it into a computer while it is wired to J105 and the battery
  is off. Its 5 V would reach `+5V_RAW` through FB102.
- **Jumpers:** change JP101–JP104 only with the power off (JP102/JP104 would connect an uncharged 100 µF to a live rail).
  JP105 is shorted live on purpose in 3C.8 and 4C.7.

## Circuit summary (what is being tested)

DESIGN.md describes each block, its parts and its values. The pinouts and probe points the tests use are below.

**Pinouts used below**

- U101 TPA3118D2 (HTSSOP-32, exposed pad = GND): 1 MODSEL (GND), 2 SDZ, 3 FAULTZ, 4 RINP, 5 RINN, 6 PLIMIT, 7 GVDD,
  8 GAIN/SLV, 9 GND, 10 LINP (GND), 11 LINN (GND), 12 MUTE, 13–15 AM2/AM1/AM0 (GND through JP106–JP108), 16 SYNC (not
  connected), 17 AVCC, 18/19 PVCC, 20 BSNL, 21 OUTNL, 22 GND, 23 OUTPL, 24 BSPL, 25 GND, 26 BSNR, 27 OUTNR, 28 GND,
  29 OUTPR, 30 BSPR, 31/32 PVCC. `OUT_P` = pins 27 + 29 (→ L101 → SPK+), `OUT_N` = pins 21 + 23 (→ L102 → SPK−)
- U103 TPS3808EG50 (SOT-23-6): 1 RESET (`AMP_PG`), 2 GND, 3 MR (`AMP_MR`, 90 kΩ internal pull-up), 4 CT (open: 20 ms),
  5 SENSE and 6 VDD (both `+5V_RAW`)
- Q101 IRF4905 (TO-220): 1 G, 2 D (SW101.2), 3 S (`VBAT_PROTECTED`). D101 (SOD-123): cathode on `VBAT_PROTECTED`, anode on
  Q101's gate
- Q102 AO3401A, Q2 2N7002 (SOT-23): 1 G, 2 S, 3 D. Q102: G GND, S `+5V_RAW`, D `+5V_DFR`. Q2: G `SPK_EN`, S GND, D `SPK_MUTE`
- U1 TLV9061 (SOT-23-5): 1 OUT, 2 V−, 3 IN+, 4 IN−, 5 V+
- U2 TPA6130A2 (WQFN-20, exposed pad 21 = GND): 1 LEFTINM, 2 LEFTINP, 3 GND, 4 RIGHTINP, 5 RIGHTINM, 6 SD, 7 SDA, 8 SCL,
  9/10 GND, 11 HPRIGHT, 12 VDD, 13 GND, 14 HPLEFT, 15/16 CPVSS, 17 CPN, 18 CPP, 19 GND, 20 VDD. − inputs from `HP_SOURCE`
  through C10 (left) and C11 (right); + inputs to GND through C22 (left) and C23 (right); both VDD pins on `HP_5V`; C13
  between CPP and CPN, C14 on CPVSS. Registers: 1 control (0xC0 = both outputs on, stereo), 2 volume and mutes (bits 7:6
  mute, 5:0 volume; 0x35 = +0.1 dB), 4 version (bits 3:0 read 0010)
- J101: 1 centre pin (+), 2 sleeve (GND), 3 switched contact (not connected). SW101: 1 from F101, 2 to Q101's drain
- D102, D103 BAT54H (SOD-323): 1 cathode (band) on `AMP_PVCC`; 2 anode, D102 on `AMP_SDZ`, D103 on `AMP_MUTE`. Both bands
  face right, D102's toward R105 and D103's toward R106
- Left edge, rear to front: J106 (JST XH header: 1 `VBAT_PROTECTED` "BAT+", marked with a triangle, 2 GND), J107
  (1 `+5V_DFR` "5V", 2 GND), J105 (1 `+5V_DISPLAY` "DISP", 2 GND), J3 (1 GND, 2 `UART_TX_CONN` TX, 3 `UART_RX_CONN` RX).
  J106 and J107 are the DFR0571's input and return
- J102 (right edge): 1 SPK−, 2 SPK+
- JP101: 1 `+5V_RAW`, 2 `+5V`. JP102: 1 `+5V`, 2 C104 `+`. JP103: 1 `+5V_RAW`, 2 `+5V_DISPLAY`. JP104: 1 `+5V_DISPLAY`,
  2 C106 `+`. JP105: 1 `AMP_MR`, 2 GND
- DFR0571 (U102, off-board): VIN+, GND, 5V OUT, GND. It isn't isolated: its two GND pads are one node
- J4 / J2 (SJ3-35063AG): 1 sleeve, 2 ring, 3 tip, 5 detect common, 6 detect NO (J2's 5/6 not connected)
- A1 (Daisy sockets, `A1.n` = Daisy pin n): 12 `I2C_SCL`, 13 `I2C_SDA`, 14 USART1 TX, 15 USART1 RX, 16 `AUDIO_IN_1`,
  17 `AUDIO_IN_2`, 18 `AUDIO_OUT_1`, 19 `AUDIO_OUT_2`, 20 GND, 22 `5V_SENSE`, 23 `HP_DETECT`, 25 `BATT_SENSE`, 27 `HP_SD`,
  28 `SPK_EN`, 32 `AMP_FAULTZ` through R30 (1k; input: low = speaker fault), 38 `3V3_D` (the I2C pull-ups), 39 `+5V`
  (VIN), 40 GND. All other pins are not connected. Probe the sockets while the Daisy is out; with it fitted the checks
  name a part on the same net
- Test points: TP1 `HP_DETECT`, TP101 `VBAT_PROTECTED`, TP103 `AMP_PVCC`, TP104 `AMP_SDZ`, TP106 `+5V_RAW`, TP109
  `AMP_FAULTZ`; TP102, TP105, TP107, TP108 GND
- Other probe points: `BATT_SENSE` at C17 pad 1 (or A1.25); `HP_5V` at C21 pad 1 or C12 pad 1; `+5V` on the power sheet's
  side of FB101 at C105 pad 1; `AMP_AVCC` at C115 pad 1; GVDD at C110 pad 1; `AMP_GAIN` at R104 pad 1; `AMP_PG` at R110
  pad 1; `AMP_MR` at JP105 pin 1; `SPK_MUTE` at R107 pad 2; U101's MUTE at C124 pad 1; `LINE_OUT`/`LINE_REF` at C108/C109
  pad 1 and U101's inputs at their pad 2; `OUT_P`/`OUT_N` at L101/L102 pad 1; the bootstrap pins at C117–C120 pad 1
  (`BSPR`, `BSNR`, `BSPL`, `BSNL`; pad 2 is the output); Q101's gate at R101 pad 1

**Options and experiments.** Bring up with the defaults below, then record every setting in the log, since some readings
depend on them.

| Option | Default for bring-up | Readings it moves |
|---|---|---|
| JP101 / JP103 (bead bypass) | Open (beads in) | 1.34 only detects a missing bead with these open |
| JP102 / JP104 (optional bulk) | Open; C104 and C106 are DNP | None until C104/C106 are fitted (3D.2) |
| JP105 (manual reset) | Open (shunted only in 3B and to clear a fault) | Shunted: SDZ held low, `AMP_MR` → GND 0 Ω, TP106 → GND ≈ 4.7 kΩ |
| F101 | Bel 0683G3150-01, T3.15A SMD, soldered (no holder, no spare values) | None |
| R105 | 0 Ω RC2512JK-070RL (2 A); spare CRCW2512 0 Ω | None |
| R106 (AVCC filter) | 10 Ω, 0603; no spares in rev 3's order (the earlier build's 4.7 Ω and 22 Ω are 1206 and don't fit) | 1.31: TP103 → C115 pad 1 |
| C108/C109 | 470 nF 25 V C0G, 1206 (GRM31C5C1E474JE01L); no spare pair in the order | None (4C.4 checks the 20 Hz loss) |
| C121/C122 | 680 nF, 0805; no spare pair in rev 3's order (the earlier build's 470 nF pair is 1206 and doesn't fit) | 4C.4: filter corner 61 kHz; a 470 nF pair would move it to 73 kHz |
| L101/L102 | 10 µH; spare pairs 6.8 µH, 15 µH | 4C.3/4C.4: corner 74 / 50 kHz, ripple up / down |

## Equipment

- Current-limited bench supply, 0–15 V, at least 2.5 A, whose limit holds at 20 mA; a lead with a 5.5 × 2.1 mm barrel plug
  (centre +) for J101 with its two wires free so they can be swapped (2.13)
- A second supply channel, 0–6 V, limit 10 mA, whose output floats (not joined to the first channel's − or to earth), for
  A1.28 and 2.14
- DMM with diode mode, oscilloscope (≥ 20 MHz, 4 channels; 2 with A − B math at the least)
- 4 Ω dummy load, 25 W or more (50 W preferred)
- The DFR0571 with its input cable (an XHP-2 housing and the ASXHSXH22K305 lead cut in two) and two output wires
  (ferrules), the S1B panel switch wired to SW101 (or a wire link), a 47 Ω 1 W resistor (3A.2), the four 2.54 mm shunts
- Signal generator or audio interface (sine 20 Hz – 20 kHz, ≥ 2 Vpp); a phone/laptop headphone output works for listening
  tests
- ¼" mono cable, 3.5 mm stereo (TRS) cable, 3.5 mm mono (TS) plug, headphones (≈ 32 Ω), 32 Ω and 16 Ω dummy loads (one per
  channel)
- Two 1 kΩ resistors and clip leads to pull A1.28 (`SPK_EN`) and A1.27 (`HP_SD`) to 3.3 V with the Daisy out
- A 3.3 V I2C master for U2 with the Daisy out (a USB-I2C adapter, or a Raspberry Pi Pico or 3.3 V Arduino), with clip
  leads to A1.12 (SCL), A1.13 (SDA), A1.20 (GND) and its 3.3 V to A1.38 (`3V3_D`, which feeds R32/R33)
- USB cable for the Daisy, USB-serial adapter (3.3 V) for J3, the display and its J105 power lead
- A 4 Ω speaker (Jensen MOD10-50 or Skar FSX10-4) with crimped quick-disconnects, and a microphone (or phone) for the
  speaker pop tests
- The Talentcell battery (Stage 7)
- Magnifier/microscope, flux, isopropyl alcohol, solder wick, a needle probe; hot air for U101's exposed pad

## Stage 0 — Visual and mechanical inspection (unpowered, no Daisy, no DFR0571)

| # | Check | Pass criteria |
|---|---|---|
| 0.1 | Clean flux residue; inspect every joint under magnification | No bridges (esp. U1, U2, U101, U103, Q2, Q102, D1–D5, D101, D102, D103), no cold/dull joints, no solder balls |
| 0.2 | IC orientation and type | U1, U2, U101 and U103 pin-1 marks match the silkscreen; U1 = TLV9061, U2 = TPA6130A2 (TI RTJ, 4 × 4 mm), U101 = TPA3118D2, U103 = TPS3808EG50. A rotated U101 can't be found by resistance |
| 0.3 | U2 (WQFN-20, 0.5 mm) | Every pin wetted at the package edge, part flat, no bridges. The exposed pad can't be seen; 1.6–1.8b and 4B check it electrically |
| 0.4 | U101 (HTSSOP-32, 0.65 mm) | All 32 pins with fillets, part flat, no bridges. Exposed pad: solder visible in the back-side mask opening and its vias, none squeezed out toward the pins. The bridges that do damage at first power: 5–6 (1.45), 19–20 and 30–31 (PVCC on a bootstrap pin); 15–16 (SYNC to GND) can only be seen |
| 0.5 | Q102 and Q2 | Q102 is the AO3401A, Q2 the 2N7002, each on the correct pads. Q2 in Q102's place leaves `+5V_RAW` dead; an AO3401A in Q2's place holds `SPK_MUTE` near 1 V |
| 0.6 | Q101 and D101 | Q101 is the IRF4905, legs in the holes the silkscreen marks, tab facing as drawn. D101's cathode band on the side the silkscreen marks (cathode on `VBAT_PROTECTED`) |
| 0.7 | Polarised parts | C5 `+` to `+5V`. C111 and C112 `+` to PVCC (backwards they fail at first power). C104 and C106 not fitted (DNP). D102 and D103: cathode bands to the right (toward R105 and R106) |
| 0.8 | Passive values vs BOM | Sheet 1: R1 (1M), R3/R4/R6/R7/R8/R9 (10k), R12/R17/R18/R19/R24/R34 (100k), R32/R33 (2.2k), R10 (3.3k), R5/R20 (470), R2/R11/R21/R30 (1k); C7 is the 1210 part; C2 (47 nF C0G), C12–C15 and C21 (10 µF) are 0805; C10/C11/C22/C23 (470 nF C0G) are 1206; R29 is 2.2 Ω; C1, C3, C4, C6, C9, C16–C20 are 0603; FB1 is the 0603 bead marked on its tape BLM18HG601 (not FB101/FB102's MPZ1608). Sheet 2: R101/R103/R107/R109/R112/R113 (10k), R114 (18k), R102 (100k 1 %), R104 (5.6k), R106 (10 Ω), R108/R110 (2.2k), R111 (100k), R105 (0 Ω 2512). The other resistors are 0603, often unmarked: take values from the tape (stage 1 catches R102/R103 swapped, a 10k for R106, R104). Ceramic caps aren't marked: fit C108/C109 (470 nF C0G, 1206), C121/C122 (680 nF), C117–C120 (220 nF), C110 (1 µF) and C103 (10 µF) straight from their tapes |
| 0.9 | F101 | The Bel 0683G3150-01 (marked "3.15A S G"), flat on its pads, both end terminations soldered with fillets, no solder bridging along the body. Record the part fitted |
| 0.10 | Screw terminals J3, J102, J105, J107, SW101; JST header J106 | Seated flat, wire openings (J106's plug opening) facing the board edge, screws turn freely; the module's input cable plugs into J106 one way round and latches |
| 0.11 | Silkscreen legends | GND/TX/RX (J3), BAT+/GND (J106), 5V/GND (J107), DISP/GND (J105), SPK+/SPK− (J102, SPK+ on pin 2, toward the rear), 12V IN (J101); each test point's net beside its reference (VBAT, PVCC, SDZ, FAULT, 5V RAW, HP DET, GND) |
| 0.12 | Jumper headers | JP101–JP105 fitted, all shunts off. JP106–JP108 (back, left of U101) bridged in copper, none cut |
| 0.13 | Daisy sockets | Both A1 1×20 sockets flush and parallel; Daisy inserts with moderate force, all pins engaged, USB connector on the correct end |
| 0.14 | Jacks J1, J4, J2 and J101 | Fully seated, flush to the board edge, plugs insert/eject cleanly |
| 0.15 | Enclosure fit (if available) | Front jacks, USB, J101, the switch, J102 and the left-edge terminals line up with panel holes and cable routes |

## Stage 1 — Unpowered resistance checks (no Daisy, no DFR0571)

Nothing on any terminal, the panel switch off, every shunt off, Daisy out. DMM red lead on the first point named, black on
the second; let capacitors charge before reading. Probe on IC pins, test points, pads or the Daisy sockets (A1), not on
connector shells.

The numbers are the resistor network with every IC and diode open. An unpowered IC pin or a diode in a parallel path can
lower a reading, by an amount that depends on the meter's test voltage; the table gives the lower bound.
- **The rails' 10.0 kΩ.** `+5V_RAW` and `+5V` are one node at DC (FB101), so every reading through either rail sees both
  rails' loads: (R6 + R7) ∥ (R18 + R19) ∥ (R109 + R110 + R111) ∥ (R112 + R114) = 20k ∥ 200k ∥ 112.2k ∥ 28k = 10.0 kΩ
  (15.6 kΩ without R112 + R114, 11.0 kΩ without R109–R111). `HP_5V` reads the same plus R29's 2.2 Ω.
- **`VBAT_PROTECTED`** carries 200 µF (C111/C112) behind 110 kΩ (R102 + R103): its readings take a minute or two to settle.
- **D102 and D103** join `AMP_SDZ` and `AMP_MUTE` to PVCC. In a row that measures from SDZ (TP104), MUTE (C124 pad 1),
  `SPK_MUTE` (R107 pad 2) or `AMP_PG` (R110 pad 1), put the **black** lead on that point and the red on the other, so the
  diode is reverse-biased. With the red lead there, the diode conducts into PVCC's 200 µF and the reading dips, then
  settles lower.
- Readings from `+5V` or `+5V_RAW` to GND also reach PVCC through R107–R110 and the diodes: they start low and climb over
  about 10 s to ≈ 9–10 kΩ where the table says 10.0 kΩ.

**1A. Audio section (rev 2's item numbers, where rev 2 has the same check)**

| # | Measure | Expect | A wrong reading means |
|---|---|---|---|
| 1.1 | `+5V` (C5 `+`) → GND | Rises to ≈ 10.0 kΩ, less with U1/U2/U103's supply pins; never below 50 Ω | Short on the 5 V rail: C4/C5/C6, C103/C105/C107/C123, U1.5. Or on `HP_5V`, through R29: C12/C15/C21, U2's VDD pin 12 or 20 bridged to GND pin 13 or 19 |
| 1.2 | C105 pad 1 → C5 `+` | < 1 Ω (one `+5V` net) | Open: the `+5V` trace from FB101 to the audio side broken |
| 1.2a | C12 pad 1 (`HP_5V`) → C5 `+`; C12 pad 1 → C21 pad 1 and → C15 pad 1 | ≈ 2 Ω (R29, 2.2 Ω: subtract the leads' own reading); < 1 Ω each | Open on the first: R29 open or missing (U2 unpowered). Open on the others: C21 or C15 not on `HP_5V` |
| 1.3 | J3.1, J101 sleeve (pin 2), J105.2, J106.2, J107.2, TP102, TP105, TP107, TP108 → A1.40 | < 1 Ω each | Open joint |
| 1.4 | `VREF` (C7) → GND | ≈ 7.5 kΩ (R7 ∥ (R6 + the other 5 V loads)); down to ≈ 5 kΩ with U1/U2's supply pins | < 1 kΩ = C7 shorted; > 10 kΩ = R7 open or wrong |
| 1.5 | J3.2 → GND; J3.3 → GND | Open; ≈ 110 kΩ (R9 + R24) | UART pins shorted to GND; ≈ 100 kΩ = R9 shorted, open = R9 or R24 open |
| 1.6 | CPVSS (C14 pad 1) → GND and → `+5V` (C5 `+`) | High (no short) | C14 shorted; U2.15 (CPVSS) bridged to U2.14 (HPLEFT) or U2.16 to U2.17 (CPN) |
| 1.6a | C13 pad 1 (CPP) → C13 pad 2 (CPN), → `+5V` and → GND; C13 pad 2 → GND and → C14 pad 1 (CPVSS) | High (no short) on all five | C13 shorted; U2 pins 16–17, 17–18, 18–19 or 19–20 bridged |
| 1.7 | A1.33 → GND and → `+5V`; A1.38 → GND and → `+5V` | Open (A1.38, `3V3_D`, reaches only R32/R33: see 1.8b) | Stray copper or a socket bridge |
| 1.8 | J4 tip → GND, J4 ring → GND, J4 ring → `+5V`, J4 tip → J4 ring | High (no short), not < 100 Ω | U2 bridge: HPRIGHT (11) to VDD (12), HPLEFT (14) to GND (13) or CPVSS (15) |
| 1.8a | U2 inputs: C10 pad 2 → C22 pad 2, C22 pad 2 → GND, C11 pad 2 → C23 pad 2, C23 pad 2 → GND | Not a short (> 1 kΩ) each | U2's input row bridged: pins 1–2, 2–3 (GND), 3–4 or 4–5 |
| 1.8b | U2 control: A1.12 → A1.38 and A1.13 → A1.38; A1.27 → GND; A1.12 → GND, A1.13 → GND and A1.27 → A1.13 | ≈ 2.2 kΩ each (R32, R33); ≈ 100 kΩ (R34); open on the last three | Open on the first: a pull-up or a B.Cu lane missing. ≈ 0 to GND: U2 pins 8–9 (SCL–GND) bridged. A1.27 low to A1.13: U2 pins 6–7 (SD–SDA) bridged. A1.27 ≈ 0: R34 shorted or SD bridged |
| 1.9 | J1 tip → GND, no plug | ≈ 0 Ω (tip-normal shorts to GND) | J1 switch / footprint issue |
| 1.10 | J1 tip → GND, plug inserted (other end open) | Open once C1 and C2 charge; not ≈ 0 Ω | ≈ 0 Ω = plug not lifting the switch |
| 1.11 | J2 tip → ring | ≈ 20 kΩ (R3 + R4) | R3/R4 open |
| 1.12 | J2 tip → GND | ≈ 10.5 kΩ (R3 + R5) | ≈ 10.0 kΩ = R5 or C3 shorted; ≈ 13.3 kΩ = a 3.3k fitted for R5 |
| 1.13 | TP1 (`HP_DETECT`) → GND, no plug in J4 | Open | J4 detect switch closed or bridged |
| 1.14 | TP1 → GND, plug in J4 | ≈ 0 Ω | J4 detect switch not closing (check pins 5/6 mapping) |
| 1.15 | TP1 → A1.23 | < 1 Ω (direct trace) | Open trace or J4 pin 6 joint |
| 1.16 | C108 pad 1 (`LINE_OUT`) → GND; C109 pad 1 (`LINE_REF`) → GND | ≈ 100 kΩ (R12); ≈ 1 kΩ (R21) | R12 or R21 missing or wrong |
| 1.17 | C108 pad 1 → A1.19 (`AUDIO_OUT_2`) | ≈ 1 kΩ (R11) | R11 open or wrong value |
| 1.18 | A1.25 (`BATT_SENSE`) → GND, once C17 and C111/C112 charge | Climbs to ≈ 10 kΩ (R103), lower if U101's PVCC pins conduct | ≈ 100 kΩ = R102 and R103 swapped; open = R103 missing; ≈ 0 = C17 shorted |
| 1.19 | A1.26 → anything | Open (A1.27 is `HP_SD`: see 1.8b) | Stray bridge |
| 1.20 | A1.28 (`SPK_EN`) → GND; R107 pad 2 (`SPK_MUTE`) → GND | ≈ 100 kΩ (R17); ≈ 20 kΩ (R107, then the rails' 10.0 kΩ), less with U1/U2/U103's supply pins, never below 10 kΩ | R17 missing; below 10 kΩ = Q2 shorted (≈ 0), or an AO3401A fitted as Q2 (its body diode conducts) |
| 1.21 | J3.2 → A1.14; J3.3 → A1.15; A1.15 → GND | ≈ 10 kΩ (R8), ≈ 10 kΩ (R9), ≈ 100 kΩ (R24) | UART series resistors, RX pull-down |
| 1.21a | A1.22 (`5V_SENSE`) → GND | ≈ 53 kΩ (R19 ∥ (R18 + the other 5 V loads)), less with U1/U2; not ≈ 0 Ω | R18/R19 missing or shorted |
| 1.21b | A1.16 (`AUDIO_IN_1`) → U1.1 | ≈ 470 Ω (R20) | Open = R20 open; ≈ 0 Ω = shorted |
| 1.21c | ESD diodes: J1 tip, J2 tip, J2 ring, J4 tip, J4 ring → GND, diode mode both ways | No conduction below ≈ 5 V either way (the meter reads open) | D1–D5 shorted, fitted wrong, or a solder bridge |
| 1.22 | Daisy socket (A1) adjacent pins: A1.17 (`AUDIO_IN_2`) → A1.18 (`AUDIO_OUT_1`); A1.18 → A1.19 (`AUDIO_OUT_2`); then spot-check the rest | Open on both (C9–C11 block DC on `AUDIO_OUT_1`); no shorts between other neighbouring pins, esp. A1.39 (`+5V`) ↔ A1.38 (3V3_D) and A1.40 (GND) | Socket bridge. **A1.39–A1.38 puts 5 V into 3V3_D and would damage the Daisy** |

**1B. Power section**

| # | Measure | Expect | A wrong reading means |
|---|---|---|---|
| 1.23 | J101 pin 1 (its solder joint) → SW101.1 | < 1 Ω (F101) | Fuse missing, blown or an end joint open |
| 1.24 | SW101.1 → SW101.2 with the panel switch wired: off, then on | Open; < 1 Ω | Switch wiring, terminal joints |
| 1.25 | SW101.2 (Q101 drain) → TP101 in diode mode, then reversed | ≈ 0.4–0.7 V (Q101's body diode); reversed: OL | ≈ 0 both ways: Q101 shorted (no reverse protection); OL both ways: Q101 missing or its legs in the wrong holes |
| 1.26 | GND → R101 pad 1 (Q101 gate) | ≈ 10 kΩ (R101) | Open = R101 missing; ≈ 0 = gate bridged to GND |
| 1.27 | R101 pad 1 → TP101 in diode mode, then reversed | ≈ 0.6–0.8 V (D101 forward); reversed: OL (a 12 V zener) | The two readings swapped: D101 backwards (VGS held at −0.7 V, Q101 off); ≈ 0 both ways: Q101's gate and source bridged |
| 1.28 | R101 pad 1 → SW101.2 (gate–drain) | Not a short | Q101's G and D legs bridged |
| 1.29 | TP101 → GND | Climbs over a minute or two to ≈ 110 kΩ (R102 + R103), lower if U101's PVCC pins conduct; never below 50 Ω | Short on the battery rail: C111/C112 (reversed?), C113/C114, U101's PVCC pins to its pad |
| 1.30 | TP101 → A1.25 (or C17 pad 1) | ≈ 100 kΩ (R102) | ≈ 10 kΩ = R102/R103 swapped; ≈ 30 kΩ = a 30k fitted for R102; open = R102 missing |
| 1.31 | TP101 → TP103; TP103 → C115 pad 1 | < 1 Ω (R105); ≈ 10 Ω (R106) | R105 missing (PVCC would stay at 0 V: see "Powering rule"); ≈ 10 kΩ = a 10k fitted for R106 |
| 1.32 | J107.1 → TP106 in diode mode, then reversed | ≈ 0.4–0.7 V (Q102's body diode); reversed: OL | ≈ 0 both ways: Q102 shorted (no reverse protection: don't run 2.14); OL both ways: Q102 missing or rotated; the two readings swapped: a 2N7002 fitted as Q102 |
| 1.33 | Q102 pin 1 → GND | < 1 Ω | Q102's gate not at GND |
| 1.34 | TP106 → C105 pad 1; TP106 → J105.1 (JP101 and JP103 open) | < 1 Ω each (FB101, FB102) | Open = a bead missing or cracked. With JP101/JP103 shunted these read 0 Ω whatever the beads are |
| 1.35 | TP106 (`+5V_RAW`) → GND | ≈ 10.0 kΩ, as 1.1, less with U1/U2/U103's supply pins; never below 1 kΩ | Short on `+5V_RAW`: C103, C123, C105, C107, U103, or 1.1's list; ≈ 4.7 kΩ = a shunt left on JP105 (10.0 kΩ ∥ R113 ∥ U103's 90 kΩ); ≈ 15.6 kΩ = R112 or R114 open (1.39) |
| 1.36 | R107 pad 2 → TP106; C124 pad 1 → R107 pad 2 | ≈ 10 kΩ (R107); ≈ 2.2 kΩ (R108) | R107/R108 open, or swapped with each other |
| 1.37 | TP104 → TP106; R110 pad 1 → TP106 | ≈ 11 kΩ ((R110 + R109) ∥ (R111 + 11.0 kΩ)); ≈ 9.2 kΩ (R109 ∥ (R110 + R111 + 11.0 kΩ)) | ≈ 111 kΩ on the first = R109 or R110 open; ≈ 2.2 kΩ on the second = R109 and R110 swapped |
| 1.38 | TP104 (SDZ) → GND | ≈ 19 kΩ (R111 ∥ (R110 + R109 + 11.0 kΩ)), less with U1/U2/U103's supply pins; never below 10 kΩ | ≈ 0 = U101 pins 1–2 (MODSEL, SDZ) bridged or C125 shorted |
| 1.39 | TP109 → TP106; TP109 → GND | ≈ 7.7 kΩ (R112 ∥ (R114 + 15.6 kΩ)); ≈ 10.6 kΩ (R114 ∥ (R112 + 15.6 kΩ)) | ≈ 34 kΩ on the first, 18 kΩ on the second = R112 open; ≈ 10 kΩ on the first, ≈ 26 kΩ on the second = R114 open (FAULTZ would sit at 5 V on Daisy pin 32) |
| 1.39a | A1.32 → TP109; A1.31 and A1.33 → A1.32 | ≈ 1 kΩ (R30); open | Open on the first: R30 missing, its vias or the trace to the socket. ≈ 0: R30 shorted. A short to a neighbour: socket bridge |
| 1.40 | JP105 pin 1 → TP106 | ≈ 9 kΩ (R113 ∥ U103's internal 90 kΩ MR pull-up) | Open/high = R113 open |
| 1.41 | J102.1 → J102.2; J102.1 → GND; J102.2 → GND | Open once C121/C122 charge; not a short | ≈ 0 between them = `OUT_P` and `OUT_N` joined (U101's output pins, L101/L102 pads); to GND = C121/C122 shorted or an output pin bridged to GND |
| 1.42 | J102.2 → L101 pad 1; J102.1 → L102 pad 1 | < 1 Ω (L101, L102) | Inductor joint open |

**1C. U101 and U103 neighbouring pins**

Pairs of adjacent pins on different nets. An unpowered U101 conducts between some pins through its own protection, so "not a
short" means above 100 Ω.

| # | Measure | Expect | A wrong reading means |
|---|---|---|---|
| 1.43 | TP104 → TP109 (U101 pins 2–3) | ≈ 18 kΩ (through R110 + R109 and R112, with R111 and R114 to GND) | ≈ 0 = SDZ–FAULTZ bridged |
| 1.44 | TP109 → C108 pad 2 (3–4); C108 pad 2 → C109 pad 2 (4–5) | Not a short | FAULTZ–RINP or RINP–RINN bridged |
| 1.45 | C109 pad 2 → C110 pad 1 (5–6) | Not a short | RINN–PLIMIT bridged: GVDD (6.4–7.4 V) on an input rated 6.3 V. **Fix before power** |
| 1.46 | C110 pad 1 → R104 pad 1 (7–8) | Starts near 5.6 kΩ and climbs (C110 charging through R104) | ≈ 0 = GVDD–GAIN bridged |
| 1.47 | R104 pad 1 → GND (8–9) | ≈ 5.6 kΩ (R104) | ≈ 0 = GAIN–GND bridged; 2.2 kΩ or 10 kΩ = the wrong part (another gain or slave mode) |
| 1.48 | C124 pad 1 (MUTE) → GND (11–12–13) | ≈ 22 kΩ (R108 + R107, then the rails' 10.0 kΩ), less with U1/U2/U103's supply pins; never below 10 kΩ | ≈ 0 = MUTE bridged to LINN or AM2 (both GND) |
| 1.49 | U101 pin 16 (SYNC) → GND, needle probe on the pin | Open | SYNC bridged to AM0 |
| 1.50 | TP103 → C120 pad 1 (19–20); TP103 → C117 pad 1 (30–31) | Not a short | PVCC on a bootstrap pin |
| 1.51 | C117, C118, C119, C120: pad 1 → pad 2 each (bootstrap–output: 29–30, 26–27, 23–24, 20–21) | Not a short | A bootstrap cap shorted or its two pins bridged |
| 1.52 | C119 pad 1 → GND (24–25); C118 pad 1 → GND (25–26) | Not a short | Bootstrap pin bridged to GND |
| 1.53 | L101 pad 1 (`OUT_P`) → GND; L102 pad 1 (`OUT_N`) → GND (21–22, 22–23, 27–28, 28–29 and the exposed pad) | Not a short | An output bridged to GND |
| 1.54 | R110 pad 1 (`AMP_PG`) → GND (U103 pins 1–2); JP105 pin 1 → GND (U103 pins 2–3) | ≈ 17 kΩ ((R110 + R111) ∥ (R109 + 11.0 kΩ)); ≈ 19 kΩ (R113 ∥ 90 kΩ, then the rails' 10.0 kΩ), both less with U1/U2/U103's supply pins | ≈ 0 = RESET or MR bridged to GND |
| 1.55 | D102 and D103 in diode mode: red on TP104 (SDZ), black on TP103 (PVCC); red on C124 pad 1 (MUTE), black on TP103; then each with the leads swapped | ≈ 0.1–0.3 V each (0.32 V at most for a BAT54 at the meter's ≈ 1 mA); swapped: OL, or a value that climbs as C111/C112 charge | ≈ 0.5–0.7 V: D102/D103 missing or open (only U101's own diode conducts). The two readings swapped: the diode fitted backwards, which would pull SDZ or MUTE up to PVCC at first power. **Fix before power** |

## Stage 2 — Battery side, DFR0571 disconnected

Left out: the Daisy, the DFR0571 (nothing on J106 or J107), the display (J105, J3), any load on J102, every shunt
(JP101–JP105). R105 fitted, the panel switch wired to SW101 (or a wire link for "on"). With no 5 V, U103 and the pull-ups
R107/R109/R112 sit at 0 V, so U101 stays in shutdown with SDZ and MUTE at 0 V, inside its rating. Only this stage and 5.9
run with the battery side up and 5 V off. Never the other way round.

Bench supply on J101 (centre +), 12.0 V, current limit **20 mA**. Expected draw is under 1 mA: the battery divider
0.11 mA (12.0 V / 110 kΩ), U101 in shutdown < 50 µA (SLOS708G, ICC(SD) at 12 V), R101/D101 under 0.1 mA, plus C111/C112
leakage. Switch on at SW101, then turn the supply on.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 2.1 | Supply current at 12.0 V | < 1 mA. Stop if it hits the limit | At the limit: a short on `VBAT_PROTECTED`/PVCC (1.29), C111/C112 reversed. A few mA: U101 not in shutdown (2.6), a lower-voltage zener for D101 |
| 2.2 | TP101, TP103, C115 pad 1 (AVCC) | All within 10 mV of the supply at J101 | ≈ 0.5 V low: Q101 on its body diode (D101 reversed, R101 open, gate bridged to source). TP103 at 0 V: R105 missing, **stop** ("Powering rule") |
| 2.3 | R101 pad 1 → TP101 (Q101's VGS) | −9 to −12 V (D101, near its knee, may hold it a few volts short of 12 V) | ≈ −0.6 V = D101 reversed; ≈ 0 V = R101 open |
| 2.4 | A1.25 (`BATT_SENSE`, or C17 pad 1) | 1.071–1.111 V: TP101 / 11, ±1.8 % | ≈ 10.9 V = R102/R103 swapped (never fit the Daisy like this); ≈ 12 V = R103 open; ≈ 3 V = a 30k fitted for R102; 0 V = R102 open or C17 shorted |
| 2.5 | TP106 (`+5V_RAW`), J107.1, C5 `+` (`+5V`) | < 50 mV | Higher: something on the battery side feeds the 5 V nets (U101's SDZ, MUTE or FAULTZ pin back through R107–R112). **Stop** |
| 2.6 | TP104 (SDZ), C124 pad 1 (MUTE), TP109 (FAULTZ) | < 50 mV each (D102 and D103 stand off 12 V here) | Volts on SDZ or MUTE: D102 or D103 fitted backwards (1.55) |
| 2.7 | C110 pad 1 (GVDD); C108 pad 2 and C109 pad 2 (U101's inputs) | Record. SLOS708G doesn't say whether GVDD or the inputs' 3 V bias run in shutdown | |
| 2.8 | J102.1 and J102.2 → GND, DMM and scope | ≈ 0 V, no switching (outputs Hi-Z in shutdown) | Switching: U101 not in shutdown (2.6) |
| 2.9 | J106.1 → J106.2 | = TP101, pin 1 positive | J106 joints |
| 2.10 | Battery range: set 9.0 V, then 12.6 V | A1.25: 0.80–0.84 V, then 1.12–1.17 V (VBAT / 11). TP101 within 10 mV of the supply each time; the divider draws 0.08 mA, then 0.11 mA | TP101 low at 9 V: Q101 not fully on (2.3) |
| 2.11 | Thermal | Nothing warm to the touch after 2 min | |
| 2.12 | Switch off at SW101 | Current drops to ≈ 0; TP101 decays over ≈ 2 min (τ ≈ 22 s) | Current stays: SW101 wiring |
| 2.13 | **Reverse polarity at J101:** supply off, swap its two wires (− to the centre pin), limit 20 mA, 12.0 V, switch on | ≈ 0 mA; TP101 ≈ 0 V. Restore the polarity and repeat 2.2 and 2.4 | Current flows: Q101 shorted or fitted wrong (1.25) |
| 2.14 | **Reverse 5 V on J107 (Q102):** keep 12.0 V on J101, correct polarity. The second, floating supply at 5.0 V, limit 10 mA: + to J107.2, − to J107.1 | ≈ 0 mA from the second supply; TP106 stays within 50 mV of 0 V; TP104 and C124 pad 1 stay at 0 V. Remove it | Current, or TP106 negative: Q102 shorted or the wrong part. Remove the supply at once |

What 2.14 risks: if Q102 is wrong (1.32 should have caught it), −5 V reaches `+5V_RAW`, and U103 (VDD rated −0.3 V minimum)
clamps it through its own diode at the 10 mA limit. With 12 V on J101, even this supply the other way round (+5 V on
J107.1) leaves U101's MUTE and SDZ inside PVCC + 0.3 V. Don't use the DFR0571 for this test: its input and output GND are
one node, so with J106 wired, J107's wires swapped short its output to GND (3B.1).

## Stage 3 — The DFR0571 and the 5 V rails, Daisy removed

**3A. The DFR0571 on its own (off the board)**

U1 and U2 are rated 5.5 V, U103 6 V, and the 5 V contract (`power-board/README.md`) is 4.75–5.25 V. The module has no
short-circuit or reverse protection (DESIGN.md "5 V supply and distribution" has its datasheet figures).

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 3A.1 | 12.0 V into its VIN+/GND, limit 50 mA, output open | Output 4.90–5.10 V; input current ≈ 0.5 mA. Record both | Above 5.25 V: don't connect it |
| 3A.2 | Repeat at 9.0 V and 12.6 V in, then with the 47 Ω 1 W resistor on the output (≈ 0.1 A) | 4.90–5.10 V each time | Sags at 9 V: record it (DFRobot: raise the minimum input at high load) |
| 3A.3 | Make its input cable: cut the ASXHSXH22K305 lead in half, screw the cut ends into the module's VIN+ and GND, and push the contacts into the XHP-2 housing, VIN+ in position 1 (J106's triangle, BAT+). Mark the VIN+ wire. Fit and label the two output wires: 5V → J107.1, GND → J107.2. Check the cable unpowered, then the outputs with the module powered as in 3A.1 | Housing position 1 → module VIN+ < 1 Ω, position 2 → module GND < 1 Ω; the 5V wire reads +5 V against either GND wire | Position 1 on GND: the cable is crimped backwards. Fix it before it goes near J106 (the module has no input reverse protection) |

**3B. On the board, U101 held in shutdown**

Left out: the Daisy, the display (J105, J3), any load on J102, shunts on JP101–JP104. Put a shunt on JP105 (borrow one from
JP101–JP104): it holds U103's MR low, so SDZ stays low and U101 stays in shutdown while the 5 V rails are checked.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 3B.1 | Supply off. Plug the module's input cable into J106 and wire its output to J107. Then TP101 → GND; J107.1 → GND; TP101 → J107.1 | Not below 1 kΩ (TP101 climbs as in 1.29, with the module's input in parallel); not a short (> 100 Ω); not a short | TP101 → GND ≈ 0: the input cable's two wires swapped (3A.3), a dead short of `VBAT_PROTECTED` at power-up through J107's ground wire. J107.1 → GND ≈ 0: J107's wires swapped (the module's output shorted to GND). TP101 → J107.1 ≈ 0: both swapped |
| 3B.2 | Supply 12.0 V on J101, limit **50 mA**; switch on | ≈ 2–5 mA (the 5 V side's ≈ 2.1 mA is ≈ 1 mA at 12 V through the buck, plus the buck's own 0.5 mA). Stop if it hits the limit | At the limit: a short on `+5V_RAW` or `+5V` (1.1, 1.35), the DFR0571's wiring (3B.1), C5 reversed, U1/U2 rotated |
| 3B.3 | TP106 (`+5V_RAW`) | 4.90–5.10 V, as 3A.1 | |
| 3B.4 | J107.1 − TP106 (Q102's drop) | < 10 mV | 0.4–0.7 V: Q102's channel is off (gate not at GND, rotated), and `+5V_RAW` sits near U103's 4.65 V threshold |
| 3B.5 | C105 pad 1 (`+5V`); J105.1 (`+5V_DISPLAY`) | Within 5 mV of TP106 (FB101, FB102) | 0 V: a bead open (1.34) |
| 3B.6 | `+5V` (C5 `+`) | Within 5 mV of C105 pad 1 (one net) | Lower: the `+5V` trace between the sheets (1.2) |
| 3B.6a | `HP_5V` (C21 pad 1 or C12 pad 1) against C5 `+` | Within 2 mV of C5 `+` (U2 shut down: under 1 µA through R29). Record it | 0 V: R29 open (1.2a). More than a few mV: U2 drawing current with `HP_SD` low (a bridge, rotated, R34 missing) |
| 3B.7 | `VREF` (C7); A1.22 (`5V_SENSE`) | Half of C5 `+` within ±1 %: 2.42–2.58 V for 4.90–5.10 V; the same | R6/R7, R18/R19 values |
| 3B.8 | U1.1, A1.16 (through R20), U1.3 | ≈ `VREF` | U1 rotated or not powered (U1.5) |
| 3B.9 | U2 shut down: A1.27 (`HP_SD`) and CPVSS (C14 pad 1) | ≈ 0 V both (R34 holds SD low, charge pump off) | CPVSS negative: SD isn't low (R34 missing, 1.8b) |
| 3B.10 | J4 tip and ring (DC) | Within ±10 mV of 0 V (U2 off) | |
| 3B.11 | C108 pad 1 (`LINE_OUT`), C109 pad 1 (`LINE_REF`) | ≈ 0 V (R12, R21) | |
| 3B.12 | A1.39; J3.1 and A1.40 | `+5V`; GND | |
| 3B.13 | R107 pad 2 (`SPK_MUTE`), C124 pad 1 (MUTE) | Within 50 mV of TP106: Q2 off (R17 holds A1.28 low), U101 muted. Both below PVCC + 0.3 V | Both < 0.1 V: Q2 on (Q2 shorted, A1.28 not low); C124 pad 1 ≈ 0 with R107 pad 2 ≈ 0.9 V (R107/R108): MUTE bridged to GND (1.48) |
| 3B.14 | JP105 pin 1; R110 pad 1 (`AMP_PG`); TP104 (SDZ) | 0 V; < 0.4 V (U103's RESET held low by MR); < 0.4 V: U101 in shutdown | |
| 3B.15 | TP109 (FAULTZ) | ≈ 0.64 × TP106 (R114 / (R112 + R114)): 3.15–3.28 V for 4.90–5.10 V (no fault); record it | ≈ TP106: R114 open (1.39). ≈ 0: R112 open, or U101 reporting a fault |
| 3B.16 | TP101, TP103; A1.25 | = the supply; 1.071–1.111 V, as 2.4 | |
| 3B.17 | **5 V on a signal terminal:** a second supply at 5.0 V, limit 50 mA, on J3.3 | A1.15 ≈ 4.55 V (R9/R24). Remove it | More: R24 open |
| 3B.18 | Thermal | Nothing warm to the touch after 2 min, U2 included | |

**3C. U101 enabled, muted**

Supply off. Park the JP105 shunt on one pin of its header (JP105 open). Limit **70 mA**: 3B's ≤ 5 mA plus U101's quiescent
current, 20 mA typical and 35 mA at most at 12 V (SLOS708G, no load or filter), plus margin.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 3C.1 | **Power-on sequence:** scope TP103 (PVCC), TP106 (`+5V_RAW`), TP104 (SDZ) and C124 pad 1 (MUTE). Supply at 12.0 V, trigger on TP106, switch on at SW101 | PVCC rises first, then `+5V_RAW` once the DFR0571 starts. SDZ stays low until ≈ 20 ms after `+5V_RAW` passes 4.65 V (U103, CT open), then rises with τ ≈ 11 ms (C125), crossing 2 V ≈ 6.5 ms later. MUTE follows `+5V_RAW` with τ ≈ 12 ms (R107 + R108 into C124). SDZ and MUTE stay below PVCC + 0.3 V throughout and change slower than 10 V/ms (SLOS708G's limit; here ≤ 0.4 V/ms) | SDZ rising with `+5V_RAW`: U103's delay missing (wrong part, CT not open). SDZ or MUTE above PVCC + 0.3 V at any time: **stop** and record it |
| 3C.2 | Supply current at 12.0 V | 3B.2's value, less ≈ 0.5 mA (JP105 open), plus U101's 20 mA typical (35 mA max; muted it may draw less). Record it; < 50 mA | More: U101 switching despite MUTE (3C.7), a fault |
| 3C.3 | TP104 (SDZ); R110 pad 1 (`AMP_PG`) | 4.0–4.56 V: R111 / (R109 + R110 + R111) × `+5V_RAW` = 4.37–4.55 V for 4.90–5.10 V, less up to 0.5 V from U101's SDZ input current (≤ 50 µA, SLOS708G). `AMP_PG` ≈ 0.1 V above SDZ | ≈ 0: U103 holding RESET (TP106 below 4.65 V, JP105 still shunted, U103 pins 1–2 or 2–3 bridged) |
| 3C.4 | TP109 (FAULTZ) | ≈ 0.64 × TP106, ≈ 3.2 V (no fault), as 3B.15 | ≈ TP106: R114 open. < 0.8 V = a latched fault ("Fault-finding hints"), or R112 open if JP105 doesn't clear it. Find it, then clear with JP105 (3C.8) |
| 3C.5 | C110 pad 1 (GVDD) | 6.4–7.4 V (SLOS708G) | ≈ 0: U101 not running (SDZ, AVCC at C115) |
| 3C.6 | C108 pad 2, C109 pad 2 (U101's inputs) | ≈ 3 V each, within ≈ 0.1 V of each other; record both | One at 0 V: its cap shorted, or the pin bridged (1.44, 1.45) |
| 3C.7 | J102.1, J102.2 (scope and DMM) | No switching (MUTE high: outputs Hi-Z). Record the DC | Switching: MUTE not reaching U101 pin 12 (R108, C124 joints) |
| 3C.8 | **JP105 manual reset:** short JP105 for ≈ 1 s with the shunt, watching TP104 and TP109 | SDZ falls below 0.8 V within ≈ 4 ms (C125 through R110) and rises again ≈ 26 ms after the shunt comes off. TP109 stays high (≈ 3.2 V) | SDZ doesn't move: MR not reaching U103 pin 3 |
| 3C.9 | **Power-off sequence:** same probes, trigger on TP103 falling, switch off at SW101 | `+5V_RAW` holds while PVCC falls, then falls with it once the DFR0571 drops out. SDZ goes low within ≈ 4 ms of `+5V_RAW` passing 4.65 V. MUTE (held up by C124) and SDZ (by C125) at most ≈ 0.35 V above PVCC as it falls: D103 and D102 clamp them. Record the times and the largest MUTE − PVCC and SDZ − PVCC | More than ≈ 0.4 V above PVCC: D102 or D103 missing or open (1.55). Record by how much and for how long (DESIGN.md "Power sequence") |
| 3C.10 | Thermal after 5 min | U101 at most warm (muted); Q101, Q102 and the DFR0571 cool | |

**3D. 5 V filter options**

Power off for every jumper change. Record each configuration tested in the log. The display's share of these tests is 6.14.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 3D.1 | Shunt JP101 and JP103 (beads bypassed); repeat 3B.5 and 3C.2 | The same readings: at a few mA the beads drop well under 1 mV | |
| 3D.2 | C104/C106 are DNP. If they're fitted for the bulk experiment (`+` toward JP102/JP104): shunt JP102/JP104 and repeat 3C.1 | `+5V_RAW` still rises monotonically and the DFR0571 starts first time; SDZ's delay unchanged. Record the rise time with and without | DFR0571 hiccups into the extra 200 µF: record it |

Return the jumpers to the defaults (or to what rev 1's bring-up chose) before going on.

## Stage 4 — Analog paths and speaker amp, Daisy removed

With the module out, its sockets (A1) reach the Daisy-side nets. Supply 12.0 V on J101 with the DFR0571, limit **70 mA**
for 4A, 4B and 4D (4C sets its own). R17 keeps the speaker muted throughout, except in 4C.

**4A. Guitar input buffer (J1 → AUDIO_IN_1)**

Inject 1 kHz, 1 Vpp sine into J1 (tip/sleeve). Scope on `A1.16` (AUDIO_IN_1) or U1.1.

| # | Check | Expect |
|---|---|---|
| 4A.1 | Output level | U1.1: 1 kHz sine riding on ≈ 2.5 V DC, amplitude ≈ input (unity gain). A1.16: the same through R20 (no Daisy load) |
| 4A.2 | Input load: add 1 MΩ in series with the generator | Output drops to ≈ half (≈ 1 MΩ input impedance, R1) |
| 4A.3 | Unplug J1 | Output goes quiet (tip shorted to GND) |
| 4A.4 | Raise amplitude until clipping | Clips symmetrically near the rails: ≈ 4.8 Vpp at U1.1 and A1.16 (no Daisy load); record the input level |
| 4A.5 | Sweep 20 Hz – 20 kHz | Flat within about ±1 dB |

**4B. Headphone filter + headphone amp (AUDIO_OUT_1 → J4)**

Connect the I2C master: SCL to A1.12, SDA to A1.13, GND to A1.20, its 3.3 V to A1.38 (the pull-ups). Pull A1.27 (`HP_SD`)
to 3.3 V through 1 kΩ. Load J4 tip and ring with 32 Ω each (or headphones at low level).

| # | Check | Expect |
|---|---|---|
| 4B.1 | CPVSS (C14 pad 1) and the supply current | ≈ −4.6 to −5.0 V, roughly `HP_5V` inverted; the 12 V supply current rises by ≈ 1 mA. ≈ 0 V: U2 not starting (A1.27, C13, pins 15–18) |
| 4B.2 | I2C: scan the bus, then read register 4 | U2 answers at 0x60; register 4 bits 3:0 read 0010. No answer: SDA/SCL swapped or open (1.8b), A1.38 not at 3.3 V, U2's joints |
| 4B.3 | Write register 1 = 0xC0 and register 2 = 0x35. Inject 1 kHz, 1 Vpp sine into `A1.18` (AUDIO_OUT_1), ground at `A1.20`, DC offset 0 V | C9 (`HP_SOURCE`): ≈ 0.75–0.8 Vpp (R10 into U2's inputs, −2 to −2.7 dB). J4 tip and ring: ≈ 0.75–0.8 Vpp centred on 0 V, inverted relative to `HP_SOURCE`, both channels equal within ≈ 0.5 dB. DC at J4 within ±1 mV (0.4 mV maximum offset) |
| 4B.4 | Register 2 = 0x2E, then 0xF5 | Output ≈ 3.2 dB lower (−3.1 dB step), then silent (both mute bits set) |
| 4B.5 | Register 2 = 0x35; sweep 20 Hz – 20 kHz into 32 Ω | Flat in the audio band; low-end corner ≈ 17 Hz or lower (C10/C22 and C11/C23 with U2's ≥ 37 kΩ inputs); falls off above ≈ 50 kHz (R10/C9) |
| 4B.6 | Listening test with headphones | Clean tone, no hum or hiss above the expected level, no oscillation (scope the outputs and CPVSS for HF ringing) |
| 4B.7 | Release A1.27 | J4 goes silent within a few ms and CPVSS returns to 0 V. Pull A1.27 up again: register 1 reads 0x00 (the shutdown cleared it) and J4 stays silent until it is written again |
| 4B.8 | Power-on/off with headphones in and U2 enabled | Note any pop level (Stage 8 is the full test) |

**4C. Speaker send and speaker amp (AUDIO_OUT_2 → U101 → J102)**

Power off and connect the 4 Ω dummy load to J102. Inject 1 kHz into `A1.19` (AUDIO_OUT_2), ground at `A1.20`, generator DC
offset 0 V. Measure J102 with two scope probes, their grounds on TP105 or TP107 and **never on J102**, CH1 on J102.2 (SPK+),
CH2 on J102.1 (SPK−), and read CH1 − CH2; or read a true-RMS DMM across the load. Both terminals sit at ≈ 6 V while U101
plays, so grounding either one shorts an output and latches U101 off. To unmute without the Daisy, pull A1.28 (`SPK_EN`) to
3.3 V through 1 kΩ from the second supply (limit 10 mA); leave it open to mute. Limit **200 mA** unless an item says
otherwise.

| # | Measure / do | Expect | A wrong reading means |
|---|---|---|---|
| 4C.1 | Muted (A1.28 open), 0.1 Vrms (0.28 Vpp) in. C108 pad 1 (`LINE_OUT`), C109 pad 1 (`LINE_REF`), J102 | ≈ 0.097 Vrms, in phase (R11 into R12 ∥ U101's 60 kΩ ±20 %: −0.2 dB); ≈ 0; J102 silent, no switching | `LINE_OUT` low: R11, C16 or R12 (1.16, 1.17) |
| 4C.2 | Unmute: A1.28 to 3.3 V through 1 kΩ | R107 pad 2 and C124 pad 1 < 0.1 V. J102 ≈ 0.97 Vrms differential (0.87–1.09 Vrms: 20 dB ± 1 dB, SLOS708G with R104 = 5.6 kΩ), SPK+ in phase with A1.19. Gain = V(J102) / V(C108 pad 1 − C109 pad 1) = 19–21 dB. Record the supply current | No output with MUTE low: SDZ (3C.3), FAULTZ (3C.4), L101/L102. ≈ 26 or 32 dB: R104 wrong. MUTE not low: Q2, the 1 kΩ pull-up |
| 4C.3 | Generator off, still unmuted | J102.1 and J102.2 each ≈ 6.0 V DC (PVCC / 2) with ≈ 0.3 Vpp of 400 kHz (376–424 kHz) on each, common to both; the difference within ±15 mV DC (SLOS708G). Record the idle supply current (SLOS708G's 20 mA is without the output filter) | 500 kHz or 1.2 MHz: an AM pin not at GND. One leg off 6 V: a PBTL tie or an output pin open |
| 4C.4 | Sweep 20 Hz – 20 kHz at 0.1 Vrms | ≈ −0.3 dB at 20 Hz against 1 kHz (C108/C109 into 60 kΩ, corner 5.6 Hz; −0.5 dB if U101's inputs are at their −20 % 48 kΩ, corner 7.1 Hz). −0.4 dB at 10 kHz and ≈ −1.4 dB at 20 kHz (R11/C16 −0.7 dB; L101/C121 and L102/C122 into 4 Ω, 61 kHz, −0.8 dB) | Peaking near the top: a filter cap missing or the wrong value |
| 4C.5 | Mute timing: scope A1.28, C124 pad 1 and J102; connect and remove the 3.3 V | Unmute ≈ 4 ms after A1.28 rises (C124 through R108, to 0.8 V); mute ≈ 6 ms after it falls (C124 through R107 + R108, to 2 V). Record any click | |
| 4C.6 | Maximum output: limit **2.5 A**, a few seconds at a time. Raise the input until the output clips | Clips at ≈ 11 V peak (≈ 7.9 Vrms, ≈ 15.5 W into 4 Ω at 12.0 V; ≈ 17 W on a full 12.6 V pack) at ≈ 0.81 Vrms in, drawing ≈ 1.5 A from the supply. Full scale (1 Vrms in) clips: the firmware caps the speaker ≈ 5 dB below it. Record the input, output and current | Clipping much earlier: TP103 sagging (R105, Q101, F101, the supply lead), R104 |
| 4C.7 | **Speaker short:** back to 0.1 Vrms in, limit 500 mA. Short J102.1 to J102.2 with a wire for ≈ 1 s | TP109 drops below 0.8 V and J102 goes silent (outputs Hi-Z, latched). Remove the short: still silent, TP109 still low. Wait 2 s, then short JP105 for ≈ 1 s: the tone returns ≈ 30 ms after release and TP109 goes high (≈ 3.2 V). Repeat, clearing it by switching off at SW101 for 5 s instead | No latch: U101's protection isn't reporting (TP109, R112, R114). The tone returns without JP105: SDZ toggling (TP104) |
| 4C.8 | Insert and remove a plug in J4 | J102 unchanged (no hardware link; muting the speaker is the firmware's job) | |
| 4C.9 | Thermal after 5 min at 0.1 Vrms in | U101 at most warm; L101/L102 cool | |
| 4C.10 | No input, speaker unmuted, then headphones on J4: listen, and take an FFT of J4 and across J102 | Hiss only; no steady tone | A tone that drifts as the board warms = U101 beating with U2's charge pump: power off, cut one of JP106–JP108 (DESIGN.md, "Speaker amp"), repeat, and record the setting |

4C.7 relies on U101's over-current protection (SLOS708G Table 4: latched, outputs Hi-Z); the low level and the 500 mA limit
keep the energy small.

Power off before disconnecting the load.

**4D. AUX input (J2 → AUDIO_IN_2)**

With the Daisy out, only R5 loads the summing node, so these levels are slightly higher than in use. 6.17 checks the real
level with the Daisy fitted.

Inject 1 kHz, 2 Vpp sine into J2 with a TRS cable, same signal on tip and ring. Scope on `A1.17` (AUDIO_IN_2) or C3.

| # | Check | Expect |
|---|---|---|
| 4D.1 | Tip and ring driven together | ≈ 0.17 Vpp centred on 0 V (R3‖R4 into R5, −21.3 dB) |
| 4D.2 | Tip only, ring grounded (TS plug) | ≈ 0.09 Vpp |
| 4D.3 | Unplug J2 | Output goes quiet (R5 holds the summing node at GND) |
| 4D.4 | Sweep 20 Hz – 20 kHz (tip and ring driven) | Flat (C3's pole is ≈ 370 kHz with no Daisy load, ≈ 400 kHz with the Daisy fitted) |

Remove the injected signal and the A1.28 pull-up before going on.

## Stage 5 — Power-up with Daisy fitted

**5.0 Before fitting it:** power the Daisy on its own from USB, nothing else connected, and measure VIN (pin 39) to GND
(pin 40). Expect < 0.5 V (Seed3 datasheet, Figure 1.0: USB doesn't drive VIN). Record it. If it reads near 5 V, USB alone
would lift `+5V` and, through FB101, `+5V_RAW`, putting U101's SDZ and MUTE above PVCC + 0.3 V: then plug in USB on this
board only while the battery is on, and skip the battery-off parts of 6.15 and 6.18.

1. **Power off.** Insert the Daisy, checking orientation against the silkscreen and that no pins are offset by one
   position.
2. Supply 12.0 V on J101 with the DFR0571, limit **300 mA**: 3C's < 50 mA plus the Daisy's 100–200 mA at 5 V (≈ 50–100 mA
   at 12 V through the buck), with room for start-up. Keep USB **unplugged** for this stage.

| # | Check | Expect |
|---|---|---|
| 5.1 | Supply current | 3C.2 plus ≈ 50–100 mA (the Daisy, depending on firmware); record value |
| 5.2 | TP106; `+5V` (C5 `+`) | 4.90–5.10 V; ≥ 4.85 V, within 30 mV of TP106 (FB101 at ≈ 0.2 A) |
| 5.3 | `3V3_D` (Daisy pin 38, probed on top of the module) | 3.3 V ± 5 % (from the Daisy regulator) |
| 5.4 | `VREF`, U1 biases, A1.25 | Same as Stage 3 |
| 5.5 | `HP_DETECT` (TP1) with a plug in J4 | ≈ 0 V. With J4 empty it floats until the firmware enables the internal pull-up: 6.7 checks that case |
| 5.6 | Hold the Daisy in reset (RESET button held) | J4 quiet (headphones on), A1.27 (`HP_SD`, on R34) ≈ 0 V and CPVSS (C14 pad 1) ≈ 0 V (U2 shut down), Q2 pin 1 (`SPK_EN`) 0 V, R107 pad 2 and C124 pad 1 ≈ TP106 (muted), J102 not switching |
| 5.7 | Daisy LED / existing firmware | Boots normally |
| 5.8 | Thermal after 5 min | Nothing hot; Q102, U2 and U101 at most warm |
| 5.9 | **Back-power, DFR0571 disconnected:** switch off, unplug the DFR0571's input cable from J106 and take its wires out of J107 (nothing on J107), limit 20 mA, 12.6 V, switch on | Current as 2.1 (< 1 mA); A1.25 ≈ 1.15 V (VBAT / 11) into the unpowered Daisy; TP106 and `+5V` < 50 mV; record `3V3_D`, which should stay near 0 V. More current, or `3V3_D` rising, means pin 25 back-powers the Daisy. Switch off, rewire the DFR0571 and repeat 3B.1 |

Then plug in USB with the board powered from J101 and confirm current/voltages don't jump unexpectedly. The Seed3 datasheet
allows both sources together (Figure 1.0).

## Stage 6 — Functional tests with test firmware

Flash a small bring-up program (libDaisy or Arduino/DaisyDuino) over USB that:

- passes audio input 1 to outputs 1 and 2, mixes input 2 (AUX) into both, and logs peak levels,
- lets `SPK_EN` be toggled and the speaker level be set from USB serial, capped ≈ 5 dB below full scale,
- prints `HP_DETECT`, the `BATT_SENSE` and `5V_SENSE` ADC readings, VBAT = 11 × V(pin 25) and the speaker-fault input
  (`AMP_FAULTZ`, pin 32: low = fault) over USB serial,
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
| 6.9 | `SPK_EN` toggled high/low | Q2 pin 1 follows. R107 pad 2 < 0.1 V while high, ≈ TP106 while low; C124 pad 1 follows within ≈ 6 ms. Record the high-state reading (Q2's gate drive from 3.3 V) |
| 6.9a | Speaker fault seen by the firmware: dummy load, `SPK_EN` high, low level. Short TP109 to TP107 (GND) for ≈ 1 s, then repeat 4C.7's speaker short (firmware playing a low-level tone, limit 500 mA) and clear it with JP105 | No fault: pin 32 reads high (TP109 ≈ 3.2 V). TP109 shorted: the firmware reads pin 32 low and shows "speaker fault"; released: high again (harmless: R112 limits it to 0.5 mA). Speaker short: TP109 < 0.8 V, "speaker fault" shown until JP105 clears the latch, then high again. Record what the firmware shows |
| 6.10 | Settings survive a hard power cut: change a setting on the display, wait for the debounce, pull the J101 plug, restore it | The setting is kept |
| 6.11 | Wiring check before connecting the display and the speaker | J3 GND/TX/RX as labelled; J105 (DISP/GND) to the display's supply; J106/J107 as 3A.3; J102: speaker + to pin 2 (SPK+), − to pin 1, neither wire to GND or the chassis; the panel switch on SW101 |
| 6.12 | `BATT_SENSE`: J101 at 9.0, 11.1 and 12.6 V, measuring TP101 each time | A1.25 and the ADC read TP101 / 11 (0.818, 1.009, 1.145 V) within ±1.8 %; the printed VBAT within ≈ 3 % of TP101 |
| 6.13 | UART on J3 with a 3.3 V USB-serial adapter (adapter TX → J3.3, RX → J3.2, GND → J3.1) | Heartbeat received; echo works. Unplug the adapter: the firmware reports no display (R24 holds RX low), and recovers when it is plugged back in. **Before connecting the real display**, confirm its TX idles at ≤ 3.3 V |
| 6.14 | Display on J3, powered from J105 (limit 2.5 A) | Shows data from the Daisy; record its supply current. With a guitar plugged into J1 and its volume up, switch the display's Wi-Fi on and off: no buzz that follows the Wi-Fi. Scope TP106, J105.1 and `+5V` (C5 `+`) with Wi-Fi and the backlight active: the display's current pulses show on J105.1 and TP106, and much less on `+5V`. Record the ripple on each and the noise floor at J4 and across J102 with the beads in (JP101/JP103 open), then bypassed, and, if C104/C106 are fitted, with JP102/JP104 shunted. Power off for each change; record each configuration |
| 6.15 | USB alone (only if 5.0 read < 0.5 V): battery off at SW101, display unplugged, Daisy on USB, 1 kHz into J1, `SPK_EN` driven high | `+5V` (C5 `+`), TP106 and TP104 ≈ 0 V; `5V_SENSE` prints ≈ 0 V. A1.18 (`AUDIO_OUT_1`, on top of the module), C9 and C108 pad 1 carry no signal: the firmware keeps the outputs silent and `HP_SD` low (DESIGN.md "Running from USB alone"). If `+5V` or TP106 rises above 0.5 V, unplug USB at once. Then switch on at SW101: `5V_SENSE` prints ≈ 2.5 V and the tone returns on J4 without a click. Record all of it |
| 6.16 | Output DC with the codec running: firmware outputs digital silence. Measure DC at A1.18 and A1.19 (on top of the module) and at C108 pad 1 (`LINE_OUT`). Then, speaker unmuted, hold RESET and release, watching C108 pad 1 and J102 | All three within ±20 mV of 0 V, which confirms the Seed3 outputs are AC-coupled. More than a few tens of mV: see DESIGN.md "Speaker send" (a 10 µF cap in series). Record any step on `LINE_OUT` and any thump on J102 at reset and release |
| 6.17 | AUX level with the Daisy fitted: 1 kHz, 2 Vpp into J2, same signal on tip and ring, then tip only with ring grounded. Scope A1.17 (on top of the module) and read the firmware's input-2 peak | Tip and ring: 0.155–0.160 Vpp (−22.2 to −21.9 dB, the Daisy's input at 4–6 kΩ). Tip only: ≈ 0.08 Vpp. Record both. ≈ 0.17 Vpp means the module adds almost no load; much lower means its input is well below 4 kΩ (see DESIGN.md "AUX input") |
| 6.18 | `+5V` transitions on USB (only if 5.0 read < 0.5 V): Daisy on USB, battery on, full-scale 1 kHz to J4 (32 Ω load). Scope `HP_5V` (C21 pad 1), CPVSS (C14 pad 1), A1.27 (`HP_SD`) and U2's LEFTINM (C10 pad 2). Switch off at SW101, then on | Power off: `HP_SD` falls when `5V_SENSE` drops below 2.2 V, and LEFTINM stays within −2.5…+3.6 V (U2's absolute rating, powered or not). Power on: `HP_SD` rises only after `5V_SENSE` is good, and audio returns ≥ 5 ms later with no click on J4. Record the times |
| 6.19 | Hot passive pickups: the hottest passive guitar available into J1, played as hard as possible | Record the logged peak. It should stay below full scale (≈ 3.9 Vpp at J1). Active pickups are out of scope |
| 6.20 | Speaker level cap: firmware full-scale 1 kHz to the speaker output, dummy load, at 12.0 V and then 9.0 V on J101 | ≈ 5.5 Vrms (≈ 7.5 W: full scale ≈ 9.7 Vrms, less 5 dB), no clipping at either voltage (at 9.0 V U101 clips at ≈ 8.4 V peak; the capped output peaks at ≈ 7.7 V). Record both |
| 6.21 | Speaker on J102 (+ tab to pin 2, SPK+) | Guitar through the speaker at a moderate level: clean, no hum or whine at idle, no rattle. Record the speaker used |
| 6.22 | Low battery: speaker muted (headphones in), display unplugged. Lower J101 from 12.0 V to 6.0 V over about a minute, then back | Record VBAT (TP101) where TP106 falls below 4.9 V (the DFR0571 drops out; DFRobot lists 8 V as its minimum), where SDZ goes low (TP106 < 4.65 V, U103), where the firmware goes silent (`5V_SENSE` < 2.2 V), and the printed VBAT. Back at 12 V: U101 restarts (SDZ ≈ 26 ms after TP106 passes 4.65 V) and the Daisy recovers or resets cleanly. The board has no battery cutoff of its own |

## Stage 7 — Soak and robustness

| # | Check | Expect |
|---|---|---|
| 7.1 | Run passthrough with audio for 30 min from the Talentcell battery (record its voltage at the start and end) | No dropouts, resets, or drift in `VREF`, TP106 or the printed VBAT |
| 7.2 | Plug/unplug J1, J4, J2 repeatedly while running | No resets, no lasting noise, jacks stay mechanically solid; `HP_DETECT` reports every J4 change |
| 7.3 | Wiggle the J3, J105, J106, J107 and J102 wires, the switch wires and the J101 plug while running | No crackle, dropouts or resets |
| 7.4 | Full-level 1 kHz into 32 Ω on J4 for 10 min | U2 at most warm; no shutdown or distortion change |
| 7.5 | Light flex/tap test on the board and Daisy, guitar plugged in, listening on J4 and the speaker | No crackle or resets (would point to a cracked joint or loose socket pin). Record any knock heard: every capacitor on the audio path is C0G (C2, C10/C11, C22/C23, C108/C109) and shouldn't make one |
| 7.6 | Board off, a phone or laptop at full volume into J2. Scope A1.17 (on top of the module) | At most ≈ 0.46 Vpp (±0.23 V) for a 2 Vrms source: the unpowered codec's input stays within its ±0.3 V rating. Record the peak |
| 7.7 | Speaker for 30 min: music at the capped level into the speaker, or 1 kHz at ≈ 2 W into the dummy load | No thermal shutdown (TP109 stays at ≈ 3.2 V, and the firmware shows no speaker fault); record U101's case temperature; L101/L102 warm at most; Q101, F101 and the DFR0571 cool |
| 7.8 | With the battery: switch on at SW101 20 times, and plug the battery into J101 (switch on) 10 times | F101 survives every inrush (record the fuse value); U101 starts each time (TP109 ≈ 3.2 V, no speaker fault shown); record any spark at the switch or the jack |

## Stage 8 — Pops, hiss and mute

Needs the product firmware (volume ramps, headphone detect, settings saved on change, `SPK_EN` delay) and an audio interface
on the laptop. Record J4 (into a 32 Ω load or EarPods) into the interface, and the speaker with a microphone or as J102's
differential voltage on the scope. **Never connect the interface to J102:** both terminals sit at ≈ 6 V. Pass means no
audible click and no spike more than ~10 dB above the recording's noise floor.

| # | Check | Expect |
|---|---|---|
| 8.1 | Power-on pop: record J4 and the speaker, then switch on at SW101 | No click on either output. U2 stays shut down (R34) until the firmware enables it, so J4 should stay silent through boot |
| 8.2 | Speaker power-on: scope TP106, TP104 (SDZ), Q2 pin 1 (`SPK_EN`), C124 pad 1 (MUTE) and J102 (differential) at power-on, into the speaker | SDZ rises ≈ 26 ms after TP106 passes 4.65 V while MUTE is still high. C108/C109 charge to U101's 3 V bias (τ ≈ 28 ms, 60 kΩ × 470 nF) while muted. `SPK_EN` goes high after audio starts and MUTE falls ≈ 4 ms later. Record any step on J102 at unmute, and listen for a thump |
| 8.3 | Power-off pop: record J4 and the speaker, switch off at SW101 | Note the result. The speaker stays unmuted until `+5V_RAW` falls below 4.65 V (U103) or the firmware sees `5V_SENSE` low, after PVCC has already sagged (3C.9 has the timing) |
| 8.4 | Hard power cut: record J4 and the speaker, pull the J101 plug while playing | Note the result. A small click is acceptable here, a loud bang is not |
| 8.5 | Headphone plug-in and removal while playing a 1 kHz tone | `SPK_EN` goes low while headphones are in and high again when they come out. No click on J4 or the speaker |
| 8.6 | Watchdog mute: debug build that stops the audio callback on a USB serial command | J4 and the speaker go silent (codec DAC power-down, and A1.27 falls: U2 shuts down), and C124 pad 1 (MUTE) is above 2 V within ~10–20 ms (IWDG ≈ 10 ms, then ≈ 6 ms for C124). The Daisy resets and boots back into silence. Record any click on J4 and the speaker |
| 8.7 | Hiss with EarPods: J1 unplugged, firmware volume at a quiet listening level, then at max | No hiss audible at a normal listening level. Record U2's volume word at each setting and whether hiss is audible at max |
| 8.8 | Maximum headphone level: full-scale 1 kHz into a 32 Ω load on J4, volume word 0x35 | ≈ 0.75 Vrms per channel, no clipping. Then into 16 Ω with both channels driven, raise the word step by step to 0x3F (+4.0 dB) and record the word where the sine starts to clip; set the firmware's cap 3 dB below it (DESIGN.md "Level and volume"). Record `HP_5V` (C21 pad 1) against C5 `+` at that level. Listening check with the intended headphones: loud enough with margin |
| 8.9 | Speaker hiss: J1 unplugged, speaker level at the cap, ear near the cone | Record whether hiss or whine is audible, and the noise across J102 on the scope (SLOS708G: 65 µV A-weighted at 20 dB) |

## Fault-finding hints

| Symptom | Look at first |
|---|---|
| Supply hits the current limit in Stage 2 | 1.29 short; C111/C112 reversed; U101's PVCC pins bridged to its exposed pad |
| `VBAT_PROTECTED` ≈ 0.5 V below the supply | Q101 on its body diode: D101 reversed, R101 open, Q101's legs (2.3) |
| Supply hits the limit in Stage 3B | `+5V_RAW` or `+5V` short (1.1, 1.35); the DFR0571's wires (3B.1); C5 reversed; U1/U2 rotated; U2 pins bridged |
| No `+5V_RAW` | The DFR0571 (3A), J107's wiring, Q102 (orientation, gate at GND, swapped with Q2) |
| `+5V_RAW` fine, no `+5V` | FB101 (1.34), the `+5V` trace between the sheets (1.2) |
| `VREF` not ≈ 2.5 V | R6/R7 values, C7 leakage/short |
| SDZ stays low | `+5V_RAW` below 4.65 V; a shunt left on JP105; U103 pins 1–2 or 2–3 bridged; R109/R110 open |
| FAULTZ low (TP109 < 0.8 V, "speaker fault" on the display) | A latched fault. Over-current: J102 shorted or a wire to GND, C121/C122, an output pin (1.41, 1.53). DC detect: C108/C109, the input pins (3C.6). Over-temperature: U101's exposed pad. Clear with JP105 or a power cycle. Low with no fault and JP105 doesn't clear it: R112 open |
| FAULTZ at 5 V instead of ≈ 3.2 V | R114 open or missing (1.39): Daisy pin 32 sees 5 V |
| Speaker silent, FAULTZ high (≈ 3.2 V) | MUTE high (Q2, `SPK_EN`, R108/C124); SDZ (TP104); L101/L102; J102 wiring |
| Speaker level wrong or distorted | R104 (gain), C108/C109, R11/R12; TP103 sagging under load (R105, F101, Q101, the supply lead) |
| Speaker never mutes | MUTE bridged to GND (U101 pins 11–13); Q2 shorted, or an AO3401A fitted as Q2 |
| Battery reading wrong | R102/R103 swapped (pin 25 near VBAT, ≈ 10× high: over the Daisy's rating); a 30k fitted for R102 (≈ 2.75× high); C17 |
| Input works only intermittently | J1 tip-normal switch, FB1/C2/R2 joints |
| No headphone output | A1.27 (`HP_SD`) high; U2 answering at 0x60 (R32/R33, A1.38 at 3.3 V, 1.8b); register 1 = 0xC0 and register 2's mute bits clear; `HP_5V` at C21 pad 1 (3B.6a); U2's joints |
| CPVSS ≈ 0 V with SD high | C13 (flying cap), C14, U2 pins 15–18 |
| DC or hum on J4 outputs | U2's ground pins and exposed pad (0.3, 1.8a); C22/C23 to GND; the input caps |
| Output only on one HP channel | That channel's input caps (C10/C22 left, C11/C23 right), U2 pins 1/2 or 4/5 (inputs), 14 or 11 (outputs), register 1's enable bits, J4 tip/ring pins |
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
| JP106–JP108 (AM2–AM0) | |
| F101 fuse | |
| R105 part | |
| R106 value | |
| C108/C109 value | |
| C121/C122 value | |
| L101/L102 value | |

| Stage | Result (Pass/Fail) | Measured values / notes |
|---|---|---|
| 0 Visual & mechanical | | |
| 1 Unpowered resistance | | TP101 → GND = ____ kΩ, A1.25 → GND = ____ kΩ, TP106 → GND = ____ kΩ |
| 2 Battery side | | I = ____ mA at 12.0 V, TP101 = ____ V, VGS = ____ V, A1.25 = ____ V |
| 2.13 / 2.14 Reverse J101 / J107 | | I = ____ mA / ____ mA |
| 3A DFR0571 alone | | Vout = ____ V (12 V in), ____ V (9 V in), ____ V (0.1 A); Iin = ____ mA |
| 3B 5 V rails | | I = ____ mA, TP106 = ____ V, Q102 drop = ____ mV, +5V = ____ V, R29 drop = ____ mV, FAULTZ = ____ V, VREF = ____ V, CPVSS (U2 off) = ____ V |
| 3C U101 enabled | | I = ____ mA, SDZ = ____ V, GVDD = ____ V, inputs = ____ / ____ V, SDZ delay = ____ ms |
| 3C.9 Power-off | | Largest MUTE − PVCC = ____ V, SDZ − PVCC = ____ V |
| 3D Filter options | | |
| 4A Guitar input buffer | | Clip level = ____ Vpp |
| 4B Headphone filter / amp | | CPVSS = ____ V, register 4 = ____, L = ____ Vpp, R = ____ Vpp into 32 Ω at 0x35, DC offset L/R = ____ / ____ mV |
| 4C Speaker amp | | Gain = ____ dB, 20 Hz = ____ dB, idle I = ____ mA, f_sw = ____ kHz, offset = ____ mV, clip = ____ V pk at ____ A, fault latch and JP105 clear OK |
| 4D AUX input | | Tip+ring = ____ Vpp |
| 5 Power-up with Daisy | | 5.0 VIN on USB = ____ V, I = ____ mA, 3V3_D = ____ V, back-power I = ____ mA |
| 6 Firmware functional | | SPK_MUTE high-state = ____ V, speaker fault shown (6.9a) ____, VBAT error = ____ %, AUX peak = ____, display I = ____ mA, DFR0571 drop-out at VBAT = ____ V, SDZ off at VBAT = ____ V |
| 7 Soak & robustness | | U101 = ____ °C after 30 min, fuse survived ____ starts |
| 8 Pops, hiss and mute | | SPK_EN delay = ____ s, mute time = ____ ms, HP max = ____ Vrms |

Rework performed:

Open issues:
