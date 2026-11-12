# Screen layer map (CE, Tracker Mini)

Source: `.work/dev` (branch loops). Paths are relative to `.work/dev/core` unless noted. Read from code only; nothing here has run on a device. "Derived" = my arithmetic from code constants, not measured.

## 1. The display

- Panel mode: 800 x 480, `kConfig800_480` in `platforms/imx/3rdparty/FT812/FT81x_Config.h:55` (lcdWidth 800, lcdHeight 480, Hcycle 1056, Vcycle 525, Pclk 2, Rotate 1, Dither 1). Used by `DisplayDriverImpl::init`, `platforms/imx/source/DisplayDriverImpl.cpp:8`.
- Controller: FTDI/Bridgetek FT812 ("EVE") graphics coprocessor, driven over SPI. Library `libs/FT812/FT812.h` + `platforms/imx/3rdparty/FT812/`. Interface class `DisplayDriver` (`include/DisplayDriver.h`), impl `DisplayDriverImpl`.
- There is NO CPU-side framebuffer. The CPU writes a display list (DL) of 32-bit commands into the chip's 8 KiB DL RAM (`RAM_DL`, `FT81x.h:40`); the chip rasterises it live, scan-out is fixed hardware. `API_CMD_SWAP()` swaps the list at the next frame.
- Colour: the chip renders RGB (8 bit/channel in the DISP_RGB macro, `displayStructs.h:~246`; dither on). Colours are 0xRRGGBB, sometimes with alpha via `API_COLOR_A`.
- Refresh rate (derived): FT81x pixel clock = 60 MHz / Pclk(2) = 30 MHz; 1056 x 525 = 554,400 clocks/frame -> about 54 Hz scan-out. Assumes the 60 MHz system clock (`LOW_FREQ_BOUND` 58.8 MHz check in `FT81x.h:46`).
- Hard limits of a frame:
  - Whole-screen DL budget is 8172 bytes (about 2043 commands of 4 bytes). `cDisplay::step3` (`libs/NewDisplay/display.cpp:621`) adds up the cached DL size of every shown control; when `controlMemoryUsed + memoryUsed >= 8172` it `break`s and silently drops the rest. Controls are appended highest index first, so the earliest-created controls are drawn LAST (on top) and are the ones lost on overflow.
  - Each control's cached DL lives in RAM_G at `controlsRamStartAddress + index*8192` (`displayStructs.h:21-23`: 150000, step 8192, max `controlsCount = 65` controls total, handles are `int8_t`).
  - RAM_G is 1 MiB (`RAM_G_SIZE`, `FT81x.h:48`). Known uses: fonts from address 0 (chained, `display.cpp:259`), logo at 80000, icon bitmaps 110000-111700+ (`display.cpp:141-176`), control DL cache 150000..682480, JPEG/PNG area `imgRamAddress = 670000` to 1,000,000 (`displayStructs.h:25-27`). The control cache (65 slots) overlaps the image area from slot 63 (arithmetic). Free RAM_G for our own data: not found; the tail 1,000,000..1,048,576 looks unused but is not verified.
  - Fonts and bitmaps are written to RAM_G once in `cDisplay::begin` (`display.cpp:294`).

## 2. Screens ("modules")

Base class `ModuleBase`, `interface/core/modulesBase.h:20`. Pure virtuals: `update()`, `start(uint32_t options)`, `stop()`, `initDisplayControls()`, `destroyDisplayControls()`. Optional: `getCurrentModeIdx()`, `hideControlsUnderMiniMenu()`, `wasLastSwitchingSuccessfull()`. Public flag `moduleRefresh` (set 1 in start, 0 in stop) gates `update()`.

Registration (all static tables, no dynamic registry), `interface/core/interface.cpp`:
- `Interface::modules[]`, `modulesCount = 13` (lines 56-71): slots 0..12 = projectEditor, sampleImporter, patternEditor, samplePlayback, songEditor, instrumentEditor, sampleEditor, configEditor, sampleRecorder, performanceMode, imageViewer, nullptr (slot 11 free), masterParams. Include each module's header at top (lines 12-22).
- `Interface::modulesButtons[][3]` (lines 73-86): {button, module index, options}. `modulesButtonsCount = 11`.
- Each module is a global instance, e.g. `cImageViewer imageViewer;` (`imageViewer/fImageViewer.cpp:21`) with `extern` in its header.

Lifecycle (`interface.cpp`):
- `Interface::activateModule` (464): clears buttons/pots/pads, sets `onScreenModule`, shows song timer, calls `initDisplayControls()` then `start(options)`.
- `Interface::deactivateModule` (481): releases Shift, clears inputs, `stop()`, hides keyboard/popups/title bar/song timer, `display.resetControlQueue()`, `display.destroyModulesControls()` (all controls created after `setModulesControlDestroyPoint`, `display.cpp:838/852`). So controls are created fresh on every entry and destroyed on exit.
- `switchModuleByButton` (512) = deactivate + activate. Modules request a switch with `eventFunct(eventSwitchModule, ...)` / `eventSwitchToPreviousModule` (event enum `interfaceDefs.h:259`).
- `Interface::update` (131) runs every main-loop pass: `onScreenModule->update()` if `moduleRefresh`, then popups.

Top bar: `TitleBar titleBar` (`interface/core/titleBar.cpp`), global; module calls `titleBar->show(); titleBar->setTitle("...")`. Title label at x 9,y 13,w 270 font 4; right label right-aligned at x 790 (762 with battery); battery icon 28x13 at x 767,y 13 (Mini only, `BATTERY_ENABLED`, lines 14, 29-50).

Bottom labels: eight `cLabel` controls across the screen bottom plus one `cBgLabel` (see `imageViewer/gImageViewer.cpp:17-41`): x = (800/8)*i + 50 centred, y 424, w 94, h 55, font 3, colours `activeLabelsColors`; background strip `cBgLabel` x 0, y 425, w 800, h 54. Mini has only four Fn keys, so the layout on the Mini still uses the 8 slots (see section 6/7; mapping of 8 labels to Fn keys not read).

Popups: `mtPopups` (`interface/core/interfacePopups.cpp`, ticked in `Interface::update`), Mini menu popup `mtMenuPopup` (`interfaceMenuPopup.cpp`).

TEMPLATE screen: `interface/imageViewer/` (399 + 82 + 54 lines). Copy:
- `imageViewer.h` (class declaration, `extern cImageViewer imageViewer;`).
- `gImageViewer.cpp:3` `initDisplayControls()`: builds label[8], bgLabel, image, text box with `display.createControl<cXxx>(&prop)` using `strControlProperties` (x,y,w,h,style,colors,text,data,value).
- `fImageViewer.cpp:21` file-scope `static` input callbacks; `start()` (66) registers inputs with `ip->setButtonObj(...)`, shows title bar, calls `showDefaultScreen()` (`gImageViewer.cpp:57`, ends with `display.synchronizeRefresh()`); `stop()` (97) hides controls; `update()` (31) per-pass work.
- Menu handling for the Mini in every screen: `ip->setButtonObj(interfaceButtonMiniMenu, functMenu)` with `functMenu` -> `mtMenuPopup.showModulePopup(IV)` on press and `hideModulePopup(IV)` on release (`fImageViewer.cpp:381`). Middle key: `ip->setButtonObj(interfaceButtonMiniMiddle, ...)`.
- Plus the 11 `ip->setButtonObj(interfaceButtonX, buttonPress, functSwitchModule)` lines in `start()` so the stock screen-switch buttons still work.
Bigger examples with waveform: `interface/samplePlayback/` (`gSamplePlay.cpp`, `fSamplePlay.cpp`, `samplePlayback.h`). Convention: `g*.cpp` = graphics (controls), `f*.cpp` = functions (logic).

Control handles: `hControl` = `int8_t` index into `controlsTable[65]`. Typical calls on `display` (`display.h:61-137`): `createControl<T>`, `setControlShow/Hide`, `setControlValue/Text/Colors/Data/Position/Size/Style`, `refreshControl`, `synchronizeRefresh`.

## 3. Existing waveform drawing

Sample waveform (`libs/NewDisplay/spectrum.cpp`, `spectrumControl.h`), class `cSpectrum`, data `strTrackerSpectrum`:
- Data format: `int8_t upperData[600]; int8_t lowerData[600]` = per-column max/min peak, pre-scaled `/300` (so 16-bit sample -> about +-109). `spectrumType` 0 = vertical min/max lines, 1 = single polyline (silence/line; type 3 = spinner stub, empty), `pointsLimit` k200/k300/k600, `width`. Hard-coded 600 columns.
- Computed on CPU by `cGraphicProcessing::processSpectrum` (`interface/core/graphicProcessing.cpp:82, 157`; zoom helpers in `graphicProcessing.h`), reads PCM min/max per column (for streamed samples it reads from SD blocking, e.g. `readInstrumentFramesBlocking`, line ~200). Cost: CPU scans the whole zoomed window once per redraw; only done when something changed (`refreshSpectrum` flag).
- Draw cost: type 0 emits 2 VERTEX2F per column = up to 1200 vertices = about 4.8 KB of the 8 KB frame DL. `cSpectrum` has `update2/update3` but is constructed with `stagesCount = 1` (`spectrum.cpp:7`), so stages 2-3 are never run: effectively one DL chunk. Stereo = two controls (`spectrumControl[0]/[1]`), each half height. Mono height `MAX_16BIT/300` = 218 px, width 600 (`gSamplePlay.cpp:85-125`), at y = 75 + (300-218)/2 = 116.
- Colours: `Theme::waveformColors[2]` (line, centre line).
- Zoom: `strZoomParams` (`interfaceDefs.h:~300`): zoomStart/zoomEnd/zoomValue/zoomWidth in 0..65535 sample-position units; functions `spectrumResetZoom/AutoZoomIn/ChangeZoom`.
- Selection / loop / start / end markers: `cPoints` (`points.cpp`, `pointsControl.h`) with `strTrackerPoints{pointsType, startPoint, endPoint, loopPoint1, loopPoint2 (all int16 pixel x), selected mask, zerocrossed mask}`. Shaded region by additive blend (`SRC_ALPHA, ONE`) rectangle, lines with end ticks via `drawPoint` (`points.cpp:196`). Slice markers: `cSlicePoints` (`slice.cpp`, `sliceControl.h`). Colours `waveformPointsColors[4]`. Pixel positions are computed in `cSamplePlayback::processPoints` (`fSamplePlay.cpp:390`).
- Wavetable position bar: `cWtProgress` (`wtProgress.cpp`); granular cursor `cLineIndicator` (`lineIndicator.cpp`).

Playhead (`progressCursor.cpp`, `cProgressCursor`): `update()` draws ONE vertical line `LINES` from (posX+value, posY) to (posX+value, posY+height) when `0 < value < width`, colour `colors[1]` (`waveformProgressColors[2]`). 8 bytes of DL. `value` is the pixel column.
Update path while a sample plays: `cSamplePlayback::calcPlayProgressValue` (`fSamplePlay.cpp:2562`) throttled by `PLAY_REFRESH_US = 5000` (line 85, an elapsed-micros timer); reads `instrumentPlayer[displayedTrack].getWavePosition()` (0..65535), maps to 0..600 (with zoom: `mapClamped`), sets `refreshSpectrumProgress`; `update()` (line 165-168) then does `display.setControlValue(progressCursor, playProgressInSpectrum); display.refreshControl(progressCursor);`.
A separate sample editor uses the same trio (`gSampleEdit.cpp:126-134`: playhead, spectrumPoints, spectrum[2]).
No ping-pong/direction concept or smooth sub-pixel motion exists in the display code: the cursor is an integer-pixel line, redrawn on demand.

## 4. Drawing primitives

Raw FT81x command set via `API_*` (FT812.h): BEGIN(POINTS, LINES, LINE_STRIP, RECTS, BITMAPS, EDGE_STRIP_x...), VERTEX2F/VERTEX2II, COLOR/COLOR_A, LINE_WIDTH, POINT_SIZE, BLEND_FUNC, SCISSOR_XY/SIZE, STENCIL_*, SAVE_CONTEXT/RESTORE_CONTEXT, BITMAP_* (+ TRANSFORM A-F for scale/rotate), CALL/JUMP, plus coprocessor `API_CMD_TEXT/NUMBER/BUTTON/GAUGE/PROGRESS/SLIDER/DIAL/CLOCK/GRADIENT/SPINNER/KEYS/TOGGLE/SCALE/ROTATE/TRANSLATE/SETMATRIX/LOADIMAGE/INFLATE/MEMCPY/APPEND`. Vertex format 0 (`API_VERTEX_FORMAT(0)`, 16ths of a pixel? set in `step3`/`begin`; pixel coordinates are passed as plain ints in existing code, check `API_VERTEX2F` scaling before sub-pixel work: NOT checked).
Existing controls (`libs/NewDisplay/*Control.h`, `enControlId` at `displayStructs.h:137`): Bar, BgLabel, Frame, Edit, Img, Label, HorizontalBar, LineIndicator, List/NewList, Keyboard, NotePopup, MultiLabel, ParamValueList, Points, ProcessingPopup, ProgressCursor, SimpleText, SlicePoints, SongPlayer, Spectrum, StartScreen, TextBox, TextPopup, Tracker (pattern grid), WtProgress, Arrangement, Battery, BoxMenu, ImgList, ImgGrid, SimpleBox, NotesKeyboardLabel. `cSimpleBox` (`simpleBox.cpp`) and `cFrame` are the cheap rectangle controls; `cBgLabel` a filled strip.
Style flags (`controlsStyle`, `displayStructs.h:89`): CenterX/Y, RightX, Border, Background, RoundedBorder, NoTransparency, Gradient, BottomShadow, VerticalText, Underline, LimitTextWidth, number formats, `ShowBitmap`, `TransformImg`.
Fonts (`display.cpp:85-139`): 5 slots, 4-bit (L4) bitmap fonts. Active set 1 (`fontsData1`, loaded in `begin`, line 312): Roboto Mono Light 14, Light 17, Regular 14, Bold 17, Regular 12 -> `controlStyleFont1..5`. Set 2 (`fontsData2`) Liberation Sans Regular 14/17, Bold 14/17, Regular 12 (selectable via `setFont`, line ~1383). `createControl` strips an out-of-range font index (`display.h:80`), so Font6-8 do not exist. Text width table: `getTextWidth`.
Bitmaps (`bitmaps[]`, `display.cpp:141+`): play icon 20x20, loop icon 20x20 (`displayPlayIcon`, `displayLoopIcon`, L4), double arrows 18x15, up/down arrows 16x8, battery; Mini logo 172x172 L8. Raw RAM_G upload: `DisplayDriver::writeDataRAMG(data, size, dstAddr)`.
Colours/themes: `Theme` struct (`source/Themes.h:6`, about 60 colour arrays); `display.getTheme()`, `setTheme(idx)`, `setCustomTheme`; `DisplayThemes` = Original, Monochrome, Anniversary (`interfaceDefs.h:218`). Colour arrays are indexed per control (text, bg, border...). Re-apply with `display.setControlColors`.
Transparency: alpha via `API_COLOR_A` and `BLEND_FUNC`; additive blend used by `cPoints`. Animation: only via re-queuing controls; `autoRefresh` flag on a control re-queues it after every draw (`display.cpp` step2); no tween/animation engine.
Cheap: a few lines/rects/points (each 2-4 bytes DL per vertex), text (one bitmap per glyph via `string2Bitmaps`), changing colour. Expensive: per-column waveform (4.8 KB of the 8 KB DL for 600 cols), many list rows, large JPEG load (`readImgFromSd`, SD read + `CMD_LOADIMAGE`), CPU recompute of a spectrum (full-window scan), SD reads for streamed samples.
Idea (not in code): pre-render a waveform with the CPU into an `L8`/`ARGB` bitmap in RAM_G via `writeDataRAMG` and draw it with one BITMAPS command (a few bytes of DL) - needs a free RAM_G block and verified bitmap format; not tried.

## 5. Refresh and animation

Loop: single super-loop in `platforms/imx/source/PlatformTrackerIMX.cpp:149-165`: `usb->update(); DevConsole_Update(); updateHardware(); platform.update(); trackerInstance->update();`. `TrackerImpl::update` (`source/Tracker.cpp:163`): `engine.updateSdStream(); display.update(); engine.updateSdStream(); padsBacklight; exporter; sliceDetector; newFileManager.update(); mtInterface.update(); engine.updateSdStream(); sequencer.update();`. Audio is separate: `TrackerImpl::updateAudioBuffers` (`Tracker.cpp:~190`) is called by the platform audio path per I2S buffer (44.1 kHz; whether from an interrupt: not verified here). So drawing never blocks audio, but it shares the CPU with the main loop, which must run fast enough for SD streaming.
Display state machine `cDisplay::update` (`display.cpp:364`): returns immediately unless the coprocessor FIFO is empty (`isCoProEmpty`), then runs ONE step per call:
- step1 (`484`): take control at `refreshQueueBott`, `DLSTART`, call its `update()` (or update2..5 for later stages) to build commands into RAM_DL.
- step2 (`549`): `CMD_MEMCPY` the new DL from `RAM_DL` into that control's RAM_G slot; record `ramSize`; if `autoRefresh` and visible, re-queue itself.
- step3 (`621`): if no `stopAppend` pending, `DLSTART`, clear to `theme->backgroundColor`, `CMD_APPEND` every visible, already-drawn control's cached DL (reverse index order), `DISPLAY`, `CMD_SWAP`.
So one screen frame costs at least three `display.update()` passes plus a coprocessor idle wait in between; changing one control re-runs all three and re-appends everything (cheap: APPEND is on-chip). The effective update rate is therefore bounded by main-loop speed and coprocessor/SPI time, not by the 54 Hz scan-out; not measured.
Queue: `refreshControl(h)` pushes onto a FIFO (`controlsRefreshQueueSize = 66`), deduplicated. `synchronizeRefresh()` (933) holds the swap until everything queued so far is drawn (use after building a whole screen so it appears at once). `highPrioRefresh` controls refresh alone. `autoRefresh` re-queues a control forever.
For a smooth playhead: make it a tiny dedicated control (like `cProgressCursor`, 8 bytes of DL) kept apart from the heavy waveform control so only it is rebuilt, use `refreshControl` on a timer (compute the position in the module `update()`, as SP does at 5 ms) and set the integer column; sub-pixel motion would need either VERTEX_FORMAT change or a bitmap with a transform (not present). Cached waveform + small overlays is the right shape; avoid `refreshControl` on the big waveform each frame. Keep total DL < 8172 bytes.

## 6. Reaching a new screen without removing a stock one

Hardware buttons (`interface/core/interfaceDefs.h:65-190`): `interfaceButton0..43`; Mini-specific: `interfaceButtonMiniMiddle`=33, `MiniMenu`=34, `MiniFn1..4`=35..38, `MiniPlus10`=39, `MiniPlus1`=40, `MiniMinus1`=41, `MiniMinus10`=42, `interfaceButtonGame`=43 (the existing 0-32 names Play/Copy/Insert/Up/Delete/Rec/Shift/Left/Down/Right and the module buttons Params..Pattern are still used internally). Pads: `interfacePad0..31` + `interfacePadKey0`, `interfacePadsCount = 48`. One virtual pot `interfacePot0` (the +/-1, +/-10 keys feed it, `interfaceInputs.cpp:~190-285`).
Mini key scheme (`interfaceInputs.cpp`): `initSpecialMiniTrackerButtons` (286) binds Fn1..4 and +/-: `functMiniFn1..4` (97, 122, 147, 172) translate a Fn press into the stock module-button press of module `InterfaceMenuPopup::modules[mtConfig.interface.functionKeysBinding[n]]` (n = 0..3 plain, 4..7 with Shift held). `+/-` act as the pot; Shift+plus/minus = master volume (`changeMasterVolume`). Direction keys + Middle are "nav buttons" with an exclusive-lock (`buttonChange`, 26-50).
Module menu on the Mini: hold `interfaceButtonMiniMenu` -> `InterfaceMenuPopup::showModulePopup` shows a `cBoxMenu` 4 columns x 3 rows = 12 cells (`kMenuColumnsCount/RowsCount`, `interfaceMenuPopup.h:43-46`; 440x330 centred); releasing the button switches to the highlighted module. Content: `kMenuModulesCount = 11` module names (`interfaceMenuPopup.cpp:6-16`) and `ModuleRef modules[11]` (line ~30-42: module, button, options, mode table). The first 8 cells are the Fn bindings, the rest the unassigned remainder. So ONE grid cell (12th) is empty.
Cleanest ways in, without removing anything:
1. Add the new screen as `Interface::modules[11]` (slot 11 is already `nullptr`, `interface.cpp:68`; `modulesCount` stays 13) and add a 12th entry to `kModuleNamesList`, `InterfaceMenuPopup::modules[]`, and `kMenuModulesCount = 12` -> fills the free 12th cell. Check: `functionKeysBinding` is bounds-checked against `kMenuModulesCount` (`interfaceMenuPopup.cpp:95-98`), the config editor lists function choices (`configEditor/configMenu.cpp:~342`, `connfigMenuActions.cpp:200-225`); the stored binding is a config value so default bindings stay unchanged. Needs a `modulesButtons[]` row and a button id for it (use an unused `interfaceButton`, e.g. reuse `interfaceButtonNote/Instr` ids 18/19, which look unused on the Mini: not verified) - or leave the row out and switch with the event `eventSwitchModule`.
2. Or a button combination handled inside an existing screen's input setup (e.g. Shift + Fn, Shift + Middle). Not checked for conflicts per screen; grep `setButtonObj(interfaceButtonMini...` before choosing.
3. Or users bind it to a Fn / Shift+Fn slot via the existing "function keys" config (`setupFunctionKeys1..8`) once it is a menu module.
Stock screens, including all Fn bindings, keep working because you only append table entries.

## 7. Mini-specific parts in the screen layer

Define `TRACKER_MINI` (platform/makefile; absent for the original). About 55 `#ifdef TRACKER_MINI` blocks in `interface/` and display. Notable:
- `libs/NewDisplay/display.cpp:~300` and `bitmaps[]` (141): 172x172 logo instead of 160x172 (the poly logo is skipped on the Mini in `begin`).
- `interface/core/titleBar.cpp:14,29-50`: battery icon, right label shifted by 28 px.
- `interface/core/interfaceInputs.cpp`: Fn/+/- keys and nav-button lock (above).
- `interface/core/interfaceMenuPopup.cpp:19-42`: the module menu popup and mode lists (instrument params: 2 modes, master: 3, perform: 2).
- `interface/core/interface.cpp:264-270`: after the start screen, `initSpecialMiniTrackerButtons()` and battery monitoring are enabled before the pattern editor opens.
- `interface/core/interfaceDefs.h:~325`: `invertValForList = true` on Mini (list scroll direction).
- Per-screen: `patternEditor/fPatternEdit.cpp` (233, 1974, 2619, 4870), `samplePlayback/fSamplePlay.cpp` (691 excluded on Mini, 3142), `sampleRecorder/fSampleRec.cpp` (e.g. 177, 347, 552, 1353, 1963, 2675-2702), `performanceMode` (greenFrame colours, `gPerformance.cpp:178`), `instrumentEditor`, `masterParams/fMasterParams.cpp:451`, `configEditor` (menu items), `sampleImporter`, `projectEditor/fProjEdit.cpp:1734`.
- No coordinate scaling: all layout is absolute 800 x 480 pixel arithmetic (`800/8`, 424, 600 wide waveform area plus a 200 px right column on the sample screens). The Mini uses the same 800 x 480 panel as the Plus (`kConfig800_480` is the only config in `platforms/imx`). The original (mk66) has its own `DisplayDriverImpl` in `platforms/mk66/`.

## Not found / unverified
- Whether `updateAudioBuffers` is called from an interrupt or a DMA thread (only the callee found).
- Measured display update rate / SPI clock (SPI speed set in `MCU_Layer.cpp:185`, value not read).
- `VERTEX2F` fractional-pixel scaling (vertex format 0 vs 4); needed for sub-pixel playhead.
- Which RAM_G ranges are truly free for a custom bitmap; which `interfaceButton` ids are unused on the Mini.
- How the eight bottom label slots map onto four Mini Fn keys in screens other than imageViewer.
- Full list of `API_*` helper semantics (`FT812.h` only skimmed).
