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

The file has two halves:

  DATA    every progression and every rhythm/pattern style, each with the
          `source` it comes from and `why` it is idiomatic. Edit this to
          change what the library contains.
  ENGINE  turns DATA into notes for all 24 keys: voice-leads the chords,
          resolves pattern symbols against each bar's chord, writes and
          re-reads every file to validate it.

Every part is exactly 4 bars = 64 sixteenth steps, so each mono part fits one
S-1 pattern. Accent = velocity 110 (plain notes 80). Slide = the note is held
SLIDE_OVERLAP ticks past the start of the next, different note (legato
overlap, which is what triggers glide on the S-1 and most mono synths).

Deterministic: the only randomness is a Random() seeded from the kit's path,
so rebuilding produces byte-identical files. Stdlib only; the MIDI helpers
are shared with tools/build_songs.py.
"""

import itertools
import json
import os
import random
import re
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

PENDING = "PENDING: source to be filled in from research"


# ===========================================================================
# DATA
# ===========================================================================
#
# Roman numerals are relative to the key's OWN scale (natural minor for minor
# keys), so in A minor "VI" = F and "bII" = Bb; in C major "bVII" = Bb.
# Case sets major/minor; suffixes: 7 maj7 9 maj9 11 6 sus2 sus4 add9 ø7 ° °7.
#
# Pattern symbols (bass and arp are resolved against each bar's chord):
#   r root   o octave   3 third   5 fifth   7 seventh (chord's, else the scale's)
#   a        chromatic approach into the NEXT bar's root
# Grid step tuples are (step 0-15, symbol, length in steps, accent 0/1, slide 0/1).
# A "bars" entry may be a list of alternatives; the engine picks the one whose
# last note sits closest to the next bar's root (smooth walking lines).
# "float": True lets the root sit in either bass octave (nearest the previous
# note) instead of always C1-B1.

GENRES = {
    "synthwave": {"name": "Synthwave", "bpm": 100, "source": PENDING, "why": ""},
    "house": {"name": "House", "bpm": 124, "source": PENDING, "why": ""},
    "lofi": {"name": "Lo-fi", "bpm": 80, "source": PENDING, "why": ""},
    "techno": {"name": "Techno", "bpm": 132, "source": PENDING, "why": ""},
    "pop": {"name": "Pop", "bpm": 112, "source": PENDING, "why": ""},
    "cinematic": {"name": "Dark / Cinematic", "bpm": 90, "source": PENDING, "why": ""},
}

CHORD_RHYTHMS = {
    "held": {"hits": [(0, 16)], "source": PENDING,
             "why": "One chord per bar, held: pads, and room for the J-6 phrase engine."},
    "house-stabs": {"hits": [(0, 2), (3, 2), (6, 2), (10, 2), (13, 2)], "source": PENDING,
                    "why": "Syncopated 3-3-4-3-3 stabs."},
    "offbeat-stabs": {"hits": [(2, 1), (6, 1), (10, 1), (14, 1)], "source": PENDING,
                      "why": "Short stabs on every off-beat 8th."},
}

ARPS = {
    "up-16": {"order": "up", "steps": "all", "reset": "bar", "accent": "beat",
              "source": PENDING, "why": "Straight 1/16 up-arp."},
    "down-gated": {"order": "down", "steps": [0, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15],
                   "reset": "bar", "accent": "beat", "source": PENDING,
                   "why": "Down-arp with gated gaps."},
    "updown-16": {"order": "updown", "steps": "all", "reset": "bar", "accent": "beat",
                  "source": PENDING, "why": "Up-down 1/16 arp."},
    "updown-lazy": {"order": "updown", "steps": [0, 2, 3, 4, 6, 8, 10, 11, 12, 14],
                    "reset": "bar", "accent": "beat", "source": PENDING,
                    "why": "Up-down with rests, lazier feel."},
    "broken-16": {"order": "broken", "steps": "all", "reset": "bar", "accent": "beat",
                  "source": PENDING, "why": "Broken-chord (1-3-2-4) figure."},
    "poly-3-over-4": {"order": [0, 2, 1], "steps": "all", "reset": "never", "accent": "cycle",
                      "poly": "3-note cycle over 1/16 = 3 against 4",
                      "source": PENDING, "why": "3-step figure against the 4/4 grid."},
}

_ACID_A = [(0, "r", 1, 1, 0), (2, "r", 1, 0, 0), (3, "o", 1, 0, 1), (4, "5", 1, 0, 0),
           (6, "r", 1, 1, 0), (7, "3", 1, 0, 1), (8, "5", 1, 0, 0), (10, "o", 1, 1, 0),
           (11, "7", 1, 0, 1), (12, "o", 1, 0, 0), (14, "5", 1, 0, 0), (15, "3", 1, 0, 1)]
_ACID_B = [(0, "r", 1, 1, 0), (1, "r", 1, 0, 0), (3, "o", 1, 1, 1), (4, "7", 1, 0, 0),
           (6, "r", 1, 0, 0), (7, "r", 1, 0, 0), (8, "5", 1, 0, 1), (9, "o", 1, 1, 0),
           (11, "3", 1, 0, 0), (12, "r", 1, 1, 0), (14, "o", 1, 0, 1), (15, "5", 1, 0, 0)]
_OCT = [(s, "r" if s % 4 == 0 else "o", 2, int(s in (0, 8)), 0) for s in range(0, 14, 2)] + [(14, "5", 2, 0, 0)]
_OFFBEAT = [(2, "r", 2, 1, 0), (6, "r", 2, 0, 0), (10, "r", 2, 1, 0), (13, "5", 1, 0, 0), (14, "o", 2, 0, 0)]
_PUMP = [(s, "r", 2, int(s in (0, 8)), 0) for s in range(0, 12, 2)] + [(12, "5", 2, 0, 0), (14, "o", 2, 0, 0)]
_SUB = [(0, "r", 8, 1, 0), (8, "5", 4, 0, 0), (12, "r", 4, 0, 1)]
_WALK_UP = [(0, "r", 4, 1, 0), (4, "3", 4, 0, 0), (8, "5", 4, 0, 0), (12, "a", 4, 0, 0)]
_WALK_DOWN = [(0, "o", 4, 1, 0), (4, "5", 4, 0, 0), (8, "3", 4, 0, 0), (12, "a", 4, 0, 0)]

BASSES = {
    "acid-303": {"bars": [_ACID_A, _ACID_B, _ACID_A, _ACID_B], "source": PENDING,
                 "why": "16th 303 line: accents and slides between root, octave, 3rd, 5th, 7th."},
    "octave-8ths": {"bars": [_OCT] * 4, "source": PENDING, "why": "Root-octave 8ths."},
    "offbeat-root-fifth": {"bars": [_OFFBEAT] * 4, "source": PENDING, "why": "Off-beat root bass."},
    "pumping-8ths": {"bars": [_PUMP] * 4, "source": PENDING, "why": "Driving root 8ths."},
    "sub-glide": {"bars": [_SUB] * 4, "source": PENDING, "why": "Long sub roots that glide into the next chord."},
    "walking": {"bars": [[_WALK_UP, _WALK_DOWN]] * 4, "float": True, "source": PENDING,
                "why": "Quarter-note walk: chord tones, then a half-step approach to the next root."},
    "poly-3-16": {"cell": [(0, "r", 1, 1, 0), (2, "o", 1, 0, 0)], "period": 3,
                  "poly": "3/16 cell over 4/4 (lands on a different 16th each beat)",
                  "source": PENDING, "why": "Polymetric 3-step bass cell."},
}

# Lead motifs: rhythm A (bars 1-3, bar 3 varies its tail) + cadence B (bar 4).
# Rhythm = (start step, length); contour = scale steps from the bar's anchor
# chord tone. Notes that land on a beat snap to a chord tone.
LEADS = {
    "synthwave-hook": {"A": [(0, 3), (3, 3), (6, 2), (8, 4), (12, 2), (14, 2)], "A_contour": [0, -1, 0, 2, 1, 0],
                       "B": [(0, 3), (3, 3), (6, 2), (8, 8)], "B_contour": [2, 1, -1, 0],
                       "slide": 0.2, "source": PENDING, "why": ""},
    "house-chop": {"A": [(0, 1), (2, 2), (6, 2), (10, 1), (12, 3)], "A_contour": [0, 0, 1, -1, 0],
                   "B": [(0, 1), (2, 2), (6, 2), (10, 6)], "B_contour": [0, 1, 2, 0],
                   "slide": 0.2, "source": PENDING, "why": ""},
    "lofi-lazy": {"A": [(2, 2), (4, 3), (8, 2), (10, 2), (12, 4)], "A_contour": [2, 1, 0, -1, 0],
                  "B": [(2, 2), (4, 2), (6, 2), (8, 8)], "B_contour": [1, 2, 1, 0],
                  "slide": 0.0, "source": PENDING, "why": ""},
    "techno-stab": {"A": [(0, 1), (3, 1), (6, 1), (8, 1), (10, 1), (11, 1), (14, 2)],
                    "A_contour": [0, 0, 2, 0, 1, 0, -1],
                    "B": [(0, 1), (3, 1), (6, 1), (8, 8)], "B_contour": [0, 0, 2, 0],
                    "slide": 0.35, "source": PENDING, "why": ""},
    "pop-hook": {"A": [(0, 2), (2, 2), (4, 4), (8, 2), (10, 2), (12, 4)], "A_contour": [0, 1, 2, 2, 1, 0],
                 "B": [(0, 2), (2, 2), (4, 4), (8, 8)], "B_contour": [2, 1, 0, 0],
                 "slide": 0.2, "source": PENDING, "why": ""},
    "cinematic-long": {"A": [(0, 6), (6, 2), (8, 8)], "A_contour": [0, 1, -1],
                       "B": [(0, 4), (4, 4), (8, 8)], "B_contour": [2, 1, 0],
                       "slide": 0.2, "source": PENDING, "why": ""},
    "dotted-eighth": {"A": [(0, 3), (3, 3), (6, 3), (9, 3), (12, 4)], "A_contour": [0, 1, 2, 1, 0],
                      "B": [(0, 3), (3, 3), (6, 3), (9, 7)], "B_contour": [2, 1, 0, 0],
                      "slide": 0.15, "poly": "dotted-1/8 phrasing (3 against 4)",
                      "source": PENDING, "why": ""},
}

# One entry per kit. Kits are numbered per mode in list order.
PROGRESSIONS = [
    # ---------------------------------------------------------------- minor
    {"mode": "minor", "genre": "synthwave", "name": "Aeolian anthem",
     "roman": ["i", "VI", "III", "VII"],
     "chords": "held", "arp": "up-16", "bass": "octave-8ths", "lead": "dotted-eighth",
     "source": PENDING, "why": ""},
    {"mode": "minor", "genre": "house", "name": "Deep minor 7ths",
     "roman": ["i9", "iv7", "VImaj7", "v7"],
     "chords": "house-stabs", "arp": "poly-3-over-4", "bass": "offbeat-root-fifth", "lead": "house-chop",
     "source": PENDING, "why": ""},
    {"mode": "minor", "genre": "lofi", "name": "Minor ii-V-i",
     "roman": ["iiø7", "V7", "i9", "VImaj7"],
     "chords": "held", "arp": "updown-lazy", "bass": "walking", "lead": "lofi-lazy",
     "source": PENDING, "why": ""},
    {"mode": "minor", "genre": "techno", "name": "i-iv-v stabs",
     "roman": ["i", "i", "iv", "v"],
     "chords": "offbeat-stabs", "arp": "down-gated", "bass": "acid-303", "lead": "techno-stab",
     "source": PENDING, "why": ""},
    {"mode": "minor", "genre": "pop", "name": "Minor pop loop",
     "roman": ["i", "III", "VII", "VI"],
     "chords": "held", "arp": "updown-16", "bass": "pumping-8ths", "lead": "pop-hook",
     "source": PENDING, "why": ""},
    {"mode": "minor", "genre": "cinematic", "name": "Phrygian bII to V",
     "roman": ["i", "bII", "VI", "V"],
     "chords": "held", "arp": "broken-16", "bass": "sub-glide", "lead": "cinematic-long",
     "source": PENDING, "why": ""},
    # ---------------------------------------------------------------- major
    {"mode": "major", "genre": "synthwave", "name": "Borrowed bVI-bVII lift",
     "roman": ["I", "vi", "bVI", "bVII"],
     "chords": "held", "arp": "up-16", "bass": "octave-8ths", "lead": "synthwave-hook",
     "source": PENDING, "why": ""},
    {"mode": "major", "genre": "house", "name": "Royal road 7ths",
     "roman": ["IVmaj7", "V7", "iii7", "vi7"],
     "chords": "house-stabs", "arp": "broken-16", "bass": "offbeat-root-fifth", "lead": "house-chop",
     "source": PENDING, "why": ""},
    {"mode": "major", "genre": "lofi", "name": "ii-V-I in 9ths",
     "roman": ["ii9", "V9", "Imaj9", "vi9"],
     "chords": "held", "arp": "updown-lazy", "bass": "walking", "lead": "lofi-lazy",
     "source": PENDING, "why": ""},
    {"mode": "major", "genre": "techno", "name": "Mixolydian I-bVII-IV",
     "roman": ["I", "I", "bVII", "IV"],
     "chords": "offbeat-stabs", "arp": "down-gated", "bass": "poly-3-16", "lead": "techno-stab",
     "source": PENDING, "why": ""},
    {"mode": "major", "genre": "pop", "name": "Axis progression",
     "roman": ["vi", "IV", "I", "V"],
     "chords": "held", "arp": "updown-16", "bass": "pumping-8ths", "lead": "pop-hook",
     "source": PENDING, "why": ""},
    {"mode": "major", "genre": "cinematic", "name": "Chromatic mediant + minor iv",
     "roman": ["I", "III", "IV", "iv"],
     "chords": "held", "arp": "broken-16", "bass": "sub-glide", "lead": "cinematic-long",
     "source": PENDING, "why": ""},
]


# ===========================================================================
# ENGINE
# ===========================================================================

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

QUALITY = {  # intervals, chord-symbol suffix. 9/11 chords drop the 5th (4 voices).
    "maj": ([0, 4, 7], ""), "min": ([0, 3, 7], "m"), "dim": ([0, 3, 6], "dim"),
    "sus2": ([0, 2, 7], "sus2"), "sus4": ([0, 5, 7], "sus4"), "add9": ([0, 4, 7, 14], "add9"),
    "6": ([0, 4, 7, 9], "6"), "m6": ([0, 3, 7, 9], "m6"),
    "7": ([0, 4, 7, 10], "7"), "maj7": ([0, 4, 7, 11], "maj7"), "m7": ([0, 3, 7, 10], "m7"),
    "m7b5": ([0, 3, 6, 10], "m7b5"), "dim7": ([0, 3, 6, 9], "dim7"),
    "9": ([0, 4, 10, 14], "9"), "maj9": ([0, 4, 11, 14], "maj9"), "m9": ([0, 3, 10, 14], "m9"),
    "m11": ([0, 3, 10, 17], "m11"), "madd9": ([0, 3, 7, 14], "madd9"),
}
UPPER_SUFFIX = {"": "maj", "7": "7", "maj7": "maj7", "9": "9", "maj9": "maj9", "6": "6",
                "sus2": "sus2", "sus4": "sus4", "add9": "add9"}
LOWER_SUFFIX = {"": "min", "7": "m7", "9": "m9", "11": "m11", "6": "m6", "add9": "madd9",
                "ø7": "m7b5", "ø": "m7b5", "°": "dim", "°7": "dim7", "dim": "dim"}
NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII"]
ROMAN_RE = re.compile(r"^([b#]?)(VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)(.*)$")


def parse_roman(roman, mode):
    """'bVII' -> (degree index, semitones above tonic, quality)."""
    m = ROMAN_RE.match(roman)
    if not m:
        raise SystemExit(f"can't parse roman numeral {roman!r}")
    acc, num, suffix = m.groups()
    deg = NUMERALS.index(num.upper())
    table = UPPER_SUFFIX if num.isupper() else LOWER_SUFFIX
    if suffix not in table:
        raise SystemExit(f"unknown chord suffix {suffix!r} in {roman!r}")
    semis = SCALES[mode][deg] + {"": 0, "b": -1, "#": 1}[acc]
    return deg, semis % 12, table[suffix]


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
    return s.replace("#", "s").replace("ø7", "m7b5").replace("ø", "m7b5").replace("°", "dim")


# ---------------------------------------------------------------------------
# Chords + voice leading
# ---------------------------------------------------------------------------

def voicing_candidates(pcs):
    lo, hi = RANGES["chords"]
    opts = [[m for m in range(lo, hi + 1) if m % 12 == pc] for pc in pcs]
    for strict in (True, False):
        out = set()
        for combo in itertools.product(*opts):
            v = tuple(sorted(combo))
            if len(set(v)) != len(v):
                continue
            if v[-1] - v[0] > (12 if len(v) == 3 else 16) + (0 if strict else 7):
                continue
            if strict and any(b - a == 1 for a, b in zip(v, v[1:])):   # no minor-2nd rubs
                continue
            out.add(v)
        if out:
            return sorted(out)
    raise SystemExit(f"no voicing for pitch classes {pcs}")


def motion(a, b):
    if len(a) == len(b):
        return sum(abs(x - y) for x, y in zip(a, b))
    return (sum(min(abs(x - y) for y in a) for x in b)
            + sum(min(abs(x - y) for y in b) for x in a)) / 2


def reg_cost(v):
    return abs(sum(v) / len(v) - 61) * 0.35


def voice_lead(chords_pcs):
    """Pick one voicing per chord minimising total movement (loop-aware DP)."""
    cands = [voicing_candidates(p) for p in chords_pcs]
    best = None
    for first in cands[0]:
        layer = {first: (reg_cost(first), [first])}
        for cs in cands[1:]:
            layer = {v: min((c + motion(p, v) + reg_cost(v), path + [v]) for p, (c, path) in layer.items())
                     for v in cs}
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
    return {"start": start, "len": length, "note": note, "acc": bool(acc), "slide": bool(slide)}


def gate(length):
    return int(STEP * 0.55) if length == 1 else length * STEP - 30


def chords_part(voicings, rhythm):
    notes = []
    for bar, v in enumerate(voicings):
        for i, (st, ln) in enumerate(CHORD_RHYTHMS[rhythm]["hits"]):
            vel = 96 if i == 0 else 84
            for m in v:
                notes.append((bar * BAR + st * STEP, gate(ln), m, vel))
    return notes


ARP_ORDER = {
    "up": lambda L: list(range(L)),
    "down": lambda L: list(range(L - 1, -1, -1)),
    "updown": lambda L: list(range(L)) + list(range(L - 2, 0, -1)),
    "broken": lambda L: [0, 2, 1, 3, 2, 4, 3, 1],
}


def arp_part(voicings, name):
    spec = ARPS[name]
    steps = list(range(16)) if spec["steps"] == "all" else spec["steps"]
    ev, k = [], 0
    for bar, v in enumerate(voicings):
        pool = sorted(v) + [min(v) + 12]
        order = spec["order"]
        seq = ARP_ORDER[order](len(pool)) if isinstance(order, str) else order
        seq = [i % len(pool) for i in seq]
        if spec["reset"] == "bar":
            k = 0
        for st in steps:
            idx = k % len(seq)
            acc = st % 4 == 0 if spec["accent"] == "beat" else idx == 0
            ev.append(E(bar * 16 + st, 1, pool[seq[idx]], acc))
            k += 1
    return ev


def chord_info(root_pc, quality, bscale):
    ivs = QUALITY[quality][0]
    third = next((i for i in ivs if i in (3, 4)), None)
    if third is None:   # sus chords: use the sus tone
        third = next(i for i in ivs if i in (2, 5))
    fifth = 6 if 6 in ivs else 7
    sev = next((i for i in ivs if i in (10, 11)), None)
    if sev is None:
        rel = [(p - root_pc) % 12 for p in bscale]
        sev = 10 if 10 in rel else 11
    return {"r": 24 + root_pc, "3": third, "5": fifth, "7": sev}


def resolve(ci, sym, nxt_root, prev, r=None, float_=False):
    r = ci["r"] if r is None else r
    if sym == "a":      # half-step approach into the next bar's root
        lo, hi = RANGES["bass"]
        targets = (nxt_root, nxt_root + 12) if float_ else (nxt_root,)
        cands = [t + d for t in targets for d in (-1, 1)]
        cands = [x for x in cands if lo <= x <= hi and x != prev]
        return min(cands, key=lambda x: (abs(x - (prev if prev is not None else x)), x))
    return {"r": r, "o": r + 12, "3": r + ci["3"], "5": r + ci["5"], "7": r + ci["7"]}[sym]


def bass_part(infos, name):
    spec = BASSES[name]
    n = len(infos)
    ev = []
    if "cell" in spec:               # polymeter: a cell repeating every `period` steps
        for start in range(0, STEPS, spec["period"]):
            for off, sym, ln, acc, sl in spec["cell"]:
                s = start + off
                if s + ln > STEPS:
                    continue
                bar = s // 16
                note = resolve(infos[bar], sym, infos[(bar + 1) % n]["r"], ev[-1]["note"] if ev else None)
                ev.append(E(s, ln, note, acc, sl))
        return ev
    prev = None
    for bar, alts in enumerate(spec["bars"]):
        ci, nxt = infos[bar], infos[(bar + 1) % n]["r"]
        if alts and isinstance(alts[0], tuple):
            alts = [alts]
        fl = spec.get("float", False)
        lo, hi = RANGES["bass"]
        best = None
        for tpl in alts:
            for r in ((ci["r"], ci["r"] + 12) if fl else (ci["r"],)):
                p, notes = prev, []
                for st, sym, ln, acc, sl in tpl:
                    p = resolve(ci, sym, nxt, p, r, fl)
                    notes.append(E(bar * 16 + st, ln, p, acc, sl))
                if not all(lo <= e["note"] <= hi for e in notes):
                    continue
                land = min(abs(notes[-1]["note"] - t) for t in ((nxt, nxt + 12) if fl else (nxt,)))
                score = land + (abs(notes[0]["note"] - prev) if prev else 0)
                if best is None or score < best[0]:
                    best = (score, notes)
        if best is None:
            raise SystemExit(f"bass style {name}: no variant fits the range in bar {bar + 1}")
        ev += best[1]
        prev = ev[-1]["note"]
    return ev


def lead_part(name, key_pcs, chords, rng):
    spec = LEADS[name]
    conA = spec["A_contour"]
    conA3 = conA[:-2] + [c + rng.choice([-2, -1, 1, 2]) for c in conA[-2:]]
    plan = [(spec["A"], conA), (spec["A"], conA), (spec["A"], conA3), (spec["B"], spec["B_contour"])]
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
    for a, b in zip(ev, ev[1:]):
        if (a["start"] + a["len"] == b["start"] and 0 < abs(a["note"] - b["note"]) <= 5
                and rng.random() < spec["slide"]):
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
    if evs:
        evs[-1]["slide"] = False                # nothing to glide into at the pattern end
    out = []
    for i, e in enumerate(evs):
        if e["start"] < 0 or e["start"] + e["len"] > STEPS:
            raise SystemExit(f"event outside the 64-step pattern: {e}")
        if i + 1 < len(evs) and evs[i + 1]["start"] < e["start"] + e["len"]:
            raise SystemExit(f"overlapping steps: {e} / {evs[i + 1]}")
        tick = e["start"] * STEP
        if e["slide"]:
            if evs[i + 1]["start"] != e["start"] + e["len"]:
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

PART_TABLES = {"chords": CHORD_RHYTHMS, "arp": ARPS, "bass": BASSES, "lead": LEADS}


def check_data():
    """Every kit must reference existing styles; every entry needs source + why."""
    missing = []
    for table_name, table in [("GENRES", GENRES)] + [(k.upper(), v) for k, v in PART_TABLES.items()]:
        for key, spec in table.items():
            if not spec.get("source") or spec["source"] == PENDING:
                missing.append(f"{table_name}[{key}]")
    for i, p in enumerate(PROGRESSIONS):
        for part, table in PART_TABLES.items():
            if p[part] not in table:
                raise SystemExit(f"PROGRESSIONS[{i}] ({p['name']}): unknown {part} style {p[part]!r}")
        if p["genre"] not in GENRES:
            raise SystemExit(f"PROGRESSIONS[{i}]: unknown genre {p['genre']!r}")
        if len(p["roman"]) != BARS:
            raise SystemExit(f"PROGRESSIONS[{i}] ({p['name']}): needs exactly {BARS} chords")
        if not p.get("source") or p["source"] == PENDING:
            missing.append(f"PROGRESSIONS[{i}] {p['name']}")
    return missing


def style_meta(table, name):
    spec = table[name]
    out = {"style": name, "source": spec.get("source", ""), "why": spec.get("why", "")}
    if spec.get("poly"):
        out["poly"] = spec["poly"]
    return out


def build_kit(tonic, idx, prog):
    mode = prog["mode"]
    t_pc = tonic_pc(tonic)
    key_pcs = [(t_pc + s) % 12 for s in SCALES[mode]]
    chords = []
    for roman in prog["roman"]:
        deg, semis, qual = parse_roman(roman, mode)
        rname, rpc = spell(tonic, deg, semis)
        ivs, suffix = QUALITY[qual]
        chords.append({"roman": roman, "name": rname + suffix, "root_pc": rpc, "quality": qual,
                       "pcs": [(rpc + i) % 12 for i in ivs]})
    voicings = voice_lead([c["pcs"] for c in chords])
    key_dir = f"{safe(tonic)}-{mode}"
    kit_id = f"{idx:02d}-{prog['genre']}-{safe('-'.join(prog['roman']))}"
    rng = random.Random(zlib.crc32(f"{key_dir}/{kit_id}".encode()))
    infos = [chord_info(c["root_pc"], c["quality"], bar_scale(key_pcs, c["pcs"])) for c in chords]
    parts = {
        "chords": chords_part(voicings, prog["chords"]),
        "arp": render_mono(arp_part(voicings, prog["arp"])),
        "bass": render_mono(bass_part(infos, prog["bass"])),
        "lead": render_mono(lead_part(prog["lead"], key_pcs, chords, rng)),
    }
    return key_dir, kit_id, chords, voicings, parts


def main():
    missing = check_data()
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)   # no stale files from older layouts
    keys, nfiles, nbytes = [], 0, 0
    for tonic_i in range(12):
        for mode in ("minor", "major"):
            tonic = TONICS[mode][tonic_i]
            progs = [p for p in PROGRESSIONS if p["mode"] == mode]
            key_entry = None
            for idx, prog in enumerate(progs, 1):
                key_dir, kit_id, chords, voicings, parts = build_kit(tonic, idx, prog)
                genre = GENRES[prog["genre"]]
                bpm = prog.get("bpm", genre["bpm"])
                folder = os.path.join(OUT_DIR, key_dir, kit_id)
                os.makedirs(folder, exist_ok=True)
                title = f"{tonic} {mode} - {genre['name']} - {' '.join(c['name'] for c in chords)}"
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
                part_meta = {part: style_meta(PART_TABLES[part], prog[part]) for part in PART_TABLES}
                key_entry["kits"].append({
                    "id": kit_id,
                    "n": idx,
                    "genre": prog["genre"],
                    "genre_name": genre["name"],
                    "bpm": bpm,
                    "name": prog["name"],
                    "source": prog["source"],
                    "why": prog["why"],
                    "roman": prog["roman"],
                    "chords": [c["name"] for c in chords],
                    "voicings": voicings,
                    "parts": {part: prog[part] for part in PART_TABLES},
                    "poly": [p for p, m in part_meta.items() if m.get("poly")],
                    "files": files,
                })
    index = {
        "generated_by": "tools/build_library.py",
        "ppq": TPQ,
        "bars": BARS,
        "steps": STEPS,
        "channels": {"all.mid": {"chords": 1, "bass": 2, "lead": 3, "arp": 4}, "single files": 1},
        "velocity": {"accent": ACC, "normal": NORM},
        "slide": f"note overlaps the next note by {SLIDE_OVERLAP} ticks at {TPQ} ppq",
        "genres": {k: {"name": g["name"], "bpm": g["bpm"], "source": g["source"], "why": g["why"]}
                   for k, g in GENRES.items()},
        "styles": {part: {name: style_meta(table, name) for name in sorted(table)}
                   for part, table in PART_TABLES.items()},
        "keys": keys,
    }
    text = json.dumps(index, indent=1, ensure_ascii=False)
    # keep short lists of numbers / strings on one line so the file stays diffable
    text = re.sub(r"\[\s*((?:-?\d+|\"[^\"\n]*\")(?:,\s*(?:-?\d+|\"[^\"\n]*\"))*)\s*\]",
                  lambda m: "[" + ", ".join(x.strip() for x in m.group(1).split(",")) + "]", text)
    with open(os.path.join(OUT_DIR, "index.json"), "w") as fh:
        fh.write(text + "\n")
    nkits = sum(len(k["kits"]) for k in keys)
    print(f"{len(keys)} keys, {nkits} kits, {nfiles} .mid files, {nbytes} bytes of MIDI -> {OUT_DIR}")
    print("all files parsed back and validated (ranges, monophony, block chords, 4-bar length).")
    if missing:
        print(f"\nWARNING: {len(missing)} data entries still have no source:")
        for m in missing:
            print("  -", m)


if __name__ == "__main__":
    main()
