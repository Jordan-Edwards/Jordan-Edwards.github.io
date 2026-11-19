# TX-6 project: staged plan (not started)

Rules: no TX-6 firmware modification. Back up TX-6 settings to a **scene** (and to USB, if 1.3.x) before every stage. Only KB1 and Tracker Mini firmware are ever changed, using the backup and recovery procedures in `../kb1-tracker-mini/IMPLEMENTATION_PLAN.md`.

## Stage 0: Verify on hardware (no firmware changes)
1. Record TX-6 OS version (system menu → os version). Save current settings to a scene.
2. **USB host test:** Tracker Mini → TX-6 USB-C with a USB-C↔USB-C data cable. Does the TX-6 show the host "H" icon? Does the Tracker's MIDI arrive (play a Tracker MIDI track on ch 1, expect TX-6 track 1 synth)? Is Tracker audio available as a TX-6 input? (Q3)
3. **BLE host test with a stand-in:** a phone BLE-MIDI app (AYN Thor) as a peripheral → TX-6 BLE host. Confirm notes on ch 1–6 and a few CCs (74, 91). This proves path A before writing any KB1 code. (Q4)
4. **Identity test** (PC → TX-6 over USB): send `F0 7E 7F 06 01 F7` and log any reply. (Q5)
5. Send CC 120 = 0 on ch 1 from the PC and confirm it acts as mute/solo, not "all sound off", so the panic rules are correct.

**Exit:** a checklist of which of A–E are possible on your unit.

## Stage 1: Software prototype (PC/phone, zero risk)
- `tools/tx6_brain.py` (or an extension of `aira_local.py`): scene recall, mix snapshot, and a CC-120-safe panic (notes off per channel only).
- Acceptance: drive every received CC in the RESEARCH §2.1 table from the script, and see each effect on the TX-6.

## Stage 2: Tracker → TX-6 automation (stock CE or your CE fork)
- Build a Tracker project template: tracks 9–14 = MIDI instruments on ch 1–6, with CC step FX for volume, filter and sends.
- Acceptance: a pattern automates TX-6 track filter and FX sends in time; tempo follows Tracker clock (if the TX-6 clock-in setting allows; check in Stage 0).

## Stage 3: KB1 "TX-6 mode" (KB1 firmware)
- Add a BLE-MIDI service (standard MIDI-over-BLE UUIDs) alongside the existing configurator service, behind a build flag.
- Mode switch (e.g. a lever-push gesture): **Tracker** (TRS only) / **TX-6** (BLE only) / **Both**.
- Mapping table (TX-6 mode): keys → notes on the selected track channel (1–6); octave buttons → track select; lever 1 → CC 74; lever 2 → CC 91; touch → CC 12 ch 8; long push → CC 46 ch 7 (start/stop).
- **Never send CC 120/123 panics over BLE to the TX-6.** Release held notes with explicit note-offs.
- Acceptance: pair from TX-6; play tracks 1–6; control filter and send; the toggle between modes works; Tracker TRS behaviour is unchanged in Both mode; reconnect after KB1 sleep works without re-pairing; no stuck notes after KB1 sleep or power-off.

## Stage 4: Tracker CE "TX-6 control profile" (optional)
- Runtime-only mapping of TX-6 controller CCs (1–37, ch 1) to Tracker mixer, performance FX and mutes. Auto-enable via Identity Reply if Stage 0 #4 succeeded, otherwise a manual toggle. Same design rules as the KB1 overlay (never written to `mtConfig`).
- Acceptance: TX-6 faders move Tracker track volumes; settings files unchanged; disabling restores stock behaviour.
