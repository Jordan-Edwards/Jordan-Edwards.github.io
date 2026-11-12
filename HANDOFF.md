# Handoff: where everything stands

## Morning summary, 12 November (release audit done; fixes in progress)

**Can Build 2 0.2.10 be released as it is? No.** Full audit with evidence: `G:\OPX1_AGENTS_20261110\release\AUDIT.md`. This is an engineering inventory, not legal advice; clearing anything for release needs a lawyer.

- **The OS:** `os.ldr` is TE's stock OP-XY OS 1.2.1 with our changes: 2,372,929 bytes identical to the stock image, 407 bytes changed, 758,520 bytes added. At least 75.8% of the shipped image is TE's OS word for word. The only release form that avoids shipping it is a patcher the user runs on their own copy, and that may still breach TE's terms or anti-circumvention law.
- **The engines:** 20 of the 22 machines run TE's own code: the 8 Field effects, the Field vocoder and 11 synths. Each capsule is the Field's instructions copied byte for byte with only addresses moved, plus tables copied from the Field image. Four capsules (mother, grid, pulse, drwave) also hold copied Analog Devices chip-ROM routines.
- **Screens, presets, names:** 19-20 of 22 screens come from the Field's own SVGs. About 159 presets look like Field factory presets (inferred from names). `op1_factory.json` is TE's catalog file. Names and descriptions say "OP-1 Field" throughout.
- **Ours:** the Scale player, the 16-band Vocoder (own DSP, no Field code), and the non-Field parts of our SDK changes. The SDK is MIT-licensed from the Open-XY contributors, so it is not ours to relicense.
- **Releasable now, subject to a lawyer:** Scale and Vocoder as source. Before that, the Vocoder needs its `field_level.hpp` dependency and the TE font name removed, and its `tools`/`make_tables.py` checked. Our non-Field SDK patches could go upstream under MIT. Also releasable: Dubious (our design) and the Tracker Mini Loops work (Polyend CE licence: share, do not sell).
- **Clean-room route to "same sound, built independently":** specs and audio renders from one side, new DSP written only from those by agents that never see Field code, new art, new names. Estimate: about 6 clean engines plus Scale and Vocoder for a first release, 3-4 months; full parity 9-15 engineer-months. Order and per-engine estimates are in AUDIT.md.

**Still running:** Nitro investigation (`G:\OPX1_AGENTS_20261110\nitro-check\REPORT.md` when done) and a search for the earlier Castle build. **The OP-XY was not in file-transfer mode this morning**, so nothing on it was checked or changed.


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
