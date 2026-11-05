# Amp hardware

The circuit boards for our capstone guitar amp, designed in KiCad 10.

## Boards

| Board | Folder | Status |
|---|---|---|
| Audio board (Seed3 carrier) | `audio-board/rev2/` | Rev 2, ordered |
| Power board | `power-board/` | Rev 1 |

**Audio board.** Holds the Daisy Seed3 that does the audio processing, the guitar and AUX inputs, the headphone amp, and
screw terminals to the power board and the display. It's a 2-layer board, hand-soldered, with every part from DigiKey.

**Power board.** Supplies 5 V and the battery level to the audio board, and drives the speaker. Its `README.md` lists what
each board expects from the other.

## Where to look

- `audio-board/rev2/DESIGN.md`: how the audio board works and why
- `audio-board/rev2/CHANGES.md`: what changed from rev 1
- `audio-board/TEST_PLAN.md`: bring-up and test steps
- `audio-board/rev2/seed3-carrier-digikey.csv`: the audio board's parts order
- `audio-board/rev2/fab/`: the Gerber zip sent to JLCPCB
- `power-board/README.md`: the power board's contract with the audio board
- `power-board/DigiKey_Import.csv`: the power board's parts order
- `amp-digikey-order.csv`: one build of both boards in a single DigiKey order, with the power board's experiment parts,
  stock substitutes and notes; `amp-digikey-cart.csv` is the same order in DigiKey's cart upload format

## Opening the designs

Open the `.kicad_pro` file in either board's folder with KiCad 10. The project's own footprints and symbols live in
`audio-board/Seed3_Carrier.pretty`, `audio-board/seed3-carrier.kicad_sym` and `power-board/Halliquest_Power.*`; the
library tables point to them, so no setup is needed.
