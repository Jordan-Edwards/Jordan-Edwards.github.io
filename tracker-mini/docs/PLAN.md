# Loops slice 1: build plan

For the engineer. Design: `docs/DESIGN.md`. Work only in `.work/dev` (branch `loops`); paths are relative to `.work/dev/core`
unless they start with `tracker-mini/`. Everything new sits inside `#ifdef TRACKER_MINI`, so the Plus and Original builds do
not change. Nothing has run on a device: report "builds" and "passes host tests", never "works".

## 1. Files to add
| File | Holds |
|---|---|
| `interface/loops/loopsLogic.h/.cpp` | Pure logic. Includes only `<stdint.h>`, `<math.h>`. Host-tested |
| `interface/loops/loopsEngine.h/.cpp` | Audio-side glue: `LoopsEngine loopsEngine` with `post(cmd)`, `audioTick()`, `fire()`, `status()`, `close()` |
| `interface/loops/loops.h`, `gLoops.cpp`, `fLoops.cpp` | Screen `cLoops loopsScreen` (`ModuleBase`), shaped like `interface/imageViewer/` |
| `libs/NewDisplay/loopWaveControl.h`, `loopWave.cpp` | `cLoopWave`: 200 bars, ruler, slice lines (static) |
| `libs/NewDisplay/loopStripControl.h`, `loopStrip.cpp` | `cLoopStrip`: slice cells and pad captions |
| `libs/NewDisplay/loopHeadControl.h`, `loopHead.cpp` | `cLoopHead`: playhead, glow, tail, arrow, edge flash, countdown (dynamic) |

New controls subclass `cDisplayControl` like `progressCursor.cpp` (pure virtuals `update`, `setStyle`, `setText`, `setValue`,
`setColors`, `setData`). The makefile finds new `.cpp` files by itself.

## 2. Files to change
| File | Change |
|---|---|
| `interface/core/interface.cpp` | include `loops/loops.h`; `modules[11] = &loopsScreen`; add row `{ interfaceButtonGame, 11, 0 }`, `modulesButtonsCount = 12` |
| `interface/core/interfaceMenuPopup.cpp/.h` | `kMenuModulesCount = 12`; add `"Loops"` and `{ mtInterface.modules[11], interfaceButtonGame, 0, nullptr }`; add `kFnBindableModulesCount = 11` |
| `interface/configEditor/configMenu.cpp` (343-355), `connfigMenuActions.cpp` (206) | use `kFnBindableModulesCount`: Loops is not offered as an Fn shortcut, so saved configs stay valid for stock firmware |
| `libs/NewDisplay/displayStructs.h` | three ids appended at the end of `enControlId` |
| `source/Tracker.cpp` (after `sequencer.tick`, line ~204) | `loopsEngine.audioTick();` |

Why `interfaceButtonGame` (43): no key produces it, no table row uses it, and all 11 stock screens already register it to
`functSwitchModule`. One new row lets every screen switch to Loops with no per-screen edit. The menu popup switches through
`eventSwitchModule` -> `switchModuleByButton`, which reads `modulesButtons`.

## 3. Screen (`gLoops.cpp`, `fLoops.cpp`)
- `initDisplayControls()`: `cLoopHead`, `cLoopStrip`, `cLoopWave`, 4 info `cLabel`s, 4 soft-key `cLabel`s (x centres
  100/300/500/700, y 424, w 194, h 55, like `label[6]` in `gSamplePlay.cpp`), one `cBgLabel` (0, 425, 800, 54). Positions:
  DESIGN section 3. Create the head first: the earliest-created control draws on top.
- `start()`: `moduleRefresh = 1`; take `mtProject.values.lastUsedInstrument`. Show a centred message and do not play when it is
  not a sample instrument, not `mtSampleTypeWaveFile`, in Wavetable or Granular mode, or `mtProject.sampleMemory[i].isStreamed`.
  Otherwise run `GP.processSpectrum` for L and R with zoom reset (as `cSamplePlayback::start`), then `reduceBars()`. Title:
  `titleBar->show(true)`, `setTitle("Loops")`, `showCurrentInstrumentOnRightLabel()`. It must be safe to call twice: the menu
  calls it again when you pick the screen you are on.
- Inputs in `start()`: the 12 `functSwitchModule` lines from `fSamplePlay.cpp:287-298`; Menu (`functMenu`, as
  `fSamplePlay.cpp:3414`); Play (copy `functPlayAction`, and `post(Rearm)` first when the loop is on); Middle; the D-pad; then
  override `interfaceButtonMiniFn1..4` and `interfaceButtonMiniPlus10/Plus1/Minus1/Minus10` with `setButtonObj(id, fn(state))`.
- Fn handlers: latch Shift at press. With Shift, forward as stock does: `ip->processButtonsInput(InterfaceMenuPopup::modules[
  mtConfig.interface.functionKeysBinding[4 + n]].button, state)`. Without: Direction, Sync, Slices, Track on press.
- Value-key handlers: with Shift call `mtInterface.changeMasterVolume(+-10 or +-1)` on press and hold (stock). Without:
  `post(PadDown, k)` on press, `post(PadUp)` on release; ignore hold.
- `stop()`: `loopsEngine.close()` (cuts the voice if it is ours), `moduleRefresh = 0`, then
  `mtInterface.initSpecialMiniTrackerButtons()`. Mini `clearAllButtons` skips buttons 35-42, so this call hands the keys back.
- `hideControlsUnderMiniMenu()`: hide wave, strip and head while the menu is up.
- `update()`: read `loopsEngine.status()`; refresh labels and strip only when their values change. When armed, playing or
  flashing and 16 ms have passed: read `instrumentPlayer[track].getWavePosition()`, run `HeadModel::advance()`, then
  `setControlData` and `refreshControl(head)`. Never refresh `cLoopWave` per frame.

## 4. State machine (`LoopsMachine`, pure; runs in the audio callback)
Commands from the UI: `Toggle`, `PadDown(k)`, `PadUp`, `Rearm`, `Close`. Per block: `onBlock(seqPlaying, stepEdge, globalPos,
voiceLost)`. Output: `None`, `FireFull`, `FireSlice(k)`, `Stop`.

| State | Event | Action, next state |
|---|---|---|
| IDLE | Toggle, pattern stopped | FireFull, LOOP |
| IDLE | Toggle, pattern playing | ARMED |
| ARMED | step edge with `globalPos % 16 == 0`, or pattern stops | FireFull, LOOP, `steps = 0` |
| ARMED | Toggle | IDLE |
| LOOP | Toggle | Stop, IDLE |
| LOOP | step edge | `steps++`; in FIT when `steps == cycleSteps`: FireFull, `steps = 0` |
| LOOP | Rearm (direction, sync, bars, track, Play) | pattern playing: ARMED (keeps sounding); stopped: FireFull |
| LOOP or IDLE | PadDown(k) | FireSlice(k), STUTTER (remember where it came from) |
| STUTTER | PadDown(j) | FireSlice(j) |
| STUTTER | PadUp, came from IDLE | Stop, IDLE |
| STUTTER | PadUp, came from LOOP | stopped: FireFull, LOOP; playing: FireFull at next `globalPos % 4 == 0`, LOOP, `steps = 0` |
| any | voiceLost or Close | (Stop on Close), IDLE |

`cycleSteps = bars * 16`, doubled for Ping-pong; bars is one of 1/4, 1/2, 1, 2, 4, 8, 16. `stepEdge`: `sequencer.isPlay()` and
`sequencer.ptrPlayer->globalPos` differs from the last block (last = -1 while stopped, so step 0 of a fresh start is an edge).
`voiceLost`: `instrumentPlayer[track].currentInstrument_idx != instr`.

## 5. Firing a note (`LoopsEngine::fire`, audio callback only)
```
strInstrument& ins = mtProject.instrument[instr];
save ins.playMode, startPoint, loopPoint1, loopPoint2, endPoint, tune, fineTune
ins.playMode   = (dir == PingPong) ? playModePingpong : playModeLoopForward;
ins.startPoint = ins.loopPoint1 = a;   ins.loopPoint2 = ins.endPoint = b;       // 0..65535
if (fit) { ins.tune = fit.tune; ins.fineTune = fit.cents; }
instrumentPlayer[track].noteOff(Sequencer::STEP_NOTE_OFF_CUT);
instrumentPlayer[track].noteOn(instr, 60, velocity, fx1_id, fx1_val, 0, 0);     // the 7-argument, AUDIO_CORE_RAM one
restore the seven fields
```
`a..b` is the instrument's own `startPoint..endPoint` for FireFull, or `sliceBounds()` for FireSlice. Reverse: `fx1_id =
FX_TYPE_REVERSE_PLAYBACK` (the loop then starts at the end point and runs backwards, `play_memory_loop_forward.cpp:101`);
otherwise no effect. `audioTick()` starts with `if (!open) return;` and does no allocation, SD access or logging. UI to audio:
`post()` writes one small command struct between `AudioNoInterrupts()` and `AudioInterrupts()`. Audio to UI: `volatile` fields.

Read these first, because the plan assumes them: (1) the value `fxReversePlayback` expects, and that the next plain note clears
it; (2) that nothing re-reads the instrument's points after `noteOn` (`playerEngine::update`, `refreshRegister`); if something
does, use `setForcedPoints`/`setPointsForceFlag` plus a forced play mode instead; (3) the velocity the stock preview passes
(`mtSequencer.cpp:2851`); (4) the gaps `checkLoopParameters` keeps between points; (5) what `sequencer.stop()` does to a voice.

## 6. Maths (all in `loopsLogic`)
```
Fit:   T = bars * 4 * 60 / bpm                 seconds per pass (4/4)
       F = sampleFrames * (b - a) / 65535      frames in the region
       S = 12 * log2(F / (44100 * T))          semitones;  n = round(S);  cents = round((S - n) * 100)
       tune = n - ins.tuneResample             note stays 60 (C5 = stored speed, kMiddleNoteIdx)
       valid when |S| <= 24;  autoBars = the allowed bar count with the smallest |S|
Slice: start = a + (b - a) * k / n;  end = a + (b - a) * (k + 1) / n
Bars:  bar[i] = max/min over spectrum columns 3i..3i+2 of both channels; px = value * 136 / 109, at least 1
Head:  x16 = pos * 12800 / 65536               1/16 px across 800 px; pos from the voice, never from tempo
       d = pos - prev;  wrap when |d| > (b - a) / 2 (flash both edges)
       ping-pong: dir = sign(d) after two reads in a row with |d| >= 8; a flip flashes the nearer edge 180 ms
       tail = clamp(smoothed px/s * 0.12, 16, 200) on the side it came from;  slice = (pos - a) * n / (b - a)
```
`cLoopHead::update()`: `API_VERTEX_FORMAT(4)`, draw, then `API_VERTEX_FORMAT(0)`; if the head lands in the wrong place on the
device, use whole pixels. Tail and flash use `API_BLEND_FUNC(SRC_ALPHA, ONE)` as `points.cpp` does, then restore the default.

## 7. Host tests
`tracker-mini/tests/loops/test_loops_logic.cpp` and `tracker-mini/tests/run.sh` (plain `g++ -std=c++17`, asserts, no framework;
compiles `loopsLogic.cpp` from `$CE_SRC`, default `.work/dev/core`). Cover: fit (a 125 BPM 2-bar loop at 130 BPM gives +0.68 st;
an exact fit gives 0; out of range is refused; autoBars); slice bounds for 8 and 16, with the last slice ending exactly on `b`;
bar reduction; every row of the state table, including Play re-arming and a pad released while the pattern plays; cycle counts
for 1/4 bar and for ping-pong; head direction, wrap and bounce on recorded position sequences.

## 8. Build and patch
1. Commit in `.work/dev` on `loops`, then `git -C .work/dev diff $(cat CE_COMMIT) loops > patches/0001-loops-slice1.patch`.
2. `echo Loops_s1 > LOOPS_NAME`, then `MAKEFLAGS=-j4 ./build.sh loops` (minutes; read `.work/build-loops.log`). Output:
   `out/TrackerMini_Loops_s1.ptf`. Add it to `out/SHA256SUMS` and the README table.
3. Compare the linker memory printout with the stock build log: SRAM_DTC growth must stay under 4 KB. Confirm `./build.sh`
   (stock) still gives the byte-identical file.

## 9. Order of work
Must: (1) an empty Loops screen reached from the menu, and back out; (2) the waveform; (3) Middle plays the loop, Fn1 direction,
playhead; (4) slices and pads. Should: (5) FIT and Up/Down; (6) bar start and per-cycle re-fire. Polish last: glow, tail, flash,
beat lamps, 1/16 px. Stopping after any step still shows the idea.

## 10. Manual test script (for Jordan, once flashed)
1. Back up `Projects/`. Copy `TrackerMini_Loops_s1.ptf` to `/Firmware/` and update from Config.
2. Stock check: play a pattern, press each Fn key, hold Menu. All as before, except the menu's last cell now says "Loops".
3. Pick an instrument that holds a drum loop (a normal sample). Hold Menu and choose Loops. The wave fills the screen.
4. Press Middle: the loop plays and the playhead sweeps.
5. Fn1: Reverse, then Ping-pong. The playhead should bounce at the ends with a flash.
6. Fn2 to FIT. Up and Down halve and double the speed. The bar count is on the screen.
7. Press Play. The pattern and the loop should start together. Listen for a minute.
8. Hold each value key: that slice stutters. Let go: the loop returns on the beat.
9. Fn3 to 16 slices. Left and Right move the four pads along the strip.
10. Leave by the menu. The loop stops. The Fn and value keys do their stock jobs. In Sample Playback the instrument's play mode
    and points are unchanged.
11. Tell us: is the playhead smooth (a phone video helps), any click at the loop point, the CPU % in Config while a loop and a
    full pattern play, and anything that felt wrong.

## 11. As built (slice 1), and where it differs from the plan above

State: builds with `./build.sh loops`; 48 host tests pass (`tests/run.sh`). Not run on a device. The changes made after
review are at the end of this section.

Checked in the source before writing (section 5, "read these first"):
1. `fxReversePlayback` takes any non-zero value (1 is used). A later note with another effect, or none, ends it (`seqFx` calls
   `endFx` on the previous effect). Loops also ends it itself when it lets go of the voice.
2. Something does defer: `envelopeNoteOn` only calls `play()` at once when the envelope is idle; otherwise it stacks the note
   and plays it later, after our values are restored. `noteOff(STEP_NOTE_OFF_CUT)` sets the envelope idle first, so with the cut
   in front `play()` runs inside `noteOn` and the borrow-and-restore holds. Without the cut it would not. Nothing else re-reads
   points or play mode unless the instrument editor sets `refreshRegister`; a fine-tune LFO does re-read `fineTune`.
3. The stock preview passes velocity as a Volume effect. Loops passes velocity -1 (none), so the instrument's own volume rules.
4. `playLoopForward` accepts start = loop 1 and loop 2 = end, and pulls loop 2 one frame inside the end.
5. `sequencer.stop()` only releases tracks the pattern has open notes on; our voice keeps playing. Stock Play, however, cuts all
   8 voices and `play()` clears every voice's step effects.

Differences from the plan:
- **Play does not post Rearm.** Because of point 5 the state machine watches the pattern start from the audio side: a running
  loop fires again on the pattern's first step (tested). Stopping the pattern leaves the loop running.
- **Pad release while the pattern plays** is the ARMED state with a quantum of 4 steps instead of a fifth state. The slice keeps
  sounding until the beat.
- **A pad pressed while ARMED** counts as coming from a running loop: releasing it goes back to waiting for the beat.
- **Fit cents** follow the player, which moves in a straight line between two semitones, not on a log scale. The shift shown on
  the screen is still the true value in semitones. After review the cents are rounded toward slow: the loop is never shorter
  than its bars and at most one cent step longer (tested).
- **Track change** is its own command: the old voice is cut, then the loop comes back on the new track (at the bar if the
  pattern plays).
- **Middle, Up and Down act once per press.** Stock turns a held D-pad key into repeated presses; Left and Right may repeat.
- **Value keys while the menu is up** move the menu selection, as stock. A pad that went down as a pad always comes up as one,
  even if Shift is pressed in between.
- **Ruler:** beat ticks are drawn up to 8 bars, bar ticks only above that. This keeps the waveform control's command list at
  about 2.2 KB, close to what a stock waveform control sends in one go.
- **Beat lamps and the arm countdown** are drawn by the playhead control, since they move.
- **Guards added:** a region under 16 frames is not played; a note that fails to start cuts any older note of ours and goes to
  idle. After every note-on the engine checks that the player really started (`getLengthIfPlaying()`); if the player had put
  the note off until later, it would start with the instrument's own settings, so that case is refused instead.
- **Section 2, `interfaceButtonGame`:** 11 stock screens register it, but the File screen does not. It makes no difference:
  the menu switches through `eventSwitchModule` and the `modulesButtons` table, not through each screen's key handlers.
- `kFnBindableModulesCount` is also used where the saved config is validated (`source/mtConfig.cpp`).
- **Patches:** four numbered files instead of one. `build.sh` applies them in name order. `.gitattributes` keeps them
  byte-exact, because two of the stock files they touch have Windows line ends.
- **Build name:** `Loops_s1`, as planned.

Not done:
- The development-build log line for the real display-list size (DESIGN section 7) was not added. DESIGN now says so.
- Section 8 step 3, rebuilding stock to confirm it is still byte-identical, was not repeated: `./build.sh` (stock) applies no
  patches, so nothing it uses has changed.

Measured from the build (linker printout, stock -> Loops): flash 1,702,396 -> 1,716,076 B (+13,680 B); SRAM_DTC 343,392 ->
346,680 B (+3,288 B); SRAM_ITC 114,640 -> 115,048 B (+408 B); SRAM_OC and EXTERNAL_RAM unchanged. SRAM_DTC is now 96.2 % full
(about 13 KB free), which is the tightest budget for later slices. (These are the figures before the review fixes; the
figures of the build in `out/` are just below.)

After review (patch `0005-loops-review-fixes.patch`):
- **A fitted loop that is in time is left alone.** At the end of a cycle the engine reads the voice's position. Within 6 ms
  of the loop's own wrap point (either end for Forward and Reverse, the start for Ping-pong) nothing is cut. Further off, it
  is cut and fired again as before. Play still restarts the loop on the pattern's first step.
- **Fit rounds toward slow**, so a correction cuts a little tail and does not play the start twice.
- **A voice that stopped by itself** (envelope ended, stock Play or Stop silenced it) is given up after about 0.7 s and the
  state goes to idle. The playhead no longer reads a stopped voice. Play pressed while a pad is held sounds the slice again.
- **A pad on a slice that cannot be played is ignored**; what sounds goes on. A refused start no longer cuts a
  pattern note of the same instrument when nothing of Loops' own is out.
- **Glide** is set to 0 for the loop's note and put back, like play mode, points and tune.
- **Snap to zero:** with the project setting on, a region no wider than the player's snap zone (128 position units) is not
  played.
- **Tempo follow** looks at the tempo four times a second, ignores changes under 0.05 BPM, keeps the last tempo when none
  is known, and redraws the waveform only when the bar count changes.
- **Fn2 with no bar count in reach** shows "FREE  no fit" in the info row.
- `tests/run.sh` warns when the development checkout differs from the last patched build.
- Measured from the final build (stock -> Loops): flash 1,702,396 -> 1,717,100 B (+14,704 B); SRAM_DTC 343,392 -> 346,688 B
  (+3,296 B, 96.18 % full, 13,760 B free); SRAM_ITC 114,640 -> 115,408 B (+768 B); SRAM_OC and EXTERNAL_RAM unchanged.
- The patched clean tree that was built and the `loops` branch in `.work/dev` have the same git tree
  (`d5fa426698e5807f87c022c45bfaa3d870868656`); the 48 host tests pass against both.
- Left open: see "Open risks" in `STATUS.md`.
