"""2N7002 N-channel MOSFET, SOT-23: 1 G, 2 S, 3 D. Ratings are JSCJ's (LCSC C8545)."""

MATCH = ["2N7002*"]
SOURCE = "JSCJ 2N7002 datasheet (2016-09), via https://jlcpcb.com/partdetail/Jscj-2N7002/C8545"


def model(p):
    p.clamp("2", "3", (0.5, 1.2), name="body", report=False)            # body diode, source (anode) to drain
    # RDS(on) is 7 Ω max at VGS 5 V and isn't given lower; 2 Ω is assumed as the low end, the case that draws most.
    p.switch("3", "2", "1", vth=(1.0, 2.5), r_on=2.0, polarity=1, i_max=0.115, assumed=True,
             source=SOURCE + "; RDS(on) 2 Ω assumed (the datasheet gives 7 Ω max at 5 V, nothing lower)")
    p.limit("1", abs=(-20.0, 20.0), ref="2", name="VGS")
    p.limit("3", abs=(None, 60.0), ref="2", name="VDS", input=False)
