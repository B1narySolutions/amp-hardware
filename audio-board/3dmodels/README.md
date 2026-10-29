# 3D placeholders

KiCad ships no 3D model for the Daisy Seed3 or the Neutrik NRJ4HF, and Same Sky's SJ3-35063AG model isn't in its library either, so
`make_placeholders.py` builds simplified STEP bodies sized from the manufacturer drawings.

- **A1** uses `Electrosmith_Daisy_Seed_placeholder.step` on two stock `PinSocket_1x20_P2.54mm_Vertical` models (8.5 mm), at x = 0 and
  15.24. **J1** uses `Neutrik_NRJ4HF_placeholder.step`. The paths are set on the board, so re-running "Update footprints from library"
  on A1 or J1 resets them to KiCad's missing models.
- **J2/J4** use `SameSky_SJ3-35063AG_placeholder.step`, set in the project footprint itself, so a footprint update keeps it.
- **The Daisy placeholder is the original Seed's outline** (micro-USB, ~1 mm overhang, 3 mm tall). The Seed3's USB-C overhangs the
  PCB by 1.55 mm and stands 3.25 mm tall (Seed3 datasheet, page 8).
