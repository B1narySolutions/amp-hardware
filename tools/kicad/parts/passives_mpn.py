"""Ratings and dielectrics of passives by manufacturer part number (the symbol's MPN field).

volts: capacitor voltage rating. tol: tolerance as a fraction. dielectric: C0G, X5R, X7R... for ceramics, or
"electrolytic" / "film". A Value such as "47uF 16V", or a Voltage, Tolerance or Dielectric field on the symbol,
overrides these.

Each entry is decoded from the manufacturer's part-numbering scheme, which encodes size, dielectric, value, tolerance
and voltage, read on 2026-11-05:
  Samsung CL series:  CL<size><dielectric><value><tol><voltage>...   size 21 = 0805, 31 = 1206; dielectric C = C0G,
                      B = X7R, A = X5R; tol J = 5 %, K = 10 %; voltage B = 50 V, A = 25 V
                      (Samsung Electro-Mechanics, "MLCC part numbering", samsungsem.com)
  KEMET commercial:   C<size>C<value><tol><voltage><dielectric>AC...   5 = 50 V; G = C0G, R = X7R
                      (KEMET, "Commercial Grade MLCC, C0G" and "... X7R" datasheets, ordering information)
  Murata GRM:         GRM<size><thickness><dielectric><voltage><value><tol>...   32 = 1210, R6 = X5R, 1C = 16 V
                      (Murata, "GRM series part numbering")
  Würth 860010472005: WCAP-ASLI aluminium electrolytic, 47 µF 16 V ±20 % (Würth Elektronik datasheet 860010472005)
"""

CATALOG = {
    "CL21C101JBANNNC": {"volts": 50, "tol": 0.05, "dielectric": "C0G"},          # 100 pF 0805
    "CL31B104KBCNNNC": {"volts": 50, "tol": 0.10, "dielectric": "X7R"},          # 100 nF 1206
    "CL21A475KACLRNC": {"volts": 25, "tol": 0.10, "dielectric": "X5R"},          # 4.7 µF 0805
    "C1206C105K5RACTU": {"volts": 50, "tol": 0.10, "dielectric": "X7R"},         # 1 µF 1206
    "C1206C102J5GACTU": {"volts": 50, "tol": 0.05, "dielectric": "C0G"},         # 1 nF 1206
    "C0805C105K5RACTU": {"volts": 50, "tol": 0.10, "dielectric": "X7R"},         # 1 µF 0805
    "C0805C332J5GACTU": {"volts": 50, "tol": 0.05, "dielectric": "C0G"},         # 3.3 nF 0805
    "GRM32ER61C476KE15L": {"volts": 16, "tol": 0.10, "dielectric": "X5R"},       # 47 µF 1210
    "860010472005": {"volts": 16, "tol": 0.20, "dielectric": "electrolytic"},    # 47 µF aluminium, D5 mm
}
