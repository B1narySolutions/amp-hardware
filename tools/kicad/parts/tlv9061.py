"""TI TLV9061 single op-amp, SOT-23-5 (DBV): 1 OUT, 2 V−, 3 IN+, 4 IN−, 5 V+.

Rail-to-rail in and out. The inputs are diode-clamped to the rails and take up to ±10 mA.
"""

MATCH = ["TLV9061*"]
SOURCE = "TI TLV9061 datasheet SBOS839N (2026-07): §6.1 abs max, §6.3 recommended, §6.10 output swing"


def model(p):
    p.supply("5", "2", vmin=1.8, vmax=5.5, abs_max=6.0)
    if p.powered:
        # The output swings to within 20–60 mV of the rails; 0 here, which can only widen the bounds.
        # §6.6: 10 MHz GBW. §6.1 note 3: the output survives a continuous short to ground.
        p.opamp(out="1", inp="3", inn="4", lo="2", hi="5", swing=0.0, gbw=10e6, short_ok=True)
    for pin in ("3", "4"):
        p.limit(pin, abs=(("2", -0.5), ("5", 0.5)), op=(("2", -0.1), ("5", 0.1)), clamp=True, inject=10e-3)
