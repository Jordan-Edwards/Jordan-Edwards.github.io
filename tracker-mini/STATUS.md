# Status

Updated: 2026-11-11, 10:48 PM Central.

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
  It covers the screen layout in pixels, what every key does, how the sound
  flows, the memory and CPU budget, and a plain report of what the hardware
  allows and where it stops.
- Planned the first slice for the engineer: [`docs/PLAN.md`](docs/PLAN.md).

What the reading found, in short:

- The Mini has no pads, no lights and no encoder. It has 18 keys and the
  800 x 480 screen. The four value keys (+10, +1, -1, -10) become the pads.
- Loop, reverse and ping-pong playback already exist in the firmware, and the
  play position can be read for the playhead. Slice 1 needs no new audio
  processing.
- There is no time-stretch. Fitting a loop to the tempo changes its pitch.
- The Mini menu has one empty cell, so Loops is added without removing
  anything.

## In progress

- Slice 1 of Loops, "see it and play it": the Loops screen in the Mini menu,
  the current instrument's sample as a full-width waveform, forward, reverse
  and ping-pong looping with a sweeping playhead, fit to bars at the project
  tempo, and slices stuttered from the four value keys. No code is written
  yet; this is design and plan only.

## Next

1. Build slice 1 as a patch in `patches/`, with tests that run on a computer
   for the logic that needs no hardware.
2. Build `TrackerMini_Loops_s1.ptf`, review it, and put it in `out/`.
3. Jordan flashes it and runs the short test script at the end of
   `docs/PLAN.md`.
4. Later slices, in order: keep a loop in the instrument and let it run on
   other screens; capture from the input; resample the Tracker's own output;
   several loop lanes; overdub.

## Open risks

- Nothing here has been flashed to a real Mini by us. A build can only be
  tried on the device by hand: copy to `/Firmware/`, then update from Config.
- The PC ("Intel-Build") has not been reachable, so nothing was copied to the
  SD card and the Tracker's storage mode was never confirmed from here.
- Retrack (the looper for the original Tracker) has no licence, so its code is
  not copied; the looper here is written new on top of CE. The Loops design
  was made from the CE source alone.
- How smooth the playhead looks cannot be known before it runs on the device.
  The screen's real redraw rate was not measured.
- Loops plays the loop on one of the 8 track voices. A pattern note on that
  track replaces the loop.
- Open questions for Jordan are listed at the end of `docs/DESIGN.md` (pad
  order, the screen keys as soft keys inside Loops, memory for capture).
