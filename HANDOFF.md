# Handoff: where everything stands

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
