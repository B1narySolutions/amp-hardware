"""Ratings of passives by LCSC part number, for parts whose Value field doesn't carry them.

volts: capacitor voltage rating. power: resistor power rating (W). tol: tolerance as a fraction.
Read from the LCSC product pages (https://www.lcsc.com/product-detail/<number>.html) on 2026-10-28.
A Value such as "47uF 16V", or a Voltage, Power or Tolerance field on the symbol, overrides these.
"""

CATALOG = {
    # capacitors
    "C1790": {"volts": 50, "tol": 0.05},       # 100 pF 0805 C0G
    "C1848": {"volts": 50, "tol": 0.10},       # 1 µF 1206 X7R
    "C1885": {"volts": 50, "tol": 0.05},       # 1 nF 1206 C0G
    "C24497": {"volts": 50, "tol": 0.10},      # 100 nF 1206 X7R
    "C77101": {"volts": 16, "tol": 0.10},      # 47 µF 1210 X5R (Murata)
    "C1779": {"volts": 25, "tol": 0.10},       # 4.7 µF 0805 X5R (Samsung CL21A475KAQNNNE)
    "C19110": {"volts": 25, "tol": 0.10},      # 2.2 µF 0805 X7R
    "C28323": {"volts": 50, "tol": 0.10},      # 1 µF 0805 X7R
    "C486355": {"volts": 50, "tol": 0.05},     # 3.3 nF 0805 C0G (FH 0805CG332J500NT)
    "C2835642": {"volts": 16, "tol": 0.20},    # 47 µF 16 V aluminium electrolytic, D5 × 11 mm (Samyoung NXB)
    # resistors
    "C17927": {"power": 0.25, "tol": 0.01},    # 1 MΩ 1206
    "C4410": {"power": 0.25, "tol": 0.01},     # 1 kΩ 1206
    "C17902": {"power": 0.25, "tol": 0.01},    # 10 kΩ 1206
    "C17414": {"power": 0.125, "tol": 0.01},   # 10 kΩ 0805
    "C26010": {"power": 0.125, "tol": 0.01},   # 3.3 kΩ 0805
    "C17900": {"power": 0.25, "tol": 0.01},    # 100 kΩ 1206
    "C17710": {"power": 0.125, "tol": 0.01},   # 470 Ω 0805
}
