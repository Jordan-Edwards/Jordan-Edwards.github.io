# Mini controls, input, live features, testing, storage (source map)

Source: `.work/dev` (branch loops, CE_COMMIT). Paths are relative to it. All facts are from reading code; nothing was run on a device. "approx" = line number read from a grep, nearby.

## 1. Physical controls as the firmware sees them

### Build-time selection
- `platforms/imx/makefile` lines 17-23: `PRODUCT` = `MINI` (target `TrackerMini`) or `PLUS` (`TrackerPlus`). Lines 65-71: MINI adds `-DTRACKER_MINI`; PLUS adds include paths `3rdparty/Leds`, `3rdparty/radio`. Top `Makefile` targets `mini`/`plus` wrap this.
- `core/makefile:57`: `-DPLATFORM_IMX -DFEATURE_SYNTH` for both Plus and Mini (synth is compiled into both).
- Extra flags: `CUSTOM_DEFINES` (makefile line 63), e.g. `-DENABLE_DEV_CONSOLE -DENABLE_LOG`.
- Rule from `CONTRIBUTING.md:58-64`: never use `__MK66FX1M0__` in core (defined for both); use `PLATFORM_IMX` / `TRACKER_MINI`. Both form factors must be considered for any UI shortcut.
- `#ifdef TRACKER_MINI` blocks exist in ~20 UI files (config menu, sample recorder, pattern editor, performance, instrument/synth editors, titleBar, popups, notePopout, display.cpp, stream.cpp, mtAudioEngine.cpp:1627).

### What the Mini does NOT initialise (platforms/imx/source/hardware.cpp)
- Inside `#ifndef TRACKER_MINI`: radio (line ~75) and, from line ~104, **pads (`PadsImpl`), LEDs (`LedsImpl.init`), encoder (`EncoderImpl.init`)**. So on the Mini: **no pads, no pad LEDs, no encoder, no radio**.
- `updateHardware` (line ~132): Mini updates `BatteryImpl`; others update the encoder. Mini init also reads the battery and can refuse to start when it is empty and not charging (line ~49-66).
- `LedsImpl.h`: on the Mini `LedsImpl::setLed` still exists (virtual from `Leds` in `core/include/Platform.h:190`) but the LED driver (`LedsDriver.h`, `init`, `turnOff`) is `#ifndef TRACKER_MINI`. Treat LED calls as no-ops on the Mini (see section 3).
- `EncoderImpl.cpp`: Mini build has only empty `setAcceleration`/`setResolution`.

### Button indices (core/interface/core/interfaceDefs.h)
- Enum `mtInterfaceButtonsDef`: `interfaceButton0..43`, `interfaceButtonsCount` (44). Pots: only `interfacePot0` (`interfacePotsCount` 1). Pads: `interfacePad0..31`, `interfacePadKey0`, `interfacePadsCount = 48`.
- Names in `mtInterfaceButtonsFunctions` (same file, after the buttons enum):
  - 0-7 `interfaceButton0..7`: the 8 buttons under the screen on the Plus/Original (also used as step buttons, mute buttons; see `blockAllInputsExceptScreenButtons`). Not Mini hardware keys in the same sense (the Mini's own keys map via the table below).
  - Params 8, Performance 9, File 10, Config 11, Master 12, SampleLoad 13, SamplePlay 14, SampleEdit 15, SampleRec 16, Song 17, Note 18, Instr 19, Vol 20 (= Fx2), Fx 21 (= Fx1), Pattern 22.
  - Play 23, Copy 24, Insert 25, Up 26, Delete 27, Rec 28, Shift 29, Left 30, Down 31, Right 32.
  - **Mini only:** `interfaceButtonMiniMiddle` = 33 (centre of the D-pad), `MiniMenu` = 34, `MiniFn1..4` = 35..38 (the four screen keys), `MiniPlus10` = 39, `MiniPlus1` = 40, `MiniMinus1` = 41, `MiniMinus10` = 42. `interfaceButtonGame` = 43 (a Plus-class button, unrelated to Mini).
- Physical so logical mapping: `platforms/imx/source/ButtonsImpl.cpp` `convertToControlButtons[80]` (separate table for Mini, `#else` branch), key-matrix chip TCA8418 driver `Drivers/Keys.cpp/.h` (`BUTTON_MAX = 48`). Mini matrix config `begin(127, 255, ...)`, desktop `begin(255, 511, ...)`.
- Plus pad grid: `PadsImpl.cpp:6` `convertToGridKey4x12` (4 rows x 12 columns = 48 pads, matrix 255 x 1023). `pad % 12` = column/slot, `pad / 12` = row (used in `fPerformance.cpp:835 functPads`).
- Screen: 800 x 480 (`interfaceMenuPopup.cpp` uses `(800 - w) / 2`, `(480 - h) / 2`; image viewer docs say image area 800 x 390).

### Mini-specific substitutes for missing hardware
- **Encoder replaced by +10/+1/-1/-10**: `interfaceInputs.cpp:197-283` `functMiniPlus10/Plus1/Minus1/Minus10` send `processPotsInput(interfacePot0, +-10/+-1, state)`. With Shift held they change master volume instead (`changeMasterVolume`). Pot boost on Shift is `#ifndef TRACKER_MINI` (modulesBase.cpp, in `processPotsInput`).
- **Pads replaced by the on-screen note keyboard**: `interfacePopups.cpp` `toggleNoteKeyboardPopup` (`interfacePopups.h:75`), 8 note rectangles drawn (`notePopout.cpp:146`, `rectangleCount = 8`); Mini direction mapping in the step popup differs (`interfacePopups.cpp:~772`: left/right are inverted, up/down = -+12).
- **Performance pads replaced by +/- buttons**: `fPerformance.cpp:344-356`: the four buttons map to pad rows 0..3 (`10 -> row 0`, `1 -> row 1`, `-1 -> row 2`, `-10 -> row 3`) via `functPads(performanceEditPlace + row * 12, state, 0)`. This is the template for "buttons act as pads".
- **Function keys**: 4 screen keys. `interfaceInputs.cpp:97-195` `functMiniFn1..4`: Fn1-4 forward to `InterfaceMenuPopup::modules[mtConfig.interface.functionKeysBinding[i]].button`; Shift+Fn uses entries 4..7. So the 4 keys are user-bindable shortcuts to modules; they are registered through `Interface::initSpecialMiniTrackerButtons()` (line 286) as button objects. A new screen can override them via `setButtonObj` on 35-38 (see 2).
- **Menu button + D-pad middle**: `MiniMenu` calls `functMenu` in each screen (e.g. `fPerformance.cpp:144`) to open the module popup (`InterfaceMenuPopup`, 4 x 3 grid, 440 x 330, `interfaceMenuPopup.h`/`.cpp:19-30`). `MiniMiddle` is used as "enter/confirm" in popups and screens.
- **Reduced module set on Mini**: popup `modules[]` (`interfaceMenuPopup.cpp:~28-39`) lists 11 modules (Pattern, Instrument Params, SamplePlay, Master, Song, SampleLoad, File, Config, Perform, SampleEdit, SampleRec) with sub-modes for Instrument/Master/Perform (`ModuleModes`).
- No `interfaceButtonSampleLoad` etc. are physical on the Mini; they are logical IDs reached through the popup.

## 2. Input events and how a screen takes them

- Entry (core/interface/core/interfaceInputs.cpp):
  - `Interface::buttonChange(n, value)` (line 26): value is `buttonRelease=0, buttonPress=1, buttonHold=2, buttonDouble=3` (`interfaceDefs.h`). Hold is the platform's auto-repeat (see below). On Mini, the five navigation buttons (Middle, Up, Down, Left, Right) are **mutually exclusive**: the first pressed locks (`activeNavButton`), others ignored until it releases (lines 7-45). Hold events for buttons 25-27, 30-32 and Middle are converted to `buttonPress` (lines 48-52), meaning held direction keys auto-repeat as presses.
  - `padPressed/padReleased/padHold` (lines 78-93) call `processPadsInput(n, 1|0|2, velo)`.
  - `potChange` (line 20) = encoder.
  - `powerButtonChange` (line 60): Shift + power takes a screenshot (`display.scheduleScreenShot(1)`).
- Hold/repeat timing: `Drivers/Keys.cpp:10` `holdTimeStepDiff = {0,100,190,235,255,270}` and default `holdTime = 333` ms (`Keys.h:98`, `setHoldTime`). First repeat after 333 ms, then interval shortens in 6 steps (333, 233, 143, 98, 78, 63 ms). `Keys::isButtonHold(n)`.
- Dispatch (core/interface/core/modulesBase.h/.cpp, class `InputProcessor`):
  - Registration: `setButtonObj(id, state, void(*)(void))` (mode 1, fires only on that state), `setButtonObj(id, state, void(*)(uint8_t))` (mode 2, passes button id), `setButtonObj(id, void(*)(uint8_t state))` (mode 3, every state), `setButtonObj(id, void(*)(uint8_t btn, uint8_t state))` (mode 4); `setPotObj(id, fn(int16))` or `fn(int16, state)`; `setPadsGlobal(fn(pad, state, velo))` (one handler for all 48 pads; padStates in the pad handler: 0 release, 1 press, 2 hold; `enum padStates` has release/press/change). `setPowerButtonObj`.
  - `processButtonsInput` (modulesBase.cpp:234): per-button block flag, then the registered mode. Only one handler per button at a time (array `buttons[]`).
  - Claim / release: each screen's `start()` calls `ip->clearAll()`-style resets and then registers its own handlers; `clearAll`, `clearAllButtons`, `clearAllPots`, `clearGlobalPads`, `clearButton(n)`, `clearButtonsRange(from,to)` (modulesBase.cpp:19-90). Block flags: `blockAllInputs`, `blockAllInputsExcept(btn[,btn2])`, `blockAllInputsExceptScreenButtons()` (leaves first 8 buttons), `unblockAllInputs` (lines 94-137). Popups use these to take over input (e.g. `InterfaceMenuPopup` re-registers D-pad and `MiniMiddle` with `setButtonObj(interfaceButtonMiniMiddle, buttonPress, functMiddlePopup)` at `interfaceMenuPopup.cpp:225`).
  - Shift / combinations: there is no combination framework. Handlers ask `buttons->isButtonPressed(interfaceButtonShift)` (`Buttons::isButtonPressed`, modulesBase.cpp:~330, class in modulesBase.h:63) at press time. The Mini Fn keys latch Shift state at press in `fnButtonShiftPressed[4]` so release goes to the same target.
- Module life cycle (modulesBase.h `ModuleBase`): `start(options)`, `stop()`, `update()` (called every UI loop), `initDisplayControls()`, `destroyDisplayControls()`, optional `getCurrentModeIdx`, `hideControlsUnderMiniMenu`. Modules are registered in `core/interface/core/interface.cpp:56-72`: `modules[13]` = {0 projectEditor, 1 sampleImporter, 2 patternEditor, 3 samplePlayback, 4 songEditor, 5 instrumentEditor, 6 sampleEditor, 7 configEditor, 8 sampleRecorder, 9 performanceMode, 10 imageViewer, 11 nullptr (free slot), 12 masterParams}; `modulesCount = 13` (line 56) and `modulesButtons[11][3]` (line 73-84: button, module index, options) used by `switchModule` (lines ~517-545). **Index 11 is an unused slot in the table, but `modulesCount` and the Mini popup list (`kMenuModulesCount`, 12 cells, 11 used) will both need changes to add a screen.**
- Direct hardware state: `getPlatform()->getButtons()->isButtonPressed(n)` also works outside handlers (used by Mini nav code).

## 3. Pad and button lights

- API: `class Leds { virtual void setLed(int idx, bool enabled, int brightness) }` (`core/include/Platform.h:190`). Brightness is an int PWM level (config `mtConfig.values.padsLightFront/padsLightBack`, used in `mtKeyboardManager.cpp:121`). Only on/off + brightness per LED; no colour.
- Higher layers: `core/source/mtPadsBacklight.cpp/.h` (`cMtPadsBacklight`: back layer + front layer, blink, gamma PWM, lines 6-65); `mtKeyboardManager.cpp` (keyboard pad lights, caps lock etc.). `PM->lightUpPadBoard()` in performance mode.
- **Mini: the LED driver is not compiled or initialised** (section 1), so there are no pad/button lights to drive. No backlight/colour API for buttons found. The only visual feedback channel on the Mini is the 800 x 480 display.
- Display path: `core/libs/NewDisplay/` (`display.cpp`, controls such as `cBoxMenu`, `notePopout.cpp`, `stream.cpp`), `graphicProcessing`; themes `DisplayThemes` (original/monochrome/anniversary) with `display.getTheme().miniBoxMenuColors`.

## 4. Performance mode and live features (what a groove box can reuse)

- Performance module: `core/interface/performanceMode/` (`fPerformance.cpp`, `gPerformance.cpp`, `performanceEngine.h/.cpp`, `performanceFx.h/.cpp`, `performanceMode.h`). Modes `mtPerformanceMaster`, `mtPerformanceFxes`. `kPerformanceTracks = kAllTracks = 16` (`core/source/mtStructs.h:~90-103`): 8 sample tracks + 8 MIDI tracks; `tracksPage` toggles the two pages of 8 (`getTrackForButton`).
- Performance has 12 slots, each holding one performance FX with up to 4 values (`strPerformDataSource`: `fxInSlot[12]`, `valuesInSlot[12][4]`, `selectedValueInSlot`, `tracksPatterns`, `trackState`, `ccValues`). `functPads` (`fPerformance.cpp:835`): press on pad column = slot, row = value; also MIDI CC can control slots (`peformanceModeOnMidiCC`, `refreshAllCC`, 50 ms).
- Per-track live state in `performanceEngine`: `tracksPerformanceState[]`, `toggleTrackPerformanceState`, per-track pattern switching (`trackPatternChange[]`, `changeInstantlyTracksOnSelected`, `changeSequentiallyTracksOnSelected`, `turnOffAtEndOfPattern`) - i.e. per-track pattern chaining and mute-like toggles exist. Track mute: `strMtValues.trackMute[kSampleTracks]` (`mtStructs.h:871`).
- Performance FX list (`performanceFx.cpp`): Volume/Velocity, Sample panning, Bit depth, Overdrive, Tune, Sample LP / HP / BP cutoff, Sample delay send, Reverb send, Sample position, Sample end, Sample playback, Volume/Panning/Finetune/Filter/Gran-WT LFO speeds, Step stutter ("stepRepeaterPerfFx"), Pattern play mode, Pattern length. Each is `cPerformFx(id, name, setFunct(track,value), clearFunct(track), &fxSetup)`. `fxSetup`: min, max, labels, blocked FX, `isGlobalFx`. Adding a new performance FX = new `cPerformFx` + id; the engine is table driven.
- Mini mapping of performance: the 4 value buttons act as rows, Shift/Left/Right to move/swap slots (`fPerformance.cpp:424-560`). Fn keys + menu used for tracks page.
- Playing instruments / slices from pads: Plus/Original use the 48 pads (note keyboard via `mtKeyboardManager`); Mini uses the on-screen note keyboard popup and Sample Playback preview (`samplePlayback`, `interfaceButtonMiniMiddle` plays). Slice and Beat Slice instrument modes exist (CHANGELOG, developer_guide 5).
- Sequencer: `core/source/mtSequencer.h` (pattern/song playback, `getPatternToUI`); song editor `playlist[SONG_MAX=255]`. Fills/FX per step: pattern step FX (Fx1, Fx2, micro-move, volume columns, FX IDs via `fxIDs`/`fxIdToName`, `FX_COUNT`). Stutter/step repeater also appears as a performance FX.

## 5. Plus/Mini hardware beyond the original (as seen in code)

- RAM: `SAMPLE_MEMORY_SIZE = (60*1024 - 64)*1024` (~60 MB) on IMX vs 11.25 MB on MK66 (`mtStructs.h:~70`); `docs/developer_guide.md` section 1 has the budget: EXTERNAL_RAM 64 MB (only ~8 KB free as shipped, ~29 MB reclaimable by lowering `SAMPLE_MEMORY_SIZE` to 31 MB), SRAM_DTC 352 KB (~21 KB free), SRAM_ITC 128 KB (~22.5 KB free), SRAM_OC 32 KB (~9.3 KB free), QSPI flash ~16.2 MB (~14.5 MB free). Delay 1.5 MB, reverb 32 KB, shared scratch 768 KB (`SHARED_SCRATCH_MEMORY_SIZE`). Edit buffer 15 MB (`EDIT_BUFF_SIZE`).
- Stereo: `SAMPLE_CHANNELS = 2` on IMX (1 on MK66).
- Tracks: 8 sample + 8 MIDI (`kSampleTracks`, `kMidiTracks`); 48 sample instruments (`kSampleInstrumentsCount`), 16 MIDI, 3 synth (`kSynthInstrumentsCount`, `FEATURE_SYNTH`), total `kTotalInstrumentsCount`; `VoiceStreamManager::kMaxInstruments = 48`. Pattern sizes `k16TracksPatternSize` etc.
- Synth engines: `core/synth/` (`Synth.cpp`, `engines/`, `registry.cpp`), `synth/include/PolySynth/config.h` `InstrumentTypeId`; custom engines documented in `docs/custom_synth_sdk.md`. Also wavetable/granular instruments, modular `.ptfx` effects (`editor-fx-sdk/`, `docs/modular_effects_system.md`), `docs/wavetable_envelopes.md`.
- Sample streaming from SD: `core/AudioEngine/VoiceStreamManager.*`; IMX streams One-shot, Forward/Backward/Ping-Pong loop, Slice, Beat Slice (not Wavetable, Granular) for samples >= 256 KB (`kStreamThresholdBytes`), pre-cache 32768 frames (developer_guide section 1 and 5). Ping-pong loop is a native play mode.
- USB audio: `platforms/imx/source/UsbAudioImpl.*`, `Platform::getUsbAudio` (`beginFillData/fillChannelData/finishFillData`); also USB MIDI, UART MIDI (`getUsbMidi`, `getUartMidi`), USB storage mode. Recorder sources (`sampleRecorder.h:230-248`): Mini = LineIn, MicLG (Mini mic), USB, MicHG, Radio(listed; hardware absent on Mini); Plus = LineIn, Radio, MicLG, MicHG, USB. `mtConfig.audioCodecConfig` has `inSelect`, `inputGain`, line in/out levels (SGTL5000 codec, `Sgtl5000Impl`).
- Battery: `BatteryImpl` (MAX17262 fuel gauge, `Drivers/MAX17262.*`), `Battery` API: `getLevel/getVoltage/getCharging/getTimeTo` (`Platform.h:178`). Mini only.
- Radio: Plus only. Encoder, pads, LEDs: Plus only (section 1).

## 6. Testing without hardware

- Unit tests / simulator / host build: **not found** (searched `core`, `platforms`, root, `docs`, makefiles for test/sim targets; top-level `Makefile` has only all/original/plus/mini/ptfx/clean/version/bump-*). Host tests must be added by us; pure logic (loop state, ping-pong position math, quantise maths) can be separated from `core/` UI headers, which pull in the display, `mtStructs.h` and `Platform.h` (only plain C++ interfaces; a mock `Platform` is feasible because it is a pure virtual class).
- Screenshots: Shift + power button takes a screenshot (`Interface::powerButtonChange`, `display.scheduleScreenShot`). The display driver is a custom GPU-style list (`API_VERTEX2F`, `cBoxMenu`), so it cannot be run on a PC as is.
- Dev console and logging: `-DENABLE_DEV_CONSOLE` compiles `platforms/imx/source/DevConsole.cpp/.h` (4 KB buffer in SRAM_DTC); `-DENABLE_LOG` (or `DEBUG`) enables logging through `log.h` (`core/source/log.h`, `platforms/imx/source/log.h`). Hooks: `core/source/Tracker.cpp:151`, `core/source/mtActions.cpp:74`. The port only enumerates when the SD card root has an empty `.develop` file (`interfaceGlobals.devMode`; also shows diagnostics on the Config screen). `docs/developer_guide.md` section 8.
- Console protocol (`DevConsole.cpp:177-200`; developer_guide section 8): CDC serial, line commands: `ping` (reply `@tracker-dev <mini|plus> <build id>`), `storage on|off`, `flash <name>` (file in `/Firmware/`, at most 31 chars), `reboot`, `help`. Replies start with `@`; everything else is log output. Log is buffered until the host opens the port.
- `tools/tracker_dev.py` (203 lines, in the tracker-mini folder; not run against a real Mini): actions seen in `main()` (line 172): `ping`, `log [seconds]` (115200 baud, prints serial), `storage on|off`, `reboot`, `deploy <file.ptf>` (find SD card root, copy, flash). Helpers: `find_port`, `command`, `card_roots`, `sha256`, `deploy`. It does **not** cover: `flash` as its own action (only inside deploy), UI automation, button injection, screenshots, or anything on-device input. The firmware console has no button/pad injection command (list above). Adding an "input inject" command would be new firmware work.
- Build check: `./build.sh loops` builds; linker prints memory usage (`-print-memory-usage` in imx makefile line ~99), which is the best hardware-free check of RAM fit.

## 7. Project and config storage

- Project folder layout (`core/FileManager/fileManagerDefs.h:57-71`): `Workspace/project.mt` (working copy), `Workspace/patterns/pattern_NN.mtp`, `Workspace/patterns/patternsMetadata`, `Workspace/instruments/instrument_NN.pti`, `Workspace/samples/instrNN.wav`; saved project: `<Projects>/<name>/project.mt`, `patterns/pattern_%02d.mtp`, etc. Save pipeline: `FileManager/ProjectSave.*` (step machine, `copyProject`), `WorkspaceProjectSave/Load.*`, `ProjectOpen.*`, `fileManagerProject.cpp:639` builds the project path.
- Versions (`core/source/mtStructs.h:43-45`): `PROJECT_FILE_VERSION = 17`, `INSTRUMENT_FILE_VERSION = 9`, `PATTERN_FILE_VERSION = 6`. Old-version upgrade path: `FileManager/mtFileManagerOldVersionRecovery.h` ("to add a new translation just increase `PROJECT_FILE_VERSION`"; recovery counts = version - 1). `strMtProject` (`mtStructs.h:989`) holds instruments, `strSong`, `strMtValues`, runtime data.
- The README/CHANGELOG rule (CHANGELOG.md:9-14): saving on CE writes pattern files `.mtp` in Version 6, which older official firmware cannot read; loading old projects upgrades them in memory. So CE projects (once saved) do not open on official firmware. Back up `Projects/` first.
- Rules for new data (CONTRIBUTING.md:58-60): do not change integer values or order of serialised enums (e.g. `InstrumentTypeId`, pattern FX ids) or shift fields in project/patch/config structs. `docs/custom_synth_sdk.md:159` repeats it for instruments.
- Safe approach for Loops (design inference, not tested): store loop data as **a new sidecar file** inside the project folder (new name such as `loops.bin` with its own magic + version + size), written and read by new code only; never edit `strMtProject`, `.mt`, `.mtp` or `.pti` layouts. Older firmware (and stock CE) should simply ignore an unknown file, but **not found**: whether Save As / project copy (`ProjectSave::copyProject`, `FileManager` copy loops) copies unknown extra files, and whether project delete removes them. That must be checked in `ProjectSave.cpp`/`WorkspaceProjectSave.cpp` before relying on it. If it does not copy them, add the file to the copy/delete lists.
- Global settings: `strMtConfig` (`mtStructs.h:1018`) with header `{id[7], version, totalSize}` and sub-structs that begin with a `uint16_t size` field (audioCodecConfig, firmware, MIDI values, interface incl. `functionKeysBinding`, `padsLightFront/Back`...). The leading `size` fields exist so structs can grow at the end; add new settings as a new trailing sub-struct with its own size and default when the stored size is smaller. Config is stored through `ConfigManager` (`core/include/ConfigManager.h`, `platforms/imx/source/ConfigManagerImpl.*`). Not checked in detail: exact EEPROM/flash size limit for config.

## Not found / unverified
- Any simulator, host test target or CI test job.
- LED or colour feedback on the Mini (driver compiled out); button backlight control.
- Whether `ProjectSave` copies unknown files in a project folder.
- Exact line numbers for the buttons enum blocks in `interfaceDefs.h` (given by name only).
- Exact config storage size limit and config write path.
