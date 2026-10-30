# Power Board Rev 1 — starter parts plan

2026-10-29. Quantities below are per board unless stated otherwise. This is a selection worksheet, not a released purchasing BOM; references/counts must be reconciled with the completed schematic. See BUILD_GUIDE.md for wiring, sources and verification requirements.

| Block | Qty | Part or initial specification | Selection status / footprint |
|---|---:|---|---|
| 5 V conversion | 1 | DFRobot DFR0571 module, existing | Keep; verify physical pin order/mounting. 1.6 A advertised output, 3 A peak |
| Speaker amplifier | 1 | TI TPA3118D2DAPR | Recommended Rev 1; DAP HTSSOP-32 with bottom exposed pad; verify/adapt land pattern |
| Input protection | 1 | ADI LTC4365CTS8#TRMPBF | Candidate UV/OV/reverse controller; TSOT-23-8, reference circuit review required |
| Protection FETs | 2 | TI CSD18534KCS, 60 V N-channel | Candidate; TO-220-3 G/D/S 1/2/3; review inrush SOA and thermal behavior |
| Protection thresholds | 3 | 1.00 Mohm, 18.2 kohm, 39.2 kohm; 1% | Illustrative 9.21 V UV / 13.49 V OV for verified raw 3S output; 0805 |
| Power-good supervision | 1 | TI TPS3808G50DBVR | Candidate 5 V monitor driving amplifier SDZ; SOT-23-6 |
| Fuse and holder | 1 each | Replaceable DC-rated fuse; 3 A initial evaluation candidate | Exact fuse/time curve/holder pending current and inrush tests |
| Master switch | 1 | DC-rated switch for full system current | Select exact physical part; connector/cable if panel-mounted |
| Battery connector | 1 | Mates actual Talentcell cable, rated above protected design current | Existing J1 RAPC10U footprint is unverified against cable |
| Carrier power connector | 1 | Four-position: 5V, GND, BAT, MUTE | Proposed 3.5 mm terminal; match exact manufacturer's drawing |
| Carrier audio connector | 1 | Two-position: LINE+, LINE- | 3.5 mm terminal candidate |
| Display power connector | 1 | Two-position: 5V_DISPLAY, GND | Terminal feeding a proper USB power cable |
| Display power cable | 1 | Correctly terminated 5 V USB cable to display USB-C input | Confirm cable/board input behavior; no bare USB-C receptacle substitution |
| Speaker connector | 1 | Two-position, current-rated, distinct from battery connector | Exact part pending harness choice |
| Speaker harness | 1 | Twisted pair to speaker's actual quick-disconnect tabs | Verify actual tab widths; neither lead grounded |
| Output inductors | 2 | Bourns SRP1038A-100M, 10 uH | Candidate; use A-series land pattern; 7.5 Arms / 12 A Isat in Bourns table |
| Output capacitors | 2 | 680 nF, 50 V X7R; allow 1 uF alternatives | Experimental 4-ohm starting values, verify effective capacitance, ripple/heating and response; 1206 candidate |
| Bootstrap capacitors | 4 | 220 nF, 25 V or higher, X7R | 0805 candidate; bootstrap-to-corresponding-output, short connections |
| Input coupling | 2 | 1.5 uF matched, low-leakage nonpolar, 16 V or higher | 1206 X7R candidate subject to bias/microphonic review; film possible if space permits |
| Amplifier bulk | 2 positions | 220 uF, 25 V, low-ESR electrolytic with adequate ripple rating | Exact series sets diameter/lead pitch/height |
| Amplifier bypass/AVCC parts | Per reference circuit | Local ceramic supply bypass and AVCC feed components | Reconcile values/counts to chosen TI schematic; do not substitute bulk for ceramic bypass |
| GVDD capacitor | 1 | 1 uF, 16 V X7R | 0805 candidate |
| Gain resistor | 1 | 5.6 kohm, 1% to GND | 0805; 20 dB master for TPA3118 |
| PLIMIT and mode settings | Per completed schematic | Divider/link positions and defined MODSEL/AM settings | Select after schematic review; do not leave controls floating |
| Snubber/EMI tuning positions | Per chosen reference topology | RC/EMI positions, initially evaluated individually | Optional/DNP; final values and count pending ringing/loss measurements |
| Buck input bulk | 1 position | 47–100 uF, 25 V | Experimental; exact series/footprint pending startup testing |
| Branch beads | 2 | Existing TDK MPZ1608S221ATA00 | 0603 / 1608 metric; current, bias and temperature suitability to be checked |
| Branch bypass links | 2 | 0 ohm, suitably current-rated | 0805 candidate; populate instead of corresponding bead |
| Branch bulk | 2 positions | 100 uF, 10 V or higher | Exact electrolytic series/footprint pending step/startup tests; optional population for comparisons |
| Small local bypass | As needed | 100 nF, X7R; 25 V on battery rail, 10 V or higher on 5 V | 0805 candidate; quantity follows schematic |
| Battery telemetry | 1 each | 30.0 kohm + 10.0 kohm, 1%; 100 nF | 0805; existing carrier makes ADC nominally VBAT_SYS/11 |
| Control resistors | Per schematic | 10k pull-ups, 100k SDZ pull-down and reset/timing parts as adopted | 0805; review total pull-up load and unpowered states |
| Test points | Approximately 12–16 | Entry/fused/protected battery; three 5 V nets; BAT; MUTE; SDZ; FAULT; nearby GND | Probe-friendly loops/pads; exact count follows layout |
| Assembly isolation links | 2 or more | Removable/current-rated battery-to-amplifier and buck branch links | Allow staged assembly/testing; verify full-current rating |
| Mounting holes/standoffs | 4 | M3 nonplated holes with enclosure clearance | Final dimensions depend on enclosure |
| Bench dummy load | 1 off-board | Non-inductive 4 ohm, 25–50 W or higher with cooling/derating | Required for amplifier testing; DC electronic load is unsuitable |

Do not buy another ESP32 or a 3.3 V regulator for the display: it already contains the ESP32-S3 and local regulation. The carrier accepts 5 V for the complete audio board. Battery charging remains through the Talentcell pack's supported charger; this revision adds no bare-cell charger or BMS.

Useful stock footprint families: Resistor_SMD:R_0805_2012Metric, Capacitor_SMD:C_0805_2012Metric, Inductor_SMD:L_0603_1608Metric, Package_TO_SOT_SMD:TSOT-23-8, Package_TO_SOT_SMD:SOT-23-6, Package_TO_SOT_THT:TO-220-3_Vertical. Each must still match the actual purchased component. Do not assign the installed SRP1038C footprint to SRP1038A without checking dimensions.

Procurement order: reuse existing module/beads → choose connector/capacitor mechanical parts → finish schematic counts/control values → verify custom IC/module/inductor footprints → release an actual BOM. Buying amplifier spares is sensible, but only one amplifier IC is fitted per board.
