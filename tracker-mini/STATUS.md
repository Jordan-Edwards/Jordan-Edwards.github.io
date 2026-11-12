# Status

Updated: 2026-11-11, 6:35 PM Central.

## Done

- Confirmed the Tracker Mini firmware is open source: Polyend's Tracker
  Community Edition covers the Original, the Plus and the Mini.
- Built the unmodified CE beta for the Mini from source
  (`out/TrackerMini_CE_1343677.ptf`). It is byte-identical to Polyend's own
  build of the same commit, so the build setup here is exact.
- `build.sh` rebuilds it, and can apply our patches on top.

## In progress

- Reading the CE source (audio engine, recorder, screens, Mini controls) and
  the Retrack looper, to design our own looper for the Mini.
- Reading the earlier Tracker Mini sessions for what was already done.

## Next

1. Design the looper ("Loops") feature inside CE for the Mini.
2. Implement it as patches in `patches/`, with tests that run on a computer
   for the parts that need no hardware.
3. Build `TrackerMini_Loops_*.ptf`, review it, and put it in `out/`.

## Open risks

- Nothing here has been flashed to a real Mini by us. A build can only be
  tried on the device by hand: copy to `/Firmware/`, then update from Config.
- The PC ("Intel-Build") has not been reachable, so nothing was copied to the
  SD card and the Tracker's storage mode was never confirmed from here.
- Retrack (the looper for the original Tracker) has no licence, so its code is
  not copied; the looper here is written new on top of CE.
