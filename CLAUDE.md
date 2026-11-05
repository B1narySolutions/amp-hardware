# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Hardware for a capstone guitar amp, in KiCad 10:
- `audio-board/rev2/` is the Seed3 carrier: a Daisy Seed3 (A1, socketed) with the guitar and AUX inputs, the headphone
  amp (U2, MAX9722A) and screw terminals to the power board and display. It is a 2-layer board, hand-soldered with an
  iron, with every part from DigiKey (`seed3-carrier-digikey.csv` is the order). Rev 2 has been ordered.
- `power-board/` is the power board, rev 1 (`Rev1_Power_Board.kicad_pro`, designed by a teammate; its order is
  `DigiKey_Import.csv`). Its README is the contract with the carrier: everything the carrier expects
  from it, and what the carrier promises back.

The repo has no scripts of its own. Every view, check, edit and export goes through KiCad's own interfaces
(`kicad-cli`, jobsets, the IPC API), following the skills from
[roccoagain/kicad-agent-skills](https://github.com/roccoagain/kicad-agent-skills): `kicad-view`, `kicad-check`,
`kicad-board-edit`, `kicad-placement`, `kicad-schematic`, `kicad-fab-export` and `kicad-design-review`. They're
installed per machine, not in this repo. **If they aren't available** (no `kicad-check` skill listed), tell the user
and offer to install them (needs Node.js):
`npx skills add roccoagain/kicad-agent-skills -g -a claude-code codex --skill '*' -y`. Improve a skill in that repo,
not here (its README covers linking a clone for editing).
The user doesn't open KiCad: Claude launches and quits the PCB editor itself when an edit needs it.

## Commands

`kicad-cli` isn't on PATH: `K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`.

```bash
# Schematic and board checks (kicad-check skill; it also has the JLC passes and the checklist DRC can't do)
"$K" sch erc --severity-error --severity-warning -o <scratch>/erc.rpt audio-board/rev2/seed3-carrier.kicad_sch
"$K" pcb drc --refill-zones --schematic-parity --severity-all -o <scratch>/drc.rpt audio-board/rev2/seed3-carrier.kicad_pcb

# The fab zip: DRC gate, then the project's jobset writes audio-board/rev2/fab/B1NARY_SOLUTIONS_gerber.zip
"$K" pcb drc --severity-error --exit-code-violations --refill-zones --schematic-parity \
     -o <scratch>/gate.rpt audio-board/rev2/seed3-carrier.kicad_pcb \
  && "$K" jobset run --stop-on-error -f audio-board/rev2/jlc-fab.kicad_jobset audio-board/rev2/seed3-carrier.kicad_pro

# Look at it (kicad-view skill): read the PDFs with the Read tool
"$K" sch export pdf -o <scratch>/sch.pdf audio-board/rev2/seed3-carrier.kicad_sch
"$K" pcb export pdf --mode-single --scale 0 -l F.Cu,F.SilkS,F.Mask,Edge.Cuts -o <scratch>/top.pdf \
     audio-board/rev2/seed3-carrier.kicad_pcb
```

## How the pieces fit together

**Documents must agree with each other and with the design.** Keep these in step when one changes:
- **`audio-board/rev2/DESIGN.md`** is the current design and the reasons for it, not its history. "What each connector
  can see" is the environment a design review checks against (`kicad-design-review` skill). Decisions the user accepts
  are recorded in it, with the reason.
- **`audio-board/TEST_PLAN.md`**: its expected readings (stages 1 and 2) must match the schematic. Recheck the
  affected readings after a schematic change.
- **`power-board/README.md`** is the contract with whoever designs the power board. Ask before changing a number in
  it, and change DESIGN.md with it.
- **`audio-board/rev2/CHANGES.md`** records only the net difference from rev 1.
- **`seed3-carrier-digikey.csv`** is the order. The schematic's MPN/DigiKey fields are its source.
- **`amp-digikey-order.csv`** (repo root) is one build of both boards in a single DigiKey order, built from the
  carrier's order and the power board's schematic and `DigiKey_Import.csv`, with its experiment parts. Its Notes column
  says where a line differs from those sources (a stock substitute, a renumbered DigiKey listing).
  `amp-digikey-cart.csv` is generated from it (Quantity, Digi-Key Part Number, Customer Reference of 48 characters at
  most). Update both when either board's parts change. DigiKey API credentials are in
  `~/.config/digikey/credentials` (`DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET`); never print them.

**KiCad libraries:** project footprints are in `audio-board/Seed3_Carrier.pretty` and symbols in
`audio-board/seed3-carrier.kicad_sym`. The tables in `rev2/` reach them through `${KIPRJMOD}/..`, so a copy of the
board outside `rev2/` reports `lib_footprint_issues` (expected in the kicad-check skill's JLC passes).

## Git workflow

- **Commit straight to `main` and push. Don't open PRs.** `main` isn't protected, and there's one committer.
- **Parallel sessions in worktrees** can't check out `main` (git allows a branch in only one worktree), so each uses a
  short-lived local branch. When its work is done, rebase it on `main`, fast-forward `main` to it
  (`git merge --ff-only`), push, and delete the branch.
- **Run sessions in parallel only when they touch different KiCad files.** `.kicad_pcb` and `.kicad_sch` files merge
  badly, so work on the same board or schematic goes one session at a time, on `main`.

## Working rules

- **After a schematic or board change,** run ERC, DRC with parity, and the JLC passes (`kicad-check` skill), and put
  the results in the commit message: errors, warnings, and anything new. After a board change, re-export the fab zip
  with the jobset and commit it in the same commit.
- **Don't accept a finding on your own.** A design-review finding or a DRC exclusion becomes accepted only when the user
  agrees, or when DESIGN.md already records the decision.
- **Board edits** go through the IPC API (`kicad-board-edit` skill), from throwaway scripts in the scratchpad. Never
  commit an edit script: replaying it later would undo newer work. New footprints use KiCad's bundled `pcbnew` module
  with the board closed, as the skill describes.
- **Expected DRC warnings:** 21 `silk_edge_clearance` warnings come from the edge-mounted connectors (J1–J6). Don't
  trim their footprints to clear them. The JLC recommended pass also flags TP1's silk circle (0.14 mm from its pad,
  JLC prefers 0.15 mm) and stock footprints' 0.12 mm silk lines. Both print fine.
