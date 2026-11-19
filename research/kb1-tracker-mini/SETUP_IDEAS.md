# What custom firmware could do with the gear you already have

Status: **ideas and feasibility only**. Nothing has been built or flashed. Builds on `RESEARCH.md`.

## 1. Inventory (as seen by your PC "Intel-Build", 2026-11-19, read-only)

| Device | Seen on PC | Firmware open? | MIDI ports (verified where marked) |
|---|---|---|---|
| **Polyend Tracker Mini** | connected (`16D0:1118`), running your vocoder build | **Yes**: Tracker CE, MIT + no-resale clause | USB **device only** (no host) [code]; 3.5 mm MIDI In/Out **TRS Type B** [manual] |
| **Pocket MIDI KB1** | known (`303A:1001`, COM3), not attached now | **Yes**: ESP32-S3, GPL-3.0 | TRS out into Tracker only (one-way) [netlist]; **BLE radio** [code]; USB-C on the ESP32-S3 (currently serial/flash only) [code] |
| Teenage Engineering **OP-XY** | known (`2367:0021`) | No | 3.5 mm MIDI = **Type A** [TE guide]; USB-C MIDI; USB **host** reported on op-forums (not yet confirmed by TE docs) |
| 1010music **bluebox** (desktop) | known | No | TRS MIDI: **receives Type A *and* B, sends Type B** [1010music staff, forum]; USB MIDI device |
| Novation **Launchpad Pro MK3** | known | Official: **no** (only the *original* Launchpad Pro has Novation's open firmware). Community "CoreFW" (Rust reimplementation) exists, with a reported "Code 10" failure after flashing | USB MIDI; TRS MIDI in/out (type not verified here) |
| Behringer **Poly D** | known (`1397:122A`) | No | 5-pin DIN MIDI + USB MIDI |
| Roland **S-1**, **J-6** (from your songbook repo) | not on this PC | No | 3.5 mm MIDI = **Type A** ("All AIRA Compacts use MIDI TRS TYPE A", Roland) |
| Focusrite **Scarlett Solo 4th Gen** | known | No | Audio only |
| AYN Thor (Android handheld) | connected | n/a | Can host USB MIDI and BLE MIDI (Android) |

**Cabling consequence:** Tracker Mini and the bluebox's *output* are **Type B**. OP-XY, S-1 and J-6 are **Type A**. A plain TRS↔TRS cable works Tracker → bluebox (the bluebox accepts B). It does **not** work Tracker → S-1/J-6/OP-XY: use the Tracker's Type-B→DIN adapter, then a Type-A DIN→TRS adapter, or route through the Poly D's DIN THRU.

## 2. Ideas, ranked by value ÷ (effort × risk)

### Tier 1: high value, uses only open firmware or no firmware

1. **KB1 auto-profile on Tracker** (already planned in `IMPLEMENTATION_PLAN.md`). Dock, switch on, play; settings untouched; stuck notes released on undock or sleep.

2. **Tracker as a USB→TRS MIDI bridge** *(Tracker CE change)*. Today Tracker CE turns MIDI thru off (`UartMidiImpl::init` → `turnThruOff()`) and never forwards USB input to the jack. Add a runtime-only "thru" that forwards selected USB-in channels to MIDI Out. Your PC, phone or `tools/aira_local.py` could then play the **Poly D, S-1, J-6, bluebox and OP-XY** through the Tracker's one TRS out, which passes through KB1's J3 when docked. No other MIDI interface needed. It also gives you a hardware MIDI path from the Windows box to the DIN/TRS gear.

3. **KB1 also plays the external synths** *(Tracker CE change, same mechanism as 2)*. Forward KB1's jack input to MIDI Out with a channel remap (KB1 is hard-wired to ch 1). For example, levers/touch → S-1 filter while keys play the Tracker, or layer KB1 onto the Poly D. This is a real use for KB1 that stock firmware can't do.

4. **KB1 + your vocoder build** *(Tracker change on the vocoder fork, after the Zelda/vocoder stopping point)*. KB1's Line-In pass-through (J1) feeds the Tracker's line in, and its keys and levers arrive as notes and CCs. A mic into KB1 J1, chords on KB1 as the carrier, and levers/touch mapped to vocoder parameters (formant, mix, bands) makes the docked pair a self-contained vocoder keyboard with KB1's built-in speakers. Treat this as a separate branch so it doesn't disturb the current vocoder work.

5. **Launchpad Pro MK3 as a Tracker performance surface** *(no firmware change)*. Tracker CE already listens for CC 41–48 (track mutes in Performance mode), CC 51–62 (performance FX slots) and CC 71–82 (mixer) [code: `fPerformance.cpp#L890`, `fMasterParams.cpp#L3075`]. A Launchpad *custom mode* (Novation Components, official) can send exactly these. Keep the official firmware; CoreFW isn't worth the brick risk.

### Tier 2: KB1 firmware, broader reach (ESP32-S3 can do these; GPL-3.0)

6. **KB1 as a USB-MIDI keyboard when undocked**. Switch the ESP32-S3's USB from Serial/JTAG to TinyUSB MIDI (`ARDUINO_USB_MODE=0`). KB1 then plugs straight into the PC, the AYN Thor, or the OP-XY (if its host mode is confirmed) and plays them. Trade-off: flashing changes slightly (KB1 Studio's Web-Serial flasher may need the ROM download mode via the BOOT button, see OPEN_QUESTIONS Q7).

7. **KB1 as a BLE-MIDI controller**. The radio is already there for the Configurator. Adding a standard BLE-MIDI service lets KB1 play the AYN Thor or the PC (Windows MIDI Services is installed) wirelessly while still docked. Combined with idea 2, PC → Tracker USB → TRS lets KB1's BLE output reach every synth. Cost: battery (KB1's own numbers: ~35 mA without radio vs 50–95 mA with BLE).

8. **Per-preset MIDI channel and persisted octave**. KB1 hard-codes channel 1 and resets octave on boot (`KeyboardControl.h`, `OctaveControl.h`). Making both preset fields helps every route above (e.g. channel 2 → S-1 per your songbook layout).

9. **Tracker-aware KB1 presets**. Ship presets mapping levers/touch to Tracker CCs that actually exist (e.g. touch → CC 1 Cutoff, lever → CC 110 synth Macro 1, push → perf FX CC 51). This mostly needs Configurator presets, not code.

### Tier 3: possible, lower priority

10. **OP-XY ↔ Tracker over USB, no PC**, *if* OP-XY's USB host is confirmed: Tracker Mini (USB device) plugs into OP-XY for clock/notes both ways. No firmware change, only verification.
11. **bluebox as recorder/mixer under Tracker control**: Tracker → bluebox via a plain TRS cable (bluebox accepts Type B), with clock/transport to start recording in sync. CC → bluebox mixer if its MIDI CC map allows (check the bluebox manual's CC table).
12. **Launchpad LED feedback from Tracker** (Tracker CE change): send pattern/track state as SysEx to the Launchpad over USB via the PC, or over TRS. More work; only after 5 proves useful.

### Not recommended
- **CoreFW on the Launchpad Pro MK3**: reverse-engineered with a reported failure after flashing, and the official modes already cover idea 5.
- Hardware mods to make KB1 bidirectional: excluded by your instructions.
- Anything on OP-XY, bluebox, Poly D, S-1, J-6 or Scarlett firmware: closed. Integrate over MIDI only.

## 3. Suggested order (when you're ready to implement)
1. Idea 1 (KB1 auto-profile), already staged.
2. Idea 2/3 (thru/bridge), a small Tracker change sharing the same `kb1link`/MIDI seam and highest leverage across your gear.
3. Idea 8 (KB1 channel + octave persist), small and low risk.
4. Idea 4 (vocoder keyboard) once the vocoder work reaches a stopping point.
5. Ideas 6/7 (KB1 USB or BLE MIDI), after the KB1 flashing and recovery path is proven on your unit.

## 4. Still to verify (adds to OPEN_QUESTIONS)
- OP-XY USB host for MIDI devices (forum claim only).
- Launchpad Pro MK3 TRS MIDI type; bluebox MIDI CC map; Poly D's MIDI CC reception (likely minimal, since it's an analogue panel synth) and whether its USB port receives notes.
- Which TRS/DIN adapters you physically have (Tracker's Type-B adapter, TE Type-A, Roland/BOSS cables).
