# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Hardware for a capstone guitar amp, in KiCad 10:
- `amp-board/` is **the amp board**, the only live design: a Daisy Seed3 (A1, socketed) with the guitar and AUX inputs,
  the headphone amp (U2, TPA6130A2), the battery input, the 5 V distribution and the class D speaker amp (U101,
  TPA3118D2), on one 4-layer board that JLC assembles. Sheet 1 (`amp-board.kicad_sch`) is the audio circuit; sheet 2
  (`power.kicad_sch`) is the power section, with designators from 101. Not ordered yet; its order doesn't wait for
  the legacy boards (DESIGN.md, "Decisions"). It is its own design: change
  its parts and circuits freely.
- `legacy/` holds the two boards it grew out of, **frozen as ordered** (2026-11-05): `legacy/audio-board/rev2/` (2-layer,
  hand-soldered, MAX9722A headphone amp), `legacy/power-board/` (rev 1, designed by a teammate) and their joint DigiKey
  order. Don't edit anything under `legacy/` unless the user asks or a bring-up result has to be written into their
  test plan. Nothing in `amp-board/` has to match them or wait for them. Their bring-up results inform the amp board's next revision.

The repo has no scripts of its own. Every view, check, edit and export goes through KiCad's own interfaces
(`kicad-cli`, jobsets, the IPC API), following the skills from
[roccoagain/kicad-agent-skills](https://github.com/roccoagain/kicad-agent-skills): `kicad-view`, `kicad-check`,
`kicad-schematic`, `kicad-board-edit`, `kicad-placement`, `kicad-routing`, `kicad-library`, `kicad-part-selection`,
`kicad-schematic-review`, `kicad-layout-review`, `kicad-simulate`, `kicad-fab-export`, `kicad-assembly-export`, `kicad-bringup` and `kicad-new-project`.
They're installed per machine, not in this repo. **If they aren't available** (no `kicad-check` skill listed), tell the
user and offer to install them (needs Node.js):
`npx skills add roccoagain/kicad-agent-skills -g -a claude-code codex --skill '*' -y`. Improve a skill in that repo,
not here (its README covers linking a clone for editing).
**Don't use KiStack's skills here** (American-Embedded/kistack: `kicad-layout`, `kicad-pcb`, `layout-placement`...,
and its own `kicad-schematic`). They target Backplane's own KiCad build, and its `layout-placement` move script
empties footprints (pads, fields, 3D model) on the stock KiCad 10.0.5 used here. Its names overlap these skills', so
`npx skills list -g` must show `roccoagain/kicad-agent-skills` as the source.
The user doesn't open KiCad: Claude launches and quits the PCB editor itself when an edit needs it.

## Commands

`kicad-cli` isn't on PATH: `K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`. Run these from `amp-board/`.

```bash
# Schematic and board checks (kicad-check skill; it also has the JLC passes and the checklist DRC can't do)
"$K" sch erc --severity-error --severity-warning -o <scratch>/erc.rpt amp-board.kicad_sch
"$K" pcb drc --refill-zones --schematic-parity --severity-all -o <scratch>/drc.rpt amp-board.kicad_pcb

# Look at it (kicad-view skill): read the PDFs with the Read tool
"$K" sch export pdf -o <scratch>/sch.pdf amp-board.kicad_sch
"$K" pcb export pdf --mode-single --scale 0 -l F.Cu,F.SilkS,F.Mask,Edge.Cuts -o <scratch>/top.pdf amp-board.kicad_pcb

# Order files, all written to fab/ (ignored by git): the DRC gate, then the three jobsets
"$K" pcb drc --severity-error --exit-code-violations --refill-zones --schematic-parity \
     -o <scratch>/gate.rpt amp-board.kicad_pcb \
  && "$K" jobset run --stop-on-error -f jlc-fab.kicad_jobset amp-board.kicad_pro \
  && "$K" jobset run --stop-on-error -f jlc-assembly.kicad_jobset amp-board.kicad_pro \
  && "$K" jobset run --stop-on-error -f digikey-order.kicad_jobset amp-board.kicad_pro
```

## Where each fact lives

Each fact has one home. Don't copy it into a second file; point to it.
- **The schematic and board** are the design. Part numbers live in the schematic's `MPN`, `Manufacturer`, `DigiKey`,
  `LCSC` and `Purchase_Note` fields and nowhere else: there is no hand-kept BOM, order or cart file. Changing a part
  means changing its fields (`kicad-part-selection`, `kicad-schematic`), then `board.py sync`.
  - **Values** are the bare value (`100nF`, `10k`); a capacitor's voltage rating is its hidden `Voltage` field.
  - **Ordered parts that aren't on the board** (the Daisy's sockets, J106's mating housing and lead, jumper shunts, the
    panel switch, the DFR0571) are symbols marked "not on board", one per piece: X101–X109 and U102 on sheet 2.
  - **Not in the BOM:** the Daisy (A1) and the test points, which aren't bought.
- **`amp-board/DESIGN.md`** is the reasons: how the board works and why, "What each connector can see" (the environment a
  design review checks against, `kicad-schematic-review` skill), "Decisions" the user accepted, and "Open items". It
  describes the design as it stands, not its history. Git is the history: there is no change list.
- **`amp-board/TEST_PLAN.md`**: its expected readings must match the schematic. After a schematic change, recheck the
  affected readings (`kicad-bringup` skill; `view.py ohms` recomputes stage 1's resistances from the netlist).
- **`amp-board/fab/`** is generated and ignored by git: the Gerber zip, `assembly/` (JLC BOM and CPL) and
  `amp-board-digikey.csv` (the whole DigiKey order, in DigiKey's upload columns). Never edit a file in it; regenerate
  it.
- **`amp-board/lib/`** holds the board's own symbols (`amp-board.kicad_sym`), footprints (`amp-board.pretty`) and 3D
  models. The project's tables reach only it and KiCad's standard libraries, so the folder works when copied anywhere.
- **`legacy/power-board/README.md`** was the contract between the two legacy boards. It binds only them.

DigiKey API credentials are in `~/.config/digikey/credentials` (`DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET`); never
print them.

## Git workflow

- **Commit straight to `main` and push. Don't open PRs.** `main` isn't protected, and there's one committer.
- **Parallel sessions in worktrees** can't check out `main` (git allows a branch in only one worktree), so each uses a
  short-lived local branch. When its work is done, rebase it on `main`, fast-forward `main` to it
  (`git merge --ff-only`), push, and delete the branch.
- **Run sessions in parallel only when they touch different KiCad files.** `.kicad_pcb` and `.kicad_sch` files merge
  badly, so work on the same board or schematic goes one session at a time, on `main`.

## Working rules

Two gates: a light one on every commit, a full one when the board is ordered.

**Every commit that changes the schematic or board:**
- Run ERC and DRC with parity (commands above), and say in the commit message: errors, warnings, and anything new.
- Search the two documents for what changed: the part's reference, its old value, its net name and the numbers derived
  from it (`grep -n -e 'R5\b' -e '3\.3k' amp-board/*.md`). Fix every hit or confirm it still holds.

**When the user orders the board** (ask first; an order is theirs to place):
1. Run the JLC passes (`kicad-check` skill, multilayer rule files) and the three jobsets above, then the
   `kicad-assembly-export` skill's `jlc_asm.py cpl` and `check` on `fab/assembly/`.
2. Check no `Customer Reference` in `fab/amp-board-digikey.csv` is over 48 characters (DigiKey's limit), and check
   stock.
3. Re-render the README's pictures: `"$K" pcb render --use-board-stackup-colors --background transparent --side top
   --quality high --width 1600 --height 1250 -o render/top.png amp-board.kicad_pcb`, and the same with `--side bottom
   --quality basic` for `render/bottom.png` (high quality's floor shadows show the top-side parts through it).
4. Commit, tag the commit `amp-board-vN` (N = the schematic's title-block revision), push the tag, and attach `fab/`'s
   files to a GitHub release of that tag. The tag is the revision: there are no revision
   folders. Raise the title-block revision in the first commit after an order.

**Always:**
- **Datasheet claims cite where they were checked.** Before writing that a datasheet "doesn't state" something, or asking
  the user to measure it, read the datasheet itself, figures included (text extraction skips drawings: read those pages
  as images), and name the table or figure.
- **Don't accept a finding on your own.** A design-review finding or a DRC exclusion becomes accepted only when the user
  agrees, or when DESIGN.md already records the decision.
- **Board edits** go through `board.py` or the IPC API (`kicad-board-edit` skill), from throwaway scripts in the
  scratchpad. Never commit an edit script: replaying it later would undo newer work. Schematic changes reach the board
  (new parts, values, fields) with the skill's `board.py sync`, run with the board closed; run it too after any API
  session that rotated a part, which drops the part's 3D model.
- **Sheet 2 is a sub-sheet.** `sch.py` gives a new symbol there the right instance path, but numbers it from 1: after
  adding a part to `power.kicad_sch`, pass or set its reference by hand (the next free number from 101), then run ERC
  on the root sheet (ERC on `power.kicad_sch` alone reports its sheet pins as unconnected).
- **Expected DRC warnings:** 29 `silk_edge_clearance` warnings from the edge-mounted connectors (J1, J2, J4, J102,
  J105, J106, J107, J3, SW101). Don't trim their footprints to clear them. The JLC recommended pass also flags the test
  points' silk circles (0.14 mm from their pads, JLC prefers 0.15 mm), 71 texts under 1.0 mm (0.8 mm references and
  legends in the dense areas) and U101's footprint silk over its own pad. All print fine. The JLC limits pass reports
  nothing else.
- **Never power the amp board from 5 V alone on J107.** With the battery side off, the 5 V feeds PVCC through R107–R110
  and D102/D103 and leaves U101 at its 4.5 V minimum supply with SDZ high. Bench supplies go on J101 (12 V,
  current-limited) with the DFR0571 connected (DESIGN.md, "Decisions").
