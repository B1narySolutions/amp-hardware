"""AOS AO3401A P-channel MOSFET, SOT-23: 1 G, 2 S, 3 D."""

MATCH = ["AO3401*"]
SOURCE = "AOS AO3401A datasheet rev 3.1 (2023-12), p1–2"


def model(p):
    p.clamp("3", "2", (0.5, 1.0), name="body", report=False)            # body diode, drain (anode) to source
    # On at VGS below −1.3 V, off above −0.5 V. 47 mΩ is RDS(on) typ at −4.5 V: the lowest, so the highest current.
    p.switch("3", "2", "1", vth=(0.5, 1.3), r_on=0.047, polarity=-1, i_max=4.0)
    p.limit("1", abs=(-12.0, 12.0), ref="2", name="VGS")
    p.limit("3", abs=(-30.0, None), ref="2", name="VDS", input=False)
