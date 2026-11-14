# OP-XY community machines: survey and compile plan

Written 14 November 2026 from a cloud session while the PC (Intel-Build) was offline.
Nothing here has been fetched, built or tested yet. Everything below is from public pages, read today.

## What we already ship (0.2.14, on the device)

Community machines pinned by `fetch.py` / `sources.json` into `G:\OPXY_COMMUNITY_20261113`:

| Machine | Source |
|---|---|
| Timestretch | `etcetc000/open-xy-core-machines@600ff0554` (stretch code AGPL-3.0) |
| Chords | `etcetc000/open-xy-core-machines@b17d21f6a` |
| Ring Mod | `etcetc000/open-xy-core-machines@32b257d92` |
| Halcyon | `colorsinspace1/halcyon@eb2fac61e` |
| Lustre | `kristapskristaps/xy-machines@0be9209c5` |
| Halo | `kristapskristaps/xy-machines@16ee2c863` |

Plus our own: the OP-1 Field ports, Scale, two vocoders, and the clean effects
Afterburner, Night Drive, Forge, Packet and Night City.

## New candidates found

### 1. mmockett/OP-XY-ModFX (MIT) — the highest-value find

Three machines, and one of them is a feature people have asked for repeatedly:

- **Omnifilter** — a *global* mod. It sits on track 12 (CV) instead of an instrument track, so it
  costs no instrument slot, and its controls steer **every instrument track at once**. Nothing we
  ship does this.
- **Lint** — a send effect: a 1970s box of effects, with its own page on the send.
- **Chroma** — a send effect: a stereo console of four modules.

**Compatibility risk:** built against the SDK's `staging` branch. Omnifilter needs machines on aux
tracks (**SDK 1.9**); Lint and Chroma need effect pages, shift rows and effect screens (**SDK 1.7**).
Targets OP-XY **OS 1.2.1**, which matches our device. Our Build 2 SDK is a pinned fork, so the aux-track
support has to be confirmed present before Omnifilter can build. Lint and Chroma are the safer two.

### 2. mmockett/OP-XY-MNMD (MIT) — big, but blocked on a version mismatch

The Elektron Machinedrum and Monomachine, written from scratch. `mdkit` alone is 33 drum machines
across four families (TRX, EFM, P-I, GND); then ten-plus Monomachine synths: `mmsaw`, `mmpulse`,
`mmens`, `mmsid`, `mmstat`, `mmpar`, `mmdyn`, `mmvo6`, `mmsin`, `mmnois`, `mmwave`, `mmddrw`,
`mmdens`, `mmbbox`.

**Blockers, in order:**
1. Its README says it builds for **OS 1.2.0 exactly**. Our device and build are **1.2.1**.
2. It needs **SDK 1.10** on `staging` (kit pan/level/filter/SRR), and 1% send steps need SDK 1.15.
3. `mde12`, `mmwave` and `mmbbox` require samples the user captures from their own ROM, so they are
   not distributable and we skip them.

Worth a compatibility probe, not a blind build. If it only needs the 1.2.0/1.2.1 label relaxed, the
payoff is large; if it needs real SDK features we lack, it waits.

### 3. Kieran9K's firmware (op-forums "Custom Firmware OP-XY", active thread)

A large set, overlapping ours in places. Named in-thread: Macro Osc (Braids port), 2op FM, Ring Mod,
Vocal Tune + Harmonizer, Cloud (granular), Piano (modal, Grand/Felt/Honky), Phase, Karplus, Shaker,
Scale Chord, Ping Pong delay, Tape, Tape Loop, Strum, guitar (Martin HD-28), groove, choir, upright.
Also named without an author: Troupe, Breadboard, Tattva, Ohmonk, Daath, Halcyon Keys, Grainfield.

**No GitHub repository was found for these in this survey.** Distribution looks to be through the
thread and/or open-xy.com's builder. Source and licence must be established before anything is built
into our firmware. Do not ship what we cannot licence.

### 4. Features the thread says users always wanted

Useful as a design queue for our own clean machines, independent of anyone's code:

- An acoustic strummer
- Stereo ping-pong delay
- PO-35-style robot-vocal effect
- A true FM engine with 4 or 6 operators
- A proper autosampler (sample a MIDI instrument automatically, rip a patch)
- A trance gate with patterns, under the Arpeggio menu

### 5. Tools (not on-device, but useful to us)

From `bnjreece/awesome-te`. These run on a PC or in a browser, not on the OP-XY:
`kmorrill/xy-format` (byte-exact .xy project decode, the reference for the format),
OPXY.APP (renames and relinks samples across projects, flags truncated filenames, batch-downsamples),
ConvertWithMoss and the SFZ/SF2/DX7/Elektron/Maschine converters, OP-PatchStudio,
`buba447/OP-XY-Sample-Extractor`, stembounce, `NeoVand/op-xy-agent`.

**`kmorrill/xy-format` matters to us directly:** the sample clean-up is held back because projects
store sample paths in a fixed 96-byte field that we chose not to rewrite. A byte-exact decoder may
let us safely update those paths, which would remove the "10 presets stay put" compromise.
OPXY.APP solves a neighbouring problem and is worth reading for its approach.

## Plan, in order, when the PC is back

1. **Probe, do not build blind.** For ModFX and MNMD, clone at a pinned commit into
   `G:\OPXY_COMMUNITY_20261114\` and run `sdk.py test --machine <path>` against our Build 2 SDK.
   Record which SDK features each needs and which we actually have. Cheap, and it decides everything.
2. **Lint and Chroma first** (SDK 1.7 features; two send effects, low risk).
3. **Omnifilter second** (SDK 1.9 aux-track machines; highest user value if it builds).
4. **MNMD third**, only if the probe says the OS 1.2.0/1.2.1 difference is a label and not real.
   Start with `mdkit` alone; skip `mde12`, `mmwave`, `mmbbox` (ROM-derived samples).
5. Extend `fetch.py` / `sources.json` with every new source **at a pinned commit**, record the licence,
   and keep the AGPL-3.0 note on Timestretch's stretch code.
6. Build 0.2.15 with whatever passed, run the release check, push in developer mode.
7. Before any public release, add these to the legal review: per-machine licences and attributions,
   the AGPL component, and the "written from scratch" claims in MNMD.

## Known defects still open on our own machines

- **Night City:** gate opens and closes at slightly different moments than the reference on sustained
  material (gated drums 0.5–0.7 dB off). Measurement plan already written; the agent was cut off by a
  model limit. Resume from `G:\CLEANROOM\mother\build\match2`.
- **Suspension:** round 4 never ran (decay/EDT, highs at low Turns, hang level, stereo −0.41 vs −0.57,
  CPU ~35,200 against a 30,000 aim). Agent was cut off at start.
- **Lattice:** build never started.
- **Forge:** sub ringing 1.78 dB off the reference; CPU estimate 46,400–47,500 (limit 48,000).
- **Packet:** quiet stutter drums start 29 ms early; music ~0.3 dB loud.
- **Vocoder:** does not react to the mic. Needs the OP-XY's live input exposed as the modulator.
- **CWO:** replacement not started.
- Nothing above has been verified by ear on hardware.

## Handoff (for Codex or another session)

**Read first, in this order:**
1. `HANDOFF.md` in this repo — master state.
2. This file.
3. On the PC: `G:\CLEANROOM\<effect>\build\BUILD-LOG.md` and `STATUS.md` for each effect.

**Work areas on the PC:**

| Purpose | Path |
|---|---|
| Build 2 SDK and firmware | `G:\OPX1_BUILD2_20261110` |
| Firmware 0.2.13/0.2.14 scripts, auto-push | `G:\OPX1_BUILD2_20261110\firmware-0213` |
| Clean-room effects | `G:\CLEANROOM\<delay\|punch\|phone\|spring\|grid\|mother>` |
| Community fetches | `G:\OPXY_COMMUNITY_20261113` (new: `...20261114`) |
| Sample clean-up plan | `G:\OPXY_SAMPLES_20261113` (`BRIEF.md`, `plan3.csv`, `files3.csv`) |
| API-billed job runner | `G:\OPXY_API` (`run_job.ps1`, needs user env var `OPXY_API_KEY`) |

**Hard rules that must not be broken:**
- The clean-room wall: a build agent reads only its effect folder, `G:\CLEANROOM\sdk` and finished
  sibling machines. Never `G:\CLEANROOM-DIRTY`, never the Field sources. This is the legal basis for
  releasing the ports at all.
- Never write the OP-XY boot partition. The push copies files; the owner presses track 2, track 5,
  power cycle.
- Never delete an original sample without a verified copy on the PC.
- Only stop processes whose PIDs you started; several jobs share this PC.
- Pin every third-party fetch to a commit and record its licence.
