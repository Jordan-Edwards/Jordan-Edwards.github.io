# Audio engine map (CE source, .work/dev)

Paths are relative to `.work/dev/core/` unless they start with `platforms/`. Read from source only; nothing here was
run on a device. "Unverified" marks things inferred but not read.

## 1. Engine: rate, blocks, flow

- Block size: `AUDIO_BLOCK_SAMPLES 128` (`libs/Audio/AudioStream.h:51`), also `kAudioBlockSamples = 128`
  (`platforms/imx/config/config.h:10`). 128 frames = 2.9 ms per block at 44.1 kHz.
- Sample rate: the Teensy-legacy define `AUDIO_SAMPLE_RATE_EXACT 44117.647` (`AudioStream.h:52`) is NOT the Mini
  value. The IMX build uses exactly 44100.0 Hz (`source/Tracker.cpp` ~L197, `kAudioSampleRate`, comment: PLL4 ->
  44100.0 Hz for Tracker+ and Mini). Profiler also assumes 44100 (`source/Profiler.h`).
- Framework: the PJRC Teensy Audio Library fork in `libs/Audio/`: `AudioStream` objects joined by `AudioConnection`,
  int16 blocks (`audio_block_t`) from a static pool, `MAX_AUDIO_MEMORY 229376` bytes (`AudioStream.cpp:36`) = 896
  blocks (229376/128/2). `AudioStream::allocate` returns NULL when the pool is empty; players then output nothing
  (`play_memory_loop_pingpong.cpp` `if (!block) return nullptr`).
- Per-block driver: `TrackerImpl::updateAudioBuffers(left,right,len)` (`source/Tracker.cpp:181`). It runs
  `midiUpdate()`, then `sequencer.tick(len/44100)`, then `engine.update()`, then `engine.updateAudioBuffers` ->
  `AudioStream::update_all()` (`AudioEngine/mtAudioEngine.cpp:316`). Wrapped by
  `Profiler::startMeasuringAudio/stopMeasuringAudio`. So sequencer, note triggering and DSP all run in the SAME
  callback, once per 128-frame block.
- Callback entry on the Mini: `updateBuffers()` in `platforms/imx/source/PlatformTrackerIMX.cpp:82`, handed to
  `i2sOut.begin(...)` in `platforms/imx/source/AudioHardware.cpp:10`. Input side: `updateInputBuffers` (L96) ->
  `engine.updateInputAudioBuffers` (I2S line-in buffer + USB-in buffer). Unverified: that this is an interrupt/DMA
  context; the code marks the hot path `AUDIO_CORE_RAM` and uses `AudioNoInterrupts()` (see section 7), which supports
  that.
- Main loop: `TrackerImpl::update()` (`Tracker.cpp:158`): `engine.updateSdStream()` (3x per pass), display, pads
  backlight, exporter, slice detector, `newFileManager.update()`, `mtInterface.update()`, `sequencer.update()`. UI
  code therefore runs on the main loop, the audio on the callback.
- Graph (class `audioEngine`, `AudioEngine/mtAudioEngine.h:34`): `kVoices = 8` sample voices (`AudioVoice`, one per
  track), plus optional `SynthVoice` (`FEATURE_SYNTH`), `metronomeTick` (an `AudioPlayMemory`), `playerWavFromSD`
  (`AudioPlaySdWav`), `AudioInput input`, `MixerAndFxs`, `AudioOutput output`, `ExportQueues`. Per voice on IMX
  (`AudioEngine/AudioVoice.h`): per channel (L,R) `AudioPlayMemory -> AudioBitDepth -> AudioFilterStateVariable ->
  AudioAmplifier -> panning AudioAmplifier -> AudioAnalyzeRMS`. Voice -> `MixerAndFxs` (tracks mixer L/R, delay send,
  reverb send: `AudioEffectShortDelay`, `AudioEffectPolyverb`) -> **master mix**.
- Master output (`AudioEngine/AudioOutput.cpp`): `limiterSidechainMux` -> `AudioEffectLimiter limiter[L/R]` ->
  `finalMixer[L/R]` (`AudioMixer<FinalMixInputs::kFinalMixerSize>`) -> `outputStream` (`AudioOutputStream`, wired to
  the I2S buffers by `output.getStream()->setOutBuffers(left,right)`). The same `finalMixer` also feeds `usbOutput`
  (master pair plus per-track USB channels, IMX only). Extra master processing: `AudioEngine/MasterEnhancer/` (bass
  enhance, 5-band EQ, surround, auto volume).
- `ExportQueues` (`AudioEngine/ExportQueues.h`) taps the output for rendering; `AudioStream::renderMode` makes
  `update_all()` and the callback return early so export can pump the graph synchronously.

## 2. Sample playback

- Voice player: `class AudioPlayMemory : public AudioStream` (`libs/Audio/play_memory.h:38`). One per voice per
  channel; the high-level wrapper is `playerEngine` (`AudioEngine/mtAudioEngine.h:267`), global array `playerEngine
  instrumentPlayer[8]` (`mtAudioEngine.cpp:24`, extern at `mtAudioEngine.h:833`). `playerEngine::playMemPtr` is a
  `vector<AudioPlayMemory*>`, one entry per channel.
- Play modes: `enum instrumentPlayMode` (`source/mtStructs.h:387`): `playModeSingleShot=0, LoopForward, LoopBackward,
  Pingpong, Slice, BeatSlice, Wavetable, Granular`. All exist as engine code: `play_memory_single_shot.cpp`,
  `_loop_forward`, `_loop_backward`, `_loop_pingpong`, `_slice`, `_beat_slice`, `_wavetable`, `_granular`. Reverse is
  separate (`reverseDirectionFlag`, `setReverse()`); each loop mode has Normal and Reverse update functions.
- Ping-pong (`play_memory_loop_pingpong.cpp`): `playLoopPingpong` just calls `playLoopForward`;
  `updateLoopPingPongNormal/Reverse` bounce between `constrainsInSamples.loopPoint1/loopPoint2` (clamped by `length`
  and `endPoint`), direction in `loopBackwardFlag` (private; "playhead direction in the loop"). A ready-made
  forward/backward bounce exists.
- Points representation: instrument stores `startPoint, loopPoint1, loopPoint2, endPoint` as `uint16_t` positions
  0..65535 of the sample (`strInstrument`, `mtStructs.h` ~L620; `MAX_16BIT = 65535`, L53). The player converts to
  frames in `pointsInSamples {start,end,loop1,loop2}` and `constrainsInSamples`. Sequencer/performance can override
  them through `setForcedPoints(sp,lp1,lp2,ep)` (-1 = keep) with `setPointsForceFlag()`;
  `playerEngine::modSeqPoints(sp,ep,fx_n)`.
- Pitch/speed: a float `pitchControl` is the step per output frame; looked up from `AudioPlayMemory::notes[120]`
  (`NOTE_LOOKUP_SIZE`) built in `initNotesLookup` (applies a clock correction). Position is accumulated in
  `fPitchCounter` (fraction) and `iPitchCounter` (integer frame offset). Glide/slide/finetune adjust `pitchControl`
  per frame (`pitchSmoothing*`). Linear interpolation is on by default (`enableInterpolation`,
  `setInterpolationEnable`). Speed is therefore tied to the note: no separate time-stretch exists (not found; see
  section 8). `playerEngine::modPitch/modFineTune/modTune`, `slide()` drive it.
- Reading the play position (for a playhead): `uint16_t AudioPlayMemory::getPosition()` (`play_memory.cpp:1037`) =
  `65535 * (pointsInSamples.start + iPitchCounter) / currentSampleLength`. Reached via
  `playerEngine::getWavePosition()` (`mtAudioEngine.cpp:2205`, reads channel 0). Also
  `getWaveStartAddressIfPlaying(ch)` and `getLengthIfPlaying()`. Existing consumers: sample editor playhead
  (`interface/sampleEditor/fSampleEdit.cpp:794,884`), recorder preview (`fSampleRec.cpp:2832`), sample playback screen
  (`interface/samplePlayback/fSamplePlay.cpp:2567`, per-track `instrumentPlayer[displayedTrack]`). The value is a
  plain read of a non-volatile counter by the UI loop; fine for drawing, stale by at most one block (2.9 ms). Caveat:
  it is relative to the whole sample, and in ping-pong it moves back and forth (counter goes down while
  `loopBackwardFlag`), which is what a ping-pong playhead needs. For streamed instruments the same `iPitchCounter` is
  used (`updateStreamPlayhead`).
- Slices: `playModeSlice` (up to `sliceNumber` slices per instrument, `mtSliceManager`), `playModeBeatSlice`
  (`play_memory_beat_slice.cpp`).
- Envelopes inside the player: per-instrument amp ADSR plus assignable envelopes/LFOs
  (`AudioVoice::EnvelopeGeneratorType`: filter, wavetable / granular position, panning, finetune). A hook for
  tempo-synced envelopes exists: `envelopeSyncTrackerSeq(seqTimer, seqSpeed)` fed by `mtAudioUpdateHandle.cpp:165`
  from `sequencer.getSeqTimer()`.

## 3. Sample memory

- Pool: `externalRamSampleMemory[SAMPLE_MEMORY_SIZE/2]` in section `.sample_memory` (`source/Tracker.cpp:22`). On
  Mini/Plus `SAMPLE_MEMORY_SIZE = (60*1024 - 64) * 1024` bytes (~60 MB, comment "minus 64 KB for pattern buffers"),
  external RAM 64 MB at 0x80000000 (`mtStructs.h:67-71`). Original Tracker: 45*256 KB = 11.25 MB, 16 MB RAM. Comment
  there says 11.25 MB = 133.7 s mono.
- 16-bit signed PCM (`int16_t*`), `SAMPLE_CHANNELS = 2` on IMX (1 on the original) (`mtStructs.h:78`). Stereo is
  stored planar: channel 1 starts at `buffer + channelMaxLength` (`Recorder::setConfig`). 60 MB / 4 bytes = ~15.7 M
  stereo frames = ~356 s stereo (or ~712 s mono) at 44.1 kHz (my arithmetic from the constants; the real usable amount
  is lower: see edit buffer below).
- Edit buffer: `EDIT_BUFF_SIZE = 15*256 KB` (3.75 MB); `EDIT_BUFF_OFFSET = SAMPLE_MEMORY_SIZE -
  2*SAMPLE_CHANNELS*EDIT_BUFF_SIZE` (`mtStructs.h:80-85`), i.e. the top ~15 MB of the pool is the effects/edit scratch
  (`externalRamEffectsBuff`, `Tracker.cpp:28`). Other fixed external RAM: `DELAY_MEMORY_SIZE` 1.5 MB,
  `REVERB_MEMORY_SIZE` 32 KB, `SHARED_SCRATCH_MEMORY_SIZE` 768 KB (`mtStructs.h:73-75`).
- Instruments: `kSampleInstrumentsCount = 48` (`mtStructs.h:105`), array `mtProject.instrument[48]`. Sample slot:
  `strInstrument::sample {type, file_name[32], int16_t* address, uint32_t length, wavetable fields}`.
  `mtProject.max_memory = SAMPLE_MEMORY_SIZE`, `used_memory` tracked (`mtStructs.h:~1000`).
- SD streaming (new in this CE commit): `AudioEngine/VoiceStreamManager.h`. `kVoiceCount 8`, `kRingFrames 16384` per
  channel (~371 ms), `kChunkFrames 4096` per async ADMA2 read, `kLoopWrapFrames 2048`, `kLookbehindFrames 512`.
  Samples longer than `kStreamPreCacheFrames = 32768` (~743 ms) are streamed when `isStreamPreferred()` (flag in
  `name[3]=='S'`) or they do not fit RAM (`FileManager/fileManagerInstrument.cpp:149-152`, `kStreamThresholdBytes =
  256 KB`, `mtStructs.h:779`). The pre-cache head stays in RAM; the rest is read from the card. Pumped from the main
  loop (`updateSdStream`, 3x per `TrackerImpl::update`). `getSample()` and `updateVoicePlayhead()` are
  `AUDIO_CORE_RAM` and called from the audio callback. A looped streamed sample uses a loop-wrap pre-cache.
  Implication: a loop that is long and streamed depends on the card keeping up; a short loop held in RAM does not.
- What the Mini/Plus adds over the original: stereo samples (2 channels per voice, `#ifdef PLATFORM_IMX`), 64 MB RAM /
  ~60 MB sample pool vs 11.25 MB, USB audio in/out (master plus per-track channels), SD streaming of instruments (the
  `VoiceStreamManager` mentions Mini/Plus-only `kMaxChannels=2`), 8 sample + 8 MIDI tracks (`kSampleTracks`,
  `kMidiTracks`).

## 4. Recording

- Class `Recorder` (`source/Recorder.h/.cpp`), global `recorder`. Config: destination buffer/size/channels, source
  channel count, and `Source { kUsb, kI2s }` (IMX only). That is the only source switch in the recorder core.
- UI source list `cSampleRecorder::sourceType` (`interface/sampleRecorder/ sampleRecorder.h:230`): LineIn, MicLG (the
  Mini's built-in mic), Usb, MicHG, Radio (order for `TRACKER_MINI`). Radio and mics are I2S inputs routed by
  codec/radio hardware, not by `Recorder`. `inputSelect {LineIn, Mic}` (`mtStructs.h:473`).
- NOT found: any "resample master / internal" recording source. Searched `Recorder.*`, `AudioInput.*`,
  `sampleRecorder.h`, `AudioEngine/*.h` for resample/master/record-master: nothing. `ExportQueues` + `Exporter/`
  render the song to a file offline (separate path).
- Capture: `Recorder::record()` takes `AudioRecordQueue` objects from `AudioInput` (I2S: `getRecordingQueueI2s`, USB:
  `getRecordingQueueUsb`), `begin()`s them; `Recorder::update()` (main loop, called from the recorder screen) copies
  whole 128-frame blocks from the queues into the buffer at `recordingHeadIdx` (memcpy for stereo, average-down for
  stereo->mono). Stops itself when `recordingHeadIdx >= maxLength - 128` and calls the full-memory callback. Mic = 1
  source channel, 1 destination channel; line-in/USB = 2 and 2 (`fSampleRec.cpp:1522-1550`).
- Storage: the destination is `externalRamSampleMemory` itself, the WHOLE sample pool (`fSampleRec.cpp:1530-1531`,
  `wasSampleMemoryOverwritten = 1`). Recording overwrites loaded samples in RAM; the recorder screen then saves to a
  WAV in `recordingDirPath` through `newFileManager.saveRecordedSound(dir, name, optionalInstrumentSlot, leftAddr,
  rightAddr, length)` (`fSampleRec.cpp:1276-1330`). With the "save and load" type it picks the first free instrument
  slot (`isActive == 0`) and the file manager imports it as an instrument. After leaving the recorder, the project's
  samples have to be reloaded (L2296 `wasSampleMemoryOverwritten` check; exact reload not read).
- Sequencer while recording: the recorder module asks to stop a playing pattern (`fSampleRec.cpp:288`
  `sequencer.isPlay()` -> `functStopPatternYes()` `sequencer.stop()`, L1387), BUT the sequencer has explicit support
  for recording with a metronome/pre-roll: `Sequencer:: tick_uStep` (`mtSequencer.cpp:~178`) ticks the metronome when
  `SR->recordInProgressFlag` or pre-roll is active. So: the stock UI does not record while the song plays and plays
  only the click. Whether the engine could do both is unproven: recording overwrites the same pool that playing
  samples are read from, so playing samples while recording into the pool would corrupt them. A loop recorder needs
  its own buffer region.
- Latency/gating: `AudioInput` has `gate[]` (`AudioEffectDynamics`), `stereoToMono`, per-channel RMS
  (`getRecordingRmsI2s`), USB amplifier.

## 5. Tempo and sync

- Class `Sequencer`, global `sequencer` (`source/mtSequencer.h/.cpp`).
- BPM: `mtProject.values.globalTempo` (float, default `DEFAULT_TEMPO 130`, `mtStructs.h:49,893`);
  `Sequencer::MIN_TEMPO 40`, `MAX_TEMPO 800` (`mtSequencer.cpp:49-50`); tempo FX range 5..200. Read with `float
  Sequencer::getCurrentTempo()` (L2248: tempo FX if active, else project tempo, else `externalTempo` when on external
  clock).
- Time base: `kStepsPerBeat = 4`, `kuStepsInStep = 48`, `kNanoStepsInUStep = 12`, `kTicksInStep = 576`
  (`mtSequencer.h:946-950,~943`). uStep period `312500 / tempo / 12` us (`getTimerPeriod_us`, L2295; swing variant).
  `Sequencer::tick(intervalSeconds)` (L91) accumulates block time and calls `tick_uStep()` for each uStep that falls
  inside this block; it passes the sub-block offset to MIDI (`midiSetClockSubBlockOffsetUs`). So step and bar
  boundaries are resolved to a fraction of a block inside the callback, but the AUDIO triggered by them starts at the
  top of the next block (see `engine.update()` after `tick`): a 2.9 ms quantization, which is fine for a looper start.
- Observable state: `sequencer.isPlay()`, `isStop()`, `isRec()`, `getSeqState()` (stop / pattern / song / performance
  / selection), `getActualPos()` (track 0 step index), `getPatternLength()` (`track[0].length + 1`), `getSeqTimer()`
  (monotonic `timerTicks`), and the public read-only `ptrPlayer` (`strPlayer`: `isPlay`, `uStep`, `globalPos`,
  per-track `uStep`, `actual_pos`, `stepTimer`...). Pattern length max: step index `MAXSTEP = 127`
  (`mtSequencer.h:67`), default 32 (`DEFAULT_PATTERN_LENGTH`).
- Callbacks (function pointers, NOT lists): `player.onGlobalStep` (called each global step, `mtSequencer.cpp:2330`),
  `onPatternOrSelectionEnd`, `onSongEnd`, `preRollMetronomeEndCalback`. Declared in `strPlayer`
  (`mtSequencer.h:594-596`). The Sequencer clears `onGlobalStep` in its reset (L1594); these are in the private
  `player` struct, so a new feature needs a small accessor patch to use them (not found: a public setter).
- Start exactly on a step/bar: the project has no "quantized start" API. Use `ptrPlayer->globalPos` / `uStep` and
  `getSeqTimer() % kTicksInStep` (576 ticks per step; `kTicksInStep` is private) to arm and fire from code that runs
  inside the callback (the `onGlobalStep` hook or a call placed beside `sequencer.tick`). A bar = `kStepsPerBeat *
  numerator` steps via `getMetronomeNumerator/Denominator`.
- Play/stop control: `sequencer.playPattern()`, `playSong()`, `stop()` (`fSampleRec.cpp:2888-2897`), MIDI-clock:
  `handleMidiInStart/Stop/Clock`, `setExternalClockComp`. Stop requested from the callback is deferred:
  `stop(StopContext::audioCallback)` sets flags that `update()` (main loop) completes because the callback must not
  use the SD card.

## 6. Preview / audition paths

1. `playerEngine::noteOn(instr_idx, note, velocity)` and the 7-arg overload with fx (`mtAudioNoteOnHandle.cpp:9`).
   Needs an active instrument; sets up all envelopes, calls `AudioNoInterrupts()`. Pattern-screen pads use it via
   `Sequencer::handleNoteOn` (`mtSequencer.cpp:2584`, call at ~L2851 on `instrumentPlayer[trackIdx]`, `noteOff()`
   first). This plays the real instrument with its stored play mode (loop forward, ping-pong, etc.), points, filter,
   envelopes. Best fit for "play an instrument as a loop": set the instrument to `playModeLoopForward/Pingpong` and
   loop points, then `noteOn`.
2. `playerEngine::noteOnWithoutInstrument(vector<int16_t*> addr, len, type, note=255, velocity=-1)`
   (`mtAudioEngine.cpp:2110`): plays raw buffers (one per channel) with a neutral chain (limiter pass-through, pan 50,
   no sends). Used by the sample editor and recorder preview through `mtPadBoard.startNoteWithoutInstrument`
   (`source/mtPadBoard.cpp:28`) which picks a free of the 8 voices (`getEmptyVoice`), tracks the source in `voices[]`
   and `stopInstrument(source)` / `cutInstrument`. No instrument needed; but no loop points either (it plays the
   buffer once, as a single shot as far as read) so loop control needs path 1 or a custom player.
3. Both take voices from the same 8 that the 8 sample tracks use (`instrumentPlayer[8]`). `cMtPadBoard::getEmptyVoice`
   returns the first free (stock pad previews use voices 0..voicesCount-1, `configureInstrumentPlayer`). A looper that
   holds a voice must not collide with the sequencer playing that track; choose a track index or stop the sequencer
   (`getSeqState()==1` guards exist in `releaseAllInstruments`: it does nothing while a pattern plays).
4. Simplest safe hook for a new screen (my judgement, unverified on hardware): use path 1 on a dedicated voice: set
   `mtProject.instrument[n].playMode`, loop points and `isActive`, then `instrumentPlayer[v].noteOff()` + `noteOn(n,
   note, vel)`; draw the playhead from `instrumentPlayer[v]. getWavePosition()`; stop with `noteOff(-3)` (cut, as
   padboard does). Drawing code reads `getWavePosition()` from the main loop like `fSampleEdit.cpp:794`. For a
   looper-owned buffer (recorded loop not in an instrument) path 2 plus a loop-flag patch is needed.
   `AudioPlayMemory::playForPrev(addr,len,type)` is the lowest-level loopless preview entry.

## 7. CPU, memory and real-time rules

- CPU meter: `Profiler` (`source/Profiler.h/.cpp`): `getAudioProcessingUsagePercent(usage, resetTempMax)` returns
  min/max/tempMax/average/last of the callback duration as % of the block budget (`kMaxAudioUpdateTime = 128 / 44100
  s` = 2902 us). Shown in the title bar (`interface/core/titleBar.cpp:260`) and the config screen
  (`interface/configEditor/gConfigEdit.cpp:919`). `freeRamBytes()` and `maxStackBytes()` (stack watermark 0xAA) also
  exist (gConfigEdit L942). No number for the percent at max polyphony was found in code comments.
- Whole audio path per block must finish in ~2.9 ms. Hot functions are tagged `AUDIO_CORE_RAM` (code in fast RAM): the
  update functions, `Sequencer::tick`, `AudioStream::allocate`, `VoiceStreamManager::getSample`. Setup/slow code is
  `AUDIO_CORE_FLASH`.
- No allocation in the audio path: the block pool is static (`allocate` takes from `memory_pool_available_mask` with
  global interrupts briefly disabled, `AudioStream.cpp:85-102`). Objects and `AudioConnection`s are created at init
  (`new` in constructors, `connections` vectors). There is a global `malloc` wrapper in `PlatformTrackerIMX.cpp:70`
  that asserts and hangs when `enableMallocCheck` is on and malloc fails. Do not `new`/use std::vector growth inside
  the callback.
- Locks/flags: no mutexes found. Cross-context sync uses `volatile` fields (`AudioPlayMemory::next/length/playing`;
  `VoiceStreamState` all volatile with a `generation` counter) and interrupt gating: `AudioNoInterrupts()` /
  `AudioInterrupts()` -> `disableAudioInterrupt()/enableAudioInterrupt()` (`source/interruptsControl.h`, impl
  `platforms/imx/source/ interruptsControl.cpp`) around parameter changes and note-on. Flag handshakes:
  `refreshRegister` masks, `stackedPlay`, `*ForceFlag`s, `getInterfacePlayingEndFlag()/clear...`, `isBlockedNoteOn[]`.
- SD card is never touched in the callback: reads are done by `VoiceStreamManager::update()` on the main loop (async
  ADMA2, ring of 16384 frames), and `Sequencer::stop` defers its SD part (see section 5).
  `VoiceStreamManager::setSuspended(true)` stops all card reads while USB host mode owns the card; voices play what is
  in RAM, then silence.
- Known edge handling worth reusing: `keepInLoop()` (`play_memory.h`, folds a playhead back into a loop when points
  move under it), zero-crossing snap (`enableSnapToZero`, `kSnapToZeroThreshold`), fade-in 32 samples on stream start
  (`fadeInCounter`), `needSmoothingFlag` on abrupt memory changes.

## 8. Not found (and where I looked)

- Time-stretch / warp / independent tempo-follow of a sample: only note-based pitch (`pitchControl`),
  `playModeBeatSlice` and slice playback. Looked in `libs/Audio/play_memory*.cpp`, `AudioEngine/`.
- Recording the master/internal mix as a source: not in `Recorder.*`, `AudioInput.*`, `sampleRecorder.h`.
- Overdub / record while the pool plays: nothing; recorder writes into the full sample pool.
- Public setter for `onGlobalStep` or a quantized-start API: `mtSequencer.h`, `mtSequencer.cpp`.
- A documented CPU % at full polyphony: `Profiler.*`, comments in `mtAudioEngine.*`.
- Exact interrupt priority / ISR confirmation of the audio callback: `platforms/imx/source/AudioHardware.cpp`,
  `PlatformTrackerIMX.cpp` (only the callback registration was read; the I2S driver itself was not).
- Host tests or a simulator for the audio engine: none in the tree.

