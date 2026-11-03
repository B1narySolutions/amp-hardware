# Rev1 Power Board

Open **Rev1_Power_Board.kicad_pro** in KiCad's project manager. Then open the matching schematic or PCB from that project. Use this folder for subsequent work and keep its libraries beside the project files.

## Files

- `Rev1_Power_Board.kicad_pro` — project and design settings.
- `Rev1_Power_Board.kicad_sch` — latest saved schematic, including the agreed capacitor reductions.
- `Rev1_Power_Board.kicad_pcb` — latest saved PCB placement and partial routing.
- `Halliquest_Power.kicad_sym` — restored local symbol library.
- `Halliquest_Power.pretty` — local custom footprints, including the corrected 10.00 mm fuse-holder footprint.
- `sym-lib-table` and `fp-lib-table` — library paths relative to this folder.
- `DigiKey_Import.csv` — initial fitted electronics purchase list.
- `DigiKey_Optional_Capacitors.csv` — optional C4/C6 parts.
- `Footprint_Verification.csv` and `FOOTPRINT_AUDIT.md` — footprint audit. Its routing counts describe the earlier audit date/state; use the current reports below.
- `PCB_Check.json` and `Schematic_Check.json` — checks on this packaged project.

## Current status

The schematic and PCB have 60 matching component footprints. C1/C2 are removed, C11/C12 are 100uF/25V with matching packages, and C4/C6 are marked DNP. This leaves 21 fitted capacitors and two optional capacitor positions.

The PCB is a 98 x 98 mm two-layer work in progress with a bottom ground pour and edge keepouts. The check finds **105 unrouted connections**. Other warnings include 16 dangling vias and silkscreen findings. No footprint/schematic parity issues or other board-check errors were found with unrouted connections allowed. The schematic retains two PBTL output-pair ERC findings and one local/global ground-label warning for review. Finish routing and electrical/assembly review before fabrication.

## Packaging notes

This folder starts from the latest saved `Halliquest_Power` schematic and PCB in the parent power-board folder. The current project settings were retained, with the signal/power net classes restored from the previous routed project settings. The missing local symbol library was recovered from the working copy. The project has a fresh identifier to let KiCad open it independently of older versions. Earlier files and backups remain in their existing locations.

This folder includes project-local symbols and footprints. Standard KiCad libraries must still be installed on the computer where you open it.
