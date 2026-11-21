# OP-XY rebuild: brief for whoever picks this up (Claude or human)

Read this whole file before acting. It is the user's intent, written down so decisions
can be made without asking. When something here conflicts with a guess, this file wins.
When something is genuinely unclear AND the wrong choice is hard to undo, stop and ask.

## The goal, in the user's words (condensed)
1. **Clean slate on the OP-XY.** Back up everything, wipe the device, update to the
   latest official Teenage Engineering firmware (reliability fixes). Losing custom
   content on the device is fine *because* it is backed up and verified first.
2. **A large, curated sound library** built from the user's best samples and
   multisamples, organized so the names teach what each sound is for.
3. **TX-6 + OP-XY integration.** When the TX-6 (already on its latest firmware) is
   plugged into the OP-XY over USB-C, it should be recognized automatically and its
   6 channels should map to OP-XY tracks 1-6. The stock firmware doesn't do this; the
   user develops on their own OP-XY in dev mode (in cooperation with TE, never
   distributing non-sanctioned firmware) and wants to make it happen.

## Where things stand
- `tools/opxy_prep.py` exists: `backup` (copy + SHA-256 verify) and `inventory`
  (compact TSV of every sample: path, size, seconds, channels, rate). Device is not
  modified by either.
- Not yet done: backup, inventory, curation, wipe, firmware update, load, TX-6 work.

## Steps, in order (don't skip ahead)
1. `python3 tools/opxy_prep.py backup <opxy-mount> <backup-dir>` -> must print `VERIFIED`.
   If it fails, stop. Nothing gets deleted without a verified backup.
2. `python3 tools/opxy_prep.py inventory inv.tsv <backup-dir> <user's other sample folders>`
   Ask the user where their other sample folders are if not known.
3. Curate from `inv.tsv` (read it with head/grep/sort; don't open folders file by file).
   Produce a plan (source path -> new name -> keep/drop) and show the user a short
   summary before copying anything.
4. Wipe the OP-XY user content, then update firmware with TE's official updater.
   Confirm the current official version number at that time (one targeted lookup).
5. Load the curated set onto the OP-XY.
6. TX-6 auto-setup. Ask the user for the dev-mode method/tools they've used before and
   build on that; don't invent a protocol. Back up before any dev-mode change; know the
   restore path before starting.

## Curation rules (how to decide)
- **Priority #1: polyphonic sounds.** This is the gap. Pads, keys, chords, poly stabs,
  brass/strings from poly synths (Prophet, Jupiter, Juno, OB, DX7, CS-80, etc.). Prefer
  multisamples that cover the full keyboard range.
- **Still keep mono sounds**, especially leads and basses that go **above C4**: the
  user's hardware bass synth can't go above C4, so the OP-XY must cover that range.
- Quality over quantity, but the user wants the result *large*. Drop: duplicates,
  near-duplicates, clipped/noisy/truncated files, unclear junk, one-shots that add
  nothing. When torn between two similar sounds, keep the cleaner, more musical one.
- Fill each role (bass, lead, pad, keys, pluck, stab, drum, fx, vox) with variety:
  short vs long, dark vs bright, clean vs dirty.
- Respect OP-XY limits (storage, name length, sample format). Check them; don't guess.

## Naming (the names are a learning tool)
- lowercase, hyphen-separated: `<role>-<source>-<character>`
- role: bass, lead, pad, keys, pluck, stab, drum, fx, vox
- source: be specific and honest. `moog`, `prof` (Prophet), `juno`, `jup` (Jupiter),
  `ob`, `dx7`, `cs80`, `tb303`... If it's not from a known synth, say what it is:
  `generic-wavetable`, `generic-analog`, `generic-fm`, `field`, `acoustic`.
  If the source is unknown, don't make one up: use `generic-<type>`.
- character: what it does musically: `short`, `long`, `stab`, `sub`, `acid`, `warm`,
  `bright`, `dark`, `pluck`, `swell`, `detuned`...
- Examples: `bass-moog-short-stab`, `pad-prof-long-warm`, `lead-generic-wavetable-bright`

## Constraints
- Token budget is limited (see `.claude/CLAUDE.md`): work inline, short replies.
- Never delete from the device without a `VERIFIED` backup. Never touch the original
  sample folders on the computer; copy, don't move.
- Only official TE firmware goes on as the release firmware; dev work stays on the
  user's own unit and is never distributed.
