"""TI TPA6132A2 DirectPath stereo headphone amp, WQFN-16 (RTE).

1 INL−, 2 INL+, 3 INR+, 4 INR−, 5 OUTR, 6 G0, 7 G1, 8 HPVSS, 9 CPN, 10 PGND, 11 CPP, 12 HPVDD, 13 EN, 14 VDD,
15 SGND, 16 OUTL, 17 EP.

Each channel is an inverting amp: the input pin sees R_IN to the amp's summing node (held at IN+), and the output
swings between the charge pump's own rails, HPVDD and HPVSS. The gain is set by G0/G1; this model reads them from
the schematic (both to GND: −6 dB, R_IN 26.4 kΩ). The charge pump runs whenever VDD is up; EN is not modelled.
"""

MATCH = ["TPA6132A2*"]
SOURCE = "TI TPA6132A2 datasheet SLOS597B: §6.1 abs max, §6.3 recommended, §6.6 R_IN"

# (G0 high, G1 high) -> (gain, R_IN), datasheet §6.6.
GAINS = {(False, False): (0.5, 26.4e3), (True, False): (1.0, 19.8e3), (False, True): (1.41, 16.5e3),
         (True, True): (2.0, 13.2e3)}
HP = 1.8   # charge-pump rail magnitude: not stated; HPVDD's 1.9 V absolute maximum implies about 1.8 V


def model(p):
    on = p.supply("14", "15", vmin=2.3, vmax=5.5, abs_max=6.0)
    hp = (HP - 0.1, HP + 0.05)
    p.rail("12", p.dc(*hp) if on else p.dc(0.0))
    p.rail("8", p.dc(-hp[1], -hp[0]) if on else p.dc(0.0))
    p.rail("11", p.wave(0.0, 5.5) if on else p.dc(0.0))     # charge-pump flying cap, + side
    p.rail("9", p.wave(-hp[1], 0.0) if on else p.dc(0.0))   # and − side
    gnd = p.gnd
    g0, g1 = p.node("6") != gnd, p.node("7") != gnd
    gain, r_in = GAINS[(g0, g1)] if on else (0.0, 10e3)     # 10 kΩ input resistance while shut down
    for inn, inp, out in (("1", "2", "16"), ("4", "3", "5")):
        p.res(inn, inp, r_in, tol=0.2, name=f"Rin{inn}")
        if on:
            p.amp(out, inp, inn, gain, lo="8", hi="12", name=f"amp{out}")
        for pin in (inn, inp):
            p.limit(pin, abs=(("8", -0.3), ("12", 0.3)), clamp=True)
        if not on:
            p.limit(out, abs=(-0.3, 3.6), name=f"{out} (off)")
    for pin in ("6", "7", "13"):
        p.limit(pin, abs=(-0.3, ("14", 0.3)))
    p.limit("12", abs=(-0.3, 1.9), name="12 HPVDD")
