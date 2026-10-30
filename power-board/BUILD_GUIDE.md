# Power Board Rev 1 — KiCad build guide

Prepared 2026-10-29 from the project handoff, the existing carrier interface, and manufacturer documentation. This is a schematic/design plan, not a fabrication release. The open KiCad files were left unchanged. At inspection, the schematic contained J1 (a DC jack); the PCB was empty.

## 1. What to build

Build a battery power-distribution board with a mono speaker amplifier. Keep the purchased DFR0571 as a module. The Seed3, guitar input, headphone amplifier and audio conditioning belong on the existing audio carrier. The ESP32 is already on the selected Waveshare display.

```text
Talentcell 12 V-class output
    |
DC-rated fuse -- master switch -- input protection/cutoff
    |
 VBAT_SYS
    |
    +-- TPA3118D2 PBTL -- two-leg LC filter -- SPK+/SPK- -- 4-ohm speaker
    |
    +-- DFR0571 module -- +5V_RAW
                            |
                            +-- link/ferrite -- local caps -- +5V_AUDIO
                            |                                    |
                            |                              audio carrier J6
                            |
                            +-- link/ferrite -- local caps -- +5V_DISPLAY
                                                                 |
                                                       USB power cable to display

VBAT_SYS -- battery divider --> audio carrier J6 BAT
audio carrier J6 MUTE ---------> speaker amplifier MUTE
audio carrier J5 LINE+/LINE- --> speaker amplifier differential audio input
```

All power returns share GND. Neither speaker terminal is GND. LINE- is an audio input and must not be shorted to this board's GND.

Recommended build order: connectors → protected battery bus → buck and branches → battery sense → amplifier and controls → footprints → placement/routing → staged testing.

## 2. Decisions and remaining measurements

- **Amplifier:** use TPA3118D2DAPR for this revision, matching the existing carrier documentation. Treat the TPA3128D2 comparison as a later controlled substitution with its own configuration review.
- **Display:** the supplied Amazon ASIN B0FHK313SJ identifies the Waveshare ESP32-S3-Touch-LCD-7B. Waveshare specifies USB-C 5 V and lists 350 mA consumption. Budget more for peaks and measure with Wi-Fi, maximum backlight and GUI activity. Its two-pin 5 V connector is documented as an output; use the documented USB-C supply input. Leave its single-cell battery socket unused.
- **Buck:** DFRobot advertises DFR0571 as 5 V / 1.6 A with a 3 A peak rating. Your 2 A measurements are useful experimental results, but do not establish continuous operation in the enclosure. Initially plan for at most 1.6 A continuous combined load, then apply thermal margin.
- **Battery:** the supplied eBay listing advertises Talentcell 72 W / 100 Wh / 12 V 8300 mAh. Confirm the label/model, polarity and cable dimensions on the actual pack. Design provisionally for 9–12.6 V. A regulated 12 V output would prevent output-voltage sensing from accurately estimating cell charge; cutoff settings must then be reconsidered.
- **Runtime:** calculate from measured average battery power. For illustration, 100 Wh × 0.8 usable / 15 W = 5.3 hours; both 0.8 and 15 W are assumptions, not achieved results.
- **Output power:** 10 W into 4 ohms needs 6.32 Vrms and 1.58 Arms. At a 9 V supply, an ideal bridge only reaches 10.1 W for an unclipped sine; real losses lower this. Plan for about 5 W clean throughout discharge and measure the attainable maximum. PBTL adds current capability, not supply voltage.

Manufacturer sources: [Waveshare](https://docs.waveshare.com/ESP32-S3-Touch-LCD-7B), [DFRobot](https://www.dfrobot.com/product-1768.html), [battery listing supplied by user](https://www.ebay.com/itm/278396464326).

## 3. Start in the existing KiCad project

1. Open `Power_Board_Rev1.kicad_pro` from this folder and save the current schematic.
2. Keep the A3 sheet for Rev 1. Put battery protection at upper left, buck and branches at upper right, sense/control below them, and the speaker amplifier/filter at the bottom. Add text boxes naming these blocks.
3. In the schematic editor: **A** adds a symbol, **E** edits properties, **R** rotates, **M** moves, **W** draws a wire, and **L** places a local net label. Draw wires onto actual pin endpoints. Matching labels connect nets on this sheet; crossing lines without a junction dot do not necessarily connect.
4. Use these names consistently: `VBAT_IN`, `VBAT_FUSED`, `VBAT_SYS`, `+5V_RAW`, `+5V_AUDIO`, `+5V_DISPLAY`, `BAT_MON`, `SPK_MUTE`, `AMP_SDZ`, `AMP_FAULTZ`, `LINE+`, `LINE-`, `SPK+`, `SPK-`, `GND`.
5. Put a junction dot wherever a branch is intended. Do not use labels such as `+12V` to imply that the battery bus is regulated.
6. Start with the connectors below. References other than the existing J1 are proposed; carrier references are on the other PCB and need not match this PCB's references.

| Power-board connector     | Pin order                                   | Destination                         |
| ------------------------- | ------------------------------------------- | ----------------------------------- |
| J1, battery               | Positive, GND; confirm physical pad numbers | Talentcell output cable             |
| J2, carrier power/control | 1 +5V_AUDIO, 2 GND, 3 BAT_MON, 4 SPK_MUTE   | Carrier J6 pins 1–4                 |
| J3, audio input           | 1 LINE+, 2 LINE-                            | Carrier J5 pins 1–2                 |
| J4, display power         | 1 +5V_DISPLAY, 2 GND                        | Properly terminated USB power cable |
| J5, speaker               | 1 SPK+, 2 SPK-                              | Speaker quick-disconnect harness    |

The display UART goes directly to the carrier's J3; it is not routed through this power board. Use different connector styles for battery and speaker so their cables cannot be interchanged. A two-pin display output terminal plus an appropriate cable avoids designing a USB-C source connector in Rev 1.

## 4. Draw the battery entry and protection

1. Connect J1 positive to F1, then a 
. Connect J1 negative to GND. Put the fuse close to entry; protect any long battery lead with a suitably located fuse too.
2. Use a replaceable DC-rated fuse holder. Reserve space for a candidate 3 A fuse; select its actual current/time characteristic after steady load and capacitor inrush tests. It must protect the weakest connector, wire and copper path. Do not increase to 5 A just to mask a startup fault.
3. A concrete protection candidate is **LTC4365CTS8#TRMPBF plus two CSD18534KCS N-channel MOSFETs**. This combines reverse-input protection with adjustable input UV/OV disconnect. Copy the controller's reference topology, including FET orientation, gate and shutdown connections. The FETs are back-to-back, with their sources joined and drains facing input/output; tie both gates to the controller gate drive. This is a controller design candidate requiring review, not a tested board circuit.
4. Use the switched/fused input for the controller supply and threshold divider, and name its protected output `VBAT_SYS`. Set SHDN to a defined enabled level following the datasheet. Place bulk capacitance downstream of protection and verify inrush against MOSFET safe operating area. The fuse remains necessary: this controller is not a short-circuit current limiter.
5. For an actually unregulated 3S output, an illustrative three-resistor chain is: input → 1.00 Mohm → UV node → 18.2 kohm → OV node → 39.2 kohm → GND. Nominal calculations give 9.21 V UV trip, 9.67 V UV recovery and 13.49 V OV trip. Use 1% parts and calculate tolerance limits. These thresholds are proposals pending battery verification. Test battery voltage rebound after cutoff; repeated restarts require more hysteresis or a latch.
6. Add test points at entry, after fuse and at VBAT_SYS. A TVS is optional pending a coordinated surge design; its actual clamp must remain below downstream limits at the relevant surge current. A generic '12 V TVS' label is insufficient.

Sources: [LTC4365 reference circuit and threshold procedure](https://www.analog.com/media/en/technical-documentation/data-sheets/4365fa.pdf), [CSD18534KCS pinout and ratings](https://www.ti.com/lit/ds/symlink/csd18534kcs.pdf).

## 5. Draw the DFR0571 module and separate 5 V branches

1. Represent the DFR0571 as a module with VIN, GND and 5V OUT terminals. Verify its actual pad/pin order; labels in a block drawing are not a physical pinout. For early work, use connector symbols for a wired module and mechanically secure it.
2. Connect VIN to VBAT_SYS, GND to GND and output to +5V_RAW. Do not place a separate buck IC, catch diode or switching inductor for this module.
3. Start with a local input capacitor position (for example 47–100 uF / 25 V plus 100 nF / 25 V). These are experimental additions; check startup and module recommendations before population.
4. From +5V_RAW make TWO independent paths: one to +5V_AUDIO and one to +5V_DISPLAY. Each gets a series link/ferrite position and downstream 100 uF / 10 V plus 100 nF / 10 V capacitor positions.
5. Your existing MPZ1608S221ATA00 beads are 0603-size parts. Use them as candidates in these branch positions. Provide an alternative 0-ohm link in parallel and populate **either** the bead **or** the link. If both are fitted, the link bypasses the filter.
6. Provide optional/DNP local bulk capacitor positions so you can compare direct, capacitor-only, and bead-plus-capacitor configurations. No change to routing should be required between tests.
7. Large added output capacitance can change converter startup or cause ringing. Test step response, startup and rail minimum at the remote connectors; a bead is not a guaranteed cure for low-frequency ripple.
8. Wire +5V_AUDIO to J2.1 and +5V_DISPLAY to J4.1. Each cable returns with its own GND wire. Put a power test point and nearby ground probe point at each branch output.

Acceptance: carrier connector 4.75–5.25 V over the intended operating range, including wiring/filter drop. Do not connect uncoordinated PC USB power and external board power simultaneously; establish a programming/power arrangement for both development boards before doing so.

## 6. Draw battery telemetry for the EXISTING carrier

Use a **30.0 kohm / 10.0 kohm, 1%** divider from VBAT_SYS:

```text
VBAT_SYS -- 30k --+-- BAT_MON --> J2.3
                 |
                 +-- 10k -- GND
                 +-- 100nF -- GND
```

The carrier already has 10k in series to the ADC and 10k from ADC to GND. Its BAT input loads your divider with 20k. Do not copy the handoff's 150k/47k divider as though it connects straight to an unloaded ADC.

- Unplugged carrier: BAT_MON = VBAT_SYS / 4; source resistance = 7.5 kohm.
- Connected carrier: lower divider resistance = 10k || 20k = 6.667 kohm.
- Thus BAT_MON = VBAT_SYS × 2/11, and the carrier ADC = VBAT_SYS / 11.
- At 12.6 V: unloaded BAT_MON = 3.15 V; connected BAT_MON = 2.291 V; ADC = 1.145 V.
- Firmware conversion starts with VBAT_SYS = 11 × ADC voltage, then uses measured calibration. State of charge remains an estimate.

Using the protected switched bus makes sensing disappear with system power. If a later design switches off only the 5 V converter while leaving VBAT_SYS live, add sensing disconnect so BAT is not driven into the unpowered carrier. Record final values and calibration in the carrier DESIGN.md when the schematic is adopted; do not silently change the shared interface contract.

## 7. Draw the speaker amplifier

Use the [TPA3118D2 datasheet](https://www.ti.com/lit/ds/symlink/tpa3118d2.pdf), especially section 7.4.1/Figure 36, and the [EVM guide](https://www.ti.com/lit/ug/slou342/slou342.pdf). The installed stock symbol libraries did not contain a TPA3118 match during inspection. Import or make a project-local symbol, checking every pin against TI; include exposed pad 33.

Core connections:

| Function | Connection |
|---|---|
| Supply | PVCC 18/19/31/32 and AVCC 17 to the locally decoupled battery supply |
| Ground | Pins 9/22/25/28 and thermal pad 33 to GND |
| Mono selection | INPL 10 and INNL 11 directly to GND |
| Audio | LINE+ through matched 1.5 uF to INPR 4; LINE- through matched 1.5 uF to INNR 5 |
| Gain | GAIN/SLV 8 through 5.6k to GND: 20 dB master |
| Positive output group | OUTPR 29 joined to OUTNR 27, before its inductor |
| Negative output group | OUTPL 23 joined to OUTNL 21, before its inductor |
| Bootstrap | Four 220 nF capacitors: 30–29, 26–27, 24–23, 20–21 |
| GVDD | Pin 7, 1 uF to GND; no external load supply |
| Mute | Pin 12 to SPK_MUTE, 10k pull-up to +5V_RAW |
| Shutdown | Pin 2 to AMP_SDZ sequencing circuit |
| Fault | Pin 3 open-drain, pull-up and test point |

For remaining settings, use the EVM: define PLIMIT, MODSEL and all AM pins; mark unused SYNC appropriately. Start with BD modulation and a documented master switching-frequency setting. Reserve PLIMIT adjustment positions; validate the chosen limiter level rather than assuming it guarantees fixed clean output power. All logic levels must stay within the amplifier's allowed rails during startup/shutdown.

Use local ceramic decoupling at each supply-pin group and nearby 220 uF / 25 V bulk positions. Copy the EVM's AVCC supply treatment and physical supply routing. Bootstrap capacitors bridge bootstrap-to-output, not bootstrap-to-GND.

The mono arrangement uses two filter inductors. Start the 4-ohm evaluation with 10 uH in each leg and 680 nF from each filtered output to GND (the datasheet's 4–8-ohm filter starting point). Reserve compatible positions for 1 uF alternatives from the PBTL example; select values after frequency-response and ringing tests with the intended speaker. Include footprints for optional snubber/EMI components using the reference topology, and determine their population from measurements.

Candidate inductors: two **Bourns SRP1038A-100M**, shielded 10 uH. Bourns lists 7.5 Arms, 12 A saturation and 30 milliohm maximum DCR. These offer generous current margin for 5–10 W, but still need switching-loss/temperature testing. At 10 W the speaker current peaks at 2.24 A before switching ripple. [Bourns datasheet](https://bourns.com/docs/product-datasheets/srp1038a.pdf).

Keep the two audio input components matched. The carrier's LINE- is referenced through resistance on the carrier: never bond it to local GND. Neither SPK+ nor SPK- may go to chassis, headphone ground or a grounded test instrument input.

## 8. Make startup and mute predictable

The carrier's existing open-drain circuit requests play by pulling SPK_MUTE low. With the proposed 10k pull-up and carrier's 470-ohm resistor, the nominal low is about 0.22 V at 5 V, before transistor drop. Open/unplugged means muted.

Keep AMP_SDZ independent of this request. A candidate is **TPS3808G50DBVR** monitoring +5V_RAW: VDD and SENSE to +5V_RAW, 100 nF supply bypass, RESET output to AMP_SDZ with 10k pull-up to +5V_RAW and 100k pull-down to GND. Start with CT open (20 ms nominal); MR can use its internal pull-up, with a reset jumper to GND. Its 4.65 V threshold inhibits the amplifier when the 5 V supply collapses; this is not a guarantee that the remote carrier still meets 4.75 V.

Bring AMP_FAULTZ out separately with its own pull-up/test point. For first bring-up use manual fault recovery through SDZ instead of assuming automatic restart is wanted. Verify input current/leakage and logic margins of the finished controls. Test off sequencing and residual pops with the assembled system; the power-good circuit alone does not guarantee pop-free behavior on every rail-collapse waveform. [TPS3808 datasheet](https://www.ti.com/lit/ds/symlink/tps3808.pdf).

## 9. Select footprints AFTER selecting actual parts

A symbol is an electrical drawing; a footprint is the copper/hole pattern for one physical package. An electrical value alone does not determine a footprint.

1. Add fields such as Manufacturer, MPN, voltage rating, tolerance and assembly notes to each symbol. Mark optional parts DNP.
2. Use **Tools → Assign Footprints**. Use the footprint viewer and compare pad numbering, pitch, body dimensions and recommended land pattern to the exact ordered part.
3. Prefer 0805 passives for hand assembly. The already owned TDK beads remain 0603; do not assign 0805 to them. Bootstrap parts should remain compact enough for short loops.
4. TPA3118D2DAPR needs **DAP bottom thermal pad**, not DAD top thermal pad and not plain TSSOP. An installed starting candidate is `Package_SO:HTSSOP-32-1EP_6.1x11mm_P0.65mm_EP5.2x11mm_Mask4.11x4.36mm_ThermalVias`; its generic exposed-pad/mask geometry must be compared to TI's DAP0032C drawing and adapted in a project-local copy if necessary. It is not preapproved by its package name. Plan stencil/reflow or appropriate hot-air assembly for the underside pad.
5. LTC4365 TS8 uses a verified TSOT-23-8 pattern; TPS3808 DBV uses SOT-23-6. The CSD18534KCS is TO-220-3 with G/D/S pins 1/2/3; the metal tab is drain, so the two tabs are electrically different nodes.
6. SRP1038A needs its **A-series** land pattern. The installed SRP1038C footprint is not automatically interchangeable.
7. Bulk capacitor footprint depends on the actual can diameter, lead spacing and height. Do not assign one before choosing the purchased series.
8. Verify DFR0571 pad spacing on the actual module or use the wired-module connector approach. Draw its body courtyard/keepout if mounting above the PCB.
9. Verify the existing J1 RAPC10U against the actual cable; having selected its footprint does not confirm mating dimensions or polarity. A generic barrel-jack footprint is not interchangeable with every DC jack.
10. Print connectors and custom footprints at 1:1 scale and physically check parts before ordering PCBs.

## 10. Check the schematic, then lay out the board

1. Annotate symbols. Run Electrical Rules Checker. Inspect each error; use PWR_FLAG only where an actual source exists and ERC needs its source type declared. Do not add flags to conceal wrong power wiring.
2. Independently check every IC pin and connector against the datasheet/cable drawing. ERC cannot prove protection thresholds, analog behavior or a custom symbol pin map.
3. Use **Tools → Update PCB from Schematic (F8)**. Set outline and mounting holes before detailed placement. [KiCad schematic manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html).
4. Four layers with a continuous ground plane directly below top routing is a useful recommendation for this mixed-signal board. Two layers are possible with careful layout and thermal/EMI verification, but do not split ground planes under audio paths.
5. Place entry/protection near the battery connector; amplifier → LC filter → speaker connector in a compact chain. Put the buck away from amplifier inputs. Keep speaker wiring away from the carrier's guitar input.
6. Place the amplifier, bootstrap caps, PVCC ceramic caps and thermal vias before general routing. Copy the reference design's loop geometry where possible. Keep switching copper compact and away from LINE+/LINE-.
7. Route high-current power and speaker paths using short, broad copper. Choose widths from actual continuous/peak current, copper thickness, length and allowable temperature rise; do not use 0.25 mm defaults for the battery path. Check via current capability if a power path changes layers.
8. Keep LINE+/LINE- adjacent and short, with a continuous reference plane. Route carrier/display supply branches separately from the buck output so display current does not pass through the audio branch wiring.
9. Connect the exposed pad to ground copper and thermal vias with an assembly-approved paste/via plan. Do not assume a few open vias make the pad reliably soldered from the back.
10. Add probe-friendly ground pads next to all supply test points, four mounting holes with clearance, polarity markings and readable connector signal names. Mark both speaker terminals as bridged outputs.
11. Refill zones and run Design Rules Checker. Resolve unconnected nets, clearance problems and schematic/PCB mismatches. Check 3D fit, cable access, enclosure clearance, component heights and underside shorts. Inspect plotted Gerbers and drill files before fabrication.

## 11. Assemble and test in stages

1. **Unpowered inspection:** verify orientation, solder bridges, fuse, connector mapping, capacitor polarity and resistance from each rail to GND. Inspect the amplifier thermal-pad assembly.
2. **Protection only:** use a current-limited bench supply and small dummy load. Check normal conduction, switch-off, UV/OV trip and recovery. Conduct reverse-input checks only within the designed circuit's verified ratings. Confirm cutoff remains off long enough under battery rebound.
3. **Buck only:** leave the amplifier branch disconnected using a planned assembly link. Test unloaded and with the electronic load at 9, 11.1 and 12.6 V inputs; check startup, step load, sustained temperature, voltage and ripple.
4. **Digital loads:** connect the carrier, then display. Measure at the far end of their cables during DSP, full backlight and Wi-Fi. Compare branch-filter populations. Record continuous and peak total 5 V current.
5. **Mute controls:** confirm disconnected/reset carrier means muted; pulling MUTE low permits play only after the supply is valid. Test independent loss of the 5 V branch while the amplifier battery branch remains live.
6. **Amplifier:** start with no input and an appropriately cooled non-inductive 4-ohm dummy load, typically a 25–50 W or higher resistor with suitable derating. Then use a low-level 1 kHz sine and increase gradually.
7. **Measure bridged output correctly:** use a suitably rated differential probe, or two ground-referenced scope channels with BOTH ground clips connected to board GND and subtract their signals. Never clip a grounded probe lead to SPK-. Confirm common-mode voltage/bandwidth ratings and measurement filtering. The DC electronic load is not an AC speaker load.
8. Measure audio RMS across the dummy load after suitable rejection of switching residue; use P = Vrms squared / 4. Record the clipping/distortion criterion. Repeat across input voltage, output level and temperature. Ordinary scope RMS including PWM is not valid audio output power or THD+N.
9. **Integration:** connect the real speaker at low volume. Compare noise under display/Wi-Fi/DSP activity. Measure battery average power and actual runtime. Repeat hot-enclosure checks and shutdown tests.

## 12. Before ordering a finished PCB/BOM

- Actual battery model, cable dimensions/polarity and voltage behavior recorded.
- Sustained/peak 5 V load and enclosure cooling support the selected buck.
- Protection schematic reviewed, including resistor tolerances, MOSFET SOA/inrush, rebound behavior and fuse coordination.
- Final amplifier controls, supply bypass parts, filter and optional EMI network fully drawn and reviewed.
- All MPNs assigned, exact footprints checked, thermal assembly method agreed.
- Shared carrier interface still satisfied; calibration documented. Add a power-board circuit verification spec when the schematic exists, and run the repository checks on both boards after interface changes.
- ERC/DRC resolved and staged bench acceptance criteria agreed.

Start now with sections 3–5. Complete those schematic blocks before routing or buying the remaining package-dependent parts.
