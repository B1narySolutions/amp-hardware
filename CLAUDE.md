# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Hardware for a capstone guitar amp, in KiCad 10:
- `audio-board/rev2/` is the audio board: a Daisy Seed3 (A1, socketed) with the guitar and AUX inputs, the headphone
  amp (U2, MAX9722A) and screw terminals to the power board and display. It is a 2-layer board, hand-soldered with an
  iron, with every part from DigiKey (`seed3-carrier-digikey.csv` is the order). Rev 2 has been ordered.
- `power-board/` is the power board, rev 1, ordered (`Rev1_Power_Board.kicad_pro`, designed by a teammate; its order is
  `DigiKey_Import.csv`). Its README is the contract with the audio board: everything the audio board expects
  from it, and what the audio board promises back.
- `audio-board/rev3/` is rev 3: audio rev 2 and power rev 1 on one 4-layer board (same `seed3-carrier` file names). Sheet 1
  is rev 2's audio sheet; sheet 2, `power.kicad_sch`, is power rev 1 with designators +100. Not ordered: its open items
  wait for the bring-up of the ordered rev 2 and rev 1 boards. Its own `DESIGN.md`, `CHANGES.md`, `TEST_PLAN.md` and
  order live in the folder.

The repo has no scripts of its own. Every view, check, edit and export goes through KiCad's own interfaces
(`kicad-cli`, jobsets, the IPC API), following the skills from
[roccoagain/kicad-agent-skills](https://github.com/roccoagain/kicad-agent-skills): `kicad-view`, `kicad-check`,
`kicad-schematic`, `kicad-board-edit`, `kicad-placement`, `kicad-routing`, `kicad-library`, `kicad-part-selection`,
`kicad-design-review`, `kicad-simulate`, `kicad-fab-export`, `kicad-assembly-export`, `kicad-bringup` and `kicad-new-project`.
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

For rev 3, use the same commands with `audio-board/rev3/`. Its jobset also plots In1.Cu and In2.Cu. Rev 3 also has JLC
assembly files (`kicad-assembly-export` skill): after the fab zip, run `jlc-assembly.kicad_jobset`, then the skill's
`jlc_asm.py cpl` and `check` on `fab/assembly/`, and commit them with the board.

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
- **`amp-digikey-order.csv`** (repo root) is one build of both boards in a single DigiKey order (ordered
  2026-11-05), built from the audio board's order and the power board's parts, with its experiment parts. Its Notes column
  says where a line differs from the original part (a stock substitute, a renumbered DigiKey listing).
- **`power-board/DigiKey_Import.csv`** is the power board's share of that order, one build, with DigiKey numbers.
  The power board's schematic MPN/Manufacturer fields match it, substitutes included: assemble from these, not
  from the original part choices.
  `amp-digikey-cart.csv` is generated from it (Quantity, Digi-Key Part Number, Customer Reference of 48 characters at
  most). Update both when either board's parts change. DigiKey API credentials are in
  `~/.config/digikey/credentials` (`DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET`); never print them.
- **Rev 3's documents** (`audio-board/rev3/`) follow the same rules for rev 3: `DESIGN.md` (with its "Decisions"),
  `CHANGES.md` (the net difference from audio rev 2 and power rev 1), `TEST_PLAN.md`, and `seed3-carrier-digikey.csv`
  plus its cart file (one build, derived from `amp-digikey-order.csv`). Rev 2's files and `power-board/` describe the
  boards that were ordered; leave them as they are unless those boards change.

**KiCad libraries:** project footprints are in `audio-board/Seed3_Carrier.pretty` and symbols in
`audio-board/seed3-carrier.kicad_sym`. The tables in `rev2/` and `rev3/` reach them through `${KIPRJMOD}/..` (rev 3 also
reaches `power-board/Halliquest_Power.*` through `${KIPRJMOD}/../..`), so a copy of the board elsewhere reports
`lib_footprint_issues` (expected in the kicad-check skill's JLC passes).

## Git workflow

- **Commit straight to `main` and push. Don't open PRs.** `main` isn't protected, and there's one committer.
- **Parallel sessions in worktrees** can't check out `main` (git allows a branch in only one worktree), so each uses a
  short-lived local branch. When its work is done, rebase it on `main`, fast-forward `main` to it
  (`git merge --ff-only`), push, and delete the branch.
- **Run sessions in parallel only when they touch different KiCad files.** `.kicad_pcb` and `.kicad_sch` files merge
  badly, so work on the same board or schematic goes one session at a time, on `main`.

## Working rules

- **After a schematic or board change,** run ERC, DRC with parity, and the JLC passes (`kicad-check` skill; it picks the
  2-layer or multilayer rule files from the board), and put the results in the commit message: errors, warnings, and
  anything new. After a board change, re-export the fab zip with the jobset and commit it in the same commit.
- **Don't accept a finding on your own.** A design-review finding or a DRC exclusion becomes accepted only when the user
  agrees, or when DESIGN.md already records the decision.
- **Board edits** go through the IPC API (`kicad-board-edit` skill), from throwaway scripts in the scratchpad. Never
  commit an edit script: replaying it later would undo newer work. Schematic changes reach the board (new parts,
  values, fields) with the skill's `board.py sync`, run with the board closed; run it too after any API session
  that rotated a part, which drops the part's 3D model.
- **Rev 3's sheet 2 is a sub-sheet.** `sch.py` numbers and paths new symbols as if the file were the root: after adding a
  part to `power.kicad_sch`, set its reference by hand (the next free +100 number) and its instance path to
  `/<root uuid>/<sheet uuid>` (copy them from a neighbouring symbol), then run ERC on the root sheet.
- **Expected DRC warnings:** rev 2 has 21 `silk_edge_clearance` warnings from the edge-mounted connectors (J1–J6); rev 3
  has 32 (J1, J2, J4, J102, J105, J106, J107, J3, SW101). Don't trim their footprints to clear them. The JLC
  recommended pass also flags the test points' silk circles (0.14 mm from their pads, JLC prefers 0.15 mm) and stock
  footprints' 0.12 mm silk lines; on rev 3 also 47 texts under 1.0 mm (0.8 mm references and legends in the dense areas) and U101's
  footprint silk over its own pad.
  All print fine. The JLC limits pass reports nothing else on either board.
- **Never power rev 3 from 5 V alone on J107.** With the battery side off, the 5 V drives U101's SDZ and MUTE above its
  PVCC + 0.3 V rating. Bench supplies go on J101 (12 V, current-limited) with the DFR0571 connected (rev 3 DESIGN.md,
  "Decisions").
