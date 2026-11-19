# KB1 ↔ Tracker Mini integration: implementation plan

**Not started.** This plan is staged so each stage is independently useful, reversible and testable. Nothing here should begin until you pick a stopping point in the Zelda work. Evidence and file references are in `RESEARCH.md`. Hardware unknowns are in `OPEN_QUESTIONS.md`.

Baselines (from `RESEARCH.md` §1):
- Tracker CE `922bba0580eb59700574e5b07c648e9933addd08` (main), or release tag `v1.0.0` `9b9a13b5…` if you prefer to start from stable.
- KB1 `17ae3abbf6e240aab0db35879203bbf8842b74c3` (main == `v2.3.3` firmware source).

Ground rules for every stage:
- Work in **new forks/clones**. Never edit an existing firmware checkout.
- Every Tracker change compiles on all three targets (`make all`). Only Mini activates the feature.
- No writes to `mtConfig`. No new config fields. No heap or SD I/O in audio-rate code.
- Keep one logical change per commit so the series rebases cleanly.
- Hardware stages require backups first (Stage 0) and a known-good stock image on the SD card.

---

## Decisions to confirm before Stage 3/4 (your preferences, not research gaps)

| # | Decision | Default proposed |
|---|---|---|
| D1 | Start from CE `main` (beta) or tag `v1.0.0` (stable)? | `v1.0.0` for first hardware tests, then rebase to the next tag |
| D2 | KB1 profile transpose | −12 (matches KB1's documented "Middle C = C-4"), applied to KB1 notes only |
| D3 | Do you actually need the Tracker-side work, or is Option 0/0b (static config + KB1 octave persist) enough? | Try Option 0 manually during Stage 1. If the remaining gaps (stuck notes, octave press) matter to you, continue |
| D4 | On-screen "KB1 connected" message | Off in v1; add in Stage 6 if wanted |
| D5 | Periodic Hello interval | 2 s, only while no key is held |

---

## Stage 0: Preparation and backups (no code, no flashing)

1. **Back up the SD card**: copy `/trackerConfig`, all project folders, `/Firmware/`, and any custom content. Record SHA-256 of `/trackerConfig` and each project's files.
2. Photograph or record **Config → MIDI** values and **Config → Firmware → version/Build**.
3. In KB1 Studio (desktop Chromium): **Device Info** → record firmware version. In the Configurator, export/record presets and current settings.
4. Put a **stock** Tracker Mini `.ptf` that matches your current version in `/Firmware/` (recovery image). Keep the matching stock KB1 `.bin` (complete image) locally.
5. Toolchains:
   - Tracker: GNU Arm Embedded 10.3-2021.10, `make mini`. Build **unmodified** CE once and confirm the build is reproducible (`make version` shows the commit).
   - KB1: PlatformIO with **pinned** `platform = espressif32@<exact>` and pinned `lib_deps` (determine the versions that match v2.3.3, see OPEN_QUESTIONS Q3). Build unmodified and run `build_complete.sh`.

**Exit criteria:** backups verified readable; both stock firmwares build locally from pinned commits; recovery images on hand.

---

## Stage 1: Observe the real wire traffic (Tracker debug build, behaviour unchanged)

Goal: replace assumptions with captures from *your* KB1 and Tracker.

Change (fork branch `kb1/observe`, debug-only, not for daily use):
- In `UartMidiImpl` (or a byte tap in `MidiUart::read`), `LOGF` each received byte with a µs timestamp, rate-limited, integer formatting only. Behaviour otherwise stock.

Captures (via the CDC console):
- KB1 power-on (switch), power-off, light-sleep entry, touch wake.
- Playing single notes, chords and strum, lever pitch-bend, sustain push, touch CC.
- KB1 while being flashed over USB (only if you choose to, with the Tracker **on** but the project saved).
- Undock while holding a note.

**Acceptance (Stage 1):**
- A1.1 Byte log shows CC 123/121 ×16 channels at boot and before sleep (or documents what is actually seen).
- A1.2 Record whether any non-MIDI or garbage bytes appear around KB1 reset, and what the parser makes of them.
- A1.3 With stock routing (`Notes in` incl. jack), hold a note on a looping/sustaining instrument and switch KB1 off. Record whether the note hangs (confirms or refutes the RESEARCH §3.5 prediction).
- A1.4 Try Option 0 (static config) for a session and note what still bothers you (feeds D3).

---

## Stage 2: Tracker: jack note tracking + All-Notes-Off (works with stock KB1)

Branch `kb1/notes-safety`. Independent of identification, and a candidate for upstreaming on its own.

Changes:
1. New `core/source/kb1link/JackNoteTracker.{h,cpp}`: a 128-entry table of `{active, effectivePitch, source}` for jack-originated notes. `onNoteOn(raw, effective)`, `onNoteOff(raw) -> effective`, `releaseAll(callback)`.
2. `mtMidi.cpp`: jack Note On/Off record and look up the effective pitch, so a Note Off always matches its Note On, even if Middle C changes mid-note.
3. `handleJackControlChange`: when CC 123 (All Notes Off) or CC 120 (All Sound Off) arrives on an accepted channel, release all tracked jack notes, before the existing CC dispatch. CC 121 stays ignored as today.

**Acceptance (Stage 2):**
- A2.1 `make all` succeeds for Original, Plus and Mini, and memory usage delta is reported (expect < 1 KB).
- A2.2 Host unit tests for `JackNoteTracker` pass (on/off pairing, duplicate on, off without on, release-all, transposition change mid-note).
- A2.3 On hardware: hold a KB1 note on a sustaining instrument and trigger KB1 light sleep (set a short timeout in the Configurator). The note is released when KB1 sends its pre-sleep panic.
- A2.4 Changing Middle C while holding a jack note no longer strands it.
- A2.5 USB-played notes are unaffected by jack CC 123.

---

## Stage 3: Tracker: KB1 detection + runtime profile overlay

Branch `kb1/link`, on top of Stage 2.

Changes:
1. `core/include/Platform.h`: add `systemExclusive` and `activeSensing` callback pointers to `UartMidi::MidiReceiveActions`. `midiInit` value-initialises the struct (`MidiReceiveActions a{}`).
2. `platforms/imx/source/UartMidiImpl.cpp`: register `setHandleSystemExclusive` / `setHandleActiveSensing` when non-null. Same for mk66 (or leave mk66 untouched if it compiles).
3. New `core/source/kb1link/Kb1Link.{h,cpp}`:
   - Hello parser (prefix `F0 7D 4B 42 31`, proto 1, checksum).
   - State machine ABSENT ⇄ PRESENT with reasons and timeouts (`RESEARCH.md` §5.3).
   - Accessors `jackNotesEnabled()`, `jackNoteChannelOk(ch)`, `jackTranspose()`, `jackCcEnabled()`, `jackCcChannelOk(ch)`.
   - `tick(nowUs)` called from `midiUpdate()`. Re-arm timers after render mode.
   - `init(disabled)` with `disabled = exists("/.kb1off")` from `Tracker.cpp`. Activation compiled in only under `TRACKER_MINI`.
4. `mtMidi.cpp` jack handlers use the accessors. USB handlers and output functions are **not** modified.

Host-side tests (in `tools/kb1link-tests/`, outside `core/source/`): feed byte sequences and timestamps, then assert state and released notes. Cases: valid Hello; corrupted checksum; Hello split by real-time bytes; FE timeout; goodbye; reboot-while-present; render pause; garbage before Hello.

**Acceptance (Stage 3), using a test sender before KB1 is modified:**
Use a computer + TRS-B MIDI interface (if available, Q5) or a second microcontroller to inject Hello/FE into the Tracker MIDI In jack.
- A3.1 With `Notes in = Off`, `CC in = Off` persisted: inject Hello + FE. Notes and CCs on ch1 are accepted within one audio block of the Hello.
- A3.2 Stop FE: within ≤ 350 ms all injected held notes are released and jack input reverts to the persisted settings (notes ignored again).
- A3.3 `/trackerConfig` midi block bytes are identical before and after A3.1–A3.2, including after forcing unrelated saves (change an instrument, open the file browser, adjust the mixer, then save).
- A3.4 `/.kb1off` present: behaviour is identical to stock (A3.1 notes ignored).
- A3.5 Corrupted Hello (bad checksum) never activates the profile.
- A3.6 Audio-ISR CPU (`/.develop` telemetry) avg/max within noise of the Stage 2 build.

---

## Stage 4: KB1 firmware: Tracker Link beacon

KB1 fork branch `tracker-link`. GPL-3.0 applies.

Changes:
1. New `firmware/src/integration/TrackerLink.h`: pure encoder `encodeHello(reason, flags, buf)` plus a scheduler `tick(nowMs, anyKeyHeld)`.
2. **TX serialisation:** wrap MIDI writes in a FreeRTOS mutex shared by the `readInputs` task and the BLE callback (`bt/CharacteristicCallbacks.cpp#L121`), so beacons and BLE CCs can't interleave with notes.
3. Hooks (small):
   - `main.cpp` `setup()` after the boot panic (`#L1335`): Hello(boot).
   - `readInputs` loop: `TrackerLink::tick()` (FE every 250 ms; periodic Hello every 2 s when no key is held).
   - `SleepControl.h` before the pre-sleep panic: Hello(goodbye). After wake: Hello(wake).
4. Build flag `-DKB1_TRACKER_LINK=1` (default on in the fork). Leaving it off reproduces stock behaviour.
5. Optional (D3): persist a default octave offset in NVS.
6. Version string suffix (e.g. `2.3.3-tl1`) so KB1 Studio's Device Info shows it is custom.

Flashing: build a **complete image** with `build_complete.sh` and use KB1 Studio → "Flash a custom .bin" **with NVS preservation** (do *not* tick "Clear device data"). Power the Tracker **off** or undock while flashing (KB1 Studio guidance).

**Acceptance (Stage 4):**
- A4.1 PlatformIO native unit test for `encodeHello` (bytes and checksum) passes.
- A4.2 With the Stage 1 observe build on the Tracker: Hello(boot) appears right after power-on, FE every 250 ms ±20 ms, Hello(goodbye) before sleep, Hello(wake) after touch wake, no Hello while keys are held.
- A4.3 With **stock** Tracker CE firmware: KB1 behaves exactly as before (beacons ignored), with no audible or functional difference.
- A4.4 KB1 settings, presets and battery calibration survive the flash (compare with Stage 0 records).

---

## Stage 5: End-to-end acceptance on your hardware

Precondition: Tracker on the Stage 3 build, KB1 on the Stage 4 build. Tracker **persisted** settings are left at whatever you normally use (ideally `Notes in = Off` or `USB`, `CC in = Off` or `USB`, Middle C default).

| ID | Scenario | Pass criteria |
|---|---|---|
| E1 | Tracker on, KB1 off and docked → switch KB1 on | Notes/CC work within ≤1 s, at the expected octave; no menu visited |
| E2 | KB1 on and docked → power on Tracker | Detected within ≤2 s of Tracker boot (periodic Hello) |
| E3 | Hold a note on a sustaining instrument → undock KB1 | Note released ≤350 ms; jack routing reverts |
| E4 | Same as E3 but switch KB1 off instead | Same as E3 |
| E5 | Let KB1 sleep (short timeout) → touch to wake | Goodbye releases notes; wake re-arms; playing resumes without menus |
| E6 | 20× dock/undock and 20× power cycles while playing | Zero stuck notes; no project parameter changed except by deliberate CC moves; no crash |
| E7 | Record in Rec mode with KB1 | Notes land in the pattern at the expected pitch; edit-step cursor advance unchanged from stock |
| E8 | Sample Playback / Sample Editor / Sample Recorder screens | KB1 plays them as stock MIDI-in would |
| E9 | USB MIDI from a computer concurrently (if available) | USB notes obey **your** persisted channel and Middle C; KB1 notes use the profile |
| E10 | Tracker MIDI Out → external synth via KB1 J3 pass-through | Outgoing note pitch identical to stock firmware (Middle C output transposition untouched) |
| E11 | KB1 removed; plug ordinary MIDI gear into the jack | Behaviour identical to stock for your persisted settings |
| E12 | Export/render a song with KB1 docked | No crash; after export, no spurious disconnect message and no stuck notes; KB1 usable again ≤2 s |
| E13 | Settings preservation | SHA-256 of `/trackerConfig` midi block unchanged across E1–E12; projects unchanged except deliberate edits |
| E14 | `/.kb1off` on SD | Tracker behaves exactly as stock CE |
| E15 | Latency (subjective + optional measurement) | No perceptible difference vs Stage 1 baseline. Optional: phone-camera/audio recording of key click vs Tracker output, compare stock vs integrated build |
| E16 | Rollback | Flash stock CE `.ptf` → Tracker boots with all settings and projects intact; flash stock KB1 → KB1 works with stock Tracker as before |

---

## Stage 6: Packaging for future CE releases (optional)

- Keep the Tracker fork as a patch series: `platform-seam`, `jack-note-safety`, `kb1link-module`, `kb1link-hooks`.
- Add a fork CI workflow: on push, run `make all` + host tests and upload `.ptf` artifacts.
- **Per new CE release:** `git rebase --onto <new-tag>`, then `git range-diff` to review, then CI, then run E1–E6, E13 and E16 on hardware before daily use.
- Optional upstream proposals (each needs a GitHub Discussion first per CE CONTRIBUTING; human-only commit trailers): (a) Stage 2 note safety; (b) the SysEx/Active-Sensing seam. If accepted, the local patch shrinks to the KB1 module and three accessor calls.
- Optional UI message (D4).

---

## Recovery procedures (keep handy before any flashing)

**Tracker Mini:**
1. Normal: **Config → Firmware → Firmware update** → pick the stock `.ptf`.
2. If the custom build won't boot: put the stock `.ptf` as the only `.ptf` in `/Firmware/`, power on, and press the **recessed reset/bootloader pinhole next to the USB-C port** with a pin (CE README §4). The bootloader is in protected flash and is not touched by `.ptf` updates.
3. Settings: the integration never writes `/trackerConfig`. If anything looks off, restore the Stage 0 copy.

**KB1:**
1. Normal: KB1 Studio → Firmware Update → stock version, with NVS preserved.
2. If the app won't boot or USB is unresponsive: ESP32-S3 ROM download mode (XIAO BOOT button held while connecting USB). This is always available in ROM, but physical access depends on the enclosure (Q7).
3. Settings: KB1 Studio backs up and restores NVS automatically. Keep the Stage 0 record of presets.
