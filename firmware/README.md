# Community firmware library — OP-XY and Polyend Tracker

A pinned, reproducible library of community firmware builds for the **Teenage
Engineering OP-XY** and the **Polyend Tracker / Tracker+ / Tracker Mini**, so we
can pull any of them down and flash quickly.

Verified by cloning and inspecting every source at its pinned commit on
**2026-11-08**.

```sh
python3 firmware/fetch.py --list      # the catalog, fetches nothing
python3 firmware/fetch.py             # fetch every pinned source
python3 firmware/fetch.py --machines  # + all 78 published Open-XY machines
python3 firmware/fetch.py --check     # has upstream moved past our pins?
```

Everything lands in `firmware/vendor/` (~460 MB for the sources, ~845 MB with
`--machines`), which is
**gitignored on purpose** — see [Why there are no binaries here](#why-there-are-no-binaries-in-this-repo).

---

## Read this first: what you can and cannot stockpile

The thing you'd most want — a folder of ready-to-flash images — mostly can't
exist legitimately, and that shapes this whole directory:

| | |
|---|---|
| **OP-XY builds** | Statically link **Teenage Engineering's own stock OS 1.2.1**. A built image contains TE's firmware, so it can't be shared. Each person builds from the `os.ldr` off their own device. |
| **Polyend patch-mods** | Shipped as *patches* against vendor firmware. Modular-Trackular states outright: *"This repository contains no Polyend code… Do not share modified `.ptf` files."* |
| **Tracker CE** | Polyend's own open-source release, with freely downloadable `.ptf` builds — but `synth/lib` holds proprietary precompiled blobs, so we link to upstream rather than mirror. |
| **Tracker CE Mods** | The one exception. Ready-to-flash `.ptf` for all three devices, committed in its repo, PolyForm Noncommercial. `fetch.py` pulls these straight down. |

So this library pins **sources plus a build/fetch path**, not binaries. In
practice that's barely slower — `fetch.py` is one command — and it stays current
and legal.

### Why there are no binaries in this repo

`Jordan-Edwards.github.io` is a **public GitHub Pages site**. Anything committed
here is published to the open web. Committing these images would mean
redistributing Teenage Engineering and Polyend code, against the mod authors'
explicit wishes. `firmware/.gitignore` therefore excludes `vendor/`, `*.ptf` and
`*.ldr`.

---

## OP-XY

### Open-XY — the one you were asking about

You called it "the retracker one where it replaces them with audio loops."
That's **Open-XY's Timestretch machine**, not RETracker — RETracker is an
unrelated Polyend reverse-engineering toolkit (below). Timestretch is the match,
and "replaces them" is literally right:

> **Timestretch** *forks the stock drum sampler* (`"base": "drumSampler"`), so each
> of the 24 pads becomes its own tempo-locked audio loop — either repitched or
> pitch-preserving (Capicola-derived).

- Lengths of 1/4, 1/2, 1, 2, 4 or 8 bars; source BPM 20–300.
- **Auto source BPM from the filename**: three digits at either end, e.g.
  `095_guitar.wav` or `guitar_095.wav`.
- Encoder 1 pitch ±12 semitones, 2 start / loop length / source BPM, 3 end and
  `repitch` ⇄ `timestretch`, 4 loop or one-shot.
- Stock slicer still works (hold a key + M1 transient/even/tap, M2 copy, M3 paste).
- Recordings from the stock recorder drop onto a pad and inherit the project tempo.

This is a strong fit for the J-6/S-1 workflow in `../s1-j6/`: bounce a loop,
name it `_124`, and it locks to the project.

**How Open-XY works.** It's an SDK plus a catalog: you choose machines from the
catalog and it links them into an exact copy of stock OS 1.2.1. Two routes:

1. **Browser builder at [open-xy.com](https://open-xy.com)** — upload your own
   `os.ldr`, pick machines, download firmware. No toolchain. Easiest path.
2. **Local build** — `firmware/vendor/open-xy/`, needs Python 3.11+, Node 22.12+,
   NumPy 2.3.5, Clang++ with wasm32/wasm-ld. Firmware builds need Windows x86_64,
   Apple-silicon macOS or Linux x86_64. Browser *previews* of a machine work
   anywhere.

Audition a machine without touching the device:

```sh
cd firmware/vendor/open-xy
python3 sdk.py preview --machine ../opxy-machines/etcetc000__open-xy-core-machines@600ff0554/machines/timestretch --out local/preview-ts
python3 tools/serve_harness.py --preview local/preview-ts   # http://127.0.0.1:8917/
```

**Flashing:** enter `te boot`, press **1** for mass storage, copy the built
`os.ldr` to the disk that appears.

### The machine library

`--machines` fetches all **78 published machines** (57 synths, 10 effects, 5 sample
engines, 5 drum kits, 1 note player) at the exact commits the catalog pins, across
41 repos, and writes an index to
`firmware/vendor/opxy-machines/machines-local.json` (id, kind, maintainer, tag,
keywords, local path). Highlights beyond Timestretch:

- **Core** (`open-xy-core-machines`): 2op FM, Macro Osc (Mutable Instruments
  Braids port), Karplus, Ring Mod, Ping Pong, Chords, plus the *Retrospective
  capture* extension — double-tap Record to insert what you just played.
- **Bar tools** (`open-xy-bar-tools`): hold BAR + M3 to loop the selected bar
  while you keep editing; Shift+Play starts from the current bar.
- Larger third-party sets: `OP-XY-Hexagon`, `OP-XY-Nonagon`, `OP-XY-MNMD`,
  `OP-XY-Trigon`, `OP-XY-ModFX`, `xy-machines`, `OP-XY-Grains`.

**Licensing note:** Timestretch's `analysis.h` / `stretch.h` adapt Capicola under
**AGPL-3.0**. Fine for personal use; it has consequences if you ever distribute a
build containing it.

---

## Polyend Tracker

### Tracker CE — start here

Polyend open-sourced the full Tracker firmware (Nov 2026). **Tracker Community
Edition** covers all three devices: original Tracker (MK66), Tracker+ and
Tracker Mini.

The headline feature is close to what you described for loops — **Hybrid SD Card
Sample Streaming**: samples 256 KB and larger keep only their attack in sample
RAM and stream the rest off the microSD, so one project can hold a pile of
full-length stems and loops on a fraction of the RAM. On Tracker+/Mini that
covers One-Shot, Forward/Backward/Ping-Pong Loop, Slice and Beat Slice.

- Stable `.ptf`: <https://github.com/polyend/tracker-ce/releases>
- Beta (built from `main`): [firmware zip](https://nightly.link/polyend/tracker-ce/workflows/build.yml/main/polyend-tracker-ce-firmware.zip) · [editor effects zip](https://nightly.link/polyend/tracker-ce/workflows/build.yml/main/polyend-tracker-ce-effects.zip)

Polyend's own note: the isolated bootloader plus the hardware recovery button
make experimenting here **comparatively safe** — a build that won't boot can be
re-flashed from the SD card. Custom firmware is still out of warranty.

### Tracker CE Mods — the quick win

The only one with **ready-to-flash images**, pulled directly by `fetch.py`:

| Device | File | sha256 |
|---|---|---|
| Tracker (original) | `PolyendTracker_CE_1.0.0.ptf` | `21e26b39f87fcf1e…` |
| Tracker+ | `TrackerPlus_CE_1.0.0.ptf` | `30831575162505697…` |
| Tracker Mini | `TrackerMini_CE_1.0.0.ptf` | `d50aadd632c6c74d1…` |

Adds polymeter, rotate, new chance conditions and live fill, song repeats,
per-track MIDI in, and a Sample Editor tempo grid. Full hashes come out of
`fetch.py`; a manual is in the repo.

### Modular-Trackular Plus — the active mod set (Tracker+)

Built into Tracker CE, one firmware file, **every mod has its own Off/On switch**
(Config → Mods, or per project). Humanize, Global Swing, Color Song, Variable
Track Length — all tested on hardware. This is where development continues.

### Modular-Trackular — the deep one (Tracker+ stock 1.2.0)

Feature-complete and now bug-fix only, patching **stock firmware 1.2.0**. Still
the richest set, and much of it is not yet ported to CE:

- **WAVE** and **PHASE** synths (wavetable; Casio CZ-style phase distortion),
  each replacing a stock synth model, with 2 LFOs, a 6-slot mod matrix, chorus.
- **Master FX**: Freeverb, Dattorro plate, spring, shimmer, gated and reverse
  reverbs; tape and bucket-brigade delays.
- **slicethru** — Beat Slice (Play Through): each note plays from its slice to
  the end of the sample, and with Loop on it loops the whole sample until
  stopped.
- **resample** — live resampling in the Sample Recorder, no cable.
- Plus humanize, colorsong, swing, conditional trigs, legato, FX interpolation,
  copy-to-new, pad visualizer.

Build it yourself against your own stock 1.2.0 `.ptf` from polyend.com.
**Don't share the resulting file** — the author asks this explicitly.

### Flashing a Tracker

Back up the `Projects/` folder on the microSD, copy the `.ptf` to `/Firmware/`,
then **Config → Firmware → Firmware update**, select it, confirm. For the
original Tracker the filename must start with `PolyendTracker_` and end `.ptf`.

---

## Tooling and reference (not device firmware)

- **RETracker** — reverse-engineering framework for the original Polyend Tracker.
  Patches the stock USB RAWHID handler to add memory dump/patch, arbitrary code
  execution and host→SD file transfer. **Not a music-feature firmware**, and last
  touched 2024-06-19 against ~1.5.0-era firmware. Build:
  `python fwtool.py -b PolyendTracker_1.5.0.ptf out_retracker.ptf`
- **PolyBrik** — Tracker CE ported to the TrimUI Brick / Brick Pro handheld.
  Nothing to flash on a Polyend device; fun if you want Tracker in your pocket.
- **awesome-te** — curated directory of TE reverse engineering, custom firmware,
  tools and teardowns. Good place to watch for new OP-XY work.

## Skip for now

- **Tracker Enhanced** — pinned only so we notice if it ships. Its own README
  says *"Status: planning. Nothing in the feature list below is implemented yet."*
  The plan (Renoise-style Lines Per Beat, extended MIDI CC, EQ/saturation/
  compressors) is appealing but would also break project-file compatibility.

---

## Before you flash anything

1. **Back up first.** Tracker: the microSD `Projects/` folder. OP-XY: your own
   stock `os.ldr` — you need it to build, and to go back.
2. **Match the target.** Open-XY wants OS 1.2.1; Modular-Trackular wants stock
   1.2.0; Modular-Trackular Plus and Tracker CE Mods are CE-based; Tracker
   Enhanced drops the original Tracker entirely.
3. **Custom firmware voids warranty coverage** for the resulting issues. Polyend
   offers out-of-warranty repair; TE makes no such statement.
4. **Re-check pins** with `python3 firmware/fetch.py --check` before a build —
   these repos move fast (Modular-Trackular Plus moved during the hour this was
   written).
