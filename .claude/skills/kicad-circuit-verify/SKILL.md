---
name: kicad-circuit-verify
description: Check a KiCad schematic's electrical stress and design claims with tools/kicad/circuit_verify.py. It works out worst-case voltage and current bounds for everything the board's spec says can reach its connectors (power states, misuse such as a wire on the wrong terminal, part tolerances), then checks every pin's absolute maximum and operating range, protection-diode currents, resistor power, capacitor voltage, MOSFET current, output loads and the claims DESIGN.md depends on. Results the bounds can't settle are simulated in ngspice to find a counterexample. It also checks interface contracts between boards and the test plan's expected readings, and circuit_faults.py injects assembly faults (opens, shorts, wrong values, solder bridges from the PCB) to show what each damages and whether the test plan catches it. Use after any schematic change, when adding or changing a part, when the user asks whether an input can see too much voltage or whether a design survives a fault, and before ordering a board.
---

# Check a schematic against its parts' limits and the design's claims

```bash
python3 tools/kicad/circuit_verify.py <board>.kicad_sch            # problems first, then the checks closest to failing
python3 tools/kicad/circuit_verify.py <board>.kicad_sch -v         # every check, plus each assumed datasheet value
python3 tools/kicad/circuit_verify.py <board>.kicad_sch --case "on*" --nets   # one state's cases and every net's range
python3 tools/kicad/circuit_verify.py <board>.kicad_sch --sim-out <scratch>/cx  # save each counterexample as SPICE
python3 tools/kicad/circuit_faults.py <board>.kicad_sch           # assembly faults: damage and test-plan coverage
python3 tools/kicad/test_circuit_verify.py                         # the engine's and simulator's own tests
```

It needs `<board>.verify.py` next to the schematic (the spec) and a model in `tools/kicad/parts/` for every part that isn't
a resistor, capacitor or connector. `tools/kicad/README.md` ("Circuit check") documents both. It never modifies anything.
Exit status 1 means at least one FAIL or UNPROVEN. It takes about 20 s on the Seed3 carrier; `--no-sim` skips the
simulation.

Reading the result:
- **FAIL** is real within the spec and the models. The bound is tight: some source inside the spec, at some tolerance
  corner, reaches it. Give the user the check, the value, the limit and the case (power state + misuse). Explain what
  physically happens, and propose a fix (a series resistor, a clamp, a different part) or a spec change if the spec is
  what's wrong.
- **FAIL with "simulation breaks it"** comes from the ngspice search: the note gives the input that breaks the limit.
  It's a real counterexample within the models. Report it like any FAIL, with that input.
- **SEARCHED** means the bound crossed the limit but no simulated input did. Give the worst simulated value next to the
  bound, and call it evidence rather than proof. It doesn't fail the exit status.
- **UNPROVEN** is left only when simulation didn't run (`--no-sim`, no ngspice, or a quantity it can't measure). Say the
  bound is pessimistic, and that simulating it would settle the question. Don't present it as a failure.
- **test plan** FAILs mean the test plan's expected reading no longer matches the schematic. Say which reading, what
  the schematic gives, and propose the corrected line in TEST_PLAN.md.
- **contract** FAILs mean this board breaks a promise in `/interfaces/`. Either the board or the contract has to change,
  and the contract is shared with the other board's team: ask before editing it.
- Fault check: lead with the damaging faults the test plan doesn't catch, then its suggested readings. Present those as
  proposed TEST_PLAN additions for the user to accept. Say so when a fault is "possible" (outside a part's model).
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
