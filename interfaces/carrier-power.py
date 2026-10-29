"""The contract between the Seed3 carrier (audio-board/rev2) and the power board, at the carrier's J6 and J5.

Both boards' circuit-check specs load this file. The carrier takes its assumptions about the power board from it, and
checks the signals it drives itself against it (spec.provides). The power board's spec, once it has a schematic, will
do the same the other way round. Change a number here, rerun tools/kicad/circuit_verify.py on both boards, and each
board sees whether it still holds its side. power-board/README.md explains each line.
"""
from circuit_spec import Interface, dc, load, tone

interface = Interface("carrier–power board")

# Driven by the power board.
interface.signal("5V", by="power board", source=dc(4.75, 5.25),
                 note="power-board/README.md, 5 V supply: 5.0 V ± 5 % at J6, never above 5.5 V")
interface.signal("BAT", by="power board", source=dc(0, 3.3, r=(0, 10e3), label="battery level"),
                 note="power-board/README.md, Battery level: 0–3.3 V, source impedance 10 kΩ or less")
interface.signal("MUTE pull-up", by="power board", source=dc(0, 5.25, r=(4.7e3, 1e6), label="mute pull-up"),
                 note="power-board/README.md, Mute: pull-up of 4.7 kΩ or more to at most the 5 V rail")
interface.signal("LINE+ load", by="power board", source=load((10e3, 1e6), label="speaker amp input"),
                 note="power-board/README.md, Input impedance: 10 kΩ or more per leg")
interface.signal("LINE- load", by="power board", source=load((10e3, 1e6), label="speaker amp input"),
                 note="power-board/README.md, Input impedance: 10 kΩ or more per leg")

# Driven by the carrier.
interface.signal("LINE+", by="carrier", source=tone(1.5, r=(0, 1.1e3)),
                 note="power-board/README.md, Input: full scale ≈ 1 Vrms from a ≈ 1 kΩ source, ≈ 0 V DC")
interface.signal("LINE-", by="carrier", source=dc(-0.01, 0.01, r=(0, 1.1e3)),
                 note="power-board/README.md, Input: LINE− is the carrier's ground through 1 kΩ")
