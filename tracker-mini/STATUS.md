# Status

Updated: 2026-11-12, 3:46 AM Central.

## What Jordan asked for

- "The retracker thing, but our own upgraded version", on the Mini.
- The look matters: the playhead sweeping over the audio waves, back and forth
  in ping-pong, with visual feedback that is "clear what it's doing, but cool
  and smooth".
- The Mini and the Tracker+ are the same hardware, so use what the Plus can do.
- "We're turning it into a really cool groove box and really making use of its
  big screen and buttons."
- Report plainly what was found, what it makes possible, and where the limits
  of the hardware are.

## Done

- Confirmed the Tracker Mini firmware is open source: Polyend's Tracker
  Community Edition covers the Original, the Plus and the Mini.
- Built the unmodified CE beta for the Mini from source
  (`out/TrackerMini_CE_1343677.ptf`). It is byte-identical to Polyend's own
  build of the same commit, so the build setup here is exact.
- `build.sh` rebuilds it, and can apply our patches on top.
- Read the CE source for the audio engine, the screen layer and the Mini's
  controls. The notes are in [`docs/map/`](docs/map/).
- Designed the feature, called "Loops": [`docs/DESIGN.md`](docs/DESIGN.md).
- Planned the first slice: [`docs/PLAN.md`](docs/PLAN.md).
- **Wrote slice 1 of Loops.** It is five patches in [`patches/`](patches/) on
  top of the pinned CE commit, a little over 2,000 lines, all new code:
  - `0001-loops-logic.patch`: the logic that needs no hardware (state
    machine, fit-to-bars, slices, waveform bars, playhead model).
  - `0002-loops-display-controls.patch`: three new screen controls (the
    200-bar waveform with ruler, the slice strip, the moving playhead).
  - `0003-loops-engine.patch`: the audio-side glue and its one hook after
    the sequencer tick.
  - `0004-loops-screen-and-menu.patch`: the Loops screen and its place as
    the 12th cell of the hold-Menu module menu.
  - `0005-loops-review-fixes.patch`: the fixes from review (below).
- **Two independent reviews read the code.** Neither found anything that
  could hang, crash, damage project data or change stock behaviour, and both
  judged it fit for a first try on a device. They found one major sound
  problem and a list of minor ones. See "Review" below.
- **It builds.** `./build.sh loops` from a clean checkout, after the fixes,
  gives [`out/TrackerMini_Loops_s1.ptf`](out/TrackerMini_Loops_s1.ptf)
  (4,870,231 bytes, sha256 `87ee484e...733c89`, full value in
  `out/SHA256SUMS`). Against the stock build: flash +14,704 bytes, fast RAM
  (SRAM_DTC) +3,296 bytes (the budget was 4 KB; 13,760 bytes of that region
  are still free), audio code RAM (SRAM_ITC) +768 bytes. The tree that was
  built and the development branch are the same git tree.
- **It passes host tests.** `tests/run.sh` compiles the same `loopsLogic.cpp`
  the firmware builds and runs 48 tests on a computer: every row of the state
  table, fit maths, the "leave an in-time loop alone" rule, slice bounds, bar
  reduction, playhead direction, wrap and bounce. Only this pure logic is
  tested on a computer. The audio glue, the screen, the menu entry and the
  display controls are not.

What "builds" and "passes host tests" do not tell us: whether it sounds right,
looks smooth, or behaves on a real Mini. None of this has run on a device.

What slice 1 does, on paper:

- Hold Menu: the last cell, empty in stock, says "Loops". Nothing stock is
  removed.
- The current instrument's sample fills the screen as 200 bars. A ruler shows
  bars and beats (FIT) or slice edges (FREE).
- Middle starts and stops the loop on one track voice (default track 8). If
  the pattern is playing it waits for the next bar ("ARMED", with a countdown
  line).
- Fn1 Direction (Forward, Reverse, Ping-pong), Fn2 Sync (FREE, FIT), Fn3
  Slices (8, 16), Fn4 Track (1 to 8). Shift+Fn keeps the stock shortcuts.
- Up and Down double and halve the speed (bar count in FIT, octave in FREE).
- The four value keys stutter slices while held; Left and Right move the four
  pads along the strip. Shift+value keys is still master volume.
- The playhead reads its position from the voice itself, with a glow, a tail
  that grows with speed, a direction arrow and a flash at the loop edges.
- In FIT, while the pattern plays, a loop that is still in time at the end of
  its cycle is left running. Only a loop that has drifted is cut and started
  again.
- RAM samples only. The loop stops when you leave. Nothing is saved, and the
  instrument's own play mode, points, tune and glide are put back after every
  note.

## Review: what was fixed and what was not

Fixed in `0005-loops-review-fixes.patch`:

- **Major: FIT cut and restarted the loop on every cycle**, and that cut did
  not line up with the loop's own wrap, so some cycles would play the first
  few milliseconds twice. Found by arithmetic, not heard. Now a loop within
  6 ms of its own wrap point is left alone, and the fit is rounded toward
  slow, so a correction cuts a little tail and does not repeat the start.
  Host-tested.
- The screen kept saying a loop was sounding after stock code had silenced
  the voice (Play while a pad is held, Stop closing an open note, an envelope
  that ends). Now Play sounds the held slice again, a voice that stays
  stopped is given up after about 0.7 s, and the playhead does not read a
  stopped voice.
- A pad on a slice too small to play used to cut the running loop. Now it is
  ignored. And when nothing of Loops' own is sounding, a refused start no
  longer cuts a pattern note of the same instrument on that track.
- The instrument's glide could make the loop slide in from the track's last
  note. Glide is now 0 for the loop's note and put back afterwards.
- With the project's Snap to zero on, a very narrow slice could end up with
  no length inside the player. Such a region is now refused.
- Tempo follow redrew the whole waveform on every small tempo change and
  switched FIT off when the tempo was unknown. It now looks four times a
  second, ignores changes under 0.05 BPM, keeps the last known tempo and
  redraws the waveform only when the bar count changes.
- Fn2 did nothing, silently, when no bar count fits. It now shows
  "FREE  no fit".
- `docs/DESIGN.md` section 7 claimed a display-list log line and RAM figures
  that were not true. It now says what is measured and what is not.
- `tests/run.sh` warns when the development checkout differs from the last
  patched build, and the README says only the pure logic is host-tested.

Not changed, and why:

- **Re-arm the loop when the tempo changes** (reviewer's suggestion). Not
  done: on an external clock the measured tempo wobbles, and re-arming would
  restart the loop again and again. So after a tempo change a fitted loop
  keeps its old pitch until the end of its cycle (up to 16 bars).
- **Force Loops into the 12th menu cell.** Not done: it only matters when a
  saved config has the same screen on two Fn keys, and forcing the cell would
  change what stock shows there in that case.
- **A key legend on the screen, and changing the instrument inside Loops.**
  Not done: more controls on a screen whose display-list size is unmeasured.
  The keys are listed in the README and below.
- **Show a pad as unavailable** when its slice cannot be played. Not done;
  the pad is just silent.

## Try it on the Mini

Nothing here has been on a device. This is the first-run script.

1. Back up `Projects/`. Keep a firmware you trust in `/Firmware/` as well.
   Copy `TrackerMini_Loops_s1.ptf` to `/Firmware/` and update from Config.
2. Stock check: play a pattern, press each Fn key, hold Menu. All as before,
   except the menu's last cell now says "Loops".
3. Pick an instrument that holds a drum loop (a normal sample). Hold Menu and
   choose Loops. The wave fills the screen.
4. Press Middle: the loop plays and the playhead sweeps.
5. Fn1: Reverse, then Ping-pong. The playhead should bounce at the ends with
   a flash.
6. Fn2 to FIT. Up and Down halve and double the speed. The bar count is on
   the screen.
7. Press Play. The pattern and the loop should start together. Listen for a
   minute, and longer with an 8 or 16 bar loop: does it stay in time, and is
   there a click or a doubled hit on any downbeat?
8. Hold each value key: that slice stutters. Let go: the loop returns on the
   beat.
9. Fn3 to 16 slices. Left and Right move the four pads along the strip.
10. Leave by the menu. The loop stops. The Fn and value keys do their stock
    jobs. In Sample Playback the instrument's play mode and points are
    unchanged.
11. Tell us: is the playhead there at all, and is it smooth (a phone video
    helps); any click at the loop point; whether the Fn labels sit over the
    right keys and which value key is which pad; the CPU % in Config while a
    loop and a full pattern play; and anything that felt wrong.

For the first try: use an empty track for the loop, an instrument with no
glide, no fine-tune LFO and a sustaining envelope, and turn the project's
Snap to zero off.

## Next

1. Jordan flashes `out/TrackerMini_Loops_s1.ptf` and runs the script above.
2. Fix what the device shows. The likely first jobs: measure the display
   list, and replace the hard cut-and-restart with a soft restart inside the
   player.
3. Later slices, in order: keep a loop in the instrument and let it run on
   other screens; capture from the input; resample the Tracker's own output;
   several loop lanes; overdub.

## Open risks

General:

- Nothing here has been flashed to a real Mini by us. A build can only be
  tried on the device by hand: copy to `/Firmware/`, then update from Config.
- The PC ("Intel-Build") has not been reachable, so nothing was copied to the
  SD card and the Tracker's storage mode was never confirmed from here.
- Retrack (the looper for the original Tracker) has no licence, so its code is
  not copied or read; the looper here is written new on top of CE.
- The review fixes were checked by host tests and one clean build. They were
  not reviewed a second time.

Findings left open:

- **Tempo changes in FIT.** After a tempo effect in the pattern or a change
  of external clock tempo, the loop is out of time until the end of its
  cycle.
- **Snap to zero and FIT.** The stock player can move each loop point by up
  to about 170 samples on a 4 s sample. The loop is then not exactly the
  fitted length, so it is cut and restarted more often, and if it came out
  shorter its first few ms can still play twice.
- **Every restart is a hard cut** (a drift correction, a pad press or
  release, Play). It may click. An instrument with a slow attack dips in
  volume at each restart.
- **A pattern note of the same instrument on the loop track** is not seen as
  "the pattern took the voice". Use an empty track.
- **Reverse on a very short slice at high speed** can run off the start and
  stop the voice (stock player behaviour). Loops then goes idle after about
  0.7 s.
- **Display list size is unmeasured.** Estimates run from 3.8 to 6.5 KB
  against a limit of 8,172 bytes. Past the limit the screen drops controls
  without an error, the playhead first. The log line that would report the
  real size is not written yet.
- **No key legend on the screen**, and the instrument cannot be changed
  inside Loops (leave, change it, come back).
- **Loops in the menu** depends on the eight Fn bindings being different. A
  saved config with a duplicate would hide it.
- **Host tests use a PC compiler.** A fit could differ by one cent on the
  device's own maths.
- A fine-tune LFO on the instrument overrides the FIT fine tune.
  Performance-mode overrides on the loop track would override Loops. A
  1-step pattern gives no step edges. An instrument whose envelope has no
  sustain fades out while looping.
- FIT changes pitch; there is no time-stretch in this firmware.

Reviewer notes that need the hardware (or were only read, not run):

- Whether it runs, sounds right and looks smooth at all. The panel scans at
  about 54 Hz; the real redraw rate, the 1/16-pixel playhead and the additive
  glow are untried on this display chip.
- Whether a restart is heard as a click or doubled hit, and how loud.
- Whether the voice reports its position correctly in Reverse and Ping-pong.
  The playhead and the new "in time" rule both depend on it.
- Whether FIT lands within one cent inside the player.
- Where Fn1 to Fn4 sit against the labels on the screen, and whether the
  value keys run +10, +1, -1, -10 from left to right.
- The cost of one loop start inside the audio callback (more with Snap to
  zero on), and of reading the engine's state on every main-loop pass.
- Whether the 13,760 bytes left in fast RAM are enough at run time. The
  growth is fixed and Loops allocates nothing while running; the stack is a
  fixed 20 KB block.
- That the audio callback runs in the audio interrupt, so the short locks
  Loops takes really shut it out, and that no higher-priority interrupt reads
  an instrument while Loops has borrowed its settings. Inferred from the
  source, not proven.
- That nothing re-reads the instrument's points, play mode or tune on the
  loop voice after the note starts. Read, not traced line by line.
- Whether any Mini key or leftover menu action sends the old "Game" button
  event. In stock that did nothing; now it would open Loops.
- Not examined at all: external MIDI clock start and stop, MIDI notes
  arriving on the loop track, mute and solo and performance mode on the loop
  track, and entering USB or file-transfer mode while a loop runs.
- The Original and Plus builds were inspected, not built. All new code is
  inside the Mini-only switch.
- The stock build was not rebuilt to re-confirm it is byte-identical. The
  stock build applies no patches, so nothing it uses has changed.
- Inside Loops the Fn and value keys are taken over and handed back on exit.
  The script above checks this.

Details and the full list of differences from the plan are in section 11 of
`docs/PLAN.md`. Open questions for Jordan are at the end of
`docs/DESIGN.md`.
