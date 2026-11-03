# Footprint audit — November 3, 2026

Audited Halliquest_Power_Routed against DigiKey_Import.csv, manufacturer mechanical drawings, the installed KiCad libraries, and the project-local footprints. The final design contains 60 physical footprints. All schematic pins have matching numbered pads, and the footprint assignments agree between schematic and PCB. No footprint courtyard overlaps or copper/hole-clearance errors remain after refilling the ground zone. Footprint_Verification.csv records each reference and its package result.

## Correction applied

F1's stock KiCad footprint placed its two holes 10.16 mm apart. Bulgin specifies 10.00 mm for FX0457. Replaced it with project-local Halliquest_Power:Fuseholder_Bulgin_FX0457_P10.00mm, using 10.00 mm pitch and 1.35 mm drilled holes. The same FX0457 stays in the purchasing list. Body/courtyard dimensions retain conservative stock clearances. The stock 3D model is illustrative and retains its original modeled lead spacing; the actual manufacturing holes use the corrected spacing.

Source: Bulgin Fuseholders catalogue, page 13. https://www.bulgin.com/us/products/pub/media/bulgin/data/Fuseholders.pdf

## Packages checked

| Group | Result |
| --- | --- |
| U1 TPA3118D2DAPR | Matches TI DAP0032C drawing. 0.65 mm pitch, 7.5 mm row spacing, 1.5 x 0.45 mm lead pads. Thermal copper 5.2 x 11 mm is mask covered except the 3.04 x 3.74 mm central opening. Six ground vias are outside the paste opening. |
| U3 TPS3808G50DBVR | DBV / SOT-23-6 package and pin numbering match. |
| Q1 IRF4905PBF | TO-220 vertical, 2.54 mm pitch. Pin 1 gate, 2 drain, 3 source. The tab is drain. |
| D1 BZT52C12-7-F | SOD-123 package and cathode/anode pad mapping match. |
| L1/L2 SRP1038A-100M | Correct lead-frame A-series footprint. Recommended outer land span 13.6 mm, inner gap 5.4 mm, height 3.5 mm. |
| J1 PJ-102AH | Correct pin offsets and numbering. KiCad's 1.6 mm round drills provide clearance for its solder blades, while the manufacturer's recommendation uses 1.0 x 1.6 mm slots. No board cutout required. |
| J2–J7 and SW1 | Phoenix PT 1.5 horizontal terminals, 3.5 mm pitch and 1.2 mm holes. J3 is four-position. Others are two-position. |
| JP1–JP5 | Harwin M20-9990245 headers and M7567-05 shunts both use 2.54 mm pitch. The stock header uses 1.0 mm holes for 0.64 mm square posts. |
| C11/C12 | Updated to Panasonic EEU-FR1E101, 100uF/25V, 6.3 mm diameter and 2.5 mm pitch. |
| C4/C6 | Same checked Panasonic package, marked DNP for initial assembly. |
| Other ceramics | KEMET C0805/C1206 and Murata GRM31 body sizes match the assigned 0805/1206 footprints. General ceramics use hand-solder pads. |
| Resistors | Yageo RC1206 and RC2512 package sizes match their footprints. |
| FB1/FB2 | TDK MPZ1608 is 1.6 x 0.8 mm (0603). Stock lands are slightly larger than TDK's nominal recommended lands and leave room for hand soldering. |
| TP1/TP2 | 2 mm copper pads, with no separate purchased component. |

U1 and the custom inductors do not have project-local 3D body models. The 2D fabrication outlines, pads and courtyards were inspected. The exposed-pad soldering process, actual enclosure heights, cable access and physical plug fit still need assembly checks. These items cannot be established by DRC or a footprint image.

## Capacitor reduction

Removed C1 and C2 from the battery input. Reduced each amplifier bulk capacitor C11/C12 from 220uF to 100uF, retaining one at each supply-pin group. Marked C4/C6 as optional and DNP. This gives 23 capacitor positions and 21 fitted capacitors for initial assembly, down from 25 fitted. The bootstrap, audio-input, speaker-filter and local bypass capacitors are retained.

DigiKey_Import.csv now contains the initial fitted parts. DigiKey_Optional_Capacitors.csv contains C4/C6 separately. The optional parts can be fitted later for filter testing. These changes assume the DFR0571 retains its own module input/output capacitors and the remote carrier/display retain load-end decoupling.

## Current layout state

The latest user-saved PCB before this audit had most traces removed. It had 126 unconnected items before the capacitor changes, plus stale ground-fill clearance violations around the moved JP4. Refilling corrected those clearance issues. The current file has 123 unconnected items and zero schematic/PCB parity issues. It has no other DRC errors. Existing dangling vias and barrel-jack silkscreen edge clips remain. This layout requires rerouting before fabrication. Earlier reports of a fully routed board apply to the earlier saved routing revision.

Backups immediately before this audit are in tmp/footprint-audit/before relative to the capstone workspace. The circuit/fault checker still requires a power-board verification specification. The ERC findings for the intended PBTL output pairs remain subject to electrical review. No waivers were added.

Additional primary sources:
- TI amplifier / package drawing: https://www.ti.com/lit/ds/symlink/tpa3118d2.pdf
- TI supervisor: https://www.ti.com/lit/ds/symlink/tps3808.pdf
- Bourns: https://bourns.com/docs/product-datasheets/srp1038a.pdf
- Same Sky jack: https://jp.sameskydevices.com/product/resource/pj-102ah.pdf
- Phoenix 1984617: https://www.phoenixcontact.com/en-us/products/printed-circuit-board-terminal-pt-15-2-35-h-1984617?type=pdf
- Panasonic FR: https://media.digikey.com/pdf/Data%20Sheets/Panasonic%20Electronic%20Components/EEU-FR_Series.pdf
- TDK bead: https://product.tdk.com/en/search/emc/emc/beads/info?part_no=MPZ1608S221ATA00
- Infineon MOSFET: https://www.infineon.com/assets/row/public/documents/24/49/infineon-irf4905-datasheet-en.pdf
