#!/usr/bin/env python3
"""
Build switchable "sets" of full arrangements for the J-6 + S-1.

Emits:
  s1-j6/sets/index.json                          registry of every set
  s1-j6/sets/sinnoh-style/set.json               what is in the set, per track
  s1-j6/sets/sinnoh-style/NN-slug/full.mid       format 1: conductor + chords ch1,
                                                 bass ch2, lead ch3, counter/arp ch4
  s1-j6/sets/sinnoh-style/NN-slug/sections/<section>-{chords,bass,lead}.mid
                                                 format 0, channel 1, exactly 4 bars:
                                                 one J-6 / S-1 pattern each

The existing genre-kit library (s1-j6/library, built by tools/build_library.py)
is registered in index.json as the read-only set `genre-kits`; this script
never writes to it.

The `sinnoh-style` set is ORIGINAL music. Every melody, bassline figure and
chord sequence below was written for this file. It borrows only the general
style of mid-2000s DS handheld RPG scores (the "Sinnoh-era DS feel"): tempos,
bright major keys with IV-V-iii-vi motion and a borrowed iv, chromatic-mediant
lifts, a half-step key change for the rival battle, sus/add9 colour, march-ish
route bass, pizzicato-style staccato bass, driving 16th battle ostinati, brass
stabs, bell/flute leads, string pads. Nothing is transcribed or paraphrased
from any game or any other song.

Notation used in DATA:
  chords   "D | G A | F#m Bm | Em7 A"  one bar per '|', 1/2/4 chords per bar
           split evenly. Slash chords (C/E) voice the chord and put E in the bass.
  lead     "F#5:4 E5:2 D5:2 | ..."      note:length-in-16th-steps, '-' = rest,
           suffix '*' accent, '~' slide into the next note. Every bar must sum
           to 16 steps; bar-1 downbeat notes are accented automatically.
  bass     a style name from BASS_STYLES, resolved against each chord slot.
  counter  optional hand-written ch4 line (same notation as lead); otherwise an
           arp style from ARP_STYLES is generated from the J-6 voicings.

Every section is exactly 4 bars = 64 sixteenth steps, so each mono part fits
one S-1 pattern and each chord part one J-6 pattern. Deterministic, stdlib only;
MIDI writing/reading and voice leading are shared with build_songs.py and
build_library.py (imported, not modified).
"""

import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from build_songs import TPQ, midi_to_name, n as note_num  # noqa: E402
from build_library import (  # noqa: E402
    ACC, BAR, END, NORM, RANGES, SLIDE_OVERLAP, STEP, STEPS, E, meta, motion, parse_smf,
    part_events, render_mono, smf_single, tempo_meta, track_chunk, voice_lead,
)
from aira_local import estimate_key, key_label, key_uses_flats, note_name, notes_from_smf, read_smf  # noqa: E402

ROOT = os.path.dirname(HERE)
SETS_DIR = os.path.join(ROOT, "s1-j6", "sets")
SET_ID = "sinnoh-style"
OUT_DIR = os.path.join(SETS_DIR, SET_ID)

SECTION_BARS = 4
MAX_SECTIONS = 8          # 8 S-1 / J-6 pattern slots per track
MIN_BARS, MAX_BARS = 32, 64
RANGES = dict(RANGES, counter=RANGES["arp"])   # counter/arp ch4: C3..C6

PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

CHORD_SUFFIX = {  # intervals above the root
    "": [0, 4, 7], "m": [0, 3, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
    "sus2": [0, 2, 7], "sus4": [0, 5, 7], "add9": [0, 4, 7, 14], "madd9": [0, 3, 7, 14],
    "6": [0, 4, 7, 9], "m6": [0, 3, 7, 9], "7": [0, 4, 7, 10], "maj7": [0, 4, 7, 11],
    "m7": [0, 3, 7, 10], "m7b5": [0, 3, 6, 10], "7sus4": [0, 5, 7, 10], "9": [0, 4, 10, 14],
}
CHORD_RE = re.compile(r"^([A-G][#b]?)(" + "|".join(sorted(map(re.escape, CHORD_SUFFIX), key=len, reverse=True))
                      + r")(?:/([A-G][#b]?))?$")

# ---------------------------------------------------------------------------
# Part styles (generic patterns, not taken from any piece)
# ---------------------------------------------------------------------------

# Chord rhythms: (step, length) hits per 16-step bar. A hit plays whatever chord
# is sounding at its step and is clipped at the end of that chord's slot.
CHORD_RHYTHMS = {
    "pad": "held for the whole chord slot (string pad)",
    "swell": [(0, 8), (8, 8)],
    "march": [(0, 3), (4, 3), (8, 3), (12, 3)],
    "offbeat": [(2, 2), (6, 2), (10, 2), (14, 2)],
    "stab": [(0, 2), (3, 2), (6, 2), (10, 2), (12, 3)],
    "battle": [(0, 1), (2, 1), (3, 1), (6, 2), (8, 1), (10, 1), (11, 1), (14, 2)],
    "tick": [(0, 3), (6, 2), (8, 3), (14, 2)],
}
CHORD_RHYTHM_NOTES = {
    "pad": "string pad, one chord per slot", "swell": "half-note swells",
    "march": "quarter-note march comping", "offbeat": "upbeat brass/organ chops",
    "stab": "syncopated DS-style brass stabs", "battle": "16th brass hits with pickups",
    "tick": "light town comping (dotted feel)",
}

# Bass styles: (step, token, length, accent) per bar, resolved against the chord
# sounding at that step. Tokens: R root, R+ octave up, 5 fifth above, 5- fifth
# below, 3 chord third, T/T+ key tonic (pedal), a = half-step approach into the
# next chord slot's root. "slot" styles play one note per chord slot.
BASS_STYLES = {
    "long": "slot",
    "halves": [(0, "R", 7, 1), (8, "R", 3, 0), (12, "5", 4, 0)],
    "march": [(0, "R", 2, 1), (4, "5-", 2, 0), (8, "R", 2, 1), (12, "5-", 2, 0)],
    "pizz": [(0, "R", 1, 1), (2, "5", 1, 0), (4, "R+", 1, 0), (6, "5", 1, 0),
             (8, "R", 1, 1), (10, "5", 1, 0), (12, "R+", 1, 0), (14, "a", 1, 0)],
    "walk": [(0, "R", 3, 1), (4, "3", 3, 0), (8, "R", 3, 0), (12, "a", 3, 0)],
    "sparse": [(0, "R", 3, 1), (6, "5-", 2, 0), (8, "R", 3, 1), (14, "a", 2, 0)],
    "drive": [(i, "R+" if i % 4 == 2 else "R", 1, int(i % 4 == 0)) for i in range(14)]
             + [(14, "5", 1, 0), (15, "a", 1, 0)],
    "gallop": [(b + d, tok, 1, int(d == 0)) for b in (0, 4, 8) for d, tok in ((0, "R"), (2, "R"), (3, "R+"))]
              + [(12, "R", 1, 1), (14, "5", 1, 0), (15, "a", 1, 0)],
    "pulse8": [(i, "R", 1, int(i % 8 == 0)) for i in range(0, 14, 2)] + [(14, "a", 1, 0)],
    "pedal8": [(i, "T+" if i % 8 == 4 else "T", 1, int(i % 8 == 0)) for i in range(0, 16, 2)],
    "drone": [(0, "T", 16, 1)],
}
BASS_NOTES = {
    "long": "one long note per chord", "halves": "root, then root-fifth answer",
    "march": "route-march oom-pah, root and fifth below", "pizz": "staccato pizzicato 8ths",
    "walk": "town walking bass with chromatic approach", "sparse": "cave/forest sparse figure",
    "drive": "driving 16th battle ostinato", "gallop": "galloping x.xx battle figure",
    "pulse8": "straight 8th pulse into an approach note", "pedal8": "tonic pedal in 8ths",
    "drone": "held tonic drone",
}

ARP_STYLES = {  # ch4 counter/arp generated from the J-6 voicings (for OP-XY / M8 covers)
    "bells8": {"every": 2, "order": "updown", "lift": 12},
    "sparkle16": {"every": 1, "order": "up", "lift": 12},
    "brass16": {"every": 1, "order": "updown", "lift": 0},
    "none": None,
}


# ===========================================================================
# DATA: the set. Titles, melodies and progressions are original.
# ===========================================================================

J6_NOTE = ("Set numbers from s1-j6/library/RESEARCH.md section 13 (J-6 manual p.25 via "
           "github.com/stonefruit/j6). Utility sets 17-24 put the chord root on the key you press; "
           "themed sets need the j6-chords.json lookup. full.mid / sections/*-chords.mid carry the "
           "exact voicings if no set fits.")

SET = {
    "id": SET_ID,
    "name": "Sinnoh-style (original)",
    "description": ("Eight ORIGINAL full-length pieces written in the general style of mid-2000s DS "
                    "handheld RPG soundtracks (Sinnoh-era DS feel): march-ish route themes, a snowy "
                    "route, a cave, a town, two battles (the rival one with a last-chorus half-step "
                    "key change), a champion-style finale and a spooky tower piece. No melody, "
                    "bassline or progression is taken from any game or song."),
    "tracks": [
        # ------------------------------------------------------------------ 1
        {
            "title": "Mossroot Walk", "slug": "mossroot-walk", "role": "Route theme (cheerful walk)",
            "bpm": 132, "key": "D major",
            "style": "Sinnoh-era DS feel: bright major march, IV-V-iii-vi motion, borrowed iv (Gm) "
                     "before the tonic, bVI-bVII-I lift out of the B section.",
            "j6": {"sets": "7 (C-major diatonic), 46 (G-major palette: C D Em G Am Bm), 40 (all add9)",
                   "style": "Chord/strum style at march pace; brass or organ preset"},
            "s1": {"bass": "SQUARE + SUB, short DECAY: tuba-ish oom-pah",
                   "lead": "SQUARE, slight vibrato LFO: DS flute/trumpet lead"},
            "cover_ideas": "OP-XY: 'brass' sampler stabs, pluck bass, flute multisample lead, snare-roll march kit. "
                           "M8: FM horn chords, wavsynth pulse bass, sampled flute lead, macro-synth glock counter.",
            "arp": "bells8", "bass_floor": 25,
            "sections": {
                "intro": {"chords": "Dadd9 | Gmaj7 | Em7 | Asus4 A", "rhythm": "swell", "bass": "long",
                          "lead": "-:4 A4:2 D5:2 E5:4 F#5:4 | G5:6 F#5:2 D5:4 B4:4 | "
                                  "E5:2 F#5:2 G5:2 B5:2 A5:4 G5:2 E5:2 | D5:4 E5:4 C#5:6 -:2"},
                "a1": {"chords": "D | G A | F#m Bm | Em7 A", "rhythm": "march", "bass": "march",
                       "lead": "F#5:4 E5:2 D5:2 A4:4 D5:4 | B4:2 D5:2 G5:4 A5:2 G5:2 E5:4 | "
                               "F#5:4 A5:2 F#5:2 D5:4 C#5:2 D5:2 | E5:6 G5:2 E5:4 C#5:4"},
                "a2": {"chords": "D/F# | G A | Gm | D", "rhythm": "march", "bass": "march",
                       "lead": "A5:4 F#5:2 A5:2 B5:4 A5:2 F#5:2 | G5:4 B5:2 A5:2 E5:4 C#5:2 E5:2 | "
                               "G5:6 F5:2 D5:4 Bb4:4 | A4:2 D5:2 F#5:2 E5:2 D5:8"},
                "b1": {"chords": "Gmaj7 | F#m7 | Em7 | Asus4 A", "rhythm": "offbeat", "bass": "pizz",
                       "lead": "B4:4 D5:4 F#5:8 | E5:4 C#5:4 A4:8 | "
                               "G4:2 B4:2 D5:2 E5:2 G5:4 F#5:4 | E5:8 C#5:8"},
                "b2": {"chords": "Gmaj7 | F#m7 B7 | Em7 A7 | Bb C", "rhythm": "offbeat", "bass": "pizz",
                       "lead": "B4:4 D5:4 A5:8 | A5:4 F#5:4 D#5:4 F#5:4 | "
                               "G5:4 E5:2 B4:2 C#5:4 E5:4 | D5:4 F5:4 E5:4 G5:4"},
                "bridge": {"chords": "Bm7 | Gmaj7 | Bm7 | Gm6", "rhythm": "pad", "bass": "long",
                           "lead": "-:4 D5:4 F#5:4 A5:4 | F#5:12 -:4 | -:4 C#5:4 D5:4 F#5:4 | E5:8 D5:8"},
            },
            "form": ["intro", "a1", "a2", "b1", "b2", "bridge", "a1", "a2"], "loop": "a1",
        },
        # ------------------------------------------------------------------ 2
        {
            "title": "Frostline Pass", "slug": "frostline-pass", "role": "Route theme (snowy, slow)",
            "bpm": 84, "key": "Bb major",
            "style": "Sinnoh-era DS feel: slow snowfield route, add9/maj7 pads, music-box lead, "
                     "Lydian #11 colour, borrowed Ebm6 and a bVI (Gbmaj7) chromatic lift.",
            "j6": {"sets": "19 (all M7) and 40 (all add9); 34 (all sus2) for the intro",
                   "style": "Long pad (slow ATTACK, long RELEASE, CHORUS on)"},
            "s1": {"bass": "TRIANGLE + SUB, long DECAY: soft upright",
                   "lead": "TRIANGLE/SQUARE, short DECAY, no SUB: music box / celesta"},
            "cover_ideas": "OP-XY: 'celesta'/'glock' multisample lead, string-pad synth, felt-piano counter, "
                           "brushed kit. M8: FM bell lead, sampled strings, soft sine sub bass.",
            "arp": "sparkle16", "bass_floor": 25,
            "sections": {
                "intro": {"chords": "Bbadd9 | Ebmaj7 | Bbadd9 | Fsus4 F", "rhythm": "pad", "bass": "long",
                          "lead": "D5:2 F5:2 C6:4 Bb5:8 | G5:2 Bb5:2 D5:4 -:8 | F5:2 C5:2 D5:4 C5:8 | -:8 A4:4 C5:4"},
                "a1": {"chords": "Bb | Dm7 | Ebmaj7 | Cm7 F", "rhythm": "pad", "bass": "halves",
                       "lead": "F5:6 D5:2 Bb4:8 | A4:4 C5:4 F5:8 | G5:4 Bb5:4 A5:4 F5:4 | Eb5:6 D5:2 C5:4 A4:4"},
                "a2": {"chords": "Gm7 | Ebmaj7 | Ebm6 | Bbadd9", "rhythm": "pad", "bass": "halves",
                       "lead": "D5:4 F5:4 Bb5:4 A5:4 | G5:8 Bb4:4 D5:4 | Gb5:6 F5:2 Eb5:4 C5:4 | D5:8 C5:4 Bb4:4"},
                "b1": {"chords": "Gm | Ebmaj7 | Cm7 | Dsus4 D", "rhythm": "swell", "bass": "walk",
                       "lead": "Bb4:2 D5:2 G5:4 F5:4 D5:4 | Eb5:4 G5:4 Bb5:6 G5:2 | "
                               "G5:4 Eb5:4 Bb4:4 C5:4 | G5:8 F#5:8"},
                "b2": {"chords": "Gm7 | Ebmaj7 | Gbmaj7 | Fsus4 F", "rhythm": "swell", "bass": "walk",
                       "lead": "D5:4 C5:2 Bb4:2 F5:8 | D5:4 Eb5:4 G5:8 | F5:4 Db5:4 Bb4:8 | Bb4:4 C5:4 A4:8"},
                "bridge": {"chords": "Ebmaj7 | Bb/D | Cm7 | Fsus4", "rhythm": "pad", "bass": "long",
                           "lead": "-:8 Bb5:4 G5:4 | F5:8 -:4 C5:4 | Eb5:8 D5:4 C5:4 | Bb4:16"},
            },
            "form": ["intro", "a1", "a2", "b1", "b2", "bridge", "a1", "a2"], "loop": "a1",
        },
        # ------------------------------------------------------------------ 3
        {
            "title": "Hollowroot Cavern", "slug": "hollowroot-cavern", "role": "Forest / cave (mystery)",
            "bpm": 104, "key": "D minor",
            "style": "Sinnoh-era DS feel: Dorian cave loop over a D pedal, sus2/sus4 colour, "
                     "pizzicato staccato bass, breathy flute lead, descending maj7/m7 B section.",
            "j6": {"sets": "34 (all sus2), 20 (all m7), 19 (all M7) - utility-style, root on the key",
                   "style": "Slow up/down arp (STYLE 1-2) or long pad"},
            "s1": {"bass": "SQUARE, very short DECAY, low CUTOFF: plucked/pizz",
                   "lead": "TRIANGLE, NOISE a touch, slow LFO vibrato: flute"},
            "cover_ideas": "OP-XY: pizzicato-strings sampler bass, flute or ocarina lead, hand-drum kit, "
                           "reverb-heavy pad. M8: sampled pizz, FM flute, granular drip texture on ch4.",
            "arp": "bells8", "bass_floor": 26,
            "sections": {
                "intro": {"chords": "Dm | Em7/D | Dm | Csus2/D", "rhythm": "pad", "bass": "pedal8",
                          "lead": "-:8 A4:4 D5:4 | E5:12 D5:4 | F5:4 E5:4 D5:4 A4:4 | C5:4 D5:12"},
                "a1": {"chords": "Dm7 | G/D | Dm7 | Cadd9", "rhythm": "offbeat", "bass": "pizz",
                       "lead": "D5:2 E5:2 F5:4 A5:2 G5:2 F5:4 | D5:2 B4:2 G4:4 A4:2 B4:2 D5:4 | "
                               "C5:4 A4:4 F5:6 E5:2 | D5:8 G5:4 E5:4"},
                "a2": {"chords": "Bbmaj7 | C | Asus4 | A", "rhythm": "offbeat", "bass": "pizz",
                       "lead": "F5:4 D5:2 F5:2 A5:4 G5:4 | E5:6 D5:2 C5:4 G4:4 | D5:8 E5:8 | C#5:12 -:4"},
                "b1": {"chords": "Fmaj7 | Em7 | Dm7 | Cmaj7", "rhythm": "swell", "bass": "sparse",
                       "lead": "A5:4 G5:2 E5:2 C5:8 | B4:4 D5:4 G5:8 | F5:4 E5:2 D5:2 A4:8 | G4:4 B4:4 E5:8"},
                "b2": {"chords": "Bbmaj7 | Gm7 | Asus4 | A7", "rhythm": "swell", "bass": "sparse",
                       "lead": "D5:4 F5:4 A5:8 | Bb5:6 A5:2 G5:4 D5:4 | E5:4 D5:4 A4:8 | C#5:4 E5:4 G5:8"},
                "bridge": {"chords": "Dm | Bbmaj7/D | Gm/D | Asus4/D", "rhythm": "pad", "bass": "drone",
                           "lead": "-:4 A5:4 -:4 E5:4 | F5:8 -:8 | -:4 G5:4 -:4 D5:4 | E5:16"},
            },
            "form": ["intro", "a1", "a2", "b1", "b2", "bridge", "a1", "a2"], "loop": "a1",
        },
        # ------------------------------------------------------------------ 4
        {
            "title": "Kettle Square", "slug": "kettle-square", "role": "Town theme",
            "bpm": 112, "key": "F major",
            "style": "Sinnoh-era DS feel: relaxed town loop, maj7/m7 colour, walking bass, "
                     "Bbm6 borrowed iv, ii-V turnarounds and a bVI (Ab) lift in the bridge.",
            "j6": {"sets": "19 (all M7) + 20 (all m7) utility sets; 7 (C-major diatonic) for the triads",
                   "style": "Light chord rhythm (short RELEASE), electric-piano-ish preset"},
            "s1": {"bass": "SQUARE + SUB, medium DECAY: round walking bass",
                   "lead": "PULSE/SQUARE, medium CUTOFF: clarinet/accordion-ish"},
            "cover_ideas": "OP-XY: e-piano or accordion sampler chords, upright bass, whistle/clarinet lead, "
                           "shaker + rim kit. M8: FM e-piano, sampled upright, square lead with slow vibrato.",
            "arp": "bells8", "bass_floor": 26,
            "sections": {
                "intro": {"chords": "Fmaj7 | Gm7 C7 | Fmaj7 | Bbmaj7 C7", "rhythm": "tick", "bass": "halves",
                          "lead": "A4:2 C5:2 F5:4 E5:4 C5:4 | D5:4 Bb4:4 E5:4 G5:4 | A5:8 F5:4 C5:4 | D5:4 F5:4 E5:8"},
                "a1": {"chords": "F | Bb C | Am7 Dm7 | Gm7 C7", "rhythm": "tick", "bass": "walk",
                       "lead": "C5:2 F5:2 A5:3 G5:1 F5:4 C5:4 | D5:3 Bb4:1 D5:2 F5:2 G5:4 E5:4 | "
                               "E5:4 C5:2 A4:2 F5:4 A5:4 | G5:4 F5:2 D5:2 E5:6 -:2"},
                "a2": {"chords": "F | Bb Bbm6 | Am7 D7 | Gm7 C7", "rhythm": "tick", "bass": "walk",
                       "lead": "A5:2 G5:2 F5:2 C5:2 A4:4 C5:4 | D5:4 F5:4 Db5:4 G5:4 | "
                               "C5:4 E5:4 F#5:4 A5:4 | Bb5:4 A5:2 G5:2 E5:4 C5:4"},
                "b1": {"chords": "Dm7 | Bbmaj7 | Gm7 | C7sus4 C7", "rhythm": "swell", "bass": "walk",
                       "lead": "F5:6 E5:2 D5:4 A4:4 | A4:4 Bb4:4 D5:8 | F5:4 D5:4 Bb4:4 G4:4 | F5:8 E5:8"},
                "b2": {"chords": "Dm7 | Bbmaj7 | Gm7 Bbm6 | F", "rhythm": "swell", "bass": "walk",
                       "lead": "A5:6 G5:2 F5:4 D5:4 | F5:4 A5:4 D5:8 | Bb4:4 D5:4 Db5:4 F5:4 | C5:4 A4:4 F4:8"},
                "bridge": {"chords": "Bbmaj7 | Am7 | Gm7 | Ab C7", "rhythm": "pad", "bass": "halves",
                           "lead": "-:4 F5:4 A5:4 F5:4 | E5:8 C5:8 | D5:4 Bb4:4 G4:8 | Eb5:8 E5:8"},
            },
            "form": ["intro", "a1", "a2", "b1", "b2", "a1", "a2", "bridge", "b1", "b2"], "loop": "a1",
        },
        # ------------------------------------------------------------------ 5
        {
            "title": "Tall Grass Ambush", "slug": "tall-grass-ambush", "role": "Wild battle",
            "bpm": 168, "key": "E minor",
            "style": "Sinnoh-era DS feel: fast minor battle, driving 16th bass ostinato, syncopated "
                     "brass stabs, scalar pickups into each phrase, bVII (D) and V7 (B7) pushes.",
            "j6": {"sets": "8 (C-minor diatonic), 58 (Techno) for hard stabs",
                   "style": "Short stab styles, fast ATTACK, short RELEASE; brass preset"},
            "s1": {"bass": "SAW, high ENV MOD, short DECAY, accents on: driving ostinato",
                   "lead": "SQUARE, bright CUTOFF, fast vibrato: DS trumpet/synth lead"},
            "cover_ideas": "OP-XY: brass-section sampler stabs, saw bass, square lead, fast 16th hat + tom fills. "
                           "M8: FM brass stabs, wavsynth saw bass, pulse lead with arp-chip counter.",
            "arp": "brass16", "bass_floor": 28,
            "sections": {
                "intro": {"chords": "Em | Cmaj7 | Am | B7", "rhythm": "stab", "bass": "drive",
                          "lead": "E4:1 F4:1 G4:1 A4:1 B4:2 -:2 E5:2 -:2 B4:2 -:2 | "
                                  "E4:1 F#4:1 G4:1 A4:1 C5:2 -:2 E5:2 -:2 C5:2 -:2 | "
                                  "E5:2 D5:2 C5:2 B4:2 A4:2 G4:2 E4:4 | F#4:4 A4:4 B4:4 D#5:4"},
                "a1": {"chords": "Em | Cmaj7 | Am | B7", "rhythm": "battle", "bass": "drive",
                       "lead": "B4:3 E5:3 G5:2 F#5:2 E5:2 B4:4 | C5:3 E5:3 G5:2 A5:2 G5:2 E5:4 | "
                               "A4:3 C5:3 E5:2 D5:2 C5:2 A4:2 B4:2 | D#5:4 F#5:4 A5:4 F#5:4"},
                "a2": {"chords": "Em | Cmaj7 | D | B", "rhythm": "battle", "bass": "drive",
                       "lead": "G5:3 F#5:3 E5:2 B5:4 A5:2 G5:2 | E5:3 G5:3 C6:2 B5:4 G5:4 | "
                               "A5:3 F#5:3 D5:2 E5:2 F#5:2 A5:4 | B5:8 -:4 D#5:4"},
                "b1": {"chords": "Am7 | D7 | Gmaj7 | Cmaj7", "rhythm": "stab", "bass": "gallop",
                       "lead": "E5:2 -:2 E5:2 G5:2 A5:4 C6:4 | F#5:4 A5:4 C6:4 A5:4 | "
                               "B5:6 A5:2 G5:4 D5:4 | E5:6 D5:2 C5:4 B4:4"},
                "b2": {"chords": "Am7 | F#m7b5 | Cmaj7 | B7", "rhythm": "stab", "bass": "gallop",
                       "lead": "C5:2 E5:2 A5:4 G5:2 E5:2 C5:4 | A4:4 C5:4 E5:4 F#5:4 | "
                               "G5:4 E5:4 B4:4 C5:4 | D#5:4 F#5:2 D#5:2 B4:8"},
                "break": {"chords": "Em | Em | C | D", "rhythm": "offbeat", "bass": "drive",
                          "lead": "E5:12 -:4 | F#5:4 G5:8 -:4 | E5:12 -:4 | F#5:4 A5:8 -:4"},
            },
            "form": ["intro", "a1", "a2", "b1", "b2", "break", "a1", "a2"], "loop": "a1",
        },
        # ------------------------------------------------------------------ 6
        {
            "title": "Ironbell Rival", "slug": "ironbell-rival", "role": "Gym leader / rival battle",
            "bpm": 152, "key": "A minor",
            "style": "Sinnoh-era DS feel: rival battle in A minor, gallop bass, Neapolitan (Bb) turn, "
                     "then a last-chorus half-step key change (E -> F pivot) into Bb minor.",
            "j6": {"sets": "8 (C-minor diatonic), 48 (Trance: minor palette with slash-chord bass)",
                   "style": "Stab styles; for the key change step every chord up one key (verify transpose on the unit)"},
            "s1": {"bass": "SAW + SUB, short DECAY, accents: galloping drive",
                   "lead": "SQUARE, bright, PORTAMENTO a touch for slides: rival lead"},
            "cover_ideas": "OP-XY: orchestral-hit + brass sampler chords, saw bass, lead on a detuned square, "
                           "timpani/snare-roll kit into the key change. M8: FM brass, saw bass, sampled timpani fills.",
            "arp": "brass16", "bass_floor": 28,
            "sections": {
                "intro": {"chords": "Am | Am7 | Fmaj7 | E7", "rhythm": "stab", "bass": "drive",
                          "lead": "A4:2 -:2 A4:2 C5:2 E5:2 -:2 A5:4 | G5:2 -:2 G5:2 E5:2 D5:2 -:2 C5:4 | "
                                  "A4:2 C5:2 F5:2 E5:2 C5:4 A4:4 | G#4:4 B4:4 D5:4 E5:4"},
                "a1": {"chords": "Am | Dm7 | G | Cmaj7", "rhythm": "battle", "bass": "gallop",
                       "lead": "E5:4 A5:2 G5:2 E5:4 C5:2 D5:2 | F5:4 A5:4 G5:2 F5:2 D5:4 | "
                               "D5:4 G5:2 B5:2 A5:4 G5:4 | E5:8 B4:4 C5:4"},
                "a2": {"chords": "Fmaj7 | Dm7 | Esus4 | E", "rhythm": "battle", "bass": "gallop",
                       "lead": "A5:6 G5:2 E5:4 C5:4 | F5:2 A5:2 D5:4 E5:2 F5:2 A5:4 | B5:4 A5:4 E5:8 | G#5:12 -:4"},
                "b1": {"chords": "F | G | Em7 Am | Dm7 E7", "rhythm": "stab", "bass": "drive",
                       "lead": "C5:2 F5:2 A5:4 G5:4 F5:4 | D5:2 G5:2 B5:4 A5:4 G5:4 | "
                               "E5:4 G5:4 A5:4 C6:4 | A5:4 F5:4 G#5:4 B5:4"},
                "b2": {"chords": "F | G | Am | Bb E7", "rhythm": "stab", "bass": "drive",
                       "lead": "A5:4 F5:2 A5:2 C6:4 A5:4 | B5:4 G5:2 B5:2 D5:4 G5:4 | "
                               "C6:6 B5:2 A5:4 E5:4 | D5:4 F5:4 E5:4 G#5:4"},
                "bridge": {"chords": "Dm | Dm | Esus4 | F", "rhythm": "offbeat", "bass": "pulse8",
                           "lead": "D5:4 F5:4 A5:8 | G5:4 F5:4 E5:4 D5:4 | E5:8 A5:8 | A5:4 C6:4 F5:4 C5:4"},
                "a1up": {"transpose": ("a1", 1), "key": "Bb minor"},
                "a2up": {"transpose": ("a2", 1), "key": "Bb minor"},
            },
            "form": ["intro", "a1", "a2", "b1", "b2", "a1", "a2", "bridge", "a1up", "a2up"], "loop": "a1",
        },
        # ------------------------------------------------------------------ 7
        {
            "title": "Summit Crown", "slug": "summit-crown", "role": "Champion-style finale",
            "bpm": 144, "key": "G minor",
            "style": "Sinnoh-era DS feel: final-battle scale, fanfare intro, chromatic-mediant lifts "
                     "(Eb -> B, Gm -> E), chromatic descent to V, and a G-major coda (bVI-bVII-I).",
            "j6": {"sets": "48 (Trance: minor palette with slash-chord bass), 33/35-38 (Cinematic)",
                   "style": "Stab + long chord alternation; brass/strings preset, CHORUS on"},
            "s1": {"bass": "SAW + SUB full, accents: heavy 8th/16th drive",
                   "lead": "SQUARE, bright, vibrato: heroic brass lead"},
            "cover_ideas": "OP-XY: full brass-section sampler, string ostinato on ch4, saw bass, big tom/cymbal kit. "
                           "M8: layered FM brass + sampled strings, pulse bass, hypersynth choir pad for the coda.",
            "arp": "brass16", "bass_floor": 26,
            "sections": {
                "intro": {"chords": "Gm | Ebmaj7 | Cm | D7", "rhythm": "stab", "bass": "pulse8",
                          "lead": "G4:2 -:1 G4:1 D5:4 G5:4 F5:2 D5:2 | Eb5:2 -:1 Eb5:1 G5:4 Bb5:6 G5:2 | "
                                  "C5:2 -:1 C5:1 Eb5:4 G5:4 A5:2 Bb5:2 | A5:4 F#5:4 D5:4 C5:4"},
                "a1": {"chords": "Gm | Ebmaj7 | Bb/D | F", "rhythm": "battle", "bass": "drive",
                       "lead": "D5:4 G5:4 A5:2 Bb5:2 A5:2 G5:2 | G5:4 Eb5:4 Bb4:8 | "
                               "F5:4 D5:2 F5:2 Bb5:4 C6:4 | A5:12 -:4"},
                "a2": {"chords": "Gm | Ebmaj7 | Cm7 | D", "rhythm": "battle", "bass": "drive",
                       "lead": "Bb5:4 A5:2 G5:2 D5:4 G5:4 | Bb5:4 G5:2 Eb5:2 D5:8 | "
                               "Eb5:4 G5:4 Bb5:4 G5:4 | F#5:8 A5:4 D5:4"},
                "b1": {"chords": "Ebmaj7 | Cm7 | B | D", "rhythm": "stab", "bass": "gallop",
                       "lead": "G5:4 Bb5:4 D5:8 | Eb5:2 F5:2 G5:4 Bb5:4 G5:4 | F#5:4 D#5:4 B4:4 D#5:4 | F#5:8 A5:8"},
                "b2": {"chords": "Gm | E | Eb | D", "rhythm": "stab", "bass": "gallop",
                       "lead": "G5:4 D5:4 G5:4 Bb5:4 | B5:4 G#5:4 E5:4 G#5:4 | G5:4 Bb5:4 Eb5:8 | A5:4 F#5:4 D5:8"},
                "bridge": {"chords": "Bb | F/A | Ebmaj7 | Dsus4 D", "rhythm": "swell", "bass": "long",
                           "lead": "D5:8 F5:8 | C6:8 A5:8 | Bb5:8 G5:8 | G5:8 F#5:8"},
                "coda": {"chords": "G | Eb | F | G", "rhythm": "march", "bass": "pulse8",
                         "lead": "D5:4 G5:4 B5:8 | Bb5:4 G5:4 Eb5:8 | A5:4 C6:4 F5:8 | G5:16"},
            },
            "form": ["intro", "a1", "a2", "b1", "b2", "bridge", "a1", "a2", "coda"], "loop": "a1",
        },
        # ------------------------------------------------------------------ 8
        {
            "title": "Lantern Hill", "slug": "lantern-hill", "role": "Spooky tower / haunted town",
            "bpm": 88, "key": "E minor",
            "style": "Old-handheld spooky-town feel (not a copy of any theme): a high repeating 8th-note "
                     "arpeggio figure over an E drone, whole-tone (Caug) and tritone (Bb/E) colour, "
                     "a slow counter-melody on ch4.",
            "j6": {"sets": "23 (all M9#11 = Lydian) for the #11 shimmer, 57 (House/Techno: C5b9 root+b9) for unease",
                   "style": "Long pad, slow ATTACK, big REVERB; or STYLE 1-2 slow arp"},
            "s1": {"bass": "SQUARE + SUB, LFO slow on pitch (tiny): drone",
                   "lead": "PULSE, short DECAY, DELAY on: high music-box/chip arpeggio"},
            "cover_ideas": "OP-XY: glass/music-box multisample for the figure, organ or choir pad, sine drone, "
                           "reverse-cymbal swells. M8: FM bell figure, sampled choir, slow granular drone on ch4.",
            "arp": "none", "bass_floor": 28,
            "sections": {
                "intro": {"chords": "Em | Em | Cmaj7 | Cmaj7", "rhythm": "pad", "bass": "drone",
                          "lead": "FIG_EM | FIG_EM | FIG_C | FIG_C",
                          "counter": "-:16 | -:16 | -:16 | -:16"},
                "a1": {"chords": "Em | Caug/E | Em | Bb/E", "rhythm": "pad", "bass": "drone",
                       "lead": "FIG_EM | FIG_AUG | FIG_EM | FIG_BB",
                       "counter": "E4:8 G4:8 | G#4:12 -:4 | F#4:8 B4:8 | A#4:8 A4:4 G4:4"},
                "a2": {"chords": "Em | Am/E | Caug/E | B7", "rhythm": "pad", "bass": "drone",
                       "lead": "FIG_EM | FIG_AM | FIG_AUG | FIG_B7",
                       "counter": "G4:8 E4:8 | A4:8 C5:8 | C5:4 G#4:4 E4:8 | D#4:12 -:4"},
                "b1": {"chords": "Cmaj7 | Am7 | F#m7b5 | B7", "rhythm": "swell", "bass": "long",
                       "lead": "FIG_C | FIG_AM | FIG_HD | FIG_B7",
                       "counter": "E5:8 D5:4 B4:4 | C5:12 -:4 | A4:8 C5:8 | B4:8 A4:4 F#4:4"},
                "b2": {"chords": "Cmaj7 | Am7 | F | B7", "rhythm": "swell", "bass": "long",
                       "lead": "FIG_C | FIG_AM | FIG_F | FIG_B7",
                       "counter": "G4:8 B4:8 | C5:8 E5:8 | F5:8 C5:4 A4:4 | D#5:12 -:4"},
                "bridge": {"chords": "Em | Bb/E | Em | Caug/E", "rhythm": "pad", "bass": "drone",
                           "lead": "FIG_EM | FIG_BB | FIG_EM | FIG_AUG",
                           "counter": "-:16 | F4:8 E4:8 | -:16 | G#4:8 C5:8"},
            },
            "form": ["intro", "a1", "a2", "b1", "b2", "bridge", "a1", "a2"], "loop": "a1",
        },
    ],
}

# The Lantern Hill figure: one bar of 8ths, first note high, drop, climb, step
# down. Original shape (down a 5th, up a m3, down a m2), re-voiced per chord.
FIGURES = {
    "FIG_EM": "B5:2 E5:2 G5:2 F#5:2 B5:2 E5:2 A5:2 G5:2",
    "FIG_C": "B5:2 E5:2 G5:2 F#5:2 C6:2 E5:2 G5:2 B5:2",
    "FIG_AUG": "C6:2 E5:2 G#5:2 F#5:2 C6:2 E5:2 A#5:2 G#5:2",
    "FIG_BB": "A#5:2 D5:2 F5:2 E5:2 A#5:2 D5:2 F5:2 E5:2",
    "FIG_AM": "C6:2 E5:2 A5:2 G5:2 C6:2 E5:2 B5:2 A5:2",
    "FIG_B7": "A5:2 D#5:2 F#5:2 E5:2 A5:2 D#5:2 B5:2 F#5:2",
    "FIG_HD": "A5:2 C5:2 E5:2 F#5:2 A5:2 C5:2 E5:2 D5:2",
    "FIG_F": "A5:2 C5:2 F5:2 E5:2 A5:2 C5:2 F5:2 C6:2",
}


# ===========================================================================
# ENGINE
# ===========================================================================

def pc_of(name):
    pc = PITCH[name[0]]
    for ch in name[1:]:
        pc += {"#": 1, "b": -1}[ch]
    return pc % 12


def parse_chord(sym):
    m = CHORD_RE.match(sym)
    if not m:
        raise SystemExit(f"can't parse chord symbol {sym!r}")
    root, suffix, slash = m.groups()
    rpc = pc_of(root)
    return {"sym": sym, "root_pc": rpc, "bass_pc": pc_of(slash) if slash else rpc,
            "ivs": CHORD_SUFFIX[suffix], "pcs": [(rpc + i) % 12 for i in CHORD_SUFFIX[suffix]]}


def transpose_sym(sym, semis, flats):
    m = CHORD_RE.match(sym)
    root, suffix, slash = m.groups()
    names = FLAT_NAMES if flats else SHARP_NAMES
    out = names[(pc_of(root) + semis) % 12] + suffix
    return out + ("/" + names[(pc_of(slash) + semis) % 12] if slash else "")


def parse_bars(line, label):
    bars = [b.split() for b in line.split("|")]
    if len(bars) != SECTION_BARS:
        raise SystemExit(f"{label}: {len(bars)} bars of chords, need {SECTION_BARS}")
    slots = []   # (start step, length, chord)
    for b, syms in enumerate(bars):
        if len(syms) not in (1, 2, 4):
            raise SystemExit(f"{label}: bar {b + 1} has {len(syms)} chords (1, 2 or 4 allowed)")
        ln = 16 // len(syms)
        for i, s in enumerate(syms):
            slots.append((b * 16 + i * ln, ln, parse_chord(s)))
    return bars, slots


def slot_at(slots, step):
    for s in slots:
        if s[0] <= step < s[0] + s[1]:
            return s
    raise SystemExit(f"no chord at step {step}")


def parse_line(line, label, accent_downbeats=True):
    """'F#5:4 E5:2 | ...' -> mono events. Every bar must add up to 16 steps."""
    for k, v in FIGURES.items():
        line = line.replace(k, v)
    bars = line.split("|")
    if len(bars) != SECTION_BARS:
        raise SystemExit(f"{label}: {len(bars)} bars of notes, need {SECTION_BARS}")
    ev, pos = [], 0
    for b, bar in enumerate(bars):
        start = pos
        for tok in bar.split():
            name, _, ln = tok.partition(":")
            ln = int(ln)
            acc, slide = "*" in name, "~" in name
            name = name.replace("*", "").replace("~", "")
            if name != "-":
                acc = acc or (accent_downbeats and pos % 16 == 0)
                ev.append(E(pos, ln, note_num(name), int(acc), slide))
            pos += ln
        if pos - start != 16:
            raise SystemExit(f"{label}: bar {b + 1} is {pos - start} steps, not 16")
    return ev


def place(pc, floor):
    return floor + (pc - floor) % 12


def fold(note, lo, hi):
    while note > hi:
        note -= 12
    while note < lo:
        note += 12
    return note


def bass_part(slots, style, tonic_pc, floor, label):
    lo, hi = RANGES["bass"]
    spec = BASS_STYLES[style]
    ev = []
    if spec == "slot":
        for st, ln, ch in slots:
            ev.append(E(st, ln, place(ch["bass_pc"], floor), 1))
        return ev
    for bar in range(SECTION_BARS):
        for step, tok, ln, acc in spec:
            s = bar * 16 + step
            st, sl, ch = slot_at(slots, s)
            root = place(ch["bass_pc"], floor)
            tonic = place(tonic_pc, floor)
            if tok == "a":
                nxt = next((x for x in slots if x[0] > s), slots[0])
                target = place(nxt[2]["bass_pc"], floor)
                prev = ev[-1]["note"] if ev else root
                cands = [c for t in (target, target + 12, target - 12) for c in (t - 1, t + 1)
                         if lo <= c <= hi and c != prev]
                note = min(cands, key=lambda c: (abs(c - prev), c))
            else:
                third = root + ch["ivs"][1] - (12 if ch["ivs"][1] > 12 else 0)
                note = {"R": root, "R+": root + 12, "5": root + 7, "5-": root - 5, "3": third,
                        "T": tonic, "T+": tonic + 12}[tok]
            ev.append(E(s, min(ln, SECTION_BARS * 16 - s), fold(note, lo, hi), acc))
    return ev


def chords_part(slots, voicings, rhythm):
    notes = []
    for (st, ln, _ch), v in zip(slots, voicings):
        if rhythm == "pad":
            hits = [(st, ln)]
        else:
            hits = []
            for bar_off in range(st - st % 16, st + ln, 16):
                for h, hl in CHORD_RHYTHMS[rhythm]:
                    s = bar_off + h
                    if st <= s < st + ln:
                        hits.append((s, min(hl, st + ln - s)))
        for s, hl in hits:
            vel = 96 if s % 16 == 0 else 84
            dur = hl * STEP - 30 if hl > 1 else int(STEP * 0.55)
            for m in v:
                notes.append((s * STEP, dur, m, vel))
    return notes


def arp_part(slots, voicings, style):
    spec = ARP_STYLES[style]
    if spec is None:
        return []
    ev = []
    for (st, ln, _ch), v in zip(slots, voicings):
        pool = sorted(v) + [min(v) + 12]
        if max(pool) + spec["lift"] <= RANGES["counter"][1]:
            pool = [p + spec["lift"] for p in pool]
        order = list(range(len(pool)))
        if spec["order"] == "updown":
            order += list(range(len(pool) - 2, 0, -1))
        for k, s in enumerate(range(st, st + ln, spec["every"])):
            ev.append(E(s, spec["every"], pool[order[k % len(order)]], int(s % 4 == 0)))
    return ev


def build_section(track, sid, spec, tonic_pc):
    label = f"{track['slug']}/{sid}"
    if "transpose" in spec:
        src_id, semis = spec["transpose"]
        src = track["sections"][src_id]
        chords = " | ".join(" ".join(transpose_sym(s, semis, flats=True) for s in bar.split())
                            for bar in src["chords"].split("|"))
        base = dict(src, chords=chords)
        sec = build_section(track, sid, base, (tonic_pc + semis) % 12)
        for e in sec["lead_ev"]:
            e["note"] += semis
        sec["key"] = spec["key"]
        sec["transposed_from"] = {"section": src_id, "semitones": semis}
        return sec
    bars, slots = parse_bars(spec["chords"], label)
    voicings = voice_lead([s[2]["pcs"] for s in slots])
    lead_ev = parse_line(spec["lead"], f"{label} lead")
    if "counter" in spec:
        counter_ev = parse_line(spec["counter"], f"{label} counter")
    else:
        counter_ev = arp_part(slots, voicings, track["arp"])
    return {
        "id": sid, "bars": bars, "slots": slots, "voicings": voicings,
        "rhythm": spec["rhythm"], "bass_style": spec["bass"], "key": track["key"],
        "chords_notes": chords_part(slots, voicings, spec["rhythm"]),
        "bass_ev": bass_part(slots, spec["bass"], tonic_pc, track["bass_floor"], label),
        "lead_ev": lead_ev, "counter_ev": counter_ev,
        "counter_kind": "hand-written counter-melody" if "counter" in spec else f"generated arp ({track['arp']})",
    }


def rendered(sec):
    """Section parts as (tick, dur, note, vel) lists, 4 bars long."""
    return {
        "chords": sorted(sec["chords_notes"]),
        "bass": render_mono([dict(e) for e in sec["bass_ev"]]),
        "lead": render_mono([dict(e) for e in sec["lead_ev"]]),
        "counter": render_mono([dict(e) for e in sec["counter_ev"]]) if sec["counter_ev"] else [],
    }


# ---------------------------------------------------------------------------
# SMF writing
# ---------------------------------------------------------------------------

FULL_ORDER = [("chords", 0, "Chords (J-6)"), ("bass", 1, "Bass (S-1)"),
              ("lead", 2, "Lead (S-1)"), ("counter", 3, "Counter/Arp (OP-XY/M8)")]


def smf_full(title, bpm, parts, markers, end):
    cond = tempo_meta(bpm, title) + [(t, 0, meta(0x06, txt.encode())) for t, txt in markers]
    chunks = [track_chunk(cond, end)]
    for part, ch, name in FULL_ORDER:
        chunks.append(track_chunk([(0, 0, meta(0x03, name.encode()))] + part_events(parts[part], ch), end))
    return b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), TPQ) + b"".join(chunks)


# ---------------------------------------------------------------------------
# Validation (reads files back with build_library.parse_smf and aira_local.read_smf)
# ---------------------------------------------------------------------------

def check_part(label, part, notes, end):
    lo, hi = RANGES[part]
    for on, off, note, *_ in notes:
        if not lo <= note <= hi:
            raise SystemExit(f"{label}: {midi_to_name(note)} outside {part} range "
                             f"{midi_to_name(lo)}-{midi_to_name(hi)}")
        if on < 0 or off > end or off <= on:
            raise SystemExit(f"{label}: note {on}-{off} outside 0-{end}")
    if part == "chords":
        groups = {}
        for on, off, *_ in notes:
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
        if a[1] > b[0] and (a[1] - b[0] > SLIDE_OVERLAP or a[2] == b[2] or a[1] > b[1]):
            raise SystemExit(f"{label}: illegal overlap {a[:3]} / {b[:3]}")


def check_file(path, expect, fmt_want, names, tempo, end):
    """expect: {part: [(tick, dur, note, vel)]} in track order after the conductor."""
    data = open(path, "rb").read()
    fmt, tpq, tracks = parse_smf(data)
    assert fmt == fmt_want and tpq == TPQ, f"{path}: format/tpq"
    assert tracks[0]["tempo"] == tempo, f"{path}: tempo"
    assert all(t["eot"] == end for t in tracks), f"{path}: length is not {end} ticks"
    note_tracks = tracks if fmt == 0 else tracks[1:]
    assert len(note_tracks) == len(expect), f"{path}: track count"
    for trk, (part, want) in zip(note_tracks, expect.items()):
        if fmt == 1:
            assert trk["name"] == names[part][1], f"{path}: track name {trk['name']}"
            assert all(c == names[part][0] for *_x, c in trk["notes"]), f"{path}: {part} channel"
        check_part(f"{os.path.relpath(path, ROOT)}:{part}", part, trk["notes"], end)
        got = [(on, off, nn, v) for on, off, nn, v, _c in trk["notes"]]
        assert got == sorted((t, t + d, nn, v) for t, d, nn, v in want), f"{path}: {part} round-trip mismatch"
    # second, independent reader (aira_local), as the scan command uses
    _tpq, events, tempos = read_smf(path)
    ons = sum(1 for e in events if e[2] & 0xF0 == 0x90 and e[4] > 0)
    assert ons == sum(len(w) for w in expect.values()), f"{path}: read_smf note count"
    assert tempos[0][1] == tempo, f"{path}: read_smf tempo"


def voice_motion(voicings):
    """Total semitones moved between neighbouring voicings (build_library.motion)."""
    moves = [motion(a, b) for a, b in zip(voicings, voicings[1:])]
    return [int(m) if m == int(m) else m for m in moves]


def sec_flats(key):
    tonic, mode = key.split()
    m = "maj" if mode == "major" else "min"
    names = {"maj": "C Db D Eb E F F# G Ab A Bb B", "min": "C C# D Eb E F F# G G# A Bb B"}
    return key_uses_flats(names[m].split().index(tonic), m)


def detected_key(path):
    _tpq, _bpm, notes = notes_from_smf(path)
    ranked = estimate_key(notes)
    return key_label(ranked[0][1], ranked[0][2])


def declared_label(key):
    tonic, mode = key.split()
    names = {"maj": "C Db D Eb E F F# G Ab A Bb B", "min": "C C# D Eb E F F# G G# A Bb B"}
    m = "maj" if mode == "major" else "min"
    return key_label(names[m].split().index(tonic), m)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def compact_json(obj):
    text = json.dumps(obj, indent=1, ensure_ascii=False)
    # keep short lists of numbers / strings on one line so the file stays diffable
    text = re.sub(r"\[\s*((?:-?[\d.]+|\"[^\"\n]*\")(?:,\s*(?:-?[\d.]+|\"[^\"\n]*\"))*)\s*\]",
                  lambda m: "[" + ", ".join(x.strip() for x in m.group(1).split(",")) + "]", text)
    text = re.sub(r"\[\s*(\[[^\[\]\n]*\](?:,\s*\[[^\[\]\n]*\])*)\s*\]",
                  lambda m: "[" + re.sub(r",\s*\[", ", [", m.group(1)) + "]", text)
    return text + "\n"


def build_track(n, track, stats):
    tonic = track["key"].split()[0]
    tonic_pc = pc_of(tonic)
    sids = list(track["sections"])
    if len(sids) > MAX_SECTIONS:
        raise SystemExit(f"{track['slug']}: {len(sids)} sections > {MAX_SECTIONS} pattern slots")
    for sid in track["form"]:
        if sid not in track["sections"]:
            raise SystemExit(f"{track['slug']}: form uses unknown section {sid}")
    unused = set(sids) - set(track["form"])
    if unused:
        raise SystemExit(f"{track['slug']}: sections never used: {sorted(unused)}")
    total_bars = len(track["form"]) * SECTION_BARS
    if not MIN_BARS <= total_bars <= MAX_BARS:
        raise SystemExit(f"{track['slug']}: {total_bars} bars, need {MIN_BARS}-{MAX_BARS}")

    tid = f"{n:02d}-{track['slug']}"
    folder = os.path.join(OUT_DIR, tid)
    sec_dir = os.path.join(folder, "sections")
    os.makedirs(sec_dir, exist_ok=True)
    tempo = int(60_000_000 / track["bpm"])

    secs, parts_by_sec = {}, {}
    for sid in sids:
        secs[sid] = build_section(track, sid, track["sections"][sid], tonic_pc)
        parts_by_sec[sid] = rendered(secs[sid])

    # section files: one J-6 / S-1 pattern each
    sec_meta = {}
    for k, sid in enumerate(sids, 1):
        sec, parts = secs[sid], parts_by_sec[sid]
        for part in ("chords", "bass", "lead"):
            if part != "chords" and len(parts[part]) and max(t + d for t, d, *_ in parts[part]) > STEPS * STEP:
                raise SystemExit(f"{tid}/{sid}: {part} exceeds 64 steps")
            path = os.path.join(sec_dir, f"{sid}-{part}.mid")
            with open(path, "wb") as fh:
                fh.write(smf_single(f"{track['title']} - {sid} - {part}", track["bpm"], parts[part]))
            check_file(path, {part: parts[part]}, 0, None, tempo, END)
            stats["files"] += 1
        moves = voice_motion(sec["voicings"])
        stats["max_motion"] = max([stats["max_motion"]] + moves)
        slot = 8 * (n - 1) + k
        sec_meta[sid] = {
            "bars": SECTION_BARS, "steps": STEPS, "home_key": sec["key"],
            "chords": [bar for bar in sec["bars"]],
            "voicings": [[note_name(m, sec_flats(sec["key"])) for m in v] for v in sec["voicings"]],
            "voice_motion_semitones": moves,
            "chord_rhythm": f"{sec['rhythm']}: {CHORD_RHYTHM_NOTES[sec['rhythm']]}",
            "bass_style": f"{sec['bass_style']}: {BASS_NOTES[sec['bass_style']]}",
            "counter": sec["counter_kind"],
            "files": {p: f"sections/{sid}-{p}.mid" for p in ("chords", "bass", "lead")},
            "pattern_slot": {"j6": slot, "s1_bass": slot, "s1_lead": slot},
        }
        if "transposed_from" in sec:
            sec_meta[sid]["transposed_from"] = sec["transposed_from"]

    # full arrangement
    full = {p: [] for p in ("chords", "bass", "lead", "counter")}
    markers, form, loop_bar = [], [], None
    for i, sid in enumerate(track["form"]):
        off = i * SECTION_BARS * BAR
        for p in full:
            full[p] += [(t + off, d, nn, v) for t, d, nn, v in parts_by_sec[sid][p]]
        bar = i * SECTION_BARS + 1
        label = sid
        if sid == track["loop"] and loop_bar is None and i > 0:
            loop_bar = bar
            label = f"{sid} (LOOP START)"
        markers.append((off, label))
        form.append({"section": sid, "bars": SECTION_BARS, "start_bar": bar})
    if loop_bar is None:
        raise SystemExit(f"{tid}: loop section {track['loop']} not found after the intro")
    end = total_bars * BAR
    markers.append((end, "LOOP END -> bar %d" % loop_bar))
    path = os.path.join(folder, "full.mid")
    with open(path, "wb") as fh:
        fh.write(smf_full(track["title"], track["bpm"], full, markers, end))
    names = {p: (ch, nm) for p, ch, nm in FULL_ORDER}
    check_file(path, full, 1, names, tempo, end)
    stats["files"] += 1

    det = detected_key(path)
    want = declared_label(track["key"])
    if det != want:
        raise SystemExit(f"{tid}: aira_local detects {det}, set.json says {track['key']} ({want})")

    return {
        "n": n, "id": tid, "dir": tid, "title": track["title"], "role": track["role"],
        "bpm": track["bpm"], "key": track["key"], "detected_key": det, "style": track["style"],
        "bars": total_bars, "form": form,
        "form_summary": " ".join(f"{f['section']}({f['bars']})" for f in form),
        "loop": {"start_bar": loop_bar, "end_bar": total_bars, "section": track["loop"],
                 "note": f"play the intro once, then loop bars {loop_bar}-{total_bars}"},
        "sections": sec_meta,
        "j6": {"closest_chord_sets": track["j6"]["sets"], "style": track["j6"]["style"]},
        "s1": {"bass_patch": track["s1"]["bass"], "lead_patch": track["s1"]["lead"],
               "pattern_slots": f"{8 * (n - 1) + 1}-{8 * (n - 1) + len(sids)}"},
        "counter_ch4": "hand-written counter-melody" if track["arp"] == "none" else f"generated {track['arp']} arp",
        "cover_ideas": track["cover_ideas"],
        "files": {"full": "full.mid", "sections": "sections/<section>-{chords,bass,lead}.mid"},
    }


def main():
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)          # this set is fully generated
    os.makedirs(OUT_DIR)
    stats = {"files": 0, "max_motion": 0}
    tracks = [build_track(n, t, stats) for n, t in enumerate(SET["tracks"], 1)]

    set_json = {
        "generated_by": "tools/build_sets.py",
        "id": SET["id"], "name": SET["name"], "description": SET["description"],
        "originality": ("All titles, melodies, basslines and chord sequences are original compositions. "
                        "'Sinnoh-era DS feel' describes the general style only (tempo, keys, harmonic "
                        "language, orchestration and rhythm cues); nothing is transcribed or paraphrased."),
        "ppq": TPQ, "section_bars": SECTION_BARS, "section_steps": STEPS,
        "channels": {"full.mid": {"chords (J-6)": 1, "bass (S-1)": 2, "lead (S-1)": 3,
                                  "counter/arp (OP-XY/M8 covers)": 4},
                     "sections/*.mid": 1},
        "ranges": {"chords": "C3-C5", "bass": "C1-C3", "lead": "C3-C6", "counter": "C3-C6"},
        "velocity": {"accent": ACC, "normal": NORM},
        "slide": f"note overlaps the next note by {SLIDE_OVERLAP} ticks (1/32), as in the genre-kit library",
        "pattern_slots": ("Each track owns 8 pattern slots: track N uses patterns 8(N-1)+1 .. 8(N-1)+8, one "
                          "per section in the order listed. The J-6 gets the chords file in that slot. The S-1 "
                          "has one pattern bank, so load either the BASS profile (sections/*-bass.mid) or the "
                          "LEAD profile (sections/*-lead.mid) into the same slot numbers; the other part goes "
                          "to an OP-XY/M8 track from full.mid."),
        "j6_chord_sets": J6_NOTE,
        "tracks": tracks,
    }
    with open(os.path.join(OUT_DIR, "set.json"), "w") as fh:
        fh.write(compact_json(set_json))

    index = {
        "generated_by": "tools/build_sets.py",
        "note": "Registry of switchable sets. Load one set onto the units at a time.",
        "sets": [
            {"id": "genre-kits", "name": "Genre kits (research library)", "path": "../library/index.json",
             "read_only": True, "built_by": "tools/build_library.py",
             "description": "4-bar genre idea kits in all 24 keys (chords, arp, bass, lead), sourced in "
                            "library/RESEARCH.md. Referenced here, not modified."},
            {"id": SET["id"], "name": SET["name"], "path": f"{SET['id']}/set.json", "read_only": False,
             "built_by": "tools/build_sets.py", "description": SET["description"],
             "tracks": [{"id": t["id"], "title": t["title"], "bpm": t["bpm"], "key": t["key"],
                         "bars": t["bars"]} for t in tracks]},
        ],
    }
    with open(os.path.join(SETS_DIR, "index.json"), "w") as fh:
        fh.write(compact_json(index))

    for t in tracks:
        print(f"  {t['id']:<24} {t['bpm']:>3} bpm  {t['key']:<9} {t['bars']} bars  "
              f"detected {t['detected_key']:<6} {t['form_summary']}")
    print(f"\n{len(tracks)} tracks, {stats['files']} .mid files -> {os.path.relpath(OUT_DIR, ROOT)}")
    print(f"largest chord-to-chord voice movement inside a section: {stats['max_motion']} semitones (sum)")
    print("all files parsed back (build_library.parse_smf + aira_local.read_smf) and validated: ranges, "
          "monophony, block chords, 4-bar sections / 64 S-1 steps, exact lengths, detected key = declared key.")


if __name__ == "__main__":
    main()
