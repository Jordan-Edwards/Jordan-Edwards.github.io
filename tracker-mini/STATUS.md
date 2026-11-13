# Status

Updated: 2026-11-13, 5:00 AM Central.

## What Jordan asked for

- "The retracker thing, but our own upgraded version", on the Mini.
- The look matters: the playhead sweeping over the audio waves, back and forth
  in ping-pong, with visual feedback that is "clear what it's doing, but cool
  and smooth".
- The Mini and the Tracker+ are the same hardware, so use what the Plus can do.
- Report plainly what was found, what it makes possible, and where the limits
  of the hardware are.
- Notice when the Tracker is plugged back in, without being told.

## Done

- Confirmed the Tracker Mini firmware is open source: Polyend's Tracker
  Community Edition (CE) covers the Original, the Plus and the Mini.
- Built the unmodified CE beta for the Mini from source
  (`out/TrackerMini_CE_1343677.ptf`); byte-identical to Polyend's own build.
  Also a build with Polyend's USB development console
  (`out/TrackerMini_CE_1343677dev.ptf`) and a host script for it.
- Nov 11: saw the card in storage mode on the PC (TRACKER_M) and its firmware
  library (Stock 2.2.1, CE 1.0.0, Retrack8 RT4, Makam, Braids, Track3r, Scope,
  CEXY 0.2.2 / 0.2.3). Read only; nothing was written to it.
- Nov 13: read the Codex project notes on the PC. The newest work there is
  CEXY 0.3.2 (`G:\TRACKER_MINI_PHRASE_20261106\iteration03`), built on official
  CE 1.0.0, with a single captured take that can be auditioned. Its own
  direction note ("Seance / Afterimage") asks for four stereo phrase lanes with
  waveforms and visible playheads, and says not to go back to the older
  patched-2.2.1 builds such as Retrack8 RT4.
- A watcher runs on the PC (`tools/card_watcher.ps1`, log in
  `G:\TRACKER_MINI_CLAUDE_STAGING\watcher.log`). It logs when the Tracker card
  is plugged in or removed and adds builds listed in `out/CARD_MANIFEST` to the
  card's Firmware folder. The manifest is empty, so it copies nothing yet. It
  stops if the PC restarts.

## What went wrong

- No work happened between the evening of Nov 11 and the morning of Nov 13.
  The research run used up the usage limit on Nov 11, and after that every
  scheduled check-in failed with "access denied", so nothing restarted the
  work. Those four scheduled tasks are now switched off.

## In progress

- The looper engine (four stereo tracks, overdub with undo, reverse, ping-pong,
  half and double speed) with tests that run on a computer.
- A read-only study of the CEXY 0.3.2 source and build setup on the PC, to
  plan how the engine and a lanes screen go into it.

## Next

1. Put the engine into CEXY as a new iteration on the PC, leaving 0.3.2 as is.
2. Build the lanes screen with the sweeping playheads, in the Seance look.
3. Build with the PC's toolchain, review, and list the result in
   `out/CARD_MANIFEST` so the watcher adds it to the card.

## Open risks

- Nothing made here has been flashed to a real Mini.
- The looper needs about 25 MB of the Mini's 60 MB sample memory.
- Recording latency cannot be measured without the device; it starts as an
  estimate with a setting to adjust.
- Retrack (the looper for the original Tracker) has no licence, so its code is
  not copied; the engine here is written new.
