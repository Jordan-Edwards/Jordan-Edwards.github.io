#!/usr/bin/env python3
"""
Build the S-1 / J-6 idea library.

Emits s1-j6/library/:
  <Key>/<NN-genre-roman>/chords.mid   J-6 style chords, one track, block chords
  <Key>/<NN-genre-roman>/arp.mid      1/16 arpeggio of the same voicings
  <Key>/<NN-genre-roman>/bass.mid     S-1 bassline, mono, accents + slides
  <Key>/<NN-genre-roman>/lead.mid     S-1 lead / topline, mono
  <Key>/<NN-genre-roman>/all.mid      the whole kit: chords ch1, bass ch2, lead ch3, arp ch4
  index.json                          what is where (read by s1-j6/library.html)

24 keys (12 roots x minor/major), 6 progressions per key, every part exactly
4 bars = 64 sixteenth steps, so each mono part fits an S-1 pattern.

Accent = velocity 110 (plain notes 80). Slide = the note is held
SLIDE_OVERLAP ticks past the start of the next (different) note: legato
overlap, which is what triggers glide on the S-1 and most mono synths.

Everything is deterministic: the only randomness is a Random() seeded from
the kit's path, so rebuilding produces byte-identical files.

Stdlib only. The MIDI helpers are shared with tools/build_songs.py.
"""

import itertools
import json
import os
import random
import shutil
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_songs import TPQ, midi_to_name, note_events, varlen  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "s1-j6", "library")

STEP = TPQ // 4           # one 1/16 step
BAR = TPQ * 4
BARS = 4
STEPS = BARS * 16         # 64 = one full S-1 pattern
END = BARS * BAR
SLIDE_OVERLAP = 30        # ticks a sliding note overlaps the next one
ACC, NORM = 110, 80

RANGES = {                # inclusive MIDI ranges each part must stay in
    "chords": (48, 72),   # C3..C5
    "arp": (48, 84),      # C3..C6
    "bass": (24, 48),     # C1..C3
    "lead": (48, 84),     # C3..C6
}

# ---------------------------------------------------------------------------
# Theory
# ---------------------------------------------------------------------------

LETTERS = "CDEFGAB"
LETTER_PC = [0, 2, 4, 5, 7, 9, 11]
SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}

# Conventional spelling for each tonic (fewest accidentals).
TONICS = {
    "major": ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"],
    "minor": ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"],
}

QUALITY = {  # intervals, chord-symbol suffix
    "maj": ([0, 4, 7], ""),
    "min": ([0, 3, 7], "m"),
    "7": ([0, 4, 7, 10], "7"),
    "maj7": ([0, 4, 7, 11], "maj7"),
    "m7": ([0, 3, 7, 10], "m7"),
    "m7b5": ([0, 3, 6, 10], "m7b5"),
    "9": ([0, 4, 10, 14], "9"),        # 9th chords drop the 5th (4 voices)
    "maj9": ([0, 4, 11, 14], "maj9"),
    "m9": ([0, 3, 10, 14], "m9"),
}

GENRES = {  # tag -> display, bpm
    "synthwave": ("Synthwave", 100),
    "house": ("House", 124),
    "lofi": ("Lo-fi", 80),
    "techno": ("Techno", 132),
    "pop": ("Pop", 112),
    "cinematic": ("Dark / Cinematic", 90),
}

# Each chord: (roman numeral, scale-degree index 0-6, semitones above tonic, quality)
PROGRESSIONS = {
    "minor": [
        ("synthwave", "Aeolian anthem: the classic 80s minor loop",
         [("i", 0, 0, "min"), ("VI", 5, 8, "maj"), ("III", 2, 3, "maj"), ("VII", 6, 10, "maj")]),
        ("house", "Deep-house minor 7ths/9ths",
         [("i9", 0, 0, "m9"), ("iv7", 3, 5, "m7"), ("VImaj7", 5, 8, "maj7"), ("v7", 4, 7, "m7")]),
        ("lofi", "Jazz minor ii-V-i with a VImaj7 turnaround",
         [("iiø7", 1, 2, "m7b5"), ("V7", 4, 7, "7"), ("i9", 0, 0, "m9"), ("VImaj7", 5, 8, "maj7")]),
        ("techno", "Hypnotic i-iv-v stabs",
         [("i", 0, 0, "min"), ("i", 0, 0, "min"), ("iv", 3, 5, "min"), ("v", 4, 7, "min")]),
        ("pop", "Minor pop loop",
         [("i", 0, 0, "min"), ("III", 2, 3, "maj"), ("VII", 6, 10, "maj"), ("VI", 5, 8, "maj")]),
        ("cinematic", "Phrygian bII + major V: dark and tense",
         [("i", 0, 0, "min"), ("bII", 1, 1, "maj"), ("VI", 5, 8, "maj"), ("V", 4, 7, "maj")]),
    ],
    "major": [
        ("synthwave", "Borrowed bVI-bVII lift (80s soundtrack)",
         [("I", 0, 0, "maj"), ("vi", 5, 9, "min"), ("bVI", 5, 8, "maj"), ("bVII", 6, 10, "maj")]),
        ("house", "Royal road with 7ths (city pop / piano house)",
         [("IVmaj7", 3, 5, "maj7"), ("V7", 4, 7, "7"), ("iii7", 2, 4, "m7"), ("vi7", 5, 9, "m7")]),
        ("lofi", "ii-V-I in 9ths with a vi9 turnaround",
         [("ii9", 1, 2, "m9"), ("V9", 4, 7, "9"), ("Imaj9", 0, 0, "maj9"), ("vi9", 5, 9, "m9")]),
        ("techno", "Mixolydian I-bVII-IV",
         [("I", 0, 0, "maj"), ("I", 0, 0, "maj"), ("bVII", 6, 10, "maj"), ("IV", 3, 5, "maj")]),
        ("pop", "The axis progression",
         [("vi", 5, 9, "min"), ("IV", 3, 5, "maj"), ("I", 0, 0, "maj"), ("V", 4, 7, "maj")]),
        ("cinematic", "Chromatic-mediant III and borrowed iv",
         [("I", 0, 0, "maj"), ("III", 2, 4, "maj"), ("IV", 3, 5, "maj"), ("iv", 3, 5, "min")]),
    ],
}

# Which pattern style each genre uses for each part.
STYLE = {
    #            chords rhythm, arp order, bass style,       lead motif
    "synthwave": ("held", "up", "octave-bounce", "synthwave"),
    "house": ("stabs", "broken", "offbeat-root-fifth", "house"),
    "lofi": ("held", "updown", "walking", "lofi"),
    "techno": ("offbeat", "down", "acid-303", "techno"),
    "pop": ("held", "updown", "pumping-root-fifth", "pop"),
    "cinematic": ("held", "broken", "sub-glide", "cinematic"),
}


def spell(tonic, degree, semis):
    """Spell the root of a chord by its scale degree, e.g. bVI of C -> Ab."""
    t_letter = LETTERS.index(tonic[0])
    t_pc = (LETTER_PC[t_letter] + (1 if "#" in tonic else 0) - (1 if "b" in tonic[1:] else 0)) % 12
    letter = LETTERS[(t_letter + degree) % 7]
    target = (t_pc + semis) % 12
    acc = (target - LETTER_PC[LETTERS.index(letter)]) % 12
    if acc > 6:
        acc -= 12
    name = letter + {0: "", 1: "#", -1: "b"}.get(acc, "?")
    if "?" in name or name in ("Cb", "Fb", "E#", "B#"):
        name = (FLATS if acc < 0 else SHARPS)[target]
    return name, target


def tonic_pc(tonic):
    return spell(tonic, 0, 0)[1]


def safe(s):
    return s.replace("#", "s").replace("ø7", "m7b5").replace("ø", "m7b5")


# ---------------------------------------------------------------------------
# Chords + voice leading
# ---------------------------------------------------------------------------

def voicing_candidates(pcs):
    lo, hi = RANGES["chords"]
    opts = [[m for m in range(lo, hi + 1) if m % 12 == pc] for pc in pcs]
    out = set()
    for combo in itertools.product(*opts):
        v = tuple(sorted(combo))
        if len(set(v)) != len(v):
            continue
        if v[-1] - v[0] > (12 if len(v) == 3 else 16):
            continue
        if any(b - a == 1 for a, b in zip(v, v[1:])):   # no minor-2nd rubs
            continue
        out.add(v)
    return sorted(out)


def motion(a, b):
    if len(a) == len(b):
        return sum(abs(x - y) for x, y in zip(a, b))
    return (sum(min(abs(x - y) for y in a) for x in b)
            + sum(min(abs(x - y) for y in b) for x in a)) / 2


def reg_cost(v):
    return abs(sum(v) / len(v) - 61) * 0.35


def voice_lead(chords_pcs):
    """Pick one voicing per chord minimising movement (loop-aware)."""
    cands = [voicing_candidates(p) for p in chords_pcs]
    best = None
    for first in cands[0]:
        # DP over the remaining chords
        layer = {first: (reg_cost(first), [first])}
        for cs in cands[1:]:
            nxt = {}
            for v in cs:
                opts = [(c + motion(p, v) + reg_cost(v), path + [v]) for p, (c, path) in layer.items()]
                nxt[v] = min(opts)
            layer = nxt
        for v, (c, path) in layer.items():
            total = c + 0.5 * motion(v, first)   # smooth back to bar 1 when looping
            if best is None or (total, path) < best:
                best = (total, path)
    return [list(v) for v in best[1]]


def bar_scale(key_pcs, chord_pcs):
    """Key scale, bent so it contains every chord tone of this bar."""
    s = set(key_pcs)
    for pc in chord_pcs:
        if pc not in s:
            s.discard((pc + 1) % 12)
            s.discard((pc - 1) % 12)
            s.add(pc)
    return sorted(s)


# ---------------------------------------------------------------------------
# Parts. Mono parts are lists of events: {start, len (in steps), note, acc, slide}
# ---------------------------------------------------------------------------

def E(start, length, note, acc=False, slide=False):
    return {"start": start, "len": length, "note": note, "acc": acc, "slide": slide}


CHORD_RHYTHM = {
    "held": [(0, 16)],
    "stabs": [(0, 2), (3, 2), (6, 2), (10, 2), (13, 2)],
    "offbeat": [(2, 1), (6, 1), (10, 1), (14, 1)],
}


def gate(length):
    return int(STEP * 0.55) if length == 1 else length * STEP - 30


def chords_part(voicings, rhythm):
    notes = []
    for bar, v in enumerate(voicings):
        for i, (st, ln) in enumerate(CHORD_RHYTHM[rhythm]):
            vel = 96 if i == 0 else 84
            for m in v:
                notes.append((bar * BAR + st * STEP, gate(ln), m, vel))
    return notes


ARP_ORDER = {
    "up": lambda L: list(range(L)),
    "down": lambda L: list(range(L - 1, -1, -1)),
    "updown": lambda L: list(range(L)) + list(range(L - 2, 0, -1)),
    "broken": lambda L: [i % L for i in (0, 2, 1, 3, 2, 4, 3, 1)],
}
ARP_STEPS = {  # which 1/16 steps sound (per bar)
    "synthwave": list(range(16)),
    "house": list(range(16)),
    "pop": list(range(16)),
    "cinematic": list(range(16)),
    "lofi": [0, 2, 3, 4, 6, 8, 10, 11, 12, 14],
    "techno": [0, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15],
}


def arp_part(voicings, order, genre):
    ev = []
    for bar, v in enumerate(voicings):
        pool = sorted(v) + [min(v) + 12]
        seq = ARP_ORDER[order](len(pool))
        for k, st in enumerate(ARP_STEPS[genre]):
            ev.append(E(bar * 16 + st, 1, pool[seq[k % len(seq)]], acc=(st % 4 == 0)))
    return ev


def chord_info(root_pc, quality, bscale):
    ivs = QUALITY[quality][0]
    third = 3 if 3 in ivs else 4
    fifth = 6 if 6 in ivs else 7
    sev = next((i for i in ivs if i in (10, 11)), None)
    if sev is None:
        rel = [(p - root_pc) % 12 for p in bscale]
        sev = 10 if 10 in rel else 11
    return {"r": 24 + root_pc, "3": third, "5": fifth, "7": sev}


ACID_A = [(0, "r", 1, 0), (2, "r", 0, 0), (3, "o", 0, 1), (4, "5", 0, 0), (6, "r", 1, 0),
          (7, "3", 0, 1), (8, "5", 0, 0), (10, "o", 1, 0), (11, "7", 0, 1), (12, "o", 0, 0),
          (14, "5", 0, 0), (15, "3", 0, 1)]
ACID_B = [(0, "r", 1, 0), (1, "r", 0, 0), (3, "o", 1, 1), (4, "7", 0, 0), (6, "r", 0, 0),
          (7, "r", 0, 0), (8, "5", 0, 1), (9, "o", 1, 0), (11, "3", 0, 0), (12, "r", 1, 0),
          (14, "o", 0, 1), (15, "5", 0, 0)]


def iv(ci, sym):
    r = ci["r"]
    return {"r": r, "o": r + 12, "3": r + ci["3"], "5": r + ci["5"], "7": r + ci["7"]}[sym]


def bass_part(infos, style):
    ev = []
    n = len(infos)
    for bar, ci in enumerate(infos):
        b0 = bar * 16
        last = bar == n - 1
        r = ci["r"]
        nxt = infos[(bar + 1) % n]["r"]
        if style == "acid-303":
            tpl = ACID_A if bar % 2 == 0 else ACID_B
            for st, sym, acc, sl in tpl:
                ev.append(E(b0 + st, 1, iv(ci, sym), bool(acc), bool(sl) and not (last and st == 15)))
        elif style == "octave-bounce":
            for k, st in enumerate(range(0, 16, 2)):
                note = r if k % 2 == 0 else r + 12
                if st == 14:
                    note = r + ci["5"]
                ev.append(E(b0 + st, 2, note, acc=st in (0, 8)))
        elif style == "offbeat-root-fifth":
            for st, ln, note, acc in [(2, 2, r, 1), (6, 2, r, 0), (10, 2, r, 1),
                                      (13, 1, r + ci["5"], 0), (14, 2, r + 12, 0)]:
                ev.append(E(b0 + st, ln, note, bool(acc)))
        elif style == "pumping-root-fifth":
            for st in range(0, 16, 2):
                note = r + ci["5"] if st == 12 else (r + 12 if st == 14 else r)
                ev.append(E(b0 + st, 2, note, acc=st in (0, 8)))
        elif style == "sub-glide":
            ev.append(E(b0, 8, r, acc=True))
            ev.append(E(b0 + 8, 4, r + ci["5"]))
            ev.append(E(b0 + 12, 4, r, slide=not last and nxt != r))
        elif style == "walking":
            if bar % 2 == 0:
                line = [r, r + ci["3"], r + ci["5"]]
            else:
                line = [r, r + ci["5"], r + 12]
            lo, hi = RANGES["bass"]
            appr = [x for x in (nxt - 1, nxt + 1, nxt + 11, nxt + 13) if lo <= x <= hi and x != line[-1]]
            line.append(min(appr, key=lambda x: (abs(x - line[-1]), x)))
            for k, note in enumerate(line):
                ev.append(E(b0 + 4 * k, 4, note, acc=k == 0))
        else:
            raise ValueError(style)
    return ev


# rhythm A (bars 1-3) and cadence B (bar 4): (start, len); contours in scale steps
LEAD_MOTIFS = {
    "synthwave": ([(0, 3), (3, 3), (6, 2), (8, 4), (12, 2), (14, 2)], [0, -1, 0, 2, 1, 0],
                  [(0, 3), (3, 3), (6, 2), (8, 8)], [2, 1, -1, 0]),
    "house": ([(0, 1), (2, 2), (6, 2), (10, 1), (12, 3)], [0, 0, 1, -1, 0],
              [(0, 1), (2, 2), (6, 2), (10, 6)], [0, 1, 2, 0]),
    "lofi": ([(2, 2), (4, 3), (8, 2), (10, 2), (12, 4)], [2, 1, 0, -1, 0],
             [(2, 2), (4, 2), (6, 2), (8, 8)], [1, 2, 1, 0]),
    "techno": ([(0, 1), (3, 1), (6, 1), (8, 1), (10, 1), (11, 1), (14, 2)], [0, 0, 2, 0, 1, 0, -1],
               [(0, 1), (3, 1), (6, 1), (8, 8)], [0, 0, 2, 0]),
    "pop": ([(0, 2), (2, 2), (4, 4), (8, 2), (10, 2), (12, 4)], [0, 1, 2, 2, 1, 0],
            [(0, 2), (2, 2), (4, 4), (8, 8)], [2, 1, 0, 0]),
    "cinematic": ([(0, 6), (6, 2), (8, 8)], [0, 1, -1],
                  [(0, 4), (4, 4), (8, 8)], [2, 1, 0]),
}


def lead_part(genre, key_pcs, chords, rng):
    rhA, conA, rhB, conB = LEAD_MOTIFS[genre]
    conA3 = conA[:-2] + [c + rng.choice([-2, -1, 1, 2]) for c in conA[-2:]]
    plan = [(rhA, conA), (rhA, conA), (rhA, conA3), (rhB, conB)]
    ev, anchor = [], 67
    for bar, ((rh, con), ch) in enumerate(zip(plan, chords)):
        pcs = ch["pcs"]
        sc = bar_scale(key_pcs, pcs)
        tones = [m for m in range(60, 77) if m % 12 in pcs]
        anchor = min(tones, key=lambda m: (abs(m - anchor), m))
        snotes = [m for m in range(36, 100) if m % 12 in sc]
        ai = snotes.index(anchor)
        all_tones = [m for m in range(48, 85) if m % 12 in pcs]
        for (st, ln), c in zip(rh, con):
            m = snotes[ai + c]
            if st % 4 == 0 and m % 12 not in pcs:
                m = min(all_tones, key=lambda t: (abs(t - m), t))
            while m > 84:
                m -= 12
            while m < 52:
                m += 12
            ev.append(E(bar * 16 + st, ln, m, acc=st % 8 == 0))
    if genre != "lofi":
        prob = 0.35 if genre == "techno" else 0.2
        for a, b in zip(ev, ev[1:]):
            if (a["start"] + a["len"] == b["start"] and 0 < abs(a["note"] - b["note"]) <= 5
                    and rng.random() < prob):
                a["slide"] = True
    return ev


def render_mono(events):
    """Mono events -> (tick, dur, note, vel). Slides overlap the next note."""
    evs = []
    for e in sorted(events, key=lambda e: e["start"]):
        if (evs and evs[-1]["slide"] and evs[-1]["note"] == e["note"]
                and evs[-1]["start"] + evs[-1]["len"] == e["start"]):
            evs[-1]["len"] += e["len"]          # same-pitch slide = tie
            evs[-1]["slide"] = e["slide"]
            continue
        evs.append(dict(e))
    out = []
    for i, e in enumerate(evs):
        if e["start"] < 0 or e["start"] + e["len"] > STEPS:
            raise SystemExit(f"event outside the 64-step pattern: {e}")
        if i + 1 < len(evs) and evs[i + 1]["start"] < e["start"] + e["len"]:
            raise SystemExit(f"overlapping steps: {e} / {evs[i + 1]}")
        tick = e["start"] * STEP
        if e["slide"]:
            if i + 1 >= len(evs) or evs[i + 1]["start"] != e["start"] + e["len"]:
                raise SystemExit(f"slide with no adjacent next note: {e}")
            dur = evs[i + 1]["start"] * STEP - tick + SLIDE_OVERLAP
        else:
            dur = gate(e["len"])
        out.append((tick, dur, e["note"], ACC if e["acc"] else NORM))
    return out


# ---------------------------------------------------------------------------
# SMF writing (helpers from build_songs.py)
# ---------------------------------------------------------------------------

def meta(mtype, payload):
    return b"\xff" + bytes([mtype]) + varlen(len(payload)) + payload


def track_chunk(events, end_tick):
    """Like build_songs.track_chunk, but End-of-Track lands exactly on end_tick
    so every file is exactly 4 bars long."""
    events = sorted(events, key=lambda e: (e[0], e[1]))
    data, prev = bytearray(), 0
    for tick, _p, payload in events:
        data += varlen(tick - prev) + payload
        prev = tick
    data += varlen(end_tick - prev) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def tempo_meta(bpm, title):
    return [
        (0, 0, meta(0x03, title.encode())),
        (0, 0, meta(0x58, b"\x04\x02\x18\x08")),
        (0, 0, meta(0x51, int(60_000_000 / bpm).to_bytes(3, "big"))),
    ]


def part_events(notes, ch):
    ev = []
    for tick, dur, note, vel in notes:
        ev += note_events(ch, note, tick, dur, vel)
    return ev


def smf_single(title, bpm, notes):
    """Format 0, one track, channel 1: tempo + name + notes."""
    trk = tempo_meta(bpm, title) + part_events(notes, 0)
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, TPQ) + track_chunk(trk, END)


ALL_ORDER = [("chords", 0, "Chords (J-6)"), ("bass", 1, "Bass (S-1)"),
             ("lead", 2, "Lead (S-1)"), ("arp", 3, "Arp (J-6)")]


def smf_all(title, bpm, parts):
    chunks = [track_chunk(tempo_meta(bpm, title), END)]
    for part, ch, name in ALL_ORDER:
        chunks.append(track_chunk([(0, 0, meta(0x03, name.encode()))] + part_events(parts[part], ch), END))
    return b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), TPQ) + b"".join(chunks)


# ---------------------------------------------------------------------------
# SMF reading for validation (independent of the writer)
# ---------------------------------------------------------------------------

def _vl(buf, i):
    v = 0
    while True:
        b = buf[i]
        i += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, i


def parse_smf(data):
    assert data[:4] == b"MThd", "no MThd"
    _, fmt, ntrk, tpq = struct.unpack(">IHHH", data[4:14])
    pos, tracks = 14, []
    for _ in range(ntrk):
        assert data[pos:pos + 4] == b"MTrk", "bad MTrk"
        ln = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + ln]
        pos += 8 + ln
        i, tick, running = 0, 0, None
        trk = {"name": None, "tempo": None, "notes": [], "eot": None}
        open_ = {}
        while i < len(body):
            d, i = _vl(body, i)
            tick += d
            st = body[i]
            if st == 0xFF:
                mt = body[i + 1]
                ml, j = _vl(body, i + 2)
                payload = body[j:j + ml]
                i = j + ml
                if mt == 0x03:
                    trk["name"] = payload.decode()
                elif mt == 0x51:
                    trk["tempo"] = int.from_bytes(payload, "big")
                elif mt == 0x2F:
                    trk["eot"] = tick
                    break
                continue
            if st & 0x80:
                running, i = st, i + 1
            st = running
            hi, ch = st & 0xF0, st & 0x0F
            if hi in (0xC0, 0xD0):
                i += 1
                continue
            d1, d2 = body[i], body[i + 1]
            i += 2
            if hi == 0x90 and d2 > 0:
                open_.setdefault((ch, d1), []).append((tick, d2))
            elif hi == 0x80 or (hi == 0x90 and d2 == 0):
                on, vel = open_[(ch, d1)].pop(0)
                trk["notes"].append((on, tick, d1, vel, ch))
        assert trk["eot"] is not None, "no end of track"
        assert not any(open_.values()), "hanging note"
        trk["notes"].sort()
        tracks.append(trk)
    assert pos == len(data), "trailing bytes"
    return fmt, tpq, tracks


def check_part(label, part, notes):
    lo, hi = RANGES[part]
    for on, off, note, vel, _ch in notes:
        if not lo <= note <= hi:
            raise SystemExit(f"{label}: {midi_to_name(note)} outside {part} range")
        if on < 0 or off > END or off <= on:
            raise SystemExit(f"{label}: note {on}-{off} outside the 4-bar pattern")
    if part == "chords":
        groups = {}
        for on, off, note, *_ in notes:
            groups.setdefault(on, []).append(off)
        starts = sorted(groups)
        for k, s in enumerate(starts):
            offs = groups[s]
            if len(offs) < 3 or len(set(offs)) != 1:
                raise SystemExit(f"{label}: chord at {s} is not a clean block chord")
            if k + 1 < len(starts) and offs[0] > starts[k + 1]:
                raise SystemExit(f"{label}: chords overlap at {s}")
        return
    for a, b in zip(notes, notes[1:]):
        if b[0] == a[0]:
            raise SystemExit(f"{label}: two notes start together at {a[0]} (not mono)")
        if a[1] > b[0]:  # overlap: only allowed as a slide into a different pitch
            if a[1] - b[0] > SLIDE_OVERLAP or a[2] == b[2] or a[1] > b[1]:
                raise SystemExit(f"{label}: illegal overlap {a} / {b}")
    if part == "arp" and any(a[1] > b[0] for a, b in zip(notes, notes[1:])):
        raise SystemExit(f"{label}: arp should not slide")


def validate_kit(folder, bpm, parts):
    tempo = int(60_000_000 / bpm)
    strip = lambda ns: [(on, off, n, v) for on, off, n, v, _c in ns]  # noqa: E731
    expect = {p: sorted((t, t + d, n, v) for t, d, n, v in notes) for p, notes in parts.items()}
    for part in ("chords", "arp", "bass", "lead"):
        path = os.path.join(folder, f"{part}.mid")
        fmt, tpq, tracks = parse_smf(open(path, "rb").read())
        assert fmt == 0 and tpq == TPQ and len(tracks) == 1, path
        t = tracks[0]
        assert t["eot"] == END and t["tempo"] == tempo, f"{path}: length/tempo"
        check_part(path, part, t["notes"])
        assert strip(t["notes"]) == expect[part], f"{path}: round-trip mismatch"
    path = os.path.join(folder, "all.mid")
    fmt, tpq, tracks = parse_smf(open(path, "rb").read())
    assert fmt == 1 and len(tracks) == 5 and tracks[0]["tempo"] == tempo, path
    for trk, (part, ch, name) in zip(tracks[1:], ALL_ORDER):
        assert trk["name"] == name and trk["eot"] == END, path
        assert all(c == ch for *_x, c in trk["notes"]), f"{path}: {part} channel"
        check_part(f"{path}:{part}", part, trk["notes"])
        assert strip(trk["notes"]) == expect[part], f"{path}: {part} mismatch"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_kit(mode, tonic, idx, genre, blurb, prog):
    t_pc = tonic_pc(tonic)
    key_pcs = [(t_pc + s) % 12 for s in SCALES[mode]]
    chords = []
    for roman, deg, semis, qual in prog:
        rname, rpc = spell(tonic, deg, semis)
        ivs, suffix = QUALITY[qual]
        chords.append({"roman": roman, "name": rname + suffix, "root_pc": rpc, "quality": qual,
                       "pcs": [(rpc + i) % 12 for i in ivs]})
    voicings = voice_lead([c["pcs"] for c in chords])
    rhythm, arp_order, bass_style, lead_style = STYLE[genre]
    key_dir = f"{safe(tonic)}-{mode}"
    kit_id = f"{idx:02d}-{genre}-{safe('-'.join(c['roman'] for c in chords))}"
    rng = random.Random(zlib.crc32(f"{key_dir}/{kit_id}".encode()))

    infos = [chord_info(c["root_pc"], c["quality"], bar_scale(key_pcs, c["pcs"])) for c in chords]
    parts = {
        "chords": chords_part(voicings, rhythm),
        "arp": render_mono(arp_part(voicings, arp_order, genre)),
        "bass": render_mono(bass_part(infos, bass_style)),
        "lead": render_mono(lead_part(lead_style, key_pcs, chords, rng)),
    }
    return key_dir, kit_id, chords, voicings, parts, (rhythm, arp_order, bass_style, lead_style)


def main():
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)   # no stale files from older layouts
    keys, nfiles, nbytes = [], 0, 0
    for tonic_i in range(12):
        for mode in ("minor", "major"):
            tonic = TONICS[mode][tonic_i]
            key_entry = None
            for idx, (genre, blurb, prog) in enumerate(PROGRESSIONS[mode], 1):
                key_dir, kit_id, chords, voicings, parts, styles = build_kit(
                    mode, tonic, idx, genre, blurb, prog)
                gname, bpm = GENRES[genre]
                folder = os.path.join(OUT_DIR, key_dir, kit_id)
                os.makedirs(folder, exist_ok=True)
                title = f"{tonic} {mode} - {gname} - {' '.join(c['name'] for c in chords)}"
                files = {}
                for part in ("chords", "arp", "bass", "lead"):
                    data = smf_single(f"{title} - {part}", bpm, parts[part])
                    with open(os.path.join(folder, f"{part}.mid"), "wb") as fh:
                        fh.write(data)
                    files[part] = f"{key_dir}/{kit_id}/{part}.mid"
                    nfiles += 1
                    nbytes += len(data)
                data = smf_all(title, bpm, parts)
                with open(os.path.join(folder, "all.mid"), "wb") as fh:
                    fh.write(data)
                files["all"] = f"{key_dir}/{kit_id}/all.mid"
                nfiles += 1
                nbytes += len(data)
                validate_kit(folder, bpm, parts)

                if key_entry is None:
                    key_entry = {"id": key_dir, "name": f"{tonic} {mode}", "tonic": tonic,
                                 "tonic_pc": tonic_pc(tonic), "mode": mode, "kits": []}
                    keys.append(key_entry)
                key_entry["kits"].append({
                    "id": kit_id,
                    "n": idx,
                    "genre": genre,
                    "genre_name": gname,
                    "bpm": bpm,
                    "about": blurb,
                    "roman": [c["roman"] for c in chords],
                    "chords": [c["name"] for c in chords],
                    "voicings": voicings,
                    "styles": dict(zip(("chords", "arp", "bass", "lead"), styles)),
                    "files": files,
                })
    index = {
        "generated_by": "tools/build_library.py",
        "ppq": TPQ,
        "bars": BARS,
        "steps": STEPS,
        "channels": {"all.mid": {"chords": 1, "bass": 2, "lead": 3, "arp": 4},
                     "single files": 1},
        "velocity": {"accent": ACC, "normal": NORM},
        "keys": keys,
    }
    with open(os.path.join(OUT_DIR, "index.json"), "w") as fh:
        json.dump(index, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    nkits = sum(len(k["kits"]) for k in keys)
    print(f"{len(keys)} keys, {nkits} kits, {nfiles} .mid files, {nbytes} bytes of MIDI -> {OUT_DIR}")
    print("all files parsed back and validated (ranges, monophony, block chords, 4-bar length).")


if __name__ == "__main__":
    main()
