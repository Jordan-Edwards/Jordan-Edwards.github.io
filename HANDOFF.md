# Handoff: where everything stands

## Morning summary, 12 November (release audit done; fixes in progress)

**Can Build 2 0.2.10 be released as it is? No.** Full audit with evidence: `G:\OPX1_AGENTS_20261110\release\AUDIT.md`. This is an engineering inventory, not legal advice; clearing anything for release needs a lawyer.

- **The OS:** `os.ldr` is TE's stock OP-XY OS 1.2.1 with our changes: 2,372,929 bytes identical to the stock image, 407 bytes changed, 758,520 bytes added. At least 75.8% of the shipped image is TE's OS word for word. The only release form that avoids shipping it is a patcher the user runs on their own copy, and that may still breach TE's terms or anti-circumvention law.
- **The engines:** 20 of the 22 machines run TE's own code: the 8 Field effects, the Field vocoder and 11 synths. Each capsule is the Field's instructions copied byte for byte with only addresses moved, plus tables copied from the Field image. Four capsules (mother, grid, pulse, drwave) also hold copied Analog Devices chip-ROM routines.
- **Screens, presets, names:** 19-20 of 22 screens come from the Field's own SVGs. About 159 presets look like Field factory presets (inferred from names). `op1_factory.json` is TE's catalog file. Names and descriptions say "OP-1 Field" throughout.
- **Ours:** the Scale player, the 16-band Vocoder (own DSP, no Field code), and the non-Field parts of our SDK changes. The SDK is MIT-licensed from the Open-XY contributors, so it is not ours to relicense.
- **Releasable now, subject to a lawyer:** Scale and Vocoder as source. Before that, the Vocoder needs its `field_level.hpp` dependency and the TE font name removed, and its `tools`/`make_tables.py` checked. Our non-Field SDK patches could go upstream under MIT. Also releasable: Dubious (our design) and the Tracker Mini Loops work (Polyend CE licence: share, do not sell).
- **Clean-room route to "same sound, built independently":** specs and audio renders from one side, new DSP written only from those by agents that never see Field code, new art, new names. Estimate: about 6 clean engines plus Scale and Vocoder for a first release, 3-4 months; full parity 9-15 engineer-months. Order and per-engine estimates are in AUDIT.md.

**Nitro: found the cause, and it is not the code** (`G:\OPX1_AGENTS_20261110\nitro-check\REPORT.md`). The capsule is the Field's own process function and matched the exact model with 0 differing samples in the emulator. Nitro's grit comes from driving it hard, and on the OP-XY it is under-driven: the +42 dB Trim default was set by ear for CWO and never measured for Nitro, and the send knob scales its input too (half send = 6 dB less drive). On top of that, at partial send the clean track fills back in what the filter removed: at send 0.3 the effect is 11-13 dB weaker than on the Field. The Field defaults are also nearly an open filter.
- **Try on the device:** send to Nitro at full, Trim +48 or +54 dB, then Feedback or Follow up and Lows/Highs moved inward.
- **Fix once you have heard it:** change Nitro's `trim` default in `definition.json` from 0.681818 (+42 dB) to 0.772727 (+48) or 0.863636 (+54) in a 0.2.11 build. Loudness stays the same and the filter gets 6-12 dB more drive. Very hot tracks may crunch. Not built yet: no point before you have listened.

**Castle: not found.** No file or folder named castle exists in any OP-XY or OPX1 project folder on G:, H: or F:, nor in the SDK's catalog or docs. The only mentions are the Dubious/Hamlet design notes, which describe Castle's look (pixel art, rising flames, the OP-1 vector feel) as a model to imitate. So Castle was most likely a machine from somewhere else (a community build or download), not something built here. Jordan to say where it came from.

**Clean-room rewrite: started (Jordan's decision, 12 November).** Goal: every engine rewritten so it sounds the same but contains no TE code, data or art, so it can be released.
- The wall: `G:\CLEANROOM-DIRTY\<engine>` is the spec side (may use the Field-derived models). `G:\CLEANROOM\<engine>` is the only folder the build side may read: SPEC.md in plain words and measurements, reference renders with their dry inputs, a neutral score.py, and WALL-LOG.md with every file's sha256.
- Build-side agents get no paths outside `G:\CLEANROOM\<engine>` and are told never to open the Field material. This is enforced by instruction and logged, not by separate machines; the audit recommends moving the dirty material offline before a public release.
- Pilot: the Nitro-like filter, working name **Afterburner**.
  - Spec side done: `G:\CLEANROOM\nitro` holds SPEC.md, 213 renders plus 19 dry inputs (all generated in code), score.py and WALL-LOG.md with sha256 for every file.
  - Build side, round 1 done: `G:\CLEANROOM\nitro\build` has new C++, BUILD-LOG.md and README.md. The build agent read only the cleanroom folder.
  - Match at default knobs: level within 0.05 dB median (0.17 worst), 1/3-octave bands within 0.5 dB median (2.7 worst).
  - Known gaps: Feedback 0.9-1 (the low-cut peak is broader and does not self-oscillate on loud input), Follow below centre (up to 12 dB off), the drive curve below clipping, and the noise floor on sweeps.
  - Rounds 2 and 3 done (330 renders after the spec side added detailed self-oscillation and drive measurements, SPEC.md sections 9-10). Worst error over all renders 12.2 dB -> 8.5 dB; default knobs within 0.11 dB median. Self-oscillation pitch, build-up and decay now match; ring level within 3.8 dB median (was 36).
  - Beat sweep (the upgrade) works: 1/16-1/8 flutter, 1/4 beat-locked wah (about 0.7-8.6 kHz), 1-4 bar risers and falls, random steps. Bit-identical to the plain effect when off.
  - Round 4 running on the last gaps: drum loops at Feedback 1 ring less than the reference, the narrow band at hot input is about 4 dB quiet at 1 kHz, ring pitch up to 5% low near Lows 0.4.
  - Round 4 done: worst over all 330 renders 5.5 dB; narrow band and ring pitch fixed. Parked for the ear test: an 18 Hz sub-ring the reference builds on long drum passages at Feedback 1 with very low Lows.
  - **OP-XY machine built:** `G:\CLEANROOM\nitro\machine\afterburner` (fixed point; within 0.5 dB of the float model on all 330 inputs; Lows, Follow, Feedback, Highs, plus Sweep, Shape and Trim on page 2; jet-nozzle page drawn in code, not yet seen rendered). Written from a cleaned SDK copy (`G:\CLEANROOM\sdk`, Field files removed). SDK checks pass. CPU: about 31,000-35,000 instructions per block by static count (aim 30,000), not measured on hardware.
  - **Private test firmware 0.2.11 built and release check PASSED:** `G:\OPX1_BUILD2_20261110\package-0211a` = 0.2.10 plus Afterburner (effect 21, page 103) next to the old Nitro, for an A/B on the device. Not copied: the OP-XY was not in file-transfer mode. Install: put the OP-XY in mtp file transfer, then `sdk.py device push G:\OPX1_BUILD2_20261110\package-0211a\candidate --record <new folder>`, then the boot write. This build is private (it still contains TE's OS and the Field ports); Afterburner itself is the clean part.
  - Old plan line follows for reference. Then: wrap Afterburner as an OP-XY effect using only the SDK's public API (not the Field runtime adapters), with its own page in the muted Field-temperature colours, and an A/B test against the old Nitro on the device. Then a provenance check (grep for Field addresses, constants and names).
- **Rules Jordan set for every clean engine (12 November):**
  1. Not finished until it matches the original everywhere, not just at the defaults.
  2. Each gets one upgrade the original lacked, ideally something users asked for, built on what the OP-XY does and the OP-1 could not: tempo sync, sixteen tracks, per-step changes. Off by default, so the plain sound still matches. Afterburner's is **Beat sweep** (a tempo-synced filter sweep; forum users said they missed tempo-synced modulation).
  3. **Art:** unique imagery that shows what the engine does, quality OP-XY-style pages, in colour. The palette stays in the same colour temperature as the OP-1 Field's but a little off and less bright, never the Field's exact colours. Drawn fresh by agents that have not seen the Field SVGs.
- **LEDs (answered, `G:\OPX1_AGENTS_20261110\leds\LEDS.md`):** the keys have two colour channels, white and red, each with its own current setting (a hidden stock debug screen, "led current tuning", has kb white current, kb red current, kb_gcc and vu_gcc). There is no green, blue or RGB. Brightness already has 64 levels (the stock "led brightness" setting, 0-63). Inferred, not proven: the driver looks like an ISSI-style matrix chip with 256 steps per LED, which would allow dimmed white, dimmed red and white+red mixes (warm white to pink). Not found yet: the driver chip, the per-key state table, LED counts, what the "vu" group is. The SDK has no LED API. Smallest test: set the stock LED brightness to its lowest and highest values and watch whether both white and red keys dim in steps.
- **Reverb page design (Jordan, 12 November):** the clean reverb is not called Mother. Its page is an original night city in a Blade Runner / Tron / Daft Punk vibe (not a copy of any game's art): a symmetrical street with you small at the bottom centre. Distance: the street deepens. Decay/Gate: windows light with the sound and fade with the tail, or snap off together. Color: the haze shifts cold blue to magenta and amber. Mix: rain and fog thicken. Hits send light trails down the street; billboards flicker with the tail; a few signs hum in silence. Upgrade: **Hold** (freeze the tail as a drone, the city freezes lit), switchable per step from the sequencer.
- **Effect queue (Jordan, 13 November: "after one, continue on to the other effects; if I can't test, keep making more"):**
  | Original | Clean name | Upgrade | Page | Status |
  |---|---|---|---|---|
  | Nitro | Afterburner | Beat sweep | jet nozzle | machine built; in private test firmware 0.2.11 (release check passed); waiting for the device |
  | Punch | Forge | Pump (tempo-synced dip) | industrial press stamping a glowing bar | built; worst level 1.56 dB; about 28,300 instructions per block; closing loud-level distortion and a sub-ring regression |
  | Delay | Night Drive | Sync (tempo-locked echo) | night highway, streetlights as echoes | **done**: worst level 0.14 dB over 133 renders, null -38.6 dB median; fixed point within 0.01 dB; SDK test and Blackfin compile pass; about 17,000-20,000 instructions per block (bound 29,700); 42.5 KiB; `G:\CLEANROOM\delay\machine\nightdrive` |
  | Spring | Suspension | Kick (slap the tank, or on every beat/bar) | suspension bridge at night | spec done; build running |
  | Phone | Packet | Hold (freeze a grain loop, tempo-synced) | light packets on a fibre between relay towers | built; statistics within 0.15 dB median; 26,000-27,000 instructions per block; closing onset and tail gaps |
  | Mother | (city reverb, name TBD) | Hold (freeze) | the night city Jordan described | spec capture running |
  | Grid | | | | spec capture running |
  | CWO | | | | next |
  - **Incident, 13 November:** the Packet build agent stopped about 12 Python processes on the PC that were probably other teams' jobs; all teams were told to check and re-run. Its process listing showed a dirty-side folder path (name only). Logged in its BUILD-LOG.
  - **Items for the legal review:** Spring's spec lists measured early-echo arrival times (readable from the renders anyway, but the closest thing to internal numbers to cross the wall). Phone's spec gives its pitch mapping as a fitted formula. Both are measurements, not copied constants, but a lawyer should see them.
- Before any public release: a lawyer on the distribution form (a patcher that the user runs on their own OS, never a shipped `os.ldr`), the names, and the art. **The OP-XY was not in file-transfer mode this morning**, so nothing on it was checked or changed.


Written 12 November 2026 at the end of a long cloud session, so the work can carry on from the PC.
Nothing below has been tested on hardware unless it says so.

## OP-XY (custom firmware, Build 2)

- **On the device:** version 0.2.10, copied from `G:\OPX1_BUILD2_20261110\package-0210b`. Copy passed read-back (178 files).
  - It only runs after the boot write on the OP-XY: track 2 (exit), track 5 (write os to boot partition), wait for "firmware written ok!", power off and on. Label should read `OPEN 0.2.10-1.2.1`.
  - New in 0.2.10: dsynth and DrWave synths, DNA knob ranges fixed to the Field's, 16 factory presets each for DNA, Pulse, Cluster, Digital, FM, Phase, String, Voltage.
  - Not in it: the adapter speed patch, phone packs, README.
- **Fallback:** 0.2.9 (`G:\OPX1_BUILD2_20261110\package-029a`), or Build 1 0.1.9.
- **Effects that "do less" (Mother Gate/Color, Nitro, Punch):** knob ranges were checked against the Field and match (`G:\OPX1_AGENTS_20261110\fxranges\REPORT.md`). Next test on the device: put the track's send to that effect at maximum, then try Trim one or two steps higher. Still unverified: Mother's ported code was never compared against the Field code in the emulator.
- **Mic vocoder (Field-style, no setup):** not started. Needs platform work (the Nightcall job).

### Device report from Jordan, 12 November evening (0.2.10 running, boot write done)

- **Both vocoders (vocoder, vocoder-f) ignore the voice.** They make whatever track they sit on sound vocoded. Cause, from the lane notes: the Field vocoder needs a second input, the modulator, written into its scratch before every block (`G:\OPX1_AGENTS_20261110\tune\vocoder-sound\HANDOFF.md`, lines 19-43; on the Field that is its selected input: mic, line or USB). A send effect on the OP-XY only receives the track's own audio, so the track ends up as both carrier and modulator. Fix: give the effect the OP-XY's live input (mic or line) as the modulator, which means finding the stock input buffer in OS 1.2.1 and exposing it to effects. This is the same platform job as the Nightcall mic path; do them together.
- **Nitro still "doesn't work that well".** Not yet tested with the send at maximum and Trim raised. Do that first; if it is still weak, compare Nitro's capsule against the Field code in the emulator, as was done for dsynth and DrWave.
- Castle and the 0.2.10 synths load.

## Dubious (new OP-XY synth, design only)

- One instrument, five layers: forest (time of day), dirt (crunch), ore (bell sparkle), water (filter, turtles), underworld (reversed swell, inward reverb). Knobs: time, dig, glint, deep / tide, rift, air, wear.
- Playable mock: `mocks/dubious/dubious-synth.html` (open in a browser). Spec: `mocks/dubious/SPEC.md`, also at `G:\OPX1_AGENTS_20261110\dubious\SPEC.md`. Brief: `G:\OPX1_AGENTS_20261110\biome\REDESIGN-20261112.md`.
- Open before firmware: 297 shapes (over 256), redraw bursts when layers move, CPU at the aim with every knob up.

## Tracker Mini (Polyend CE firmware, folder `tracker-mini/`)

- **Built firmware:** `tracker-mini/out/TrackerMini_Loops_s1.ptf` (sha256 in `out/SHA256SUMS`). Loops slice 1: hold Menu, cell 12. One lane, bar waveform. Builds, passes 48 host tests, reviewed. Never run on a Mini.
  - Before flashing: back up `Projects/` from the card; keep the official `.ptf` in `/Firmware/`; turn Snap to zero off for the first try. Test script: `tracker-mini/STATUS.md`, section "Try it on the Mini".
- **The look Jordan wants next:** `mocks/tracker-mini/3-four-loops.html` (concept 3). Four stacked loops, each with its own playhead, flat display, direction shown by what has played since the last turn, Up/Down pick a loop, Fn1-4 = direction, speed, mute, record; mute/record/solo wait for the bar. Earlier tries for comparison: `1-loops-slice1.html`, `2-flow-lanes.html` (rejected as too glossy), and three whole-OS looks `os-concept-*.html`.
- **Next firmware step:** rebuild the Loops screen to concept 3: four lanes on four voices, queued actions, played-since-turn fill. Design notes and source map: `tracker-mini/docs/`.
- **Hardware facts:** no pads, no lights, no encoder; 18 keys; 800x480 FT812 screen with an 8 KB display list per frame (anti-aliased lines, filled strips and alpha are cheap); 8 voices shared with the pattern; no time-stretch; the stock recorder cannot capture the master output.

## Repo

Everything here is on branch `ccr-3b99e718-kuaqt4` of `Jordan-Edwards/Jordan-Edwards.github.io`. The S-1/J-6 songbook was removed (synths sold).
