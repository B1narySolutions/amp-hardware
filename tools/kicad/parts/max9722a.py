"""Maxim MAX9722A DirectDrive stereo headphone amp, 16-pin TSSOP (EUE).

1 INL+, 2 SHDN, 3 PVDD, 4 C1P, 5 PGND, 6 C1N, 7 PVSS, 8 SGND, 9 INR+, 10 INR−, 11 SVDD, 12 OUTR, 13 SVSS, 14 OUTL,
15 SVDD, 16 INL−. The TSSOP has no exposed pad.

Each channel is an op-amp whose gain the board sets with external resistors (−RF/RIN, Figure 7). The charge pump
inverts PVDD onto PVSS, which the board ties to SVSS, so the outputs swing about GND between SVSS and SVDD. The charge
pump runs whenever the supply is above the UVLO; SHDN (active low) isn't modelled.
"""

MATCH = ["MAX9722A*"]
SOURCE = "Maxim MAX9722A/MAX9722B datasheet 19-3049 rev 2: Absolute Maximum Ratings, Electrical Characteristics"

# PVSS is "roughly proportional to PVDD and not regulated" (Powering Other Circuits from a Negative Supply): the
# inverted supply, less up to 0.7 V across the charge pump's ≈ 6 Ω output resistance (Typical Operating
# Characteristics) at full output current. PVSS is the fallback when PVDD isn't a declared rail.
PVSS = (-5.5, -4.0)


def model(p):
    on = p.supply("3", "5", vmin=2.4, vmax=5.5, abs_max=6.0)
    p.supply("11", "8", vmin=2.4, vmax=5.5, abs_max=6.0)
    vdd = p.circ.fixed.get(p.node("3"))
    pvss = (-vdd.hi, min(-vdd.lo + 0.7, PVSS[1])) if vdd is not None else PVSS
    p.rail("7", p.dc(*pvss) if on else p.dc(0.0))
    p.rail("4", p.wave(0.0, -pvss[0]) if on else p.dc(0.0))     # flying cap, + side
    p.rail("6", p.wave(pvss[0], 0.0) if on else p.dc(0.0))      # and − side
    for inp, inn, out in (("1", "16", "14"), ("9", "10", "12")):
        if on:
            # Outputs survive a continuous short to GND (Absolute Maximum Ratings).
            p.opamp(out=out, inp=inp, inn=inn, lo="13", hi="11", gbw=1e6, short_ok=True)
        for pin in (inp, inn):
            # IN_ to SGND: SVSS − 0.3 V to SVDD + 0.3 V. Input common-mode range −0.5 V to +0.7 V.
            p.limit(pin, abs=(("13", -0.3), ("11", 0.3)), op=(-0.5, 0.7), clamp=True)
        p.limit(out, abs=(-3.0, 3.0), name=f"{out} OUT")
    p.limit("2", abs=(-0.3, ("11", 0.3)), name="2 SHDN")
