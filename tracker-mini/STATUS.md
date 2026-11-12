# Status

Updated: 2026-11-11, 11:12 PM Central.

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
- **Wrote slice 1 of Loops.** It is four patches in [`patches/`](patches/) on
  top of the pinned CE commit, about 2,000 lines, all new code:
  - `0001-loops-logic.patch`: the logic that needs no hardware (state
    machine, fit-to-bars, slices, waveform bars, playhead model).
  - `0002-loops-display-controls.patch`: three new screen controls (the
    200-bar waveform with ruler, the slice strip, the moving playhead).
  - `0003-loops-engine.patch`: the audio-side glue and its one hook after
    the sequencer tick.
  - `0004-loops-screen-and-menu.patch`: the Loops screen and its place as
    the 12th cell of the hold-Menu module menu.
- **It builds.** `./build.sh loops` from a clean checkout gives
  `TrackerMini_Loops_s1.ptf`. Against the stock build: flash +13,680 bytes,
  fast RAM (SRAM_DTC) +3,288 bytes (the budget was 4 KB; about 13 KB of that
  region is still free), audio code RAM (SRAM_ITC) +408 bytes.
- **It passes host tests.** `tests/run.sh` compiles the same `loopsLogic.cpp`
  the firmware builds and runs 43 tests on a computer: every row of the state
  table, fit maths, slice bounds, bar reduction, playhead direction, wrap and
  bounce.

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
- RAM samples only. The loop stops when you leave. Nothing is saved, and the
  instrument's own play mode, points and tune are put back after every note.

## In progress

- Review of the slice-1 code. The built `.ptf` is deliberately not in `out/`
  or the README table yet; it is added after review.

## Next

1. Review, then commit `out/TrackerMini_Loops_s1.ptf` with its checksum.
2. Jordan flashes it and runs the short test script at the end of
   `docs/PLAN.md` (back up `Projects/` first).
3. Later slices, in order: keep a loop in the instrument and let it run on
   other screens; capture from the input; resample the Tracker's own output;
   several loop lanes; overdub.

## Open risks

- Nothing here has been flashed to a real Mini by us. A build can only be
  tried on the device by hand: copy to `/Firmware/`, then update from Config.
- The PC ("Intel-Build") has not been reachable, so nothing was copied to the
  SD card and the Tracker's storage mode was never confirmed from here.
- Retrack (the looper for the original Tracker) has no licence, so its code is
  not copied; the looper here is written new on top of CE.
- How smooth the playhead looks cannot be known before it runs on the device.
  The screen's real redraw rate was not measured, and placing the playhead in
  1/16 pixel steps is untried on this chip.
- Every re-fire (each cycle in FIT, each pad press) is a hard cut and restart
  of the voice. That may click. A soft restart needs a small change inside
  the stock player and is left for the next slice.
- Loops plays the loop on one of the 8 track voices. A pattern note on that
  track replaces the loop. Use an empty track.
- An instrument whose envelope has no sustain fades out while looping, and a
  fine-tune LFO on the instrument overrides the FIT fine tune.
- FIT changes pitch; there is no time-stretch in this firmware.
- Inside Loops the Fn and value keys are taken over and handed back on exit.
  The manual test checks this.
- Details and the full list of differences from the plan are in section 11 of
  `docs/PLAN.md`. Open questions for Jordan are at the end of
  `docs/DESIGN.md`.
