---
name: kicad-circuit-verify
description: Check a KiCad schematic's electrical stress and design claims with tools/kicad/circuit_verify.py. It works out worst-case voltage and current bounds for everything the board's spec says can reach its connectors (power states, misuse such as a wire on the wrong terminal, part tolerances), then checks every pin's absolute maximum and operating range, protection-diode currents, resistor power, capacitor voltage, MOSFET current, output loads and the claims DESIGN.md depends on. Use after any schematic change, when adding or changing a part, when the user asks whether an input can see too much voltage or whether a design survives a fault, and before ordering a board.
---

# Check a schematic against its parts' limits and the design's claims

```bash
python3 tools/kicad/circuit_verify.py <board>.kicad_sch            # problems first, then the checks closest to failing
python3 tools/kicad/circuit_verify.py <board>.kicad_sch -v         # every check, plus each assumed datasheet value
python3 tools/kicad/circuit_verify.py <board>.kicad_sch --case "on*" --nets   # one state's cases and every net's range
python3 tools/kicad/test_circuit_verify.py                         # the engine's own tests
```

It needs `<board>.verify.py` next to the schematic (the spec) and a model in `tools/kicad/parts/` for every part that isn't
a resistor, capacitor or connector. `tools/kicad/README.md` ("Circuit check") documents both. It never modifies anything.
Exit status 1 means at least one FAIL or UNPROVEN.

Reading the result:
- **FAIL** is real within the spec and the models. The bound is tight: some source inside the spec, at some tolerance
  corner, reaches it. Give the user the check, the value, the limit and the case (power state + misuse). Explain what
  physically happens, and propose a fix (a series resistor, a clamp, a different part) or a spec change if the spec is
  what's wrong.
- **UNPROVEN** means the static bound goes through a clamp or an amplifier at its rail, where it is pessimistic. Say so,
  give the bound, and note that a simulation would settle it. Don't present it as a failure.
- Results marked as using an assumed value depend on a number the datasheet doesn't give. `-v` lists them with the
  reason. Mention this when one decides a result.

Rules:
- Don't add a waiver on your own. A waiver records a decision: suggest one, with the reason, and add it only when the
  user agrees or DESIGN.md already records the decision (cite the section in the reason).
- Don't change a port's environment to make a check pass. The spec states what the outside world can do; change it only
  when the user says the assumption was wrong.
- When adding a part model, take every number from the datasheet. Put the section in `source=`; mark anything you had to
  assume with `assumed=True` and say why. Add a test to `test_circuit_verify.py` when you change the engine.
- When a claim in the spec stops matching DESIGN.md, or a check shows a DESIGN.md number is off, tell the user. Update
  DESIGN.md only if they want it.
