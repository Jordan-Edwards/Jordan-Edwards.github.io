# KB1 ↔ Tracker Mini native integration: research

Status: **research only**. Nothing has been built, flashed or modified. All conclusions below come from reading the pinned public sources listed in §1; anything that needs your physical hardware is marked **[HW]** and collected in `OPEN_QUESTIONS.md`.

Legend: **[CODE]** = established by reading source/netlist at the pinned commit. **[DOC]** = stated in vendor documentation (not verified in code). **[HW]** = needs a test on your units.

---

## 0. Summary of findings

| Question | Answer |
|---|---|
| How does KB1 connect? | It **docks**: four PCB-mounted 3.5 mm plugs go into the Tracker Mini's Line In, Line Out, MIDI In and MIDI Out jacks. KB1 re-exposes Line In, Line Out and MIDI Out as pass-through jacks. **[CODE: netlist]** |
| Direction of MIDI | **One-way, KB1 → Tracker only.** The Tracker's MIDI Out is passed straight to KB1's jack J3. It is not wired to the ESP32. The ESP32 `UART_RX` pad is *unconnected* on the PCB. **[CODE: netlist]** |
| USB identification | **Not possible.** The Tracker Mini firmware has only a USB *device* stack (no host), and KB1's USB-C is used for charging and flashing (USB-Serial/JTAG mode), not MIDI. **[CODE]** |
| Can Tracker detect plug-in or power-on electrically? | **No.** No jack-detect is read in code, and an un-powered KB1 looks identical to an empty jack (no loop current). Presence can only be inferred from bytes KB1 sends. **[CODE]** |
| What KB1 sends today (v2.3.3) | Note On/Off and CC, **always channel 1**. CC 123 + CC 121 on all 16 channels at boot and before sleep, and CC 123 ch1 from the brownout ISR. **No SysEx, no Active Sensing, no pitch-bend, no CC64**: pitch-bend and sustain are emulated on the keyboard. **[CODE]** |
| Settings users change today | Config → MIDI: **Notes in = MIDI In jack, Notes in channel = CH1, CC in = MIDI In jack, CC in channel = CH1, Middle C = C-4**. **[DOC: KB1 Studio guide]** |
| Which of those are strictly required? | From factory defaults (`Notes in = Off`, `CC in = Off`, channels = ALL, Middle C = C-5), only **Notes in** and **CC in** must include the jack. CH1 is optional because ALL already accepts ch1. Middle C = C-4 is an octave preference (−12). **[CODE]** |
| Hidden side-effect of the documented setup | Tracker's `Middle C` is **global**: it also transposes MIDI *output* to other gear by +12 (`mtMidi.cpp:682,713`). The `Notes in channel` filter is shared between USB and jack. **[CODE]** |
| Does KB1's "All Notes Off" work on the Tracker? | **Not in Tracker CE code.** Incoming CC 123/121 are not mapped to anything, so they are silently ignored. KB1's panic does not release Tracker voices. **[CODE]**; behaviour on hardware **[HW]** |
| Auto-config feasible? | **Yes, with firmware changes on both sides.** KB1 broadcasts an identity beacon + Active Sensing, and Tracker applies a **runtime-only overlay** to jack-input routing. The overlay never writes `mtConfig`, so restoration happens by construction. **Feasible from code; not yet proven on hardware.** |
| Zero-firmware alternative | Set Tracker once to `Notes in = USB + MIDI In jack`, `CC in = USB + MIDI In jack`, channels `ALL`, Middle C unchanged, then use KB1's Octave-Down. This removes per-session menu changes. It does **not** fix stuck notes on disconnect, ignored CC 123, the octave resetting on every KB1 boot, or exposure to boot-time garbage. |

---

## 1. Sources and pinned commits

All inspection was done on fresh clones in a scratch directory (no existing checkout was touched).

| Repo | Role | Pinned commit | Date | Notes |
|---|---|---|---|---|
| [PocketMidi/KB1](https://github.com/PocketMidi/KB1) | KB1 firmware, hardware, references | `17ae3abbf6e240aab0db35879203bbf8842b74c3` (`main`) | 2026-10-09 | Latest tag `v2.3.3` = `7e98abaf9ee9822819290a7bc00e7abccfa4296e` (2026-08-16). **`firmware/src` and `platformio.ini` are byte-identical between `v2.3.3` and `main`.** |
| [PocketMidi/KB1-studio](https://github.com/PocketMidi/KB1-studio) | User guide (Tracker settings), browser flasher | `fe38588ea7b40b463a831a3562df593896fdc10d` | 2026-10-13 | Guide text is in `index.html`. |
| [PocketMidi/KB1-config](https://github.com/PocketMidi/KB1-config) | BLE configurator web app | `d04d68a969a9672a4dd3e7d6c2fb5e0794ad9a9c` | 2026-10-12 | No Tracker-specific logic relevant here. |
| [polyend/tracker-ce](https://github.com/polyend/tracker-ce) | Tracker Community Edition firmware | `922bba0580eb59700574e5b07c648e9933addd08` (`main`) | 2026-11-18 | Linked from Polyend's announcement ([polyend.com, 2026-11-02](https://polyend.com/whats-up/tracker-the-biggest-update-yet/)). Release tag `v1.0.0` = `9b9a13b56fef94710e5c1d4bf1a321681080a6c8` (2026-11-02); `main` is 176 commits ahead (beta, see `UPCOMING.md`). |

Link shorthand used below:
- `TCE:` → `https://github.com/polyend/tracker-ce/blob/922bba0580eb59700574e5b07c648e9933addd08/`
- `KB1:` → `https://github.com/PocketMidi/KB1/blob/17ae3abbf6e240aab0db35879203bbf8842b74c3/`

### 1.1 Licences

| Component | Licence | Implication |
|---|---|---|
| Tracker CE source | MIT **plus a "Wholesale Commercial Clone Restriction"** (`TCE:LICENSE`). You may modify and share, but not *sell* compiled `.ptf` builds or clone hardware. | A personal fork with KB1 support is fine. Do not sell builds. |
| Tracker CE `synth/prebuilt/*.psyn` | Proprietary (`synth/prebuilt/LICENSE-PROPRIETARY.txt`) | Untouched by this work. |
| Tracker CE contributions | `CONTRIBUTING.md`: PRs grant Polyend relicensing rights. **Commit trailers must not credit AI tools.** | Relevant only if you ever upstream a piece. |
| KB1 repo root | MIT (`KB1:LICENSE`, "© 2026 PocketMidi / Sean Johnston") | — |
| KB1 `firmware/` | **GPL-3.0** (`KB1:firmware/LICENSE`, and GPL headers in `firmware/src/main.cpp`) | **Conflict with the root README's "Software & Firmware: MIT".** Treat firmware modifications as GPL-3.0 (share source if you distribute binaries). Personal use is unaffected. |
| KB1 hardware | CERN-OHL-S v2 (`KB1:hardware/LICENSE.txt`), OSHWA UID US002800 | Only relevant to hardware changes (out of scope). |
| KB1-studio, KB1-config | MIT | — |

### 1.2 Available vs. missing

Available: complete KB1 firmware (PlatformIO), KiCad schematic + PCB (`hardware/electronics/KB1_KiCad.zip`), PDF schematic, BOM refs, STLs/STEPs, assembly guide, the browser flasher (with NVS backup/restore), and the complete Tracker CE source for all three devices, including the bootloader-recovery description.

Missing or weak:
- **Build reproducibility (KB1):** `platformio.ini` does not pin `platform = espressif32` or `lib_deps` versions, so a rebuild today may use a different Arduino-ESP32 core than the released v2.3.3 binary. Pin before building.
- **Tracker Mini hardware docs:** no schematic in `tracker-ce`. MIDI electrical behaviour (opto-isolator, jack detect) is not documented. The `MIDI_IN`/`MIDI_OUT` labels on `GPIO_SD_B1_00/01` exist only in a pin-tool YAML comment (`TCE:platforms/imx/board/pin_mux.c` lines 38–39). No code reads them.
- **Tracker Mini TRS type:** stated as **Type B** in the community manual bundled in the KB1 repo (`KB1:references/Polyend-Tracker-Mini-Manual-2v2v0a.txt`, "Adapter (Type B) supplied"). KB1's wiring is Type-B (§2.2). Consistent, but secondary-source.
- **Bootloader source** for the i.MX devices is not in the repo (it lives in protected flash at `0x60000000–0x6002FFFF`). Recovery is documented, not inspectable.
- No official protocol doc for KB1 beyond code. No KB1 SysEx/identity exists.

---

## 2. KB1: hardware, connection and MIDI behaviour

### 2.1 Physical connection (netlist evidence) [CODE]

Extracted from `KB1:hardware/electronics/KB1_KiCad.zip` → `KB1v8.1.kicad_pcb` pad→net mapping:

| Part | Pad | Net | Meaning |
|---|---|---|---|
| `plug_3` (into Tracker **MIDI In**) | T | `+3V3` via **R5 = 33 Ω** + ferrite FB2 | MIDI current source |
| | R | ESP32 `UART_TX` (GPIO43, D6) via **R1 = 10 Ω** + ferrite FB1 | MIDI data (sink) |
| | S | GND | |
| `plug_4` (into Tracker **MIDI Out**) | T/R/S | → `J3` T/R/S only | Passive pass-through. **Not connected to the MCU.** |
| `plug_1` → `J1` | T/R/S | pass-through | Line In |
| `plug_2` → `J2` + amp input (R12/R13 → PAM8406) | T/R, S=GND | pass-through + speakers | Line Out |
| XIAO `M2` pad 8 | — | `unconnected-(M2-UART_RX-Pad8)` | **No receive path.** |

Consequences:
- Tip = source and Ring = sink is the **TRS Type B** layout. The 33 Ω/10 Ω values match the MIDI 1.1 3.3 V recommendation. (The KB1 repo's own reference image is `references/hardware/IO/Midi/trs midi B.jpg`.)
- **No handshake is possible** without a hardware change, because the Tracker cannot send anything that KB1 can receive.
- When KB1 is switched off (`S6` disconnects the battery from the XIAO), `+3V3` disappears and the loop carries no current. That is electrically indistinguishable from "nothing plugged in" or "KB1 idle".
- While docked, **KB1 physically occupies the Tracker's MIDI In jack**, and KB1 offers no MIDI-In pass-through. Any jack-input routing change while KB1 is present cannot affect other TRS MIDI gear. Only USB MIDI and the Tracker's MIDI Out remain shared.

### 2.2 MIDI output vocabulary (firmware v2.3.3 == main) [CODE]

- UART: `MIDI_CREATE_INSTANCE(HardwareSerial, Serial0, MIDI)` (`KB1:firmware/src/main.cpp#L157`); `Serial0.begin(31250)` (`#L1324`); TX buffer 512 B. FortySevenEffects MIDI Library, unpinned version.
- **Channel is hard-coded to 1** in every send (`controls/KeyboardControl.h`, e.g. `playMidiNote` `#L175`, `constexpr byte channel = 1`; levers/push/touch `sendControlChange(..., 1)`).
- Messages that reach the wire:
  - **Note On / Note Off** (velocity is internal state, default changed by the "velocity" lever mapping).
  - **CC** 0–127 from levers, lever pushes and touch, only when the configured number is ≤127. Defaults: touch → **CC 1** (Tracker: Cutoff), range 38–114.
  - Numbers ≥128 are **internal pseudo-CCs** (128 velocity, 200–206 strum/arp/scale/chord/root, 208 pitch-bend, 209 sustain) and are *not* transmitted (`controls/LeverControls.h` ~L496–L601, `LeverPushControls.h` ~L457–L586).
  - **Pitch bend** is emulated by retriggering held notes ±1–2 semitones (`KeyboardControl.h#L119` `setPitchBendOffset`). **Sustain** is emulated by delaying Note Offs (`setSustainActive`). No `0xE0` and no CC64.
  - **Panic:** `sendMidiPanic()` sends CC 123 and CC 121 on channels 1–16, then drains TX (`main.cpp#L174`). It is called at boot (`#L1335`) and before light/deep sleep (`controls/SleepControl.h#L86`, `#L210`).
  - **Brownout ISR:** writes `B0 7B 00` (CC 123 ch1) straight into the UART FIFO (`main.cpp#L1188`). The comment says "prevents stuck notes on Polyend Tracker" (but see §3.5).
- Nothing else: no SysEx, no Active Sensing, no clock, no program change. `MIDI.read()` is never called.
- **Boot garbage:** code comment at `main.cpp#L1327` says the panic exists to "clear any garbage state caused by UART TX floating during ESP32 reset/flash". KB1 Studio also says: "If KB1 is connected to Tracker Mini, power down Tracker before flashing." So random bytes on the MIDI line around KB1 reset/flash are a known phenomenon. Exact content is **[HW]**.
- **Two concurrent UART writers:** most MIDI is sent from the `readInputs` FreeRTOS task (`main.cpp#L1815`). The BLE characteristic callback also calls `MIDI.sendControlChange` from the BLE stack task (`bt/CharacteristicCallbacks.cpp#L121`). The MIDI library writes byte-by-byte, so messages from two tasks *can* interleave. This is pre-existing and only matters while the Configurator's live sliders are used. A new beacon must not add a third writer.

### 2.3 Timing and power [CODE]

- Input scan every 5 ms (`vTaskDelay(5)` in `readInputs`), key-press debounce 10 ms, release debounce 30 ms (`KeyboardControl.h#L82–83`).
- Light sleep after `lightSleepTimeout` (default 300 s) of no activity, deep sleep later. Touch wakes it. The CPU is not running the app between timer wake-ups during sleep. Panic is sent before sleep.
- Octave offset starts at 0 every boot (`OctaveControl.h`: `currentOctave(0)`, not stored in NVS).
- Settings and presets persist in ESP32 NVS. KB1 Studio's updater backs up and restores NVS around flashing.

---

## 3. Tracker Mini (Tracker CE): MIDI input, configuration and persistence

### 3.1 Platform and build [CODE]
- Tracker Mini = `PLATFORM=IMX PRODUCT=MINI`, compile define `TRACKER_MINI` (`TCE:core/makefile` L62–63, `platforms/imx/makefile` L66–67). i.MX RT1051/RT1064 Cortex-M7.
- Toolchain: GNU Arm Embedded **10.3-2021.10**; `make mini` → `build/TrackerMini_CE_<ver>.ptf`.
- `core/makefile` collects sources with `find ./source/ -name *.cpp`. **A new folder under `core/source/` is compiled automatically, with no makefile edit.**

### 3.2 TRS MIDI receive path [CODE]
1. **UART driver:** `TCE:platforms/imx/source/Drivers/MidiUart.cpp`. LPUART5 at 31250 baud, interrupt-driven RX ring buffer of 511 bytes, TX inverted.
2. **Parser:** vendored FortySevenEffects MIDI Library **5.0.0** (`platforms/imx/3rdparty/MIDI/`). Settings are `DefaultSettings`: SysExMaxSize 128, `UseReceiverActiveSensing=false`, running status accepted on input, 1-byte parsing.
3. **Glue:** `TCE:platforms/imx/source/UartMidiImpl.cpp#L15` `setReceiveActions` registers **only** NoteOn, NoteOff, Clock, Start, Stop, SongPosition, Continue and ControlChange. **SysEx, Active Sensing, Pitch Bend, Aftertouch, Program Change and System Reset are parsed and dropped.**
4. **Callback table:** `TCE:core/include/Platform.h#L139` `UartMidi::MidiReceiveActions` (plain function pointers; the USB one is at `#L124`).
5. **Dispatch:** `TCE:core/source/mtMidi.cpp#L35` `midiInit` wires jack callbacks to `handleJackNoteOn/Off`, `handleJackControlChange` and the clock/transport handlers. Note: `MidiReceiveActions` is a stack local that is *not* value-initialised, so any new field must be set explicitly.
6. **Polling cadence and context:** `midiUpdate()` (`mtMidi.cpp#L63`) drains UART and USB queues. It is called from `TrackerImpl::updateAudioBuffers` (`TCE:core/source/Tracker.cpp#L192`), i.e. **once per 128-sample audio block (~2.9 ms) in audio-interrupt context**. It returns immediately in render (export) mode. Anything added to this path must be ISR-safe: no heap, no SD I/O, no blocking, no `%f` logging (`docs/developer_guide.md`, §Logging and CONTRIBUTING §3).

### 3.3 Exactly how the five settings act [CODE]

Config struct `strMIDIValues` (`TCE:core/source/mtStructs.h#L1073`), menu in `core/interface/configEditor/configMenu.cpp#L190–L233`, labels in `configMenuDefs.h#L199–L231`, factory defaults in `mtConfig.cpp#L513–L523`.

| Menu item | Field | Values (index) | Factory default | Used at |
|---|---|---|---|---|
| Notes in | `notesInMode` | 0 Off, 1 USB, 2 MIDI In jack, 3 USB + MIDI In jack | **0 Off** | `mtMidi.cpp#L102` (jack on), `#L187` (jack off), USB at `#L148/#L233` |
| Notes in channel | `notesInChannel` | 0 ALL, 1–16 | **0 ALL** | `isIncomingChannelDesired` `#L85`. **Shared by USB and jack** |
| CC in | `ccInMode` | same enum as Notes in | **0 Off** | `handleJackControlChange` `#L274` |
| CC in channel | `ccInChannel` | 0 ALL, 1–16 | **0 ALL** | `#L277`, shared with USB `#L294` |
| Middle C | `middleC` | 0 C-3, 1 C-4, 2 C-5, 3 C-6 | **2 C-5** | Input: `transp = 12*(middleC-2)` (`#L109,#L192`, USB `#L153,#L238`). **Output:** `transp = 12*(2-middleC)` in `sendPolyPressure`/`sendMidiNoteOn`/`sendMidiNoteOff` (`#L619,#L682,#L713`) |

So KB1's documented Middle C = C-4 shifts KB1 notes down 12 *and* shifts every note the Tracker sends to external MIDI gear up 12. A KB1 profile must not touch `middleC` globally.

Jack Note On flow when enabled: velocity 0 → note off; channel filter; transpose; then by `sequencer.getMidiInVoiceMode()` to `sequencer.handleNoteOn(GRID_OUTSIDE_PATTERN, pitch, vel, pitch+100)` (live play, records in Rec mode), or Sample Playback / Sample Editor / Sample Recorder handlers. **USB and jack share the note "source" id `pitch+100`.**

### 3.4 What incoming CCs do [CODE]
`handleJackControlChange` (`mtMidi.cpp#L271`) → `peformanceModeOnMidiCC` (CC 41–48 tracks, 51–62 FX slots, Performance screen only), `changeMixerOnMidiCC` (CC 71–82), `cInstrumentEditor::onControlChangeReceive` (sample-instrument CCs 1, 3, 5, 7, 9–15, 20–31, 83–88, 102–119; synth CCs 110–119), and `cSamplePlayback::onControlChangeReceive`. **These write into `mtProject` values**, so CC input changes the open project, and the change is saved with the project. That is intended behaviour, but it means stray CCs (e.g. boot garbage) can alter a project.

### 3.5 All-Notes-Off and stuck notes [CODE]
- CC 120/121/123 are in no handler's range. The only CE use of All-Notes-Off is internal (`core/synth/Synth.cpp#L1693` `silencePart`). **An incoming CC 123 from the jack does not release live notes.** KB1's boot/sleep/brownout panic therefore has no effect on the Tracker in CE code. Confirm **[HW]**.
- `Sequencer::stopManualNotes()` (`mtSequencer.cpp#L1552`) releases every live "manual" note on all tracks. It is a blunt tool: it would also cut USB-played notes.
- If `middleC` changes between a Note On and its Note Off, the off is transposed differently and the note sticks. This is a pre-existing edge case, and the same applies to any overlay that changes transposition while a note is held.

### 3.6 Persistence [CODE]
- `mtConfig` lives in `/trackerConfig` on the SD card (`TCE:platforms/imx/config/config.h#L17`, `ConfigManagerImpl`).
- `forceSaveConfig()` (`mtConfig.cpp#L79`) rewrites **every** sub-struct including `mtConfig.midi`. `saveConfig()` is requested from many unrelated places (file browser, sample import, master params, sample playback, performance). **Any runtime mutation of `mtConfig.midi` will be persisted by the next unrelated save.** A "temporary profile" therefore must not be implemented as "write mtConfig, restore later".
- `readConfig` is size-tolerant per sub-struct, and the firmware-version-change hooks for Mini are no-ops in CE (`mtConfig.cpp#L635`). Flashing a fork does not reset settings, though it does trigger one config rewrite. CONTRIBUTING forbids shifting config fields; this design adds none.
- Precedent for a feature flag without config changes: `/.develop` on the SD card is read once at boot (`Tracker.cpp#L149`).

### 3.7 USB [CODE]
`platforms/imx/usb/` contains only the device stack (composite: audio, MIDI, MSC, CDC). VID `0x16D0`, PIDs `0x1118/0x1119` (`usb_device_descriptor.h#L359–363`). There are no USB host files. The Tracker Mini cannot enumerate KB1 or any USB MIDI controller.

### 3.8 Tooling available for testing [CODE/DOC]
- `LOG()`/`LOGF()` are ISR-safe (ring buffer, flushed from the main loop) over a CDC-ACM serial console (`docs/developer_guide.md` §Logging/§Console Protocol). The Tracker itself can therefore act as the **MIDI sniffer** for KB1's output, with no extra MIDI interface.
- `/.develop` enables audio-ISR CPU min/max/avg telemetry on the Config screen, to check that the integration adds no measurable load.
- GitHub Actions builds `.ptf` for all three devices on every push.

---

## 4. Can KB1 be identified automatically through the actual connection?

| Mechanism | Possible? | Why |
|---|---|---|
| USB enumeration (VID/PID, descriptors) | **No** | Tracker Mini has no USB host (§3.7). KB1's USB is not connected to the Tracker when docked. |
| Electrical plug/power detect on TRS | **No** (without hardware change) | No jack-detect is read. An off KB1 equals an empty jack (§2.1). |
| Request/response handshake (e.g. Universal Identity Request `F0 7E 7F 06 01 F7`) | **No** | No return path (ESP32 RX unconnected, §2.1). |
| **Unsolicited identity beacon from KB1** (SysEx) | **Yes, needs KB1 firmware + Tracker firmware** | KB1 can transmit anything. Tracker CE's parser already receives SysEx and only needs a callback registered (§3.2). |
| **Liveness via Active Sensing (`0xFE`)** | **Yes, needs both** | Standard 1-byte real-time message, ≤300 ms period. Ignored by gear that doesn't use it. Loss of it = disconnect, power-off or sleep. |
| Fingerprint of stock KB1 (boot panic: CC 123 + CC 121 on ch 1→16) | Weak | Same burst is sent before sleep. Generic panics from other gear look similar. Needs the Tracker on before KB1. Cannot detect disconnect (KB1 is silent while idle). Not recommended as the primary mechanism. |
| Bidirectional link via hardware mod (opto from `plug_4` data → ESP32 GPIO44) | Possible | **Hardware change: out of scope.** Listed only for completeness. |

**Conclusion:** "connect/power → recognised" is achievable only as **KB1 announces, Tracker listens**. It needs firmware changes on both devices. Disconnect and power-off detection relies on the *absence* of a periodic signal (timeout), not on an electrical event.

---

## 5. Recommended architecture

### 5.1 Design principles
1. **Never write the user's settings.** The KB1 profile is a *runtime overlay* consulted at the jack-input decision points. When KB1 goes away the overlay simply stops applying. There is nothing to restore, so restoration cannot fail, and a crash or power-loss cannot leave the overlay persisted.
2. **Scope the overlay to the MIDI In jack only.** USB input, MIDI output, clock and transport are untouched. Middle C stays global for everything except KB1-sourced notes.
3. **Identify positively, deactivate conservatively.** Activate only on a valid KB1 beacon. Deactivate on goodbye, liveness timeout or KB1 reboot, and release every note KB1 started.
4. **Isolate code.** Put new logic in new files. Hooks in existing files are a handful of one-liners, so the patch rebases cleanly onto future CE releases.

### 5.2 Wire protocol ("KB1 Tracker Link v1"), KB1 → Tracker
- **Hello** (SysEx, 13 bytes): `F0 7D 4B 42 31 <proto=01> <reason> <fwMaj> <fwMin> <fwPatch> <flags> <chk> F7`
  - `7D` = MIDI non-commercial/prototype manufacturer ID (suitable for personal use; PocketMidi would need a real ID for a commercial release).
  - `4B 42 31` = "KB1". `reason`: 1 boot, 2 wake, 3 periodic, 4 goodbye. `flags` bit0 = Active Sensing on. `chk` = 7-bit XOR of the preceding payload bytes.
  - The checksum and fixed prefix make accidental matches from boot garbage practically impossible.
- **When:** immediately after `Serial0.begin` and the boot panic (`reason=1`); after wake (`2`); every ~2 s while **no key is held** (`3`, so a Tracker powered on after KB1 still detects it); immediately before sleep (`4`).
- **Active Sensing** `FE` every 250 ms while awake (≈0.32 ms of line time per 250 ms).
- Sent from the `readInputs` task only, behind a small TX mutex that the existing BLE writer also uses (this also fixes the interleaving risk in §2.2).
- Existing note/CC behaviour is unchanged. Stock Tracker firmware ignores all of this (parsed and dropped, §3.2), so a beacon-enabled KB1 stays fully compatible with stock Tracker firmware and other gear.

### 5.3 Tracker-side module (`core/source/kb1link/`)
State machine, all in audio-ISR context, fixed-size state, no heap:

```
ABSENT --valid Hello(boot|wake|periodic)--> PRESENT
PRESENT --Hello(goodbye) | no FE for >330 ms (if flags.AS) | no Hello for >5 s (if !flags.AS)--> ABSENT  [release KB1 notes]
PRESENT --Hello(boot|wake)--> PRESENT  [release KB1 notes first: KB1 rebooted, orphaned notes]
PRESENT --jack CC 123/120 on KB1 channel--> PRESENT [release KB1 notes]   (makes KB1's existing panic work)
```

Effective-setting accessors (used **only** by the jack handlers):

| Decision | KB1 present | KB1 absent |
|---|---|---|
| Jack notes accepted? | yes | `notesInMode ∈ {jack, usb+jack}` (stock) |
| Jack note channel accepted? | `ch == 1` (profile channel) | `isIncomingChannelDesired(ch)` (stock) |
| Jack input transpose | profile value (default −12, i.e. KB1's documented "C-4") | `12*(middleC-2)` (stock) |
| Jack CC accepted / channel | yes / `ch == 1` | stock |

Stuck-note safety: a 128-entry table indexed by KB1's raw pitch stores the *effective* pitch used at Note On. Note Off and release-all use the stored value, so a transposition change mid-note can't strand a voice. Release-all synthesises Note Offs through the normal jack-off path, so it works in every `midiInVoiceMode` and only touches KB1-originated notes (USB notes are left alone).

Other parts:
- **Kill switch:** if `/.kb1off` exists on the SD card at boot, the module stays disabled and behaviour is byte-for-byte stock. This follows the `/.develop` precedent, with no config field and no menu edit.
- **Render/export:** `midiUpdate` doesn't run during render. On the first update after render, liveness timers are re-armed rather than timing out spuriously.
- **UI (optional stage):** an ISR sets a flag, and the main loop shows a brief "KB1 connected/disconnected" message (`showInfoPopup` exists, but whether it blocks still needs checking in code).

### 5.4 Hook points (expected merge-conflict footprint)

| File | Change | Size |
|---|---|---|
| `core/include/Platform.h` (`UartMidi::MidiReceiveActions`) | add `systemExclusive(const uint8_t*, unsigned)` and `activeSensing()` pointers | +2 lines |
| `platforms/imx/source/UartMidiImpl.cpp#L15` | register the two callbacks if non-null | +4 lines |
| `platforms/mk66/source/UartMidiImpl.cpp` | same (or nothing; must still compile) | +0–4 |
| `core/source/mtMidi.cpp` | `midiInit`: set new callbacks. Jack handlers: replace 3 expressions with `kb1link::` accessors and add note tracking. `midiUpdate`: `kb1link::tick()` | ~12 lines |
| `core/source/Tracker.cpp#L149` | `kb1link::init(fs->exists("/.kb1off"))` | +1 line |
| **new** `core/source/kb1link/Kb1Link.{h,cpp}` | all logic | new files |

Activation is limited to `TRACKER_MINI` at first. It compiles on all three targets, as CE requires (`make all`).

### 5.5 Reuse across future CE releases
- Keep the work as a **small patch series** (one commit per hook plus one for the module) on a fork branch, rebased onto each upstream tag. `git range-diff` shows when upstream touched a hook.
- A CI job (fork's GitHub Actions) runs `make all` on every rebase, plus host-side unit tests of the state machine. Host tests must live **outside** `core/source/`, or the firmware makefile's `find` will compile them.
- Two pieces are generally useful and could be proposed upstream separately, which would shrink the local patch: (a) jack-input All-Notes-Off/Reset handling, and (b) a SysEx/Active-Sensing callback seam in `UartMidi`.

### 5.6 Alternatives considered

| Option | Firmware changes | Pros | Cons |
|---|---|---|---|
| **0. One-time static config** (`Notes in` and `CC in` = USB + MIDI In jack, channels ALL, Middle C unchanged, KB1 Octave-Down after each KB1 power-on) | none | Works today. No per-session menu changes. | Octave resets on every KB1 boot (needs one button press). No stuck-note protection. Jack always open, so boot garbage can reach the project. Fixed routing if you use other jack gear. |
| 0b. Option 0 + KB1 "persist default octave = −1" | KB1 only (tiny) | Removes the octave press | Same remaining gaps as 0 |
| A. Tracker-only manual "KB1 mode" (runtime-only toggle, no persistence) | Tracker only | No KB1 flashing | One action per session, so not automatic |
| B. Tracker-only heuristic detection of stock KB1 panic burst | Tracker only | No KB1 flashing | Unreliable (§4). No disconnect detection. |
| **C. Recommended: KB1 beacon + Active Sensing, Tracker runtime overlay** | both | Automatic connect/disconnect, stuck-note release, settings never touched, other gear unaffected | Two custom firmwares to maintain. Fork Tracker firmware. |

---

## 6. Feasibility, limitations and risks

**Established from code:** one-way transport. No USB path. Jack is exclusive while docked. Exact settings semantics and their side effects. Where to hook. Overlay can avoid persistence. Parser already receives SysEx/FE. ISR constraints. The makefile auto-includes new files.

**Not yet established (needs your hardware):** that a docked KB1's bytes arrive cleanly at the jack parser. What appears on the line at KB1 reset/flash. Whether stock CE really leaves notes hanging when KB1 powers off mid-note. Actual end-to-end latency. Your exact firmware versions. See `OPEN_QUESTIONS.md`.

Limitations and risks:
- Disconnect is detected by timeout: ≈300 ms after the last `FE` (or up to ~5 s if Active Sensing is disabled). During that window a held note keeps sounding.
- KB1 sleeping looks exactly like KB1 removed. That is fine because notes are released, and the profile re-arms on the wake Hello.
- If KB1 is power-cycled faster than the timeout, the reboot Hello's "boot" reason still triggers a release, but boot garbage between power-on and Hello could reach the parser while the overlay is still active. In practice ESP32 boot plus panic takes longer than 330 ms. Verify **[HW]**.
- Latency budget (estimate): KB1 scan ≤5 ms + press debounce 10 ms + 0.96 ms per 3-byte message on the wire + ≤2.9 ms Tracker poll + audio output buffering. The integration adds O(1) work per message. A beacon can delay one note by at most ~4.2 ms (13 bytes); restricting periodic Hellos to "no keys held" avoids even that.
- Maintaining a forked Tracker firmware means you need to rebase for each CE release you want. The patch is designed to make that mechanical, but it is not zero work.
- Do not sell resulting `.ptf` builds (licence). KB1 firmware modifications are GPL-3.0.
