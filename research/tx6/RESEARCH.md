# TX-6 custom-firmware project: research

Status: **research only**. Nothing has been flashed, and nothing was sent to any device. Your PC's USB history shows no TX-6 ever connected there, so everything below comes from Teenage Engineering's public docs and the public firmware file.

Legend: **[DOC]** TE documentation · **[FW]** inspected public firmware file · **[FORUM]** community report, unverified · **[HW]** needs a test on your unit.

---

## 0. Bottom line

| Question | Answer |
|---|---|
| Can we write and flash our own TX-6 firmware? | **Not realistically.** The firmware is closed, the update image is encrypted, and TE hardened bootloader security in the latest release (§1). Breaking that means bypassing TE's security, risks bricking a battery device with a radio, and voids the warranty. **Not recommended and not planned.** |
| Can we make the TX-6 do new things anyway? | **Yes, a lot.** TE exposes **external MIDI control of all TX-6 parameters**, a "local control off" switch, MIDI notes for its synth/sequencer, scene recall, and USB + Bluetooth **host** modes [DOC]. A device with *open* firmware can act as the TX-6's "brain", which gives firmware-like features without touching the TX-6. |
| Which of your devices can be that brain? | **KB1** (ESP32-S3 with BLE + USB, open GPL firmware), **Tracker Mini** (Tracker CE, open), and your **PC or phone** (software, zero risk). |

---

## 1. TX-6 firmware: what was verified

- **Source:** none published. TE's downloads page offers binary `.tfw` images only. Update by TE's web MIDI updater, or hold **CUE** while powering on to get a mass-storage "update mode" and drop the `.tfw` on it [DOC: teenage.engineering/downloads/tx-6].
- **Latest:** `1.3.3+1` (2026-01-28): "usb audio stability, **improved bootloader security**" [DOC].
- **Image inspected** (public download, bytes only, nothing executed): `tx-6_firmware_1_3_3+1.tfw`, 611,856 bytes, SHA-256 `6ee4f3b59fe78619a124a8c3797cd30c1db2c17ac4c3db173dd104c21b4052b6` [FW]:
  - Plain outer header starting with magic `BA BE CA FE`, version fields `1.3.3.1`, then a second header `BE EF CA FE`.
  - **Payload entropy 7.99 bits/byte in every 16 KB block**, with no meaningful strings. Unencrypted ARM code and data sit well below that and contain readable strings. **The payload is encrypted** (and possibly signed).
- **Community:** no custom/open TX-6 firmware projects found. One lines-forum report of a unit that boots into update mode 50–75 % of the time [FORUM], a reminder that update mode itself can misbehave.

**Conclusion:** custom TX-6 firmware would require defeating TE's encryption/signing. We shouldn't do that.

---

## 2. TX-6 capabilities that matter for integration [DOC]

From the TX-6 guide (v1.3.0, "midi reference" section) and release notes:

- **Connections:** MIDI over **USB-C** and **Bluetooth LE**. No TRS/DIN MIDI jack is listed. Clock/sync **output** on aux/cue (PO-sync 8th or 16th notes, with start/stop).
- **Host modes:** USB **MIDI host** (since 1.1.4), USB **audio host** (1.2.10, for CM-15/TP-7), BLE **host** for "peripherals like BLE midi keyboards" (1.1.4), BLE MIDI clock in/out.
- **Remote control:** "external midi control of all TX-6 parameters" (1.1.4). **Local control off** (CC 122 ch 7) disables the TX-6's own knobs and faders, so an external device can take over completely.
- **Built-in synth / sequencer / sampler / looper / DJ mode** (1.2.x–1.3.0). Notes on ch 1–6 play track 1–6 synth chromatically. Ch 7 notes C–A trigger "parameter" per track.
- 1.3.0 additions whose exact behaviour is in image-only guide pages: **"midi synth generator"**, **"midi cc knob function"**, **link mode**, user-configurable sequencer patterns (pitch per step), pattern chaining, extra scenes on USB [DOC, details **[HW]**].

### 2.1 MIDI reference (copied from TE's guide)

**Sent by TX-6 in controller mode** (channel 1): faders CC 1–6; upper knobs CC 7–12; middle CC 13–18; lower CC 19–24; track buttons CC 25–30 (0/127); encoder turn CC 31 (relative −64…+63); encoder button CC 32; FX I CC 33; FX II CC 34; shift CC 35; aux CC 36; cue CC 37.

**Received:**

| Control | CC | Channel |
|---|---|---|
| track volume | 7 | 1–6 (per track) |
| pan / balance | 8 | 1–6 |
| gain | 9 | 1–6 |
| seq pattern | 14 | 1–6 |
| mute/solo | 120 | 1–6 |
| filter freq | 74 | 1–6 |
| EQ high / mid / low | 85 / 86 / 87 | 1–6 |
| compressor | 93 | 1–6 |
| synth waveform / freq / length / detune | 3 / 89 / 90 / 95 | 1–6 |
| FX I send / aux send / aux II send | 91 / 92 / 94 | 1–6 |
| main / aux / cue volume | 7 / 14 / 15 | 7 |
| local control | 122 | 7 |
| start/stop toggle; tempo relative | 46; 47 | 7 |
| FX I/II enable, engine, param 1/2/3 | 82, 15, 12/13/14 | 8 (FX I), 9 (FX II) |
| FX I return level; FX II track select | 7; 9 | 8; 9 |

Notes: ch 1–6 = chromatic synth per track; ch 7 notes C,D,E,F,G,A = track 1–6 "parameter". Program change ch 7 = scene slots. On/off values: 0–63 off, 64–127 on.

**Caution:** the TX-6 uses **CC 120 for mute/solo**, which is All Sound Off in standard MIDI. A device that sends standard "panic" messages to the TX-6 may toggle mutes.

---

## 3. Your gear vs. the TX-6 (from your PC's device history, plus your songbook repo)

| Device | Firmware | How it can reach the TX-6 |
|---|---|---|
| **KB1** | **open** (ESP32-S3, GPL) | Today: none (TRS out only, docked to the Tracker). **With custom firmware: BLE-MIDI → TX-6 BLE host**, or USB-MIDI → TX-6 USB host |
| **Tracker Mini** | **open** (Tracker CE) | USB-C **device** → TX-6 USB **host** (MIDI; audio is a question, Q3). Tracker can send notes/CC/clock over USB today |
| OP-XY | closed | USB (OP-XY reported as host *and* device [FORUM]) or audio cables |
| bluebox | closed | Audio; USB MIDI device (TX-6 host could control it if supported) |
| Poly D, S-1, J-6 | closed | Audio into TX-6 channels. S-1/J-6 are USB-MIDI devices that a TX-6 host might drive (Q6) |
| Scarlett Solo | closed | Audio interface on the PC |
| PC (Windows MIDI Services) / AYN Thor | software | USB or BLE MIDI to the TX-6. Zero-risk prototyping |

Constraint: the TX-6 has one USB-C port. If it is hosting the Tracker, it can't also be a USB device to the PC at the same time. BLE stays free.

---

## 4. What we can make the TX-6 do, ranked

### A. KB1 "TX-6 mode" over Bluetooth (KB1 firmware, recommended first)
Add a standard **BLE-MIDI peripheral** to KB1's existing BLE stack. The TX-6 connects to it in BLE host mode. Then:
- KB1 keys play the TX-6 synth chromatically on ch 1–6. Octave buttons (or a lever push) pick the target track.
- Levers → per-track **filter (CC 74)**, **FX I send (CC 91)**, **synth detune (CC 95)**. Touch strip → FX I parameter (CC 12–14, ch 8).
- Lever-push gestures → **start/stop (CC 46 ch 7)**, **scene recall (program change ch 7)**.
- KB1 stays docked to the Tracker and playing it over TRS **at the same time**, so one keyboard drives both instruments (e.g. a split by octave, or a mode toggle).

Why first: KB1 is the device built for custom firmware, the TX-6 officially supports BLE MIDI keyboards, and nothing on the TX-6 changes. Cost: BLE battery draw (KB1's own figures: ~35 mA without radio, 50–95 mA with BLE).

### B. Tracker Mini as the TX-6's sequencer and mix automation (no firmware change needed)
Tracker Mini (USB device) → TX-6 (USB MIDI host). Tracker **MIDI instrument tracks** send notes to the TX-6 synth (ch 1–6) and **CC step FX** automate the TX-6 mixer per pattern step: volume (CC 7), filter (74), EQ (85–87), FX sends (91/92/94), FX parameters (ch 8/9). The Tracker becomes the TX-6's automation lane, and works with stock CE. **[HW]**: confirm the TX-6 hosts the Tracker Mini (Q3).

### C. TX-6 as a hands-on controller for the Tracker (Tracker CE change)
In controller mode the TX-6 sends fixed CC 1–37 on ch 1. These only partly line up with the Tracker's map (CC 1 cutoff, CC 7 volume…). A small **"TX-6 control profile"** in Tracker CE, structured like the KB1 overlay (runtime-only, never written to settings), could map:
- faders → Tracker track volumes (mixer CC 71–82 range)
- knobs → performance FX slots (51–62)
- track buttons → mutes (41–48)

Two-way USB also allows **auto-detection**: the Tracker can send a MIDI *Identity Request*, and **if** the TX-6 answers (Q5), the profile switches on automatically.

### D. A PC/phone "TX-6 brain" (software only, zero risk)
A script in the style of `tools/aira_local.py`: scene recall, mix snapshots, timed mixer moves, and a CC-120-safe panic. Good for prototyping A–C before writing any firmware.

### E. Lower priority / needs verification
- TX-6 sequencer or "midi synth generator" driving S-1/J-6/OP-XY over USB host (Q6).
- Tracker Mini audio into the TX-6 over the same USB cable (Q3), which would make it a one-cable rig.
- TX-6 sync out (PO-sync on aux/cue) clocking other gear. This is a built-in feature, no firmware needed.

### Not recommended
- Modified or decrypted TX-6 firmware (§1).
- Sending generic MIDI "panic" (CC 120/123 on all channels) to the TX-6, because CC 120 = mute/solo there.

---

## 5. Sources
- TE TX-6 guide (v1.3.0), especially "midi reference": https://teenage.engineering/guides/tx-6
- TE TX-6 downloads and release notes: https://teenage.engineering/downloads/tx-6
- Firmware file inspected: https://teenage.engineering/_software/tx-6/tx-6_firmware_1_3_3+1.tfw (SHA-256 above)
- Community: lines forum TX-6 thread p.19 (update-mode boot issue); op-forums "TX-6 update 1.2.10" (USB host "H" icon)
- KB1 and Tracker CE evidence: `../kb1-tracker-mini/RESEARCH.md`
