"""Nexperia PESD5V0S1BA bidirectional ESD diode, SOD-323: pins 1 and 2 (either way round)."""

MATCH = ["PESD5V0S1BA*"]
SOURCE = "Nexperia PESD5V0S1BA datasheet v.6 (2024-04): Table 5 (VBR 5.5–9.5 V at 1 mA), Table 6 (VCL 10 V at 1 A)"


def model(p):
    # Continuous dissipation isn't in the datasheet: 20 mA (≈ 200 mW at 9.5 V, typical for SOD-323) is assumed.
    p.tvs("1", "2", vbr=(5.5, 9.5), r_dyn=0.5, i_max=20e-3, assumed=True,
          source=SOURCE + "; 20 mA continuous assumed: Ptot isn't in the datasheet")
