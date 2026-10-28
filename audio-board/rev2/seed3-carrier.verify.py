"""What the Seed3 carrier's connectors can see, which rails are up, how the Daisy's pins are set, and the numbers
DESIGN.md depends on. Checked by tools/kicad/circuit_verify.py:

    python3 tools/kicad/circuit_verify.py audio-board/rev2/seed3-carrier.kicad_sch

Every source below is an assumption about the outside world. When one changes (a new display, a different speaker
amp, a pedal now in scope), change it here and re-run the check.
"""
from circuit_spec import Gain, I, Spec, V, dc, load, open_, tone, wave

spec = Spec()

# ------------------------------------------------------------------------------------------------------------- rails

spec.rail("+5V", dc(4.70, 5.25))      # 5V_IN at 4.75–5.25 V through Q1, which drops tens of mV

# Firmware pin modes (DESIGN.md "Firmware requirements" and "Daisy pins").
spec.config("A1", out=[14, 28], inp=[15], pullup=[23], adc=[22, 25])

# -------------------------------------------------------------------------------------------------------- connectors

FIVE_V = dict(r=0.1)                  # a stray wire from the power board's 5 V output

# J6, power board. Pin 1 feeds +5V through Q1: while the rail is on, the rail stands for it, so the port is open.
spec.port("J6.1", nominal=open_(), note="5V_IN")
spec.port("J6.3", nominal=dc(0, 3.3, r=1e3, label="battery level, 0–3.3 V"),
          misuse=[dc(4.75, 5.25, label="5 V wire on BAT", **FIVE_V)])
spec.port("J6.4", nominal=dc(0, 5.25, r=10e3, label="power board's pull-up, ≤ 5 V"),
          misuse=[dc(4.75, 5.25, label="5 V wire on MUTE", **FIVE_V)])

# J3, display UART: 3.3 V logic. The display's RX input is high impedance with protection diodes to its own rails.
DISPLAY_RX = open_(clamp=(-0.5, 3.8), i_max=1e-3, label="display RX, powered")
spec.port("J3.2", nominal=DISPLAY_RX, misuse=[dc(4.75, 5.25, label="5 V wire on TX", **FIVE_V)])
spec.port("J3.3", nominal=wave(0, 3.3, r=50, label="display TX"),
          misuse=[dc(4.75, 5.25, label="5 V wire on RX", **FIVE_V)])

# J5, speaker amp's differential input (≥ 10 kΩ per leg).
spec.port("J5.1", nominal=load(10e3, label="amp input"),
          misuse=[dc(0, r=0.01, label="LINE+ shorted"), dc(4.75, 5.25, label="5 V wire on LINE+", **FIVE_V)])
spec.port("J5.2", nominal=load(10e3, label="amp input"),
          misuse=[dc(4.75, 5.25, label="5 V wire on LINE−", **FIVE_V)])

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

# ------------------------------------------------------------------------------------------------------------ claims

spec.claim("AUX peak at the Daisy", V("/AUDIO_IN_2"), lo=-1.15, hi=1.15, cases=["on", "daisy out"],
           source="DESIGN.md AUX input: 'R5 sets the level, whatever the Daisy's input impedance is': ±1.13 V nominal, "
                  "±1.14 V with 1 % resistors")
spec.claim("AUX level, both channels", Gain(["J2.3", "J2.2"], "/AUDIO_IN_2", 1e3), lo=-11.7, hi=-10.3, cases="on",
           source="DESIGN.md AUX input, Level: −11.5 / −10.9 / −10.5 dB with the codec at 4k / 5k / 6k")
spec.claim("AUX level, one channel", Gain("J2.3", "/AUDIO_IN_2", 1e3), lo=-17.7, hi=-16.2, cases="on",
           source="DESIGN.md AUX input, Level: one channel alone, a gain of 0.14 (−16.9 dB)")
spec.claim("Guitar loss to the codec", Gain("J1.T", "A1:in16", 1e3), lo=-1.2, hi=-0.6, cases="on",
           source="DESIGN.md Guitar input: 'R20 costs ≈ 0.8 dB'")
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
