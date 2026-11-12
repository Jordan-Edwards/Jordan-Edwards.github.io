# Tracker Mini firmware work

Custom firmware for the Polyend Tracker Mini, built from Polyend's open-source
[Tracker Community Edition](https://github.com/polyend/tracker-ce) (CE).

Where things stand right now is in [STATUS.md](STATUS.md).

## Firmware files

| File | What it is | Tested on a Mini? |
|---|---|---|
| [`out/TrackerMini_CE_1343677.ptf`](out/TrackerMini_CE_1343677.ptf) | Unmodified Polyend CE beta (main at `1343677`, newer than CE 1.0.0). Built here and **byte-identical** to Polyend's own build of that commit. | It is Polyend's build; not flashed by us yet |
| [`out/TrackerMini_CE_1343677dev.ptf`](out/TrackerMini_CE_1343677dev.ptf) | The same source with Polyend's USB development console and logging switched on (`-DENABLE_DEV_CONSOLE -DENABLE_LOG`). Behaves like the build above unless the card has a `.develop` file. | No |
| [`out/TrackerMini_Loops_s1.ptf`](out/TrackerMini_Loops_s1.ptf) | The CE beta above plus our **Loops** screen, slice 1 (the five patches in [`patches/`](patches/), review fixes included). Stock screens are unchanged; Loops is the last cell of the hold-Menu module menu. Builds and passes host tests only. | No |

Checksums are in [`out/SHA256SUMS`](out/SHA256SUMS).

## Loops (reviewed by reading, not flashed yet)

"Loops" is our looper screen for the Mini: the current sample as a full-width
waveform, looped forward, reversed or ping-pong with a sweeping playhead, fitted
to bars, with slices on the four value keys. It is new code on top of CE, kept
as patches in [`patches/`](patches/). The design is in
[`docs/DESIGN.md`](docs/DESIGN.md), the build plan and what was actually built
in [`docs/PLAN.md`](docs/PLAN.md).

It builds (`./build.sh loops`) and its logic passes tests on a computer
(`tests/run.sh`). Two independent reviews read the code; the fixes that came out
of them are in the fifth patch. It has not run on a Mini. What to try first,
what was fixed and what is still open are in [STATUS.md](STATUS.md).

On the Loops screen: Middle starts and stops the loop. Fn1 Direction, Fn2 Sync
(FREE or FIT to bars), Fn3 Slices (8 or 16), Fn4 Track. Up and Down double and
halve the speed. The four value keys play slices while held; Left and Right
move them along the strip. Hold Menu to leave.

## Hands-off flashing (development console)

With the `dev` build on the Mini and an empty file named `.develop` in the root
of the SD card, the Mini shows up on the computer as a USB serial port. Over
that port a script can put the Mini in storage mode, copy a new `.ptf`, start
the firmware update and read the log, with nobody touching the device.
[`tools/tracker_dev.py`](tools/tracker_dev.py) does this
(`pip install pyserial`, then `python tools/tracker_dev.py ping`). The script
is written from Polyend's protocol notes and has not been run against a real
Mini yet.

## Put a build on the Mini

1. **Back up the `Projects/` folder** from the SD card first. Once a project is
   saved on CE firmware its patterns are in a newer format that the older
   official firmware cannot read.
2. Make sure a firmware you trust is also in `/Firmware/` on the card (your
   current official one), so you can always go back.
3. Copy the `.ptf` into `/Firmware/` on the card.
4. On the Mini: **Config > Firmware > Firmware update**, pick the file, confirm.

## Go back

- Normal way: **Config > Firmware > Firmware update** and pick the older `.ptf`.
- If a build will not boot: leave only a known-good `TrackerMini_*.ptf` in
  `/Firmware/`, power on, and press the recessed reset button next to the USB-C
  port with a pin. The bootloader flashes that file. The bootloader is separate
  from the firmware, so a bad build cannot remove it.

## Rebuild from source

```bash
./build.sh          # stock CE at the commit in CE_COMMIT
./build.sh loops    # CE plus every patch in patches/
```

Linux x86_64 with `git`, `make`, `python3`, `curl`. The script downloads the Arm
toolchain Polyend's CI uses (GNU Arm Embedded 10.3-2021.10).

```bash
tests/run.sh        # host tests for the Loops logic (needs g++ or clang++)
```

The tests compile the same `loopsLogic.cpp` that goes into the firmware. Only
that pure logic (state machine, fit maths, slices, playhead model) is tested on
a computer. The audio glue, the screen, the menu entry and the display controls
are not, and the tests run on a PC compiler, not the Arm one. By default the
source comes from the development checkout (`.work/dev`); the script warns when
that differs from the last patched build.

## Licence

The firmware is Polyend's, under the Polyend Tracker Community Edition License
(MIT with a no-commercial-clone clause): free to use, modify and share, not to
sell. The licence texts are in [`licenses/`](licenses/). This is a community
build, not supported by Polyend, and flashing it is at your own risk.

Copyright (c) 2020-2026 Polyend Sp. z o.o. and Polyend Tracker Community Edition Contributors.
