#!/usr/bin/env python3
"""
Build the S-1 / J-6 songbook.

Emits:
  s1-j6/songs.js      song data consumed by the web player
  s1-j6/midi/*.mid    one Standard MIDI File per song (track 1 = J-6, track 2 = S-1)

Everything is derived from SONGS below, so the page, the MIDI files and the
printed step grids can never drift apart.
"""

import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "s1-j6")
MIDI_DIR = os.path.join(OUT_DIR, "midi")

TPQ = 480  # ticks per quarter note

NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def n(name):
    """'A2' -> midi number. C4 = 60 (middle C)."""
    name = name.strip()
    letter, i = name[0].upper(), 1
    val = NOTE_BASE[letter]
    while i < len(name) and name[i] in "#b":
        val += 1 if name[i] == "#" else -1
        i += 1
    octave = int(name[i:])
    return val + (octave + 1) * 12


def nn(*names):
    return [n(x) for x in names]


def midi_to_name(m):
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[m % 12]}{m // 12 - 1}"


# ---------------------------------------------------------------------------
# Step helpers for the S-1 sequencer
# ---------------------------------------------------------------------------

def S(note, acc=False, slide=False, gate=0.5):
    """One S-1 step that plays a note."""
    return {"n": n(note), "acc": acc, "slide": slide, "gate": gate}


R = None  # a rest


def steps(spec):
    """Parse a compact step string into step dicts.

    Tokens separated by spaces. '-' is a rest. A note may be suffixed with
    '*' for accent and '~' for slide (tie into the next step).
    """
    out = []
    for tok in spec.split():
        if tok == "-":
            out.append(None)
            continue
        acc = "*" in tok
        slide = "~" in tok
        name = tok.replace("*", "").replace("~", "")
        out.append(S(name, acc=acc, slide=slide, gate=0.9 if slide else 0.5))
    return out


# ---------------------------------------------------------------------------
# Songs
# ---------------------------------------------------------------------------

SONGS = [
    # ---------------------------------------------------------------- 1
    {
        "id": "neon-mile",
        "title": "Neon Mile",
        "genre": "Synthwave",
        "bpm": 100,
        "key": "A minor",
        "difficulty": "Easy",
        "blurb": "Wide J-6 pad, octave-jumping S-1 bass. The one to start with — "
                 "four chords, sixteen steps, sounds finished in about two minutes.",
        "j6": {
            "chord_set": "Synthwave / 80s Pop",
            "style": "Pad or slow Arp",
            "variation": "1–3 (keep it simple)",
            "knobs": {
                "CUTOFF": "1 o'clock", "RESONANCE": "9 o'clock",
                "ATTACK": "10 o'clock (slow-ish swell)", "RELEASE": "3 o'clock",
                "REVERB": "2 o'clock", "DELAY": "11 o'clock", "CHORUS": "ON — this is the JUNO sound",
            },
            "prog": ["Am", "F", "C", "G"],
            "chords": [nn("A3", "C4", "E4"), nn("F3", "A3", "C4"),
                       nn("C3", "E3", "G3"), nn("G3", "B3", "D4")],
        },
        "s1": {
            "role": "Bass",
            "div": 4,
            "patch": {
                "WAVE": "SAW", "SUB": "1 o'clock", "CUTOFF": "11 o'clock",
                "RESONANCE": "10 o'clock", "ENV MOD": "12 o'clock",
                "DECAY": "10 o'clock", "ACCENT": "1 o'clock", "LFO": "off",
            },
            "steps": steps(
                "A1 - A2 - A1 - A2 - A1* - A2 - A1 A2 A1 A2 "
                "F1 - F2 - F1 - F2 - F1* - F2 - F1 F2 F1 F2 "
                "C2 - C3 - C2 - C3 - C2* - C3 - C2 C3 C2 C3 "
                "G1 - G2 - G1 - G2 - G1* - G2 - G1 G2 G1 G2 "
            ),
        },
    },
    # ---------------------------------------------------------------- 2
    {
        "id": "acid-rain",
        "title": "Acid Rain",
        "genre": "Acid Techno",
        "bpm": 130,
        "key": "A minor",
        "difficulty": "Medium",
        "blurb": "The reason you buy an S-1. Slides and accents doing the classic "
                 "303 thing while the J-6 throws short stabs over the top.",
        "j6": {
            "chord_set": "Techno / House",
            "style": "Stab / short Arp",
            "variation": "4–6 (busier)",
            "knobs": {
                "CUTOFF": "12 o'clock", "RESONANCE": "1 o'clock",
                "ATTACK": "full left (instant)", "RELEASE": "9 o'clock (very short)",
                "REVERB": "10 o'clock", "DELAY": "1 o'clock", "CHORUS": "OFF",
            },
            "prog": ["Am", "Am", "Dm", "E"],
            "chords": [nn("A3", "C4", "E4"), nn("A3", "C4", "E4"),
                       nn("D3", "F3", "A3"), nn("E3", "G#3", "B3")],
        },
        "s1": {
            "role": "Acid bass",
            "div": 4,
            "patch": {
                "WAVE": "SAW", "SUB": "off", "CUTOFF": "9 o'clock (low — let the env open it)",
                "RESONANCE": "3 o'clock (high, that's the squelch)",
                "ENV MOD": "2 o'clock", "DECAY": "11 o'clock",
                "ACCENT": "3 o'clock", "LFO": "off",
            },
            "steps": steps(
                "A1* - A1 A2~ A2 - C2 - A1* - E2~ E2 - D2 - - "
                "A1* - A1 A2~ A2 - G2 - A1* - C3~ C3 - A2 - - "
                "D2* - D2 D3~ D3 - F2 - D2* - A2~ A2 - F2 - - "
                "E2* - E2 E3~ E3 - G#2 - E2* - B2~ B2 - G#2 - - "
            ),
        },
    },
    # ---------------------------------------------------------------- 3
    {
        "id": "deep-end",
        "title": "Deep End",
        "genre": "Deep House",
        "bpm": 122,
        "key": "F minor",
        "difficulty": "Medium",
        "blurb": "Lush 7th chords on the J-6, round sub bass on the S-1. Turn the "
                 "S-1 cutoff down until you feel it more than you hear it.",
        "j6": {
            "chord_set": "House / Neo Soul",
            "style": "Chord + Arp",
            "variation": "3–5",
            "knobs": {
                "CUTOFF": "12 o'clock", "RESONANCE": "10 o'clock",
                "ATTACK": "9 o'clock", "RELEASE": "1 o'clock",
                "REVERB": "2 o'clock", "DELAY": "12 o'clock", "CHORUS": "ON",
            },
            "prog": ["Fm7", "Bbm7", "Eb7", "Abmaj7"],
            "chords": [nn("F3", "Ab3", "C4", "Eb4"), nn("Bb2", "Db3", "F3", "Ab3"),
                       nn("Eb3", "G3", "Bb3", "Db4"), nn("Ab2", "C3", "Eb3", "G3")],
        },
        "s1": {
            "role": "Sub bass",
            "div": 4,
            "patch": {
                "WAVE": "SQUARE", "SUB": "full right (this is the whole point)",
                "CUTOFF": "9 o'clock", "RESONANCE": "full left",
                "ENV MOD": "10 o'clock", "DECAY": "12 o'clock",
                "ACCENT": "11 o'clock", "LFO": "off",
            },
            "steps": steps(
                "F1 - - F1 - - F1 - - - F1 - Ab1 - C2 - "
                "Bb1 - - Bb1 - - Bb1 - - - Bb1 - Db2 - F2 - "
                "Eb1 - - Eb1 - - Eb1 - - - Eb1 - G1 - Bb1 - "
                "Ab1 - - Ab1 - - Ab1 - - - Ab1 - C2 - Eb2 - "
            ),
        },
    },
    # ---------------------------------------------------------------- 4
    {
        "id": "lo-fi-sunday",
        "title": "Lo-Fi Sunday",
        "genre": "Lo-Fi / Chill",
        "bpm": 78,
        "key": "C major",
        "difficulty": "Easy",
        "blurb": "Slow, jazzy and forgiving. Nothing here is fast enough to go "
                 "wrong. Good last-one-before-bed track.",
        "j6": {
            "chord_set": "Neo Soul / Jazz",
            "style": "Chord (long)",
            "variation": "1–2",
            "knobs": {
                "CUTOFF": "11 o'clock (dark)", "RESONANCE": "9 o'clock",
                "ATTACK": "11 o'clock", "RELEASE": "3 o'clock",
                "REVERB": "3 o'clock", "DELAY": "1 o'clock", "CHORUS": "ON",
            },
            "prog": ["Cmaj7", "Am7", "Dm7", "G7"],
            "chords": [nn("C3", "E3", "G3", "B3"), nn("A2", "C3", "E3", "G3"),
                       nn("D3", "F3", "A3", "C4"), nn("G2", "B2", "D3", "F3")],
        },
        "s1": {
            "role": "Soft lead",
            "div": 2,
            "patch": {
                "WAVE": "TRIANGLE / SQUARE", "SUB": "10 o'clock",
                "CUTOFF": "1 o'clock", "RESONANCE": "10 o'clock",
                "ENV MOD": "10 o'clock", "DECAY": "2 o'clock",
                "ACCENT": "10 o'clock", "LFO": "slow, light pitch wobble",
            },
            "steps": steps(
                "E4 - G4 B4 - A4 G4 - "
                "C4 - E4 G4 - E4 D4 - "
                "F4 - A4 C5 - B4 A4 - "
                "D4 - F4 B4 - G4 - - "
            ),
        },
    },
    # ---------------------------------------------------------------- 5
    {
        "id": "midnight-drive",
        "title": "Midnight Drive",
        "genre": "Dark Techno",
        "bpm": 140,
        "key": "D minor",
        "difficulty": "Medium",
        "blurb": "Fast, moody, relentless. Hold the J-6 chords long and let the "
                 "S-1 hammer straight sixteenths underneath.",
        "j6": {
            "chord_set": "Techno / Minimal",
            "style": "Arp (fast)",
            "variation": "6–9",
            "knobs": {
                "CUTOFF": "11 o'clock", "RESONANCE": "2 o'clock",
                "ATTACK": "full left", "RELEASE": "12 o'clock",
                "REVERB": "1 o'clock", "DELAY": "2 o'clock", "CHORUS": "OFF",
            },
            "prog": ["Dm", "Dm", "Bb", "C"],
            "chords": [nn("D3", "F3", "A3"), nn("D3", "F3", "A3"),
                       nn("Bb2", "D3", "F3"), nn("C3", "E3", "G3")],
        },
        "s1": {
            "role": "Driving bass",
            "div": 4,
            "patch": {
                "WAVE": "SAW", "SUB": "12 o'clock", "CUTOFF": "10 o'clock",
                "RESONANCE": "1 o'clock", "ENV MOD": "1 o'clock",
                "DECAY": "9 o'clock (short and tight)", "ACCENT": "2 o'clock",
                "LFO": "off",
            },
            "steps": steps(
                "D1* D1 D1 D1 D1* D1 D2 D1 D1* D1 D1 F1 D1* D1 A1 D1 "
                "D1* D1 D1 D1 D1* D1 D2 D1 D1* D1 D1 F1 D1* D1 C2~ C2 "
                "Bb1* Bb1 Bb1 Bb1 Bb1* Bb1 Bb2 Bb1 Bb1* Bb1 Bb1 D2 Bb1* Bb1 F2 Bb1 "
                "C2* C2 C2 C2 C2* C2 C3 C2 C2* C2 C2 E2 C2* C2 G2~ G2 "
            ),
        },
    },
    # ---------------------------------------------------------------- 6
    {
        "id": "greensleeves",
        "title": "Greensleeves",
        "genre": "Traditional (public domain)",
        "bpm": 90,
        "key": "A minor",
        "difficulty": "Medium",
        "blurb": "A real tune, so you can hear the S-1 actually sing. Traditional "
                 "English, out of copyright for about four hundred years.",
        "j6": {
            "chord_set": "Pop / Ballad",
            "style": "Chord (long) or slow Arp",
            "variation": "1–3",
            "knobs": {
                "CUTOFF": "12 o'clock", "RESONANCE": "9 o'clock",
                "ATTACK": "10 o'clock", "RELEASE": "2 o'clock",
                "REVERB": "2 o'clock", "DELAY": "10 o'clock", "CHORUS": "ON",
            },
            "prog": ["Am", "C", "Am", "E"],
            "chords": [nn("A3", "C4", "E4"), nn("C3", "E3", "G3"),
                       nn("A3", "C4", "E4"), nn("E3", "G#3", "B3")],
        },
        "s1": {
            "role": "Lead melody",
            "div": 2,
            "patch": {
                "WAVE": "SQUARE", "SUB": "10 o'clock", "CUTOFF": "2 o'clock",
                "RESONANCE": "10 o'clock", "ENV MOD": "10 o'clock",
                "DECAY": "1 o'clock", "ACCENT": "12 o'clock",
                "LFO": "slight pitch vibrato",
            },
            "steps": steps(
                "A3 - C4 - D4 E4 F4 - "
                "E4 - D4 - B3 - G#3 A3 "
                "B3 - A3 - G#3 - E3 - "
                "E3 - - - - - - - "
            ),
        },
    },
    # ---------------------------------------------------------------- 7
    {
        "id": "ode-to-joy",
        "title": "Ode to Joy",
        "genre": "Traditional (public domain)",
        "bpm": 120,
        "key": "C major",
        "difficulty": "Easy",
        "blurb": "Beethoven, 1824. Every note is a step or two from the last one, "
                 "so it's the easiest melody to punch in by hand.",
        "j6": {
            "chord_set": "Pop / Classic",
            "style": "Chord (long)",
            "variation": "1–2",
            "knobs": {
                "CUTOFF": "1 o'clock", "RESONANCE": "9 o'clock",
                "ATTACK": "9 o'clock", "RELEASE": "1 o'clock",
                "REVERB": "1 o'clock", "DELAY": "off", "CHORUS": "ON",
            },
            "prog": ["C", "G", "C", "G"],
            "chords": [nn("C3", "E3", "G3"), nn("G2", "B2", "D3"),
                       nn("C3", "E3", "G3"), nn("G2", "B2", "D3")],
        },
        "s1": {
            "role": "Lead melody",
            "div": 2,
            "patch": {
                "WAVE": "SQUARE", "SUB": "11 o'clock", "CUTOFF": "2 o'clock",
                "RESONANCE": "9 o'clock", "ENV MOD": "10 o'clock",
                "DECAY": "12 o'clock", "ACCENT": "12 o'clock", "LFO": "off",
            },
            "steps": steps(
                "E4 - E4 - F4 - G4 - "
                "G4 - F4 - E4 - D4 - "
                "C4 - C4 - D4 - E4 - "
                "E4 - - D4 D4 - - - "
            ),
        },
    },
    # ---------------------------------------------------------------- 8
    {
        "id": "rising-sun",
        "title": "House of the Rising Sun",
        "genre": "Traditional (public domain)",
        "bpm": 72,
        "key": "A minor",
        "difficulty": "Easy",
        "blurb": "Traditional American folk. The 6/8 rolling arpeggio sits "
                 "beautifully on the S-1 — let the notes ring into each other.",
        "j6": {
            "chord_set": "Ballad / Cinematic",
            "style": "Arp (triplet feel) or long Chord",
            "variation": "2–4",
            "knobs": {
                "CUTOFF": "12 o'clock", "RESONANCE": "10 o'clock",
                "ATTACK": "10 o'clock", "RELEASE": "3 o'clock",
                "REVERB": "3 o'clock", "DELAY": "12 o'clock", "CHORUS": "ON",
            },
            "prog": ["Am", "C", "D", "F"],
            "chords": [nn("A3", "C4", "E4"), nn("C3", "E3", "G3"),
                       nn("D3", "F#3", "A3"), nn("F3", "A3", "C4")],
        },
        "s1": {
            "role": "Rolling arpeggio",
            "div": 2,
            "patch": {
                "WAVE": "TRIANGLE", "SUB": "12 o'clock", "CUTOFF": "1 o'clock",
                "RESONANCE": "10 o'clock", "ENV MOD": "10 o'clock",
                "DECAY": "3 o'clock (long — let them ring)",
                "ACCENT": "11 o'clock", "LFO": "off",
            },
            "steps": steps(
                "A2 C3 E3 A3 E3 C3 - - "
                "C3 E3 G3 C4 G3 E3 - - "
                "D3 F#3 A3 D4 A3 F#3 - - "
                "F2 A2 C3 F3 C3 A2 - - "
            ),
        },
    },
]


# ---------------------------------------------------------------------------
# Standard MIDI File writer (pure stdlib)
# ---------------------------------------------------------------------------

def varlen(value):
    """MIDI variable-length quantity."""
    buf = value & 0x7F
    value >>= 7
    while value:
        buf <<= 8
        buf |= ((value & 0x7F) | 0x80)
        value >>= 7
    out = bytearray()
    while True:
        out.append(buf & 0xFF)
        if buf & 0x80:
            buf >>= 8
        else:
            break
    return bytes(out)


def track_chunk(events):
    """events: list of (abs_tick, priority, bytes). Returns an MTrk chunk."""
    events = sorted(events, key=lambda e: (e[0], e[1]))
    data = bytearray()
    prev = 0
    for tick, _prio, payload in events:
        data += varlen(tick - prev)
        data += payload
        prev = tick
    data += varlen(0) + b"\xff\x2f\x00"  # end of track
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def note_events(ch, note, start, dur, vel):
    """Note-off gets priority 0 so it lands before a same-tick note-on."""
    note = max(0, min(127, note))
    return [
        (start, 1, bytes([0x90 | ch, note, vel])),
        (start + max(1, dur), 0, bytes([0x80 | ch, note, 0])),
    ]


def song_to_midi(song):
    bpm = song["bpm"]
    chords = song["j6"]["chords"]
    s1 = song["s1"]
    div = s1["div"]                      # steps per beat
    step_ticks = TPQ // div
    bar_ticks = TPQ * 4
    total_bars = len(chords)

    # --- conductor track: tempo + time signature + name
    micros = int(60_000_000 / bpm)
    cond = [
        (0, 0, b"\xff\x03" + varlen(len(song["title"].encode())) + song["title"].encode()),
        (0, 0, b"\xff\x58\x04\x04\x02\x18\x08"),
        (0, 0, b"\xff\x51\x03" + micros.to_bytes(3, "big")),
    ]

    # --- J-6 track (channel 1 / index 0): one held chord per bar
    j6 = [(0, 0, b"\xff\x03\x03J-6")]
    j6.append((0, 0, bytes([0xC0, 0])))
    for bar, ch_notes in enumerate(chords):
        start = bar * bar_ticks
        for note in ch_notes:
            j6 += note_events(0, note, start, int(bar_ticks * 0.96), 88)

    # --- S-1 track (channel 2 / index 1): the step sequence
    s1_ev = [(0, 0, b"\xff\x03\x03S-1")]
    s1_ev.append((0, 0, bytes([0xC1, 0])))
    seq = s1["steps"]
    for i, st in enumerate(seq):
        if st is None:
            continue
        start = i * step_ticks
        # a slide ties this step into the next one
        length = step_ticks
        if st["slide"]:
            j = i + 1
            while j < len(seq) and seq[j] is None:
                length += step_ticks
                j += 1
            length += step_ticks
            dur = length
        else:
            dur = max(1, int(step_ticks * st["gate"]))
        vel = 112 if st["acc"] else 80
        s1_ev += note_events(1, st["n"], start, dur, vel)

    header = b"MThd" + struct.pack(">IHHH", 6, 1, 3, TPQ)
    return header + track_chunk(cond) + track_chunk(j6) + track_chunk(s1_ev)


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

def jsonable(song):
    """Strip the song down to what the web page needs."""
    s1 = song["s1"]
    return {
        "id": song["id"],
        "title": song["title"],
        "genre": song["genre"],
        "bpm": song["bpm"],
        "key": song["key"],
        "difficulty": song["difficulty"],
        "blurb": song["blurb"],
        "j6": {
            "chordSet": song["j6"]["chord_set"],
            "style": song["j6"]["style"],
            "variation": song["j6"]["variation"],
            "knobs": song["j6"]["knobs"],
            "prog": song["j6"]["prog"],
            "chords": song["j6"]["chords"],
            "chordNames": [[midi_to_name(m) for m in c] for c in song["j6"]["chords"]],
        },
        "s1": {
            "role": s1["role"],
            "div": s1["div"],
            "patch": s1["patch"],
            "steps": [
                None if st is None else {
                    "n": st["n"], "name": midi_to_name(st["n"]),
                    "acc": st["acc"], "slide": st["slide"], "gate": st["gate"],
                }
                for st in s1["steps"]
            ],
        },
        "midi": f"midi/{song['id']}.mid",
    }


def validate(song):
    """A step list must fill exactly one step per subdivision of every bar."""
    bars = len(song["j6"]["chords"])
    want = bars * 4 * song["s1"]["div"]
    got = len(song["s1"]["steps"])
    if got != want:
        raise SystemExit(
            f"{song['id']}: {got} steps but {bars} bars at 1/{song['s1']['div'] * 4} "
            f"needs exactly {want}. Fix the step string."
        )
    if want > 64:
        raise SystemExit(f"{song['id']}: {want} steps exceeds the S-1's 64-step limit.")


def main():
    os.makedirs(MIDI_DIR, exist_ok=True)
    payload = []
    for song in SONGS:
        validate(song)
        data = song_to_midi(song)
        path = os.path.join(MIDI_DIR, f"{song['id']}.mid")
        with open(path, "wb") as fh:
            fh.write(data)
        payload.append(jsonable(song))
        print(f"  {song['id']:<18} {len(data):>5} bytes  "
              f"{len(song['s1']['steps']):>2} steps  {song['bpm']} bpm")

    js = "// Generated by tools/build_songs.py — do not edit by hand.\n"
    js += "window.SONGS = " + json.dumps(payload, indent=1) + ";\n"
    with open(os.path.join(OUT_DIR, "songs.js"), "w") as fh:
        fh.write(js)
    print(f"\n{len(payload)} songs -> {OUT_DIR}/songs.js + {MIDI_DIR}/*.mid")


if __name__ == "__main__":
    main()
