# Legacy boards

The two boards the amp board (`../amp-board/`) grew out of, kept as they were ordered on 2026-11-05. They are frozen:
the amp board doesn't have to match them, and they change only if a board that was ordered turns out to differ from
these files. Their bring-up results go into the amp board's `DESIGN.md`, "Open items".

| Board | Folder | What it is |
|---|---|---|
| Audio board rev 2 | `audio-board/rev2/` | Daisy Seed3, guitar and AUX inputs, MAX9722A headphone amp. 2-layer, hand-soldered |
| Power board rev 1 | `power-board/` | Battery input, 5 V supply, TPA3118D2 speaker amp |

- `audio-board/rev2/DESIGN.md`: how the audio board works and why; `CHANGES.md`: what changed from its rev 1
- `audio-board/TEST_PLAN.md`: the audio board's bring-up and test steps
- `audio-board/rev2/seed3-carrier-digikey.csv`: the audio board's parts; `audio-board/rev2/fab/`: the Gerber zip sent
  to JLCPCB
- `power-board/README.md`: what each of the two boards expects from the other
- `power-board/DigiKey_Import.csv`: the power board's parts, substitutes included. Assemble from these
- `amp-digikey-order.csv`: the DigiKey order that was placed, one build of both boards, with the power board's
  experiment parts, stock substitutes and notes; `amp-digikey-cart.csv` is the same order in DigiKey's cart format

The audio board's footprints and symbols are in `audio-board/Seed3_Carrier.pretty` and
`audio-board/seed3-carrier.kicad_sym`; the power board's are in `power-board/Halliquest_Power.*`.
