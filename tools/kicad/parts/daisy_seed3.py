"""Electrosmith Daisy Seed3 module (STM32H750 + TI TAC5242 codec), pins 1–40.

The firmware decides what each GPIO does, so the board's spec says it:

    spec.config("A1", out=[14, 28], inp=[15], pullup=[23], adc=[22, 25])

  out     push-pull output, 0..3.3 V
  inp     digital input
  pullup  digital input with the internal pull-up on
  adc     analog input
Pins not listed are left out of the model. The audio pins (16–19), VIN and the 3.3 V outputs are always modelled.
The module counts as powered when VIN is up, or when the power state lists A1 under powered= (running from USB).
"""

MATCH = ["Daisy Seed3*", "Daisy_Seed3*"]
SOURCE = ("Daisy Seed3 datasheet v2.1.0 (2026-08), Tables 1–3: "
          "https://daisy.nyc3.cdn.digitaloceanspaces.com/products/seed3/Daisy_Seed3_datasheet.pdf")
STM32 = "STM32H750 datasheet DS12556 rev 5: Table 7 pin types, Table 19 VIN, Table 20 I_INJ, Table 58 R_PU"
TAC = "TI TAC5242 datasheet SLASF27A: §6.1 abs max, §6.5 input impedance 5 kΩ ±20%, line-out load ≥ 600 Ω"

# STM32 port and I/O type behind each Daisy GPIO (Seed3 Table 2, DS12556 Table 7). FT pins are 5 V tolerant in digital
# mode; FT_a pins are not in analog mode; TT pins never are. None of them takes positive injection current.
PINS = {14: ("PB6", "FT"), 15: ("PB7", "FT"), 22: ("PC0", "FT_a"), 23: ("PA3", "FT_a"), 24: ("PB1", "TT"),
        25: ("PA7", "TT_a"), 28: ("PC4", "TT_a"), 29: ("PA5", "TT"), 30: ("PA4", "TT")}
V33 = (3.2, 3.4)          # the module's 3.3 V rails: the datasheet gives no tolerance, ±3 % is assumed


def model(p):
    p.supply("39", "40", vmin=4.0, vmax=17.0, abs_max=17.0)
    on = p.powered
    for pin in ("21", "38"):
        p.rail(pin, p.dc(*V33) if on else p.dc(0.0))
    v33 = "38"

    # Audio inputs: AC-coupled on the module into the codec's 5 kΩ ±20 %. The coupling cap's value isn't published.
    # The datasheet's ±1.8 V absolute maximum (and 3.6 Vpp full scale) is applied to the signal after that cap,
    # which is how DESIGN.md reads it: pin 16 sits at VREF (≈ 2.5 V DC) by design.
    for pin in ("16", "17"):
        node = f":in{pin}"
        p.cap(pin, node, 10e-6, tol=0.2, name=f"Cin{pin}")
        p.res(node, p.gnd, 5e3, tol=0.2, name=f"Rin{pin}")
        if on:
            p.limit(node, abs=(-1.8, 1.8), op=(-1.8, 1.8), clamp=True, name=f"in{pin}", assumed=True,
                    source="Seed3 Table 1: ±1.8 V, applied after the module's coupling cap (the pin itself may sit "
                           "at a DC bias); the codec's 5 kΩ ±20 % from the TAC5242 datasheet stands in for the pin's")
        else:
            # Unpowered codec: its inputs are rated −0.3 V to AVDD + 0.3 V, and AVDD is 0 V.
            p.limit(node, abs=(-0.3, 0.3), clamp=True, name=f"in{pin} (off)", source=TAC)

    # Audio outputs: 1 Vrms full scale. Output impedance and coupling aren't published: 50 Ω, DC-coupled, is assumed
    # (DC coupling is the worse case for current pushed back into the pin). Line-out minimum load is 600 Ω.
    for pin in ("18", "19"):
        drv = p.drive(pin, p.tone(1.414) if on else p.dc(0.0), r=50.0, name=f"out{pin}")
        p.min_load(pin, 600.0, exclude=drv, source=TAC)

    modes = {}
    for mode in ("out", "inp", "pullup", "adc"):
        for pin in p.config.get(mode, ()):
            modes[int(pin)] = mode
    for num, mode in sorted(modes.items()):
        port, kind = PINS[num]
        pin = str(num)
        label = f"{num} {port}"
        if mode == "out" and on:
            p.drive(pin, p.wave(0.0, V33[1]), r=40.0, i_max=20e-3, name=f"gpio{num}", assumed=True,
                    source="STM32 GPIO: 40 Ω output resistance and 20 mA per pin assumed (typical STM32 figures, "
                           "not read from DS12556)")
        if mode == "pullup":
            p.res(pin, v33, 40e3, tol=0.25, name=f"pullup{num}")
        # Below VSS, FT pins conduct into their diode to VSS and take up to 5 mA; TT_a pins take none.
        clamp = None if kind.startswith("TT") else "lo"
        if mode == "adc":
            # In analog mode no pin is 5 V tolerant: VDDA + 0.3 V (ST AN4899 §5.2.2, not in DS12556 itself).
            hi = 4.0 if kind.startswith("TT") else (v33, 0.3)
            p.limit(pin, abs=(-0.3, hi), clamp=clamp, inject=5e-3, name=label,
                    source=STM32 + ("" if kind.startswith("TT") else "; VDDA + 0.3 V in analog mode is from ST "
                                    "AN4899 §5.2.2, quoted on the ST forum, not DS12556"),
                    assumed=not kind.startswith("TT"))
            if on:
                # The ADC reads 0..VREF+ (DS12556 Table 85), and VREF+ is the module's 3.3 V rail.
                p.limit(pin, op=(0.0, V33[0]), name=label, assumed=True,
                        source="ADC range 0..VREF+ (DS12556 Table 85); the 3.3 V rail's ±3 % tolerance is assumed")
        elif kind.startswith("TT"):
            p.limit(pin, abs=(-0.3, 4.0), name=label, source=STM32)
        else:
            # FT: the module datasheet allows 0..5 V on its GPIO; unpowered, the STM32 allows VDD + 4.0 V = 4.0 V.
            p.limit(pin, abs=(-0.3, 5.0 if on else 4.0), clamp=clamp, inject=5e-3, name=label,
                    source=SOURCE + "; " + STM32)
