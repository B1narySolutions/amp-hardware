"""What the Seed3 carrier's connectors can see, which rails are up, how the Daisy's pins are set, and the numbers
DESIGN.md depends on. Checked by tools/kicad/circuit_verify.py:

    python3 tools/kicad/circuit_verify.py audio-board/rev2/seed3-carrier.kicad_sch

Every source below is an assumption about the outside world. When one changes (a new display, a different speaker
amp, a pedal now in scope), change it here and re-run the check.
"""
from circuit_spec import Gain, I, Interface, Spec, V, dc, load, open_, tone, wave

spec = Spec()

# What the power board promises at J6 and J5, and what the carrier promises back: shared with the power board's spec.
power = Interface.load("../../interfaces/carrier-power.py")

# ------------------------------------------------------------------------------------------------------------- rails

supply = power.source("5V")
spec.rail("+5V", dc(supply.lo - 0.05, supply.hi))      # 5V_IN through Q1, which drops tens of mV

# Firmware pin modes (DESIGN.md "Firmware requirements" and "Daisy pins").
spec.config("A1", out=[14, 28], inp=[15], pullup=[23], adc=[22, 25])

# -------------------------------------------------------------------------------------------------------- connectors

FIVE_V = dict(r=0.1)                  # a stray wire from the power board's 5 V output

# J6, power board. Pin 1 feeds +5V through Q1: while the rail is on, the rail stands for it, so the port is open.
spec.port("J6.1", nominal=open_(), note="5V_IN")
spec.port("J6.3", nominal=power.source("BAT"), misuse=[dc(4.75, 5.25, label="5 V wire on BAT", **FIVE_V)])
spec.port("J6.4", nominal=power.source("MUTE pull-up"), misuse=[dc(4.75, 5.25, label="5 V wire on MUTE", **FIVE_V)])

# J3, display UART: 3.3 V logic. The display's RX input is high impedance with protection diodes to its own rails.
DISPLAY_RX = open_(clamp=(-0.5, 3.8), i_max=1e-3, label="display RX, powered")
spec.port("J3.2", nominal=DISPLAY_RX, misuse=[dc(4.75, 5.25, label="5 V wire on TX", **FIVE_V)])
spec.port("J3.3", nominal=wave(0, 3.3, r=50, label="display TX"),
          misuse=[dc(4.75, 5.25, label="5 V wire on RX", **FIVE_V)])

# J5, the speaker amp's differential input. The carrier drives it, and checks what it drives against the contract.
spec.port("J5.1", nominal=power.source("LINE+ load"),
          misuse=[dc(0, r=0.01, label="LINE+ shorted"), dc(4.75, 5.25, label="5 V wire on LINE+", **FIVE_V)])
spec.port("J5.2", nominal=power.source("LINE- load"), misuse=[dc(4.75, 5.25, label="5 V wire on LINE−", **FIVE_V)])
spec.provides(power, {"LINE+": "J5.1", "LINE-": "J5.2"}, cases="on")

# Audio sources are tones (sines anywhere in 20 Hz–20 kHz): music has no DC or long steps. A wave(...) source instead
# covers any waveform, steps included, which is harsher behind a coupling cap (C2 can then double the swing).

# J1, guitar. Passive pickups only; a boost pedal is out of scope, so it is misuse that must not damage anything.
spec.port("J1.T", nominal=tone(1.5, r=10e3, label="hot passive pickups, 3 Vpp"),
          misuse=[tone(9, r=1e3, label="18 V boost pedal at full output")], exposed=True)

# J2, AUX: a phone or laptop headphone output, the same signal on both channels at worst.
spec.port("J2.3", nominal=tone(2.83, r=1, label="2 Vrms laptop, tip"),
          misuse=[tone(5, r=10, label="pro line out at full level, ±5 V")], exposed=True)
spec.port("J2.2", nominal=tone(2.83, r=1, label="2 Vrms laptop, ring"),
          misuse=[tone(5, r=10, label="pro line out at full level, ±5 V")], exposed=True)

# J4, headphones (16 Ω or more), and its plug-detect switch to GND.
spec.port("J4.3", nominal=load(16, label="16 Ω headphones"), exposed=True)
spec.port("J4.2", nominal=load(16, label="16 Ω headphones"), exposed=True)
spec.port("J4.6", nominal=[open_(label="no plug"), dc(0, r=0.05, label="plug in")])

# ------------------------------------------------------------------------------------------------------ power states

BOARD_OFF = {"J3.2": open_(clamp=(-0.5, 0.5), i_max=1e-3, label="display RX, off"),
             "J3.3": dc(0, r=50, label="display off"),
             "J6.4": dc(0, r=10e3, label="power board off")}

spec.state("on", rails=["+5V"], note="power board on, Daisy running")
spec.state("daisy out", rails=["+5V"], absent=["A1"], misuse=False, note="TEST_PLAN stage 2: powered without the Daisy")
spec.state("usb only", powered=["A1"], ports=BOARD_OFF, misuse=False,
           note="DESIGN.md 'Running from USB alone': flashing on the bench, power board and display off")
spec.state("off", misuse=False, note="everything off; a guitar or phone may still be playing, the display may be on")
spec.state("reversed", ports={"J6.1": dc(-5.25, -4.75, r=0.05, label="5 V and GND swapped")}, misuse=False,
           note="TEST_PLAN 2.12: supply leads swapped")

# Assembly faults (tools/kicad/circuit_faults.py) are checked with the board on.
spec.fault_states = ["on"]

# ---------------------------------------------------------------------------------------------------------- test plan
# TEST_PLAN.md stages 1 and 2, the checks made before the Daisy goes in. The circuit check reads each expected value off
# the schematic; the fault check works out which assembly faults each reading catches. The schematic doesn't model the
# jacks' switches, so only the readings with them open are here (1.10 with a plug in J1, 1.13 with none in J4), and
# 1.21c is a diode test.
stage1 = spec.test_stage("TEST_PLAN stage 1", absent=["A1"])
stage1.measure("1.1", "+5V", "GND", expect=(1e3, None), note="> 1 kΩ, not < 50 Ω")
stage1.measure("1.2", "J6.1", "GND", expect="open")
stage1.measure("1.3", "J6.2", "GND", expect="short")
stage1.measure("1.3", "J3.1", "GND", expect="short")
stage1.measure("1.4", "/VREF", "GND", expect=(5e3, 10e3))
stage1.measure("1.5", "J3.2", "GND", expect="open")
stage1.measure("1.5", "J3.3", "GND", expect=110e3, note="R9 + R24")
stage1.measure("1.6", "C15.1", "+5V", expect="open")
for pin in ("A1.33", "A1.38"):
    stage1.measure("1.7", pin, "GND", expect="open")
    stage1.measure("1.7", pin, "+5V", expect="open")
stage1.measure("1.8", "J4.3", "GND", expect="open")
stage1.measure("1.8", "J4.2", "GND", expect="open")
stage1.measure("1.8", "J4.2", "+5V", expect="open")
stage1.measure("1.10", "J1.T", "GND", expect="open", note="plug in J1, so the tip switch is open")
stage1.measure("1.11", "J2.3", "J2.2", expect=20e3)
stage1.measure("1.12", "J2.3", "GND", expect=10.5e3)
stage1.measure("1.13", "TP1.1", "GND", expect="open", note="no plug in J4")
stage1.measure("1.15", "TP1.1", "A1.23", expect="short")
stage1.measure("1.16", "J5.1", "GND", expect=100e3)
stage1.measure("1.16", "J5.2", "GND", expect=1e3)
stage1.measure("1.17", "J5.1", "A1.19", expect=1e3)
stage1.measure("1.18", "J6.3", "A1.25", expect=10e3)
stage1.measure("1.18", "A1.25", "GND", expect=10e3)
for pin in ("A1.26", "A1.27"):
    stage1.measure("1.19", pin, "GND", expect="open")
    stage1.measure("1.19", pin, "+5V", expect="open")
stage1.measure("1.20", "A1.28", "GND", expect=100e3)
stage1.measure("1.20", "J6.4", "GND", expect="open")
stage1.measure("1.20", "J6.4", "Q2.3", expect=470)
stage1.measure("1.21", "J3.2", "A1.14", expect=10e3)
stage1.measure("1.21", "J3.3", "A1.15", expect=10e3)
stage1.measure("1.21", "A1.15", "GND", expect=100e3)
stage1.measure("1.21a", "A1.22", "GND", expect=(1.0, 100e3), note="below 100 kΩ, not ≈ 0 Ω")
stage1.measure("1.21b", "A1.16", "U1.1", expect=470)

# Stage 2: 5.0 V from a bench supply on J6, the Daisy out, a 10k pull-up to 3.3 V on J6.4 for 2.10.
stage2 = spec.test_stage("TEST_PLAN stage 2", absent=["A1"], rails={"+5V": dc(4.95, 5.0)},
                         ports={"J6.4": dc(3.3, r=10e3, label="10k pull-up to 3.3 V")})
stage2.voltage("2.2", "C5.1", expect=(4.9, 5.0))
stage2.voltage("2.3", "/VREF", expect=(2.45, 2.55))
stage2.voltage("2.4", "U1.1", expect=(2.4, 2.6))
stage2.voltage("2.4", "A1.16", expect=(2.4, 2.6))
stage2.voltage("2.5", "U1.3", expect=(2.4, 2.6))
stage2.voltage("2.6", "C15.1", expect=(1.0, 2.0), note="HPVDD positive")
stage2.voltage("2.6", "C14.1", expect=(-2.0, -1.0), note="HPVSS negative")
stage2.voltage("2.7", "J4.3", expect=(-0.005, 0.005))
stage2.voltage("2.7", "J4.2", expect=(-0.005, 0.005))
stage2.voltage("2.8", "J5.1", expect=(-0.05, 0.05))
stage2.voltage("2.9", "A1.39", expect=(4.9, 5.0))
stage2.voltage("2.9", "A1.22", expect=(2.4, 2.6))
stage2.voltage("2.10", "J6.4", expect=(3.2, 3.4))

# ------------------------------------------------------------------------------------------------------------ claims

spec.claim("AUX peak at the Daisy", V("/AUDIO_IN_2"), lo=-0.25, hi=0.25, cases=["on", "daisy out"],
           source="DESIGN.md AUX input: 'R5 sets the level, whatever the Daisy's input impedance is': ±0.24 V nominal, "
                  "±0.25 V with 1 % resistors")
spec.claim("AUX level, both channels", Gain(["J2.3", "J2.2"], "/AUDIO_IN_2", 1e3), lo=-22.5, hi=-21.6, cases="on",
           source="DESIGN.md AUX input, Level: −22.2 / −22.0 / −21.9 dB with the codec at 4k / 5k / 6k")
spec.claim("AUX level, one channel", Gain("J2.3", "/AUDIO_IN_2", 1e3), lo=-28.5, hi=-27.6, cases="on",
           source="DESIGN.md AUX input, Level: one channel alone, a gain of 0.040 (−28.0 dB)")
spec.claim("Guitar loss to the codec", Gain("J1.T", "A1:in16", 1e3), lo=-1.2, hi=-0.6, cases="on",
           source="DESIGN.md Guitar input: 'R20 costs ≈ 0.8 dB'")
for net in ("/HP_L", "/HP_R"):
    spec.claim(f"Headphone level, {net[4:]}", Gain("A1:out18.src", net, 1e3), lo=-8.6, hi=-7.4, cases="on",
               source="DESIGN.md Headphone output, Level: full scale (1 Vrms) puts ≈ 0.40 Vrms on each output")
spec.claim("5V_SENSE reading", V("/5V_SENSE"), lo=2.30, hi=2.70, cases="on",
           source="DESIGN.md Firmware requirements: reads ≈ 2.4–2.5 V with +5V at 4.85–5.0 V")
spec.claim("VREF", V("/VREF"), lo=2.30, hi=2.70, cases=["on", "daisy out"],
           source="DESIGN.md Mid-rail reference: VREF ≈ 2.5 V")
spec.claim("Display RX current, display off", I("R8"), lo=-0.35e-3, hi=0.35e-3, cases="usb only",
           source="DESIGN.md Display connector: R8 keeps the current into the display's RX diode to ≈ 0.27 mA")
for pin in ("1", "4"):
    for side in "+-":
        spec.claim(f"U2.{pin} protection current, USB only", I(f"U2:{pin}.prot{side}"), hi=0.5e-3, cases="usb only",
                   source="DESIGN.md Running from USB alone: R10 limits the current into U2's protection to ≈ 0.3 mA")

# ----------------------------------------------------------------------------------------------------------- waivers

spec.waive("U2.* abs *", "usb only",
           "DESIGN.md 'Running from USB alone': the firmware keeps both outputs at digital silence while 5V_SENSE "
           "reads low, so pin 18 is quiet whenever U2 is unpowered. The check assumes full scale on pin 18.")
