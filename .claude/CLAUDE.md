# Working rules for this repo

## Token economy (usage is limited: weekly reset Tue 16:00 UTC, monthly usage-credit cap)
- Do the work inline. Spawn subagents only for truly parallel work; when you do, use `model: haiku` or `sonnet`.
- No web research unless a fact is version-sensitive (firmware versions, MIDI specs). One targeted search beats several broad ones; scrape at most 1-2 pages.
- Don't re-read files already in context. Don't paste large outputs; use `head`/`grep`.
- Keep replies short: what was done, what's next, what's needed from the user.
- Don't switch models or add MCP servers mid-session (it invalidates the prompt cache).

## Hardware work (Teenage Engineering OP-XY, TX-6, Tracker Mini; Roland AIRA Compacts)
- Devices are on the user's own computer over USB. A cloud session cannot see them: run Claude Code locally, or attach the computer's folder via Remote Control.
- Pattern: put device scripts in `tools/` (see `tools/aira_local.py`); the user runs them on their machine.
- Never send data to a device that is in firmware-update/bootloader mode except with the vendor's official updater.
- Back up device contents to the computer and verify the copy (file count + sizes) before deleting anything on a device.

## Sample naming (OP-XY multisamples)
- lowercase, hyphen-separated: `<role>-<source>-<character>`
  - role: bass, lead, pad, keys, pluck, stab, drum, fx, vox
  - source: moog, prof (Prophet), juno, jup, dx7, generic-wavetable, generic-analog, etc.
  - character: short, long, stab, warm, bright, acid, sub, ...
- e.g. `bass-moog-short-stab`, `pad-prof-long-warm`, `lead-generic-wavetable-bright`

## Current project
- OP-XY rebuild: follow `tools/opxy_plan.md` (goal, order of steps, curation and naming rules).
