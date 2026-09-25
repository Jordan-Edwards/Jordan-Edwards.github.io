#!/usr/bin/env python3
"""
Build the S-1 / J-6 idea library.

Emits s1-j6/library/:
  <Key>/<NN-genre-roman[-poly]>/chords.mid   J-6 style chords, one track, block chords
  <Key>/<NN-genre-roman[-poly]>/arp.mid      arpeggio of the same chords
  <Key>/<NN-genre-roman[-poly]>/bass.mid     S-1 bassline, mono, accents + slides
  <Key>/<NN-genre-roman[-poly]>/lead.mid     lead / topline, mono
  <Key>/<NN-genre-roman[-poly]>/all.mid      the whole kit: chords ch1, bass ch2, lead ch3, arp ch4
  index.json                                 what is where (read by s1-j6/library.html)
  RESEARCH.md                                the sourced research the DATA block is built from
                                             (hand-maintained; the builder never deletes it)

The file has two halves:

  DATA    every genre, progression and part pattern, each tagged with the
          report item it comes from (`ref`), its `source` URL(s), a
          `confidence` (sourced / constructed / common-practice, matching the
          tags in RESEARCH.md) and `why` it is idiomatic. Nothing goes in DATA
          that is not in RESEARCH.md.
  ENGINE  turns DATA into notes for all 24 keys: voice-leads the chords,
          resolves pattern offsets against each bar's chord, writes and then
          re-reads every file to validate it.

Every part is exactly 4 bars = 64 sixteenth steps, so each mono part fits one
S-1 pattern. Polymetric parts (odd cycles such as 13 or 3 steps) are written
out across the 64 steps, so the cycle drifts against the bar exactly as it
would on the unit with the stated S-1 last-step setting.

Accent = velocity 110 (plain notes 80, ghost notes 64). Slide = the note is
held SLIDE_OVERLAP ticks (1/32) into the next, different note: a legato
overlap. How the S-1 itself maps velocity/overlap to accent/slide has not been
verified against its manual (see RESEARCH.md section 16).

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
SLIDE_OVERLAP = TPQ // 8  # 1/32: how far a sliding note overlaps the next one
ACC, NORM, GHOST = 110, 80, 64

RANGES = {                # inclusive MIDI ranges each part must stay in
    "chords": (48, 72),   # C3..C5
    "arp": (48, 84),      # C3..C6
    "bass": (24, 48),     # C1..C3
    "lead": (48, 84),     # C3..C6
}

CONFIDENCE = ("sourced", "constructed", "common-practice")


# ===========================================================================
# DATA  (every entry comes from s1-j6/library/RESEARCH.md; `ref` = its item id)
# ===========================================================================
#
# Roman numerals follow RESEARCH.md: relative to the MAJOR scale of the tonic,
# lowercase = minor, b/# = flat/sharp degree. So in A minor "bVI" = F, "bII" = Bb.
# Suffixes: 7 maj7 9 maj9 11 13 maj13 6 sus2 sus4 add9 5b9 ø7 ° °7 (lowercase maj7 = mM7).
#
# Bass/grid offsets are semitones from the bar's chord root, as in the report's
# `n:` rows. A string "T<n>" is n semitones from the key's tonic instead (pedals,
# P7). "a" = chromatic approach into the next bar's root.
# Grid tuples: (step 0-15, offset, length in steps, accent, slide) with accent
# 1 = accent, 0 = normal, -1 = ghost. Report steps are 1-16; these are 0-15.

J6_SETS = {  # RESEARCH.md section 13, from github.com/stonefruit/j6 j6-chords.json
    "synthwave": "Sets 39-47 (Synthwave), 34 (all sus2), 27 (Pop/Synth); set 40 = all add9",
    "acid": "Set 58 (Techno), set 57 (House/Techno, has C5b9 root+b9 stab)",
    "deephouse": "Sets 49-54 (House), 55-56 (Jazz House), 47 (all m7/M7), 20 (all m7), 22 (all m9)",
    "chicago": "Sets 49-54 (House)",
    "lofi": "Sets 68-69 (Lofi R&B), 72-81 (Neo Soul), 19 (all M7), 20 (all m7), 21 (all M9)",
    "techno": "Set 58 (Techno), 57 (C5b9 stab), 20 (all m7), 22 (all m9), 24 (all m9/11)",
    "melodictechno": "Set 48 (Trance: minor palette, slash-chord bass), 58 (Techno)",
    "ukg": "Sets 22, 24 (m9, m9/11), 49-52 (House)",
    "dnb": "Sets 22 (all m9), 21 (all M9), 19 (all M7), 55-56 (Jazz House)",
    "trap": "Sets 8 (C-minor diatonic), 7-11 (Trad Maj/Min, Pop Min)",
    "ambient": "Sets 33-38 (Cinematic), 23 (all M9#11 = Lydian), 34/36 (sus2)",
    "futuregarage": "Set 34 (all sus2), 20 (all m7), 22 (all m9)",
}

GENRES = {
    "synthwave": {"name": "Synthwave / Darksynth", "bpm": 100, "range": "80-118",
                  "source": ["https://vibesdj.io/dj-tools/what-bpm-is-synthwave",
                             "https://emastered.com/blog/synthwave-chord-progressions"],
                  "why": "~100 BPM (outrun ~105, darksynth ~114); minor keys, Phrygian/Mixolydian, harmonic-minor V in darkwave."},
    "acid": {"name": "Acid house / techno", "bpm": 130, "range": "118-140",
             "source": ["https://grokipedia.com/page/Acid_house", "https://www.mixgraph.io/bpm-for/acid-techno"],
             "why": "Acid techno 130-140, Chicago acid 118-125; a pedal on one root, Dorian/Phrygian fragments."},
    "deephouse": {"name": "Deep house", "bpm": 120, "range": "118-124",
                  "source": ["https://beatkey.app/how-to-make-deep-house-music"],
                  "why": "118-124 BPM, minor keys, Dorian im7-IV7 vamps, m7/m9 voicings."},
    "chicago": {"name": "Chicago house", "bpm": 124, "range": "118-125",
                "source": ["https://samplefocus.com/blog/cubase-vs-ableton-classic-chicago-house-tracks/"],
                "why": "118-125 BPM four-on-the-floor; offbeat stabs mirroring the open hat."},
    "lofi": {"name": "Lo-fi hip hop", "bpm": 82, "range": "70-90",
             "source": ["https://blog.flat.io/lofi-chord-progressions/"],
             "why": "70-90 BPM (mostly 80-85), maj7/m7/9 chords held a bar or more; swing it on the OP-XY."},
    "techno": {"name": "Berlin techno", "bpm": 132, "range": "124-140",
               "source": ["https://bpmcalc.com/genres/techno/", "https://www.theoryhelper.com/genres/techno/scales"],
               "why": "Mostly 130-140 (minimal 124-130); Phrygian for dark techno; stabs and pedals, not progressions."},
    "melodictechno": {"name": "Melodic techno", "bpm": 123, "range": "120-125",
                      "source": ["https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies"],
                      "why": "120-125 BPM, minor keys only, chords change every 2 or 4 bars."},
    "ukg": {"name": "UK garage / 2-step", "bpm": 132, "range": "130-140",
            "source": ["https://www.musicradar.com/how-to/uk-garage-tutorial", "https://bpmcalc.com/genres/garage/"],
            "why": "~130-134 BPM with heavy swing (60%); m7/m9 in Am/Cm/Dm; stabs share the bass rhythm."},
    "dnb": {"name": "Liquid drum & bass", "bpm": 174, "range": "165-175",
            "source": ["https://www.edmprod.com/how-to-make-liquid-drum-and-bass/"],
            "why": "174 BPM (liquid 165-175), extended chords, sub in the D#1-G#1 sweet spot."},
    "trap": {"name": "Trap / dark pop", "bpm": 140, "range": "130-170 (half-time feel)",
             "source": ["https://chordmap.io/trap-chord-progressions"],
             "why": "140-160 BPM felt in half-time; natural/harmonic minor and Phrygian; sparse chords leave room for the 808."},
    "ambient": {"name": "Ambient / cinematic", "bpm": 72, "range": "60-90 (common practice)",
                "source": ["https://www.chordgen.org/chords/cinematic", "https://www.chordgen.org/chords/ambient"],
                "why": "Slow modal vamps, sus/maj7/add9 open voicings, pedal tones."},
    "futuregarage": {"name": "Future garage / chillwave", "bpm": 136, "range": "130-140 (chillwave 80-110)",
                     "source": ["https://en.wikipedia.org/wiki/Future_garage", "https://vibesdj.io/dj-tools/synthwave-bpm-chart"],
                     "why": "Future garage 130-140 with thinned 2-step drums and slow minor sus2/m7 pads; chillwave 80-110."},
}

CHORD_RHYTHMS = {
    "held": {"hits": [(0, 16)], "ref": "LF voicing / DH7 organ", "confidence": "sourced",
             "source": ["https://blog.flat.io/lofi-chord-progressions/"],
             "why": "Hold each chord a bar or more; also how the 'Can You Feel It' organ is played."},
    "offbeat": {"hits": [(2, 1), (6, 1), (10, 1), (14, 1)], "ref": "CH stab rhythm", "confidence": "sourced",
                "source": ["https://www.drumloopai.com/blog/house-chord-progressions/"],
                "why": "Short stabs on the 'and' of each beat, mirroring the offbeat hat."},
    "syncopated": {"hits": [(3, 1), (6, 1), (9, 1), (14, 1)], "ref": "CH stab rhythm", "confidence": "constructed",
                   "source": ["https://www.attackmagazine.com/technique/passing-notes/levelling-up-your-chord-stabs/"],
                   "why": "16th stab that skips the main drum hits and favours offbeat 16ths (...x|..x.|.x..|..x.)."},
    "single-stab": {"hits": [(0, 2)], "ref": "Acid pairing", "confidence": "sourced",
                    "source": ["https://www.attackmagazine.com/technique/beat-dissected/armando-acid-house/"],
                    "why": "Acid runs with no chords or a single stab: one hit per bar."},
    "follow-bass": {"follow": True, "ref": "UKG harmony", "confidence": "sourced",
                    "source": ["https://theproducerschool.com/blogs/featured-blogs/master-uk-garage-production-complete-guide-to-filthy-basslines-and-swing-drums"],
                    "why": "Garage stabs use the same MIDI rhythm as the bassline, with the notes shortened."},
}

ARPS = {
    "sw-up": {"hits": list(range(16)), "order": "up", "pool": "root", "ref": "Synthwave arp", "confidence": "sourced",
              "source": ["https://futureproofmusicschool.com/blog/dive-into-synthwave-create-your-own-sound-today"],
              "why": "16th arp, Up mode: root, 3rd, 5th, octave."},
    "sw-updown": {"hits": list(range(16)), "order": "updown", "pool": "root", "ref": "Synthwave arp", "confidence": "sourced",
                  "source": ["https://futureproofmusicschool.com/blog/dive-into-synthwave-create-your-own-sound-today"],
                  "why": "16th arp, Up/Down mode over root, 3rd, 5th, octave."},
    "one-octave": {"hits": list(range(16)), "order": "up", "pool": "octave", "ref": "SW-B2/SW-B3", "confidence": "constructed",
                   "source": ["https://www.attackmagazine.com/technique/tutorials/an-introduction-to-arpeggiators/"],
                   "why": "Arp set to a 1-octave range holding one note: root and octave in 16ths."},
    "j6-updown-8": {"hits": list(range(0, 16, 2)), "order": "updown", "pool": "voicing", "ref": "J-6 STYLE 1-2",
                    "confidence": "sourced", "source": ["https://articles.roland.com/getting-to-know-aira-compact-j-6-chord-synth/"],
                    "why": "J-6 styles 1-2 are up/down arps at various speeds; this is the 8th-note speed over the pad voicing."},
    "j6-up-16": {"hits": list(range(16)), "order": "up", "pool": "voicing", "ref": "J-6 STYLE 1-2",
                 "confidence": "sourced", "source": ["https://articles.roland.com/getting-to-know-aira-compact-j-6-chord-synth/"],
                 "why": "J-6 styles 1-2 are up/down arps at various speeds; this is the 16th speed over the pad voicing."},
    "mt-pluck": {"hits": list(range(16)), "order": "up", "pool": "voicing", "ref": "MT lead/arp", "confidence": "sourced",
                 "source": ["https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies"],
                 "why": "Plucked 16th arp cycling the chord tones (short decay, low sustain)."},
    "p1-3-over-4": {"hits": [0], "period": 3, "order": "up", "pool": "voicing", "accent": "beat",
                    "ref": "P1", "confidence": "sourced", "poly": "3 against 4 (P1)",
                    "source": ["https://www.pointblankmusicschool.com/blog/exploring-polyrhythms-in-modern-music-production/"],
                    "why": "A note every 3 sixteenths walking up the chord, so it lands on a different 16th each beat. "
                           "Accents fall where the cycle meets a beat (every 12 steps). On the S-1 a 3-step loop "
                           "(SHIFT+pad 4 (LAST), VALUE = 3) gives the rhythm; enter all 64 steps to keep the moving chord tones."},
    "p2-33334": {"hits": [0, 3, 6, 9, 12], "order": "up", "pool": "voicing", "accent": "cycle",
                 "ref": "P2", "confidence": "sourced", "poly": "3-3-3-3-4 cross-rhythm (P2)",
                 "source": ["https://www.8notes.com/school/lessons/piano/trance_pattern1.asp",
                            "https://www.myloops.net/programming-trance-arpeggios-and-rhythmic-sequences"],
                 "why": "Trance cross-rhythm x..x..x..x..x... cut short to realign with every bar. Last step 16 (no change needed)."},
    "p6-6-step": {"hits": [0, 2, 3], "period": 6, "order": "updown", "pool": "voicing", "accent": "cycle",
                  "ref": "P6", "confidence": "constructed", "poly": "6-step part over a 16-step bar (P6)",
                  "source": ["https://keithmcmillen.com/blog/analog-rytm-programming-with-polymeter/"],
                  "why": "Techno polymeter: this part repeats every 6 steps against the 16-step kick. "
                         "On the S-1: SHIFT+pad 4 (LAST) + VALUE = 6."},
    "p8-loop-28": {"hits": [0, 10], "period": 28, "len": 8, "order": "updown", "pool": "voicing", "accent": "cycle",
                   "ref": "P8", "confidence": "constructed", "poly": "7-beat loop against the 4-beat bar (P8)",
                   "source": ["https://www.musicradar.com/tuition/tech/how-to-create-a-generative-evolving-ambient-drone-sound-in-ableton-live-590880"],
                   "why": "Eno-style unsynchronised loops: this part repeats every 7 beats (28 steps), the lead every 5, so they drift. "
                          "S-1 last step = 28."},
}

BASSES = {
    "sw-b1": {"grid": [(s, 0 if s % 4 == 0 else 12, 2, int(s % 8 == 0), 0) for s in range(0, 16, 2)],
              "ref": "SW-B1", "confidence": "sourced",
              "source": ["https://blog.imseankim.com/synthwave-retro-production-techniques-modern-tools/"],
              "why": "Octave 8ths (Kavinsky / Perturbator): root low/high alternating."},
    "sw-b2": {"grid": [(s, 0, 1, int(s % 4 == 0), 0) for s in range(16)], "ref": "SW-B2", "confidence": "sourced",
              "source": ["https://www.sweetwater.com/insync/atmospheric-virtual-instruments-catching-the-synthwave/",
                         "https://babyaud.io/blog/how-to-make-synthwave"],
              "why": "Root repeated in 16ths, following the chord root each bar."},
    "sw-b3": {"grid": [(s, 0 if s % 2 == 0 else 12, 1, int(s % 4 == 0), 0) for s in range(16)],
              "ref": "SW-B3", "confidence": "constructed",
              "source": ["https://www.attackmagazine.com/technique/tutorials/an-introduction-to-arpeggiators/"],
              "why": "16th octave bass: the 1-octave arp on one note."},
    "sw-b4": {"grid": [(0, 0, 1, 1, 0), (2, 0, 1, 0, 0), (3, 0, 1, 0, 0), (4, 0, 1, 1, 0), (6, 0, 1, 0, 0),
                       (7, 12, 1, 0, 0), (8, 0, 1, 1, 0), (10, 0, 1, 0, 0), (11, 0, 1, 0, 0), (12, 0, 1, 1, 0),
                       (14, 12, 1, 0, 0), (15, 0, 1, 0, 0)],
              "ref": "SW-B4", "confidence": "common-practice", "source": [],
              "why": "Darksynth gallop x.xx with octave pickups."},
    "ac-b1": {"cell": [(0, 23, 1, 1, 1), (1, -1, 1, 0, 0), (2, 0, 1, 1, 0), (3, 12, 1, 1, 0),
                       (4, 0, 1, 0, 0), (5, 15, 1, 1, 0), (6, 3, 1, 0, 0), (7, 12, 1, 1, 0)], "period": 8,
              "ref": "AC-B1", "confidence": "sourced",
              "source": ["https://djjondent.blogspot.com/2020/04/famous-303-bassline-patterns-page-1.html",
                         "https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/1112706-phuture-acid-tracks-303-pattern.html"],
              "why": "Phuture 'Acid Tracks': 8 steps looped twice per bar. The octave reading of the 303 up/down flags is the "
                     "researcher's; octaves are folded into C1-C3 here."},
    "ac-b2": {"grid": [(s, n, 1, int(s in (9, 12)), 0) for s, n in
                       enumerate([0, 0, 4, 0, 0, 12, 0, 4, 0, 0, 4, 0, 12, 0, 4, 0])],
              "ref": "AC-B2", "confidence": "constructed",
              "source": ["https://djjondent.blogspot.com/2020/04/famous-303-bassline-patterns-page-1.html"],
              "why": "Josh Wink 'Higher State' idea: two notes (root and major 3rd), accents on steps 10 and 13. "
                     "Exact note order is not in the source; this is a placeholder."},
    "ac-b4": {"grid": [(s, n, 1, int(s in (2, 6, 10, 12)), int(s in (1, 6, 11, 14))) for s, n in
                       enumerate([0, 0, 12, 0, 0, 3, 0, 12, 0, 0, 7, 0, 12, 0, 3, 0])],
              "ref": "AC-B4", "confidence": "constructed",
              "source": ["https://www.musicradar.com/news/producers-guide-to-the-roland-tb-303-and-clones",
                         "https://synths101.com/how-to-make-a-tb-303-acid-sequence-tutorial-clones/"],
              "why": "Straight 16ths on 1-2 pitches, slides into octave jumps, accents on offbeats."},
    "ac-b5-13": {"cell": [(s, n, 1, int(s in (2, 6, 10, 12)), int(s in (1, 6, 11))) for s, n in
                          enumerate([0, 0, 12, 0, 0, 3, 0, 12, 0, 0, 7, 0, 12])], "period": 13,
                 "ref": "AC-B5 / P4", "confidence": "constructed", "poly": "13-step acid loop over 4/4 (P4)",
                 "source": ["https://www.musicradar.com/news/producers-guide-to-the-roland-tb-303-and-clones"],
                 "why": "AC-B4 cut to 13 steps so it drifts against the bar ('woozy'). "
                        "On the S-1: SHIFT+pad 4 (LAST), VALUE = 13, and enter just the first 13 steps."},
    "ac-b6-lanes": {"lanes": {"notes": [0, 0, 12, 0, 0, 3, 0, 12, 0, 0, 7, 0, 12, 0, 3, 0],
                              "accent": [1, 0, 0, 1, 0, 0, 0], "slide": [0, 1, 0, 0, 0]},
                    "ref": "AC-B6 / P5", "confidence": "constructed", "poly": "notes 16 / accents 7 / slides 5 (P5)",
                    "source": ["https://www.mind-flux.com/news-1/2025/5/26/acid-v-by-arturia-a-walkthrough-for-crafting-authentic-acid-lines"],
                    "why": "Accent and slide lanes of different lengths from the note lane (16/7/5), written out over 64 steps. "
                           "The S-1 has one pattern length, so keep last step = 64 and use these 64 steps as-is."},
    "dh-b1": {"grid": [(2, 0, 2, 0, 0), (6, 0, 2, 0, 0), (10, 0, 2, 0, 0), (14, 0, 2, 0, 0)],
              "ref": "DH-B1 / TB-2", "confidence": "sourced",
              "source": ["https://www.myloops.net/how-to-make-a-melodic-techno-bassline"],
              "why": "Offbeat 8th on the 'and' of each beat, ducked by the kick; long offbeat notes."},
    "dh-b2": {"grid": [(0, 0, 2, 1, 0), (3, 12, 1, 0, 0), (6, 0, 2, 0, 0), (8, 0, 2, 1, 0), (11, 12, 1, 0, 0),
                       (14, 7, 2, 0, 0)],
              "ref": "DH-B2", "confidence": "constructed", "source": ["https://www.edmprod.com/how-to-make-classic-deep-house/"],
              "why": "Root on the beat moved partly to offbeats, plus octave leaps."},
    "dh-b3": {"grid": [(0, 0, 3, 1, 0), (6, 0, 3, 0, 0), (12, 12, 3, 0, 0)],
              "ref": "DH-B3 / P9", "confidence": "sourced", "poly": "tresillo 3-3-2 (P9)",
              "source": ["https://www.myloops.net/how-to-make-a-melodic-techno-bassline"],
              "why": "Tresillo 3-3-2 on steps 1, 7, 13. Fits a normal 16-step S-1 pattern."},
    "dh-b4": {"grid": [(0, "T0", 6, 1, 0), (8, "T0", 6, 0, 0)],
              "ref": "DH-B4", "confidence": "sourced",
              "source": ["https://www.attackmagazine.com/technique/passing-notes/kerri-chandler-chords-part2/"],
              "why": "Kerri Chandler pedal: the bass holds the tonic while the chords move."},
    "ch-b1": {"grid": [(0, 0, 1, 1, 0), (2, 12, 1, 0, 0), (3, 0, 1, 0, 0), (6, 0, 2, 0, 0),
                       (8, 0, 1, 1, 0), (10, 12, 1, 0, 0), (11, 0, 1, 0, 0), (14, 12, 2, 0, 0)],
              "ref": "CH-B1", "confidence": "constructed",
              "source": ["https://samplefocus.com/blog/cubase-vs-ableton-classic-chicago-house-tracks/"],
              "why": "Repetitive, hooky, octave-jumping and syncopated, locked to the kick."},
    "lf-b1": {"grid": [(0, 0, 4, 1, 0), (6, 0, 2, 0, 0), (8, 7, 4, 0, 0)],
              "ref": "LF-B1", "confidence": "constructed",
              "source": ["https://www.lofimusicacademy.com/crafting-warm-basslines-for-lofi-music-production"],
              "why": "Root on beat 1, mostly root and 5th. Apply 55-60% swing on the OP-XY."},
    "lf-b2": {"grid": [(0, 0, 4, 1, 0), (6, 12, 2, -1, 0), (10, 0, 2, 0, 0), (12, 7, 4, 0, 0)],
              "ref": "LF-B2", "confidence": "constructed",
              "source": ["https://www.transmissionsamples.com/how-to-make-lofi-bass"],
              "why": "Root with a ghost offbeat octave, then the 5th."},
    "lf-b2-12": {"cell": [(0, 0, 4, 1, 0), (6, 12, 2, -1, 0), (10, 0, 2, 0, 0)], "period": 12,
                 "ref": "LF-B2 / P11", "confidence": "constructed", "poly": "3/4 bass (12 steps) over 4/4 (P11)",
                 "source": ["https://support.roland.com/hc/en-us/articles/15032698015899-S-1-How-to-Input-a-Sequence-in-3-4-Time"],
                 "why": "LF-B2 folded into a 3/4 bar that drifts against the 4/4 chords. "
                        "On the S-1: SHIFT+pad 4 (LAST), VALUE = 12."},
    "lf-b3": {"grid": [[(0, 0, 4, 1, 0), (4, 3, 4, 0, 0), (8, 7, 4, 0, 0), (12, "a", 4, 0, 0)],
                       [(0, 12, 4, 1, 0), (4, 7, 4, 0, 0), (8, 3, 4, 0, 0), (12, "a", 4, 0, 0)]], "float": True,
              "ref": "LF-B3", "confidence": "sourced",
              "source": ["https://www.learnjazzstandards.com/blog/learning-jazz/bass/write-walking-bass-line/"],
              "why": "Walking line: chord tones, then a half-step into the next chord's root (jazz source)."},
    "tb-1": {"grid": [(s, 0, 1, int(s % 4 == 2), 0) for s in range(16) if s % 4],
             "ref": "TB-1", "confidence": "sourced",
             "source": ["https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/"],
             "why": "Rolling 16ths with the first 16th of each beat left empty for the kick."},
    "tb-1-phrygian": {"grid": [(s, [0, 0, 1][s % 4 - 1], 1, int(s % 4 == 2), 0) for s in range(16) if s % 4],
                      "ref": "TB-1", "confidence": "sourced",
                      "source": ["https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/"],
                      "why": "Rolling 16ths off the kick, 0 0 1 variant for the Phrygian b2."},
    "tb-1-octave": {"grid": [(s, [0, 12, 0][s % 4 - 1], 1, int(s % 4 == 2), 0) for s in range(16) if s % 4],
                    "ref": "TB-1", "confidence": "sourced",
                    "source": ["https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/"],
                    "why": "Rolling 16ths off the kick, 0 12 0 variant."},
    "tb-3": {"grid": [(s, 12 if s % 4 == 2 else 0, 1, int(s % 4 == 0), 0) for s in range(16)],
             "ref": "TB-3", "confidence": "constructed", "source": ["https://www.studiobrootle.com/ebm-bassline-tutorial-ableton/"],
             "why": "EBM: all 16 steps on, octave on the 3rd 16th of each beat; distort it."},
    "tb-5": {"grid": [(s, [0, 7, 0, 3][s % 4], 1, int(s % 4 == 0), 0) for s in range(16)],
             "ref": "TB-5", "confidence": "constructed",
             "source": ["https://theproducerschool.com/blogs/featured-blogs/building-a-rolling-bassline-like-chris-stussy-the-3-note-pattern-that-defines-modern-tech-house"],
             "why": "Near-continuous 16ths on 3 notes (0 7 0 3); add swing and velocity variation."},
    "mt-offbeat-ghost": {"grid": [(2, 0, 2, 0, 0), (6, 0, 1, 0, 0), (7, 0, 1, -1, 0), (10, 0, 2, 0, 0),
                                  (14, 0, 1, 0, 0), (15, 0, 1, -1, 0)],
                         "ref": "MT bass", "confidence": "sourced",
                         "source": ["https://www.myloops.net/how-to-make-a-melodic-techno-bassline"],
                         "why": "Offbeat 8ths with a ghost 16th (vel 64) just before the next kick."},
    "mt-tresillo-10": {"grid": [(s, 0, 1, int(s in (0, 6, 12)), 0) for s in (0, 2, 3, 5, 6, 8, 9, 11, 13, 14)],
                       "ref": "MT bass", "confidence": "constructed", "poly": "tresillo backbone (P9)",
                       "source": ["https://www.myloops.net/how-to-make-a-melodic-techno-bassline"],
                       "why": "16 slots with 10 filled on a tresillo backbone (x.xx|.xx.|xx.x|.xx.)."},
    "uk-b1": {"grid": [(0, 0, 2, 1, 0), (3, 0, 1, 0, 0), (6, 12, 2, 0, 0), (10, 0, 2, 1, 0), (13, 10, 2, 0, 0)],
              "ref": "UK-B1", "confidence": "constructed",
              "source": ["https://www.studiobrootle.com/uk-garage-drum-pattern-with-presets-and-bassline/"],
              "why": "Skippy line following the 2-step kick, b7 pickup. Swing ~60% on the OP-XY."},
    "uk-b2": {"grid": [(0, 0, 6, 1, 0), (6, 0, 4, 0, 0), (10, 0, 6, 0, 0)],
              "ref": "UK-B2", "confidence": "sourced",
              "source": ["https://www.studiobrootle.com/uk-garage-drum-pattern-with-presets-and-bassline/"],
              "why": "Long sub notes (x---|--x-|--x-|----) for a slow-attack 'wub'."},
    "uk-b3": {"grid": [(0, 0, 1, 1, 0), (2, 12, 1, 0, 0), (5, 0, 1, 0, 0), (7, 12, 1, 0, 0),
                       (8, 0, 1, 1, 0), (10, 12, 1, 0, 0), (13, 0, 1, 0, 0)],
              "ref": "UK-B3", "confidence": "common-practice", "source": [],
              "why": "M1 organ-bass bounce, root/octave."},
    "db-b1": {"grid": [(0, 0, 10, 1, 0), (10, 0, 6, 0, 0)], "ref": "DB-B1", "confidence": "sourced",
              "source": ["https://www.musicradar.com/how-to/beat-programming-drums-bass-rhythm-section"],
              "why": "Sub on every kick of the two-step (steps 1 and 11), long notes on the chord root."},
    "db-b2": {"grid": [(0, 0, 10, 1, 1), (10, 7, 6, 0, 1)], "ref": "DB-B2", "confidence": "sourced",
              "source": ["https://bassgorilla.com/what-is-reese-how-make-one/"],
              "why": "Reese: legato notes on the two-step kick that glide into each other."},
    "db-b4": {"grid": [(0, 0, 2, 1, 0), (3, 0, 2, 0, 0), (6, 0, 2, 0, 0), (10, 0, 1, 0, 0), (11, 12, 1, 0, 0),
                       (13, 0, 2, 0, 0)],
              "ref": "DB-B4", "confidence": "constructed",
              "source": ["https://www.musicradar.com/how-to/beat-programming-drums-bass-rhythm-section"],
              "why": "Rolling offbeat (x..x|..x.|..xx|.x..) weaving around the kick."},
    "db-p7": {"cell": [(0, "T0", 6, 1, 0), (6, "T3", 6, 0, 0), (12, "T7", 6, 0, 0), (18, "T0", 6, 1, 0),
                       (24, "T8", 6, 0, 0), (30, "T7", 6, 0, 0)], "period": 36,
              "ref": "DB2 / DB4 / P7", "confidence": "sourced", "poly": "bass change every 3 eighths (P7)",
              "source": ["https://www.musicradar.com/how-to/how-to-create-uplifting-liquid-dnb-chords"],
              "why": "One new bass note every three 8ths (A C E A F E in A minor) under one shared upper shape, so the "
                     "bass alone changes the chord. 36-step cycle: S-1 last step = 36."},
    "808-1": {"grid": [(0, 0, 3, 1, 0), (3, 0, 7, 0, 1), (10, 12, 6, 0, 0)], "ref": "808-1", "confidence": "constructed",
              "source": ["https://songen.app/blog/808-bass-guide/"],
              "why": "808 on the kick, sliding up an octave (half-time bar)."},
    "808-2": {"grid": [(0, 0, 3, 1, 0), (3, 0, 7, 0, 1), (10, 3, 4, 0, 1), (14, 0, 2, 0, 0)],
              "ref": "808-2", "confidence": "constructed",
              "source": ["https://www.productionmusiclive.com/blogs/news/trap-beat-guide-bass-essential-tips-for-making-808-patterns"],
              "why": "808 glides to the b3 and back to the root."},
    "am-b1": {"grid": [(0, "T0", 16, 1, 0)], "tie": True, "ref": "AM-B1", "confidence": "sourced",
              "source": ["https://www.chordgen.org/chords/ambient"],
              "why": "Drone / pedal on the tonic, one note tied across all four bars."},
    "fg-b1": {"grid": [(0, 0, 10, 1, 0), (10, 0, 6, 0, 0)], "ref": "FG-B1", "confidence": "constructed",
              "source": ["https://en.wikipedia.org/wiki/Future_garage"],
              "why": "Long sine sub on the 2-step kick positions (steps 1 and 11)."},
}

# Leads.  kind "motif": rhythm A (bars 1-3, bar 3 varies its tail) + cadence B
#   (bar 4); contour in scale steps from a chord tone near `center`; notes on a
#   beat snap to chord tones; `octaves` shifts each bar.
# kind "tonic": per-bar (rhythm, scale steps from the tonic near `center`, shift).
# kind "cycle": notes (offset, len, scale step from tonic) repeating every `period` steps.
_SW_A = [(0, 3), (3, 3), (6, 2), (8, 4), (12, 2), (14, 2)]
_SW_B = [(0, 3), (3, 3), (6, 2), (8, 8)]
LEADS = {
    "sw-motif": {"kind": "motif", "A": _SW_A, "A_contour": [0, -1, 0, 2, 1, 0], "B": _SW_B, "B_contour": [2, 1, -1, 0],
                 "center": 62, "octaves": [0, 0, 12, 12], "slide": 0.2, "ref": "Synthwave lead", "confidence": "constructed",
                 "source": ["https://synthwavepro.com/how-to-make-synthwave-melodies-in-ableton-tips-and-tutorial/"],
                 "why": "Motif from chord tones, repeated and transposed, doubled an octave up the second time round. "
                        "Detuned saw with moderate portamento."},
    "dotted-8th": {"kind": "motif", "A": [(0, 3), (3, 3), (6, 3), (9, 3), (12, 4)], "A_contour": [0, 1, 2, 1, 0],
                   "B": [(0, 3), (3, 3), (6, 3), (9, 7)], "B_contour": [2, 1, 0, 0], "center": 67, "slide": 0.15,
                   "ref": "P2 / P3", "confidence": "constructed", "poly": "dotted-8th phrasing 3-3-3-3-4 (P2/P3)",
                   "source": ["https://www.8notes.com/school/lessons/piano/trance_pattern1.asp",
                              "https://delay.beatkey.app/dotted-eighth-delay"],
                   "why": "Notes every 3 sixteenths, cut short to realign each bar. Add a dotted-8th delay "
                          "(45000/BPM ms) for the synthwave 'waterfall'."},
    "mt-motif": {"kind": "tonic", "center": 69,
                 "bars": [([(0, 4), (4, 4), (8, 4), (12, 4)], [0, 2, 4, 3], 0),
                          ([(0, 4), (4, 4), (8, 4), (12, 4)], [0, 2, 4, 3], 3),
                          ([(0, 4), (4, 4), (8, 4), (12, 4)], [0, 2, 4, 3], 0),
                          ([(0, 4), (4, 4), (8, 8)], [0, 2, 4], 3)],
                 "ref": "MT lead", "confidence": "sourced",
                 "source": ["https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies"],
                 "why": "Chord-tone motif A-C-E-D (in A minor), sequenced up a 4th (D-F-A-G), then back."},
    "lf-motif": {"kind": "tonic", "center": 72,
                 "bars": [([(0, 2), (2, 2), (4, 4), (8, 8)], [0, -1, -2, -3], 0),
                          ([(4, 2), (6, 2), (8, 2), (12, 4)], [0, -1, -2, -3], 0),
                          ([(0, 3), (3, 1), (4, 4), (10, 6)], [0, -1, -2, -3], 0),
                          ([(2, 2), (6, 2), (8, 2), (10, 6)], [0, -1, -2, 0], 0)],
                 "ref": "LF melody", "confidence": "sourced",
                 "source": ["https://producersociety.com/how-to-make-a-lo-fi-piano-melody/",
                            "https://mysticalankar.com/blogs/blog/crafting-lofi-melodies-a-step-by-step-guide"],
                 "why": "Sparse 4-note motif stepping down from the tonic (C-B-A-G in C), repeated with rhythmic variation and rests."},
    "trap-bells": {"kind": "motif", "A": [(0, 2), (2, 2), (4, 3), (10, 2), (12, 4)], "A_contour": [2, 1, 0, -1, 0],
                   "B": [(0, 2), (2, 2), (4, 4), (12, 4)], "B_contour": [2, 1, 0, -2], "center": 77, "slide": 0.0,
                   "ref": "Trap melody", "confidence": "constructed",
                   "source": ["https://songen.app/blog/how-to-make-trap-melodies/"],
                   "why": "Bell lead in a high octave: a call in the first half of each bar, a response in the gap."},
    "chop": {"kind": "motif", "A": [(0, 1), (3, 1), (6, 2), (10, 1), (11, 2), (14, 1)],
             "A_contour": [0, 0, 1, -1, 0, 1], "B": [(0, 1), (3, 1), (6, 2), (10, 6)], "B_contour": [0, 0, 1, 0],
             "center": 69, "slide": 0.1, "ref": "FG vocal chops", "confidence": "constructed",
             "source": ["https://en.wikipedia.org/wiki/Future_garage"],
             "why": "Pitched vocal-chop style hits on chord tones, placed around the 2-step kick."},
    "house-motif": {"kind": "motif", "A": [(2, 2), (6, 1), (8, 2), (10, 2), (14, 2)], "A_contour": [0, 1, 0, -1, 0],
                    "B": [(2, 2), (6, 2), (10, 6)], "B_contour": [1, 0, 0], "center": 67, "slide": 0.1,
                    "ref": "Synthwave lead rule", "confidence": "constructed",
                    "source": ["https://synthwavepro.com/how-to-make-synthwave-melodies-in-ableton-tips-and-tutorial/"],
                    "why": "No house-specific lead in the research: a chord-tone motif with repetition (the general rule), "
                           "placed on offbeats like the stabs."},
    "acid-303-lead": {"kind": "motif", "A": [(s, 1) for s in (0, 2, 3, 6, 7, 8, 10, 11, 14)],
                      "A_contour": [0, 0, 7, 0, 2, 4, 0, 7, 4], "B": [(0, 1), (2, 1), (3, 1), (6, 1), (8, 8)],
                      "B_contour": [0, 0, 7, 2, 0], "center": 60, "slide": 0.35, "snap": False,
                      "ref": "Acid rules", "confidence": "constructed",
                      "source": ["https://www.musicradar.com/news/producers-guide-to-the-roland-tb-303-and-clones"],
                      "why": "Acid has no separate lead in the research: a second 303-style line (16ths, octave jumps with "
                             "slides) up in the lead register."},
    "dnb-motif": {"kind": "motif", "A": [(0, 6), (6, 2), (8, 4), (12, 4)], "A_contour": [0, 1, 2, 1],
                  "B": [(0, 6), (6, 2), (8, 8)], "B_contour": [2, 1, 0], "center": 71, "slide": 0.2,
                  "ref": "Synthwave lead rule", "confidence": "constructed",
                  "source": ["https://synthwavepro.com/how-to-make-synthwave-melodies-in-ableton-tips-and-tutorial/"],
                  "why": "No DnB lead in the research: long chord-tone motif (the general rule) that sits over the half-time feel."},
    "p6-5-step": {"kind": "cycle", "period": 5, "center": 69, "notes": [(0, 1, 0), (2, 1, 2), (3, 1, 4)],
                  "ref": "P6", "confidence": "constructed", "poly": "5-step lead over a 16-step bar (P6)",
                  "source": ["https://keithmcmillen.com/blog/analog-rytm-programming-with-polymeter/",
                             "https://www.productionmusiclive.com/blogs/news/hypnotic-polymetric-lead-in-analog-melodic-techno-ableton-tutorial"],
                  "why": "Hypnotic polymetric lead: a 3-note figure repeating every 5 steps. S-1 last step = 5."},
    "p8-loop-20": {"kind": "cycle", "period": 20, "center": 72, "notes": [(0, 6, 4), (8, 4, 2), (12, 8, 0)],
                   "ref": "P8", "confidence": "constructed", "poly": "5-beat loop against the 4-beat bar (P8)",
                   "source": ["https://www.musicradar.com/tuition/tech/how-to-create-a-generative-evolving-ambient-drone-sound-in-ableton-live-590880"],
                   "why": "Unsynchronised loop: repeats every 5 beats (20 steps) while the arp repeats every 7. S-1 last step = 20."},
}

# Kits. `bars` = the chord in each of the 4 bars; `roman` = the report's numerals.
# `pairing` cites the RESEARCH.md pairing matrix (section 15) or genre notes.
_M, _m = "major", "minor"
PROGRESSIONS = [
    # -------------------------------------------------------------- synthwave
    {"mode": _m, "genre": "synthwave", "ref": "SW1", "name": "Darkwave anthem, add9 pads",
     "roman": "i-bVI-bIII-bVII", "bars": ["iadd9", "bVIadd9", "bIIIadd9", "bVIIadd9"],
     "confidence": "sourced", "source": ["https://emastered.com/blog/synthwave-chord-progressions"],
     "why": "i-bVI-bIII-bVII in darkwave; add9 colour as on J-6 set 40.",
     "chords": "held", "arp": "sw-up", "bass": "sw-b1", "lead": "sw-motif",
     "pairing": "SW-B1 under sus2/add9 pads on SW1 with a 16th arp: the core outrun sound (matrix, sourced)."},
    {"mode": _m, "genre": "synthwave", "ref": "SW2", "name": "Dreamy Dystopia, sus2 pads", "bpm": 105,
     "roman": "i-bIII-bVI-bVII", "bars": ["isus2", "bIIIsus2", "bVIsus2", "bVIIsus2"],
     "confidence": "sourced", "source": ["https://emastered.com/blog/synthwave-chord-progressions",
                                         "https://unison.audio/synthwave-chord-progressions/"],
     "why": "The 'Dreamy Dystopia' loop (Timecop1983 'Lovers'), voiced as sus2 like J-6 set 34.",
     "chords": "held", "arp": "one-octave", "bass": "sw-b2", "lead": "dotted-8th",
     "pairing": "Root-pulse bass with a 1-octave 16th arp (Attack arpeggiator guide, sourced)."},
    {"mode": _m, "genre": "synthwave", "ref": "SW5", "name": "Nightcall verse", "bpm": 92,
     "roman": "i-bVII-bVI-iv", "bars": ["i", "bVII", "bVI", "iv"],
     "confidence": "sourced", "source": ["https://www.hooktheory.com/theorytab/view/kavinsky/nightcall"],
     "why": "Kavinsky 'Nightcall' verse (A minor, 92 BPM); the original has bVII over its 3rd (G/B).",
     "chords": "held", "arp": "sw-updown", "bass": "sw-b1", "lead": "sw-motif",
     "pairing": "Octave 8ths are the Kavinsky bass style (imseankim, sourced)."},
    {"mode": _m, "genre": "synthwave", "ref": "SW9", "name": "Darksynth, harmonic-minor V", "bpm": 114,
     "roman": "i-bVII-bVI-V", "bars": ["i", "bVII", "bVI", "V"], "scale": "harmonic",
     "confidence": "sourced", "source": ["https://emastered.com/blog/synthwave-chord-progressions"],
     "why": "Darkwave i-bVII-bVI-V with the harmonic-minor major V.",
     "chords": "held", "arp": "sw-up", "bass": "sw-b4", "lead": "sw-motif",
     "pairing": "Darksynth: SW9 + gallop bass at 110-118 (common practice)."},
    {"mode": _M, "genre": "synthwave", "ref": "SW4", "name": "Timecop1983 rising bass",
     "roman": "IV-V-vi-I", "bars": ["IVadd9", "Vadd9", "viadd9", "Iadd9"],
     "confidence": "sourced", "source": ["https://www.synthwavedojo.com/blog/timecop1983-chord-progressions-demystified"],
     "why": "IV-V-vi-I from Timecop1983 'Come Back' / 'Lovers', with a rising bass.",
     "chords": "held", "arp": "sw-up", "bass": "sw-b1", "lead": "sw-motif",
     "pairing": "SW-B1 under add9 pads on SW4 (matrix, sourced)."},
    {"mode": _M, "genre": "synthwave", "ref": "SW3", "name": "Neon Nights",
     "roman": "I-V-vi-IV", "bars": ["I", "V", "vi", "IV"],
     "confidence": "sourced", "source": ["https://emastered.com/blog/synthwave-chord-progressions"],
     "why": "'Neon Nights' I-V-vi-IV.",
     "chords": "held", "arp": "sw-updown", "bass": "sw-b2", "lead": "dotted-8th",
     "pairing": "Root 16ths with a 16th arp on top (matrix, sourced)."},
    {"mode": _M, "genre": "synthwave", "ref": "SW7", "name": "1-6-4-5",
     "roman": "I-vi-IV-V", "bars": ["I", "vi", "IV", "V"],
     "confidence": "sourced", "source": ["https://www.orpheusaudioacademy.com/synthwave-chords/"],
     "why": "The '1-6-4-5' synthwave progression.",
     "chords": "held", "arp": "sw-up", "bass": "sw-b3", "lead": "sw-motif",
     "pairing": "16th octave bass (1-octave arp on one note) with an up arp (Attack, constructed)."},
    # -------------------------------------------------------------- acid
    {"mode": _m, "genre": "acid", "ref": "AC1", "name": "Acid Tracks pedal", "bpm": 124,
     "roman": "i (pedal)", "bars": ["i7", "i7", "i7", "i7"],
     "confidence": "sourced", "source": ["https://djjondent.blogspot.com/2020/04/famous-303-bassline-patterns-page-1.html"],
     "why": "One root, no chord changes: Phuture looped one pattern for ~12 minutes.",
     "chords": "single-stab", "arp": "j6-up-16", "bass": "ac-b1", "lead": "acid-303-lead",
     "pairing": "303 with no chords or a single stab (Attack, Armando acid house, sourced)."},
    {"mode": _m, "genre": "acid", "ref": "AC2", "name": "Phrygian bII acid", "bpm": 135,
     "roman": "i-bII-i", "bars": ["i", "bII", "i", "i"], "scale": "phrygian",
     "confidence": "sourced", "source": ["https://musiversal.com/blog/master-phrygian-mode"],
     "why": "The Phrygian i-bII-i move.",
     "chords": "single-stab", "arp": "j6-up-16", "bass": "ac-b4", "lead": "acid-303-lead",
     "pairing": "Acid techno 130-140 with Phrygian bII under AC-B4 (common practice)."},
    {"mode": _m, "genre": "acid", "ref": "AC1", "name": "Woozy 13-step acid", "bpm": 132,
     "roman": "i (pedal)", "bars": ["i", "i", "i", "i"],
     "confidence": "sourced", "source": ["https://djjondent.blogspot.com/2020/04/famous-303-bassline-patterns-page-1.html"],
     "why": "Pedal on one root so the odd-length 303 loop can drift freely.",
     "chords": "single-stab", "arp": "j6-up-16", "bass": "ac-b5-13", "lead": "acid-303-lead",
     "pairing": "303 pedal with a single stab (Attack, sourced); odd length from MusicRadar."},
    {"mode": _m, "genre": "acid", "ref": "AC3", "name": "Phrygian with v dim, lanes", "bpm": 135,
     "roman": "i-v°-bII-i", "bars": ["i", "v°", "bII", "i"], "scale": "phrygian",
     "confidence": "sourced", "source": ["https://musiversal.com/blog/master-phrygian-mode"],
     "why": "i-v°-bII-i in Phrygian.",
     "chords": "single-stab", "arp": "j6-up-16", "bass": "ac-b6-lanes", "lead": "acid-303-lead",
     "pairing": "303 lines under sparse stabs (Attack, sourced); lane polymeter from mind-flux."},
    {"mode": _m, "genre": "acid", "ref": "AC4", "name": "Chicago chromatic m7 stab", "bpm": 124,
     "roman": "i7-biii7-iv7", "bars": ["i7", "biii7", "iv7", "biii7"],
     "confidence": "sourced", "source": ["https://www.musicradar.com/how-to/how-to-create-classic-chicago-house-spread-piano-chords"],
     "why": "One m7 shape moved chromatically (Cm7 > Ebm7 > Fm7), like a pitched sampled chord.",
     "chords": "offbeat", "arp": "j6-up-16", "bass": "ac-b4", "lead": "acid-303-lead",
     "pairing": "AC4 chromatic stab over a 303 line (matrix, sourced)."},
    {"mode": _m, "genre": "acid", "ref": "AC5", "name": "Two-chord acid vamp", "bpm": 128,
     "roman": "i-bVII", "bars": ["i", "bVII", "i", "bVII"],
     "confidence": "common-practice", "source": [],
     "why": "i-bVII two-chord vamp.",
     "chords": "single-stab", "arp": "j6-up-16", "bass": "ac-b2", "lead": "acid-303-lead",
     "pairing": "303 two-note line under a single stab (Attack pairing, sourced)."},
    # -------------------------------------------------------------- deep house
    {"mode": _m, "genre": "deephouse", "ref": "DH1", "name": "m7 two-bar vamp",
     "roman": "im7-ivm7", "bars": ["i9", "i9", "iv7", "iv7"],
     "confidence": "sourced", "source": ["https://beatkey.app/how-to-make-deep-house-music"],
     "why": "im7 for 2 bars, ivm7 for 2 bars; 9th added as the voicing guide suggests.",
     "chords": "held", "arp": "j6-updown-8", "bass": "dh-b1", "lead": "house-motif",
     "pairing": "Static m7/m9 pads with the offbeat bass (matrix, sourced)."},
    {"mode": _m, "genre": "deephouse", "ref": "DH3", "name": "Dorian vamp", "bpm": 122,
     "roman": "im7-IV7", "bars": ["i7", "IV7", "i7", "IV7"], "scale": "dorian",
     "confidence": "sourced", "source": ["https://beatkey.app/how-to-make-deep-house-music"],
     "why": "Dorian im7-IV7 (Am7-D7): the raised 6th.",
     "chords": "held", "arp": "j6-updown-8", "bass": "dh-b3", "lead": "house-motif",
     "pairing": "Static pads with the tresillo bass (matrix, sourced)."},
    {"mode": _m, "genre": "deephouse", "ref": "DH6", "name": "Kerri Chandler parallel m7s", "bpm": 122,
     "roman": "i7-ii7-#iv7-bvii7", "bars": ["i7", "ii7", "#iv7", "bvii7"],
     "confidence": "sourced", "source": ["https://www.attackmagazine.com/technique/passing-notes/kerri-chandler-chords/"],
     "why": "'Bar a Thym' parallel m7s (G#m7-A#m7-Dm7-F#m7).",
     "chords": "held", "arp": "j6-updown-8", "bass": "dh-b4", "lead": "house-motif",
     "pairing": "Moving parallel chords over a tonic pedal (Attack, Kerri Chandler part 2, sourced)."},
    {"mode": _m, "genre": "deephouse", "ref": "DH7", "name": "Can You Feel It",
     "roman": "i-bVI7-bVII-I7", "bars": ["i", "bVI7", "bVII", "I7"],
     "confidence": "sourced", "source": ["https://www.hooktheory.com/theorytab/view/mr-fingers/can-you-feel-it",
                                         "https://chordify.net/chords/mr-fingers-songs/can-you-feel-it-4-chords"],
     "why": "Mr Fingers 'Can You Feel It' (G#m-E7-F#-G#7), organ held like strings.",
     "chords": "held", "arp": "j6-updown-8", "bass": "dh-b2", "lead": "house-motif",
     "pairing": "Long held organ chords (gearspace, sourced) over a syncopated root/octave bass (constructed)."},
    {"mode": _M, "genre": "deephouse", "ref": "DH2", "name": "ii-V-I at 120",
     "roman": "ii7-V7-Imaj7", "bars": ["ii7", "V7", "Imaj7", "Imaj7"],
     "confidence": "sourced", "source": ["https://beatkey.app/how-to-make-deep-house-music"],
     "why": "ii7-V7-Imaj7 at ~120 BPM.",
     "chords": "held", "arp": "j6-updown-8", "bass": "dh-b1", "lead": "house-motif",
     "pairing": "Held 7th pads with the offbeat bass (matrix, sourced)."},
    {"mode": _M, "genre": "deephouse", "ref": "DH4", "name": "III-vi-ii-V turnaround",
     "roman": "III7-vi7-ii7-V7", "bars": ["III7", "vi7", "ii7", "V7"],
     "confidence": "sourced", "source": ["https://unison.audio/house-chord-progressions/"],
     "why": "E7-Am7-Dm7-G7 in C: a secondary-dominant circle.",
     "chords": "held", "arp": "j6-updown-8", "bass": "dh-b2", "lead": "house-motif",
     "pairing": "Held 7ths with the syncopated root/octave bass (edmprod rule, constructed)."},
    # -------------------------------------------------------------- chicago house
    {"mode": _m, "genre": "chicago", "ref": "CH5", "name": "Minor with borrowed majors",
     "roman": "i-bVI-bVII", "bars": ["i7", "bVI", "bVII", "bVII"],
     "confidence": "constructed", "source": ["https://mixedinkey.com/captain-plugins/wiki/house-music-chords/"],
     "why": "Minor key with major chords borrowed in (the example chords are the researcher's).",
     "chords": "offbeat", "arp": "j6-up-16", "bass": "ch-b1", "lead": "house-motif",
     "pairing": "Offbeat stabs with the octave-jump bass (matrix: MusicRadar spread piano, samplefocus)."},
    {"mode": _M, "genre": "chicago", "ref": "CH1", "name": "I-IV-V-vi",
     "roman": "I-IV-V-vi", "bars": ["I", "IV", "V", "vi7"],
     "confidence": "sourced", "source": ["https://mixedinkey.com/captain-plugins/wiki/house-music-chords/"],
     "why": "The most common house chord family.",
     "chords": "syncopated", "arp": "j6-up-16", "bass": "ch-b1", "lead": "house-motif",
     "pairing": "Syncopated stabs with the octave-jump bass (matrix)."},
    # -------------------------------------------------------------- lo-fi
    {"mode": _m, "genre": "lofi", "ref": "LF7", "name": "Half-diminished ii-V-i",
     "roman": "iiø7-V7-i7", "bars": ["iiø7", "V7", "i7", "i7"], "scale": "harmonic",
     "confidence": "common-practice", "source": ["https://blog.landr.com/lofi-chord-progressions/"],
     "why": "m7b5 colour for darker chill (LANDR); the ii-V-i example is common practice.",
     "chords": "held", "arp": "j6-updown-8", "bass": "lf-b1", "lead": "lf-motif",
     "pairing": "Held 7ths with root-5th bass and swing (matrix: flat.io, lofimusicacademy)."},
    {"mode": _M, "genre": "lofi", "ref": "LF2", "name": "Circling",
     "roman": "Imaj7-vi7-ii7-V7", "bars": ["Imaj7", "vi7", "ii7", "V7"],
     "confidence": "sourced", "source": ["https://blog.flat.io/lofi-chord-progressions/"],
     "why": "Cmaj7-Am7-Dm7-G7, the 'circling' loop.",
     "chords": "held", "arp": "j6-updown-8", "bass": "lf-b2", "lead": "lf-motif",
     "pairing": "Held 7ths with root/ghost-octave bass (matrix)."},
    {"mode": _M, "genre": "lofi", "ref": "LF4", "name": "Descending 7ths",
     "roman": "IVmaj7-iii7-ii7-Imaj7", "bars": ["IVmaj7", "iii7", "ii7", "Imaj7"],
     "confidence": "sourced", "source": ["https://www.chordoo.com/blog/lofi-chord-progressions-for-chill-beats"],
     "why": "Fmaj7-Em7-Dm7-Cmaj7 stepping down.",
     "chords": "held", "arp": "j6-updown-8", "bass": "lf-b3", "lead": "lf-motif",
     "pairing": "Walking line that steps to each next root (jazz source; pairing constructed)."},
    {"mode": _M, "genre": "lofi", "ref": "LF6", "name": "maj9 colour", "bpm": 78,
     "roman": "Imaj9-IVmaj13", "bars": ["Imaj9", "Imaj9", "IVmaj13", "IVmaj13"],
     "confidence": "sourced", "source": ["https://blog.landr.com/lofi-chord-progressions/"],
     "why": "Ebmaj9-Abmaj13 in Eb: all-maj9 colour, two bars each.",
     "chords": "held", "arp": "j6-updown-8", "bass": "lf-b1", "lead": "lf-motif",
     "pairing": "Held chords with root-5th bass (matrix)."},
    {"mode": _M, "genre": "lofi", "ref": "LF1", "name": "ii-V-I, 3/4 bass drift", "bpm": 85,
     "roman": "ii7-V7-Imaj7", "bars": ["ii7", "V7", "Imaj7", "Imaj7"],
     "confidence": "sourced", "source": ["https://blog.flat.io/lofi-chord-progressions/"],
     "why": "Dm7-G7-Cmaj7.",
     "chords": "held", "arp": "j6-updown-8", "bass": "lf-b2-12", "lead": "lf-motif",
     "pairing": "Held 7ths with the root/ghost bass (matrix), folded into 3/4 (P11)."},
    # -------------------------------------------------------------- Berlin techno
    {"mode": _m, "genre": "techno", "ref": "DT1", "name": "Phrygian bII stabs",
     "roman": "i-bII-i", "bars": ["i", "bII", "i", "i"], "scale": "phrygian",
     "confidence": "sourced", "source": ["https://musiversal.com/blog/master-phrygian-mode"],
     "why": "Em-F-Em: the Phrygian half-step for dark techno.",
     "chords": "offbeat", "arp": "p6-6-step", "bass": "tb-1-phrygian", "lead": "p6-5-step",
     "pairing": "Offbeat stabs over rolling 16ths (matrix: Attack warehouse bass)."},
    {"mode": _m, "genre": "techno", "ref": "DT3", "name": "Root + b9 stab", "bpm": 134,
     "roman": "i5b9", "bars": ["i5b9", "i5b9", "i5b9", "i5b9"], "scale": "phrygian",
     "confidence": "sourced", "source": ["https://splice.com/blog/how-to-make-basslines/"],
     "why": "Root+b2 stab on the offbeats; voiced as J-6 set 57's C5b9 (root, 5th, b9). Attribution approximate.",
     "chords": "offbeat", "arp": "p6-6-step", "bass": "tb-5", "lead": "p6-5-step",
     "pairing": "One stab chord over rolling bass (matrix)."},
    {"mode": _m, "genre": "techno", "ref": "DT4", "name": "Parallel m7 stabs", "bpm": 134,
     "roman": "i7-biii7-iv7", "bars": ["i7", "biii7", "iv7", "i7"],
     "confidence": "sourced", "source": ["https://www.attackmagazine.com/technique/tutorials/the-theory-of-techno-parallel-chord-stabs/"],
     "why": "Keep the m7 shape and transpose it (Em7 > Gm7 > Am7); J-6 set 20 does this on every key.",
     "chords": "offbeat", "arp": "p6-6-step", "bass": "tb-1-octave", "lead": "p6-5-step",
     "pairing": "Parallel stabs over rolling 16ths (matrix)."},
    {"mode": _m, "genre": "techno", "ref": "DT5", "name": "Dub techno m7", "bpm": 126,
     "roman": "i7", "bars": ["i7", "i7", "i7", "i7"],
     "confidence": "sourced", "source": ["https://www.transmissionsamples.com/tutorials/sound-design/dub-chords-sound-design",
                                         "https://www.studiobrootle.com/dub-techno-tutorial-ableton/"],
     "why": "One m7 stab through a dotted delay (set it to 45000/BPM ms on the OP-XY).",
     "chords": "offbeat", "arp": "p6-6-step", "bass": "dh-b1", "lead": "p6-5-step",
     "pairing": "Dub stab over the offbeat 8th (TB-2, sourced)."},
    {"mode": _m, "genre": "techno", "ref": "DT6", "name": "Chromatic minor line", "bpm": 130,
     "roman": "i-imaj7-i7-i6", "bars": ["i", "imaj7", "i7", "i6"],
     "confidence": "sourced", "source": ["https://motifkit.com/dark-chord-progressions/"],
     "why": "The dark cliché: a chromatic line falling inside one minor chord. Search summary.",
     "chords": "offbeat", "arp": "j6-up-16", "bass": "tb-3", "lead": "p6-5-step",
     "pairing": "One chord with EBM all-16ths bass (TB-3, constructed pairing)."},
    # -------------------------------------------------------------- melodic techno
    {"mode": _m, "genre": "melodictechno", "ref": "MT2", "name": "i-bVI, two bars each",
     "roman": "i-bVI", "bars": ["i", "i", "bVI", "bVI"],
     "confidence": "sourced", "source": ["https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies"],
     "why": "Am-F, changing every 2 bars.",
     "chords": "held", "arp": "mt-pluck", "bass": "mt-offbeat-ghost", "lead": "mt-motif",
     "pairing": "Offbeat 8th + ghost 16th under a 16th pluck arp (matrix, myloops)."},
    {"mode": _m, "genre": "melodictechno", "ref": "MT1", "name": "Afterlife loop", "bpm": 124,
     "roman": "i-bVI-bIII-bVII", "bars": ["i", "bVI", "bIII", "bVII"],
     "confidence": "sourced", "source": ["https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies"],
     "why": "'The sound of Tale Of Us, Anyma, Afterlife' (one chord per bar here; the genre usually holds 2-4).",
     "chords": "held", "arp": "p1-3-over-4", "bass": "mt-tresillo-10", "lead": "dotted-8th",
     "pairing": "Tresillo-backbone bass, 3-against-4 arp (matrix + P1)."},
    {"mode": _m, "genre": "melodictechno", "ref": "MT5", "name": "Dorian i-IV", "bpm": 122,
     "roman": "i-IV", "bars": ["i", "i", "IV", "IV"], "scale": "dorian",
     "confidence": "constructed", "source": ["https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies"],
     "why": "Dorian's raised 6th as a major IV (Am-D); example constructed from the Dorian mention.",
     "chords": "held", "arp": "p2-33334", "bass": "mt-offbeat-ghost", "lead": "mt-motif",
     "pairing": "Offbeat + ghost bass (matrix) with a trance 3-3-3-3-4 arp (P2)."},
    {"mode": _m, "genre": "melodictechno", "ref": "MT4", "name": "i-iv-bVII",
     "roman": "i-iv-bVII", "bars": ["i", "i", "iv", "bVII"],
     "confidence": "sourced", "source": ["https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies"],
     "why": "Am-Dm-G.",
     "chords": "held", "arp": "mt-pluck", "bass": "mt-offbeat-ghost", "lead": "mt-motif",
     "pairing": "Offbeat + ghost bass under a 16th pluck arp (matrix)."},
    # -------------------------------------------------------------- UK garage
    {"mode": _m, "genre": "ukg", "ref": "UK1", "name": "Crazy Love i-v", "bpm": 134,
     "roman": "i-v", "bars": ["i9", "v7", "i9", "v7"],
     "confidence": "sourced", "source": ["https://chordu.com/chords-tabs-uk-garage-mj-cole-crazy-love-id_4QMA2WGvtmQ"],
     "why": "MJ Cole 'Crazy Love' centres on Dm-Am-Dm at 134 BPM; m9/m7 colour per vixsound.",
     "chords": "follow-bass", "arp": "j6-updown-8", "bass": "uk-b1", "lead": "chop",
     "pairing": "Stabs in the bass rhythm over a skippy swung bass (matrix: TPS UKG guide)."},
    {"mode": _m, "genre": "ukg", "ref": "UK2", "name": "m9 vamp",
     "roman": "im9-ivm9", "bars": ["i9", "i9", "iv9", "iv9"],
     "confidence": "common-practice", "source": [],
     "why": "Cm9-Fm9.",
     "chords": "follow-bass", "arp": "j6-updown-8", "bass": "uk-b2", "lead": "chop",
     "pairing": "Stabs follow the long 'wub' bass (matrix: studio brootle)."},
    {"mode": _m, "genre": "ukg", "ref": "UK3", "name": "Descending maj7s", "bpm": 130,
     "roman": "im7-bVIImaj7-bVImaj7", "bars": ["i7", "bVIImaj7", "bVImaj7", "bVImaj7"],
     "confidence": "common-practice", "source": [],
     "why": "Am7-Gmaj7-Fmaj7.",
     "chords": "follow-bass", "arp": "j6-updown-8", "bass": "uk-b3", "lead": "chop",
     "pairing": "Organ bounce bass with stabs in the same rhythm (common practice + TPS rule)."},
    # -------------------------------------------------------------- DnB
    {"mode": _m, "genre": "dnb", "ref": "DB1", "name": "Liquid 9ths",
     "roman": "i9-iv7-bVImaj9-bVIImaj7", "bars": ["i9", "iv7", "bVImaj9", "bVIImaj7"],
     "confidence": "sourced", "source": ["https://beatkey.app/how-to-make-liquid-dnb-music"],
     "why": "Dm9-Gm7-Bbmaj9-Cmaj7. Search summary.",
     "chords": "held", "arp": "j6-updown-8", "bass": "db-b1", "lead": "dnb-motif",
     "pairing": "Extended chords over a sub on every kick (matrix: MusicRadar, edmprod)."},
    {"mode": _m, "genre": "dnb", "ref": "DB2", "name": "Shared shape, bass moves", "bpm": 172,
     "roman": "i9 / bIIImaj7 (shared)", "bars": ["bIIImaj7", "bIIImaj7", "bIIImaj7", "bIIImaj7"],
     "confidence": "sourced", "source": ["https://www.musicradar.com/how-to/how-to-create-uplifting-liquid-dnb-chords"],
     "why": "Am9 and Cmaj7 share C E G B: hold that shape and let the bass (A C E A F E) change the chord.",
     "chords": "held", "arp": "p1-3-over-4", "bass": "db-p7", "lead": "dnb-motif",
     "pairing": "The MusicRadar liquid example itself: one shape, bass every three 8ths."},
    {"mode": _m, "genre": "dnb", "ref": "DB3", "name": "i-iv-bVI reese", "bpm": 170,
     "roman": "i-iv-bVI", "bars": ["i9", "iv7", "bVImaj7", "bVImaj7"],
     "confidence": "sourced", "source": ["https://www.youtube.com/watch?v=TmAVC96Zg4w"],
     "why": "i-iv-bVI.",
     "chords": "held", "arp": "j6-updown-8", "bass": "db-b2", "lead": "dnb-motif",
     "pairing": "Reese bass under extended chords (matrix)."},
    # -------------------------------------------------------------- trap
    {"mode": _m, "genre": "trap", "ref": "TR1", "name": "i-bVI-bVII",
     "roman": "i-bVI-bVII", "bars": ["i", "bVI", "bVII", "bVII"],
     "confidence": "sourced", "source": ["https://unison.audio/trap-chord-progressions/"],
     "why": "Cm-Ab-Bb.",
     "chords": "held", "arp": "j6-updown-8", "bass": "808-1", "lead": "trap-bells",
     "pairing": "Sparse minor chords, 808 following the kick with slides, bells on top (matrix: songen, chordmap)."},
    {"mode": _m, "genre": "trap", "ref": "TR3", "name": "Emotional trap", "bpm": 150,
     "roman": "i-v-bVI-bVII", "bars": ["i", "v", "bVI", "bVII"],
     "confidence": "sourced", "source": ["https://www.drumloopai.com/blog/trap-chord-progressions/"],
     "why": "Cm-Gm-Ab-Bb. Search summary.",
     "chords": "held", "arp": "j6-updown-8", "bass": "808-2", "lead": "trap-bells",
     "pairing": "808 gliding to the b3 and back (matrix)."},
    {"mode": _m, "genre": "trap", "ref": "TR6", "name": "Bad Guy", "bpm": 135,
     "roman": "i-iv-V7", "bars": ["i", "iv", "V7", "V7"], "scale": "harmonic",
     "confidence": "sourced", "source": ["https://emastered.com/blog/dark-chord-progressions"],
     "why": "Billie Eilish 'Bad Guy': Gm-Cm-D7 at 135 BPM. Search summary.",
     "chords": "held", "arp": "j6-updown-8", "bass": "808-1", "lead": "trap-bells",
     "pairing": "808 on the kick, octave slide (matrix)."},
    # -------------------------------------------------------------- ambient / cinematic
    {"mode": _m, "genre": "ambient", "ref": "CI1", "name": "Inception shorthand",
     "roman": "i-bVI-bIII-bVII", "bars": ["iadd9", "bVImaj7", "bIIIadd9", "bVIIsus2"],
     "confidence": "sourced", "source": ["https://www.chordgen.org/chords/cinematic"],
     "why": "Zimmer 'Inception' shorthand with maj7/add9/sus2 open colours.",
     "chords": "held", "arp": "p8-loop-28", "bass": "am-b1", "lead": "p8-loop-20",
     "pairing": "Sus/maj7 chords over a drone pedal (matrix: chordgen ambient)."},
    {"mode": _m, "genre": "ambient", "ref": "CI4", "name": "Phrygian dread", "bpm": 64,
     "roman": "i-bII", "bars": ["i", "bIImaj7", "i", "bIImaj7"], "scale": "phrygian",
     "confidence": "sourced", "source": ["https://www.chordgen.org/chords/cinematic"],
     "why": "Phrygian i-bII for dread.",
     "chords": "held", "arp": "p8-loop-28", "bass": "am-b1", "lead": "p8-loop-20",
     "pairing": "Pedal tone held under changing chords (CI6 / AM-B1, sourced)."},
    {"mode": _M, "genre": "ambient", "ref": "CI3", "name": "Lydian wonder",
     "roman": "I-II", "bars": ["Imaj7", "II", "Imaj7", "II"], "scale": "lydian",
     "confidence": "sourced", "source": ["https://www.chordgen.org/chords/cinematic"],
     "why": "Lydian I-II (C-D/C): the raised 4th sounds like wonder. J-6 set 23 is all M9#11.",
     "chords": "held", "arp": "p8-loop-28", "bass": "am-b1", "lead": "p8-loop-20",
     "pairing": "Drone under the vamp (matrix: chordgen ambient)."},
    # -------------------------------------------------------------- future garage / chillwave
    {"mode": _m, "genre": "futuregarage", "ref": "FG1", "name": "m7 to maj7",
     "roman": "im7-bVImaj7", "bars": ["i7", "i7", "bVImaj7", "bVImaj7"],
     "confidence": "common-practice", "source": [],
     "why": "Am7-Fmaj7 (4 bars each in the original idea; 2 here).",
     "chords": "held", "arp": "j6-updown-8", "bass": "fg-b1", "lead": "chop",
     "pairing": "Slow pads over a long sub on the 2-step kicks (matrix: Wikipedia future garage)."},
    {"mode": _m, "genre": "futuregarage", "ref": "FG2", "name": "sus2 drift",
     "roman": "isus2-bVIsus2-bVIIsus2", "bars": ["isus2", "bVIsus2", "bVIIsus2", "bVIIsus2"],
     "confidence": "common-practice", "source": [],
     "why": "Asus2-Fsus2-Gsus2; J-6 set 34 has all of these chords.",
     "chords": "held", "arp": "j6-updown-8", "bass": "fg-b1", "lead": "chop",
     "pairing": "sus2 pads over the 2-step sub (matrix)."},
    {"mode": _M, "genre": "futuregarage", "ref": "CW1", "name": "Chillwave maj7 loop", "bpm": 95,
     "roman": "Imaj7-IVmaj7", "bars": ["Imaj7", "IVmaj7", "Imaj7", "IVmaj7"],
     "confidence": "common-practice", "source": [],
     "why": "Imaj7-IVmaj7 at chillwave tempo (80-110; vibesdj).",
     "chords": "held", "arp": "sw-updown", "bass": "sw-b1", "lead": "dotted-8th",
     "pairing": "Chillwave borrows synthwave sounds (common practice): octave bass and up/down arp."},
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
MAJOR = [0, 2, 4, 5, 7, 9, 11]

SCALES = {
    "major": MAJOR, "minor": [0, 2, 3, 5, 7, 8, 10], "harmonic": [0, 2, 3, 5, 7, 8, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11], "mixolydian": [0, 2, 4, 5, 7, 9, 10],
}

# Conventional spelling for each tonic (fewest accidentals).
TONICS = {
    "major": ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"],
    "minor": ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"],
}

QUALITY = {  # intervals, chord-symbol suffix. 9/11/13 chords drop the 5th (4 voices).
    "maj": ([0, 4, 7], ""), "min": ([0, 3, 7], "m"), "dim": ([0, 3, 6], "dim"),
    "sus2": ([0, 2, 7], "sus2"), "sus4": ([0, 5, 7], "sus4"),
    "add9": ([0, 4, 7, 14], "add9"), "madd9": ([0, 3, 7, 14], "m(add9)"),
    "6": ([0, 4, 7, 9], "6"), "m6": ([0, 3, 7, 9], "m6"),
    "7": ([0, 4, 7, 10], "7"), "maj7": ([0, 4, 7, 11], "maj7"), "m7": ([0, 3, 7, 10], "m7"),
    "mM7": ([0, 3, 7, 11], "m(maj7)"), "m7b5": ([0, 3, 6, 10], "m7b5"), "dim7": ([0, 3, 6, 9], "dim7"),
    "9": ([0, 4, 10, 14], "9"), "maj9": ([0, 4, 11, 14], "maj9"), "m9": ([0, 3, 10, 14], "m9"),
    "m11": ([0, 3, 10, 17], "m11"), "maj13": ([0, 4, 11, 21], "maj13"), "5b9": ([0, 7, 13], "5(b9)"),
}
UPPER_SUFFIX = {"": "maj", "7": "7", "maj7": "maj7", "9": "9", "maj9": "maj9", "maj13": "maj13", "6": "6",
                "sus2": "sus2", "sus4": "sus4", "add9": "add9", "5b9": "5b9"}
LOWER_SUFFIX = {"": "min", "7": "m7", "m7": "m7", "9": "m9", "m9": "m9", "11": "m11", "6": "m6",
                "add9": "madd9", "maj7": "mM7", "sus2": "sus2", "5b9": "5b9",
                "ø7": "m7b5", "ø": "m7b5", "°": "dim", "°7": "dim7"}
NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII"]
ROMAN_RE = re.compile(r"^([b#]?)(VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)(.*)$")


def parse_roman(roman):
    """'bVII' -> (degree index, semitones above tonic, quality). Relative to major."""
    m = ROMAN_RE.match(roman)
    if not m:
        raise SystemExit(f"can't parse roman numeral {roman!r}")
    acc, num, suffix = m.groups()
    deg = NUMERALS.index(num.upper())
    table = UPPER_SUFFIX if num.isupper() else LOWER_SUFFIX
    if suffix not in table:
        raise SystemExit(f"unknown chord suffix {suffix!r} in {roman!r}")
    semis = MAJOR[deg] + {"": 0, "b": -1, "#": 1}[acc]
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
    s = s.replace("#", "s").replace("ø7", "m7b5").replace("ø", "m7b5").replace("°", "dim")
    s = re.sub(r"[^A-Za-z0-9-]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


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
            if v[-1] - v[0] > (14 if len(v) == 3 else 16) + (0 if strict else 7):
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
    return sorted(s | set(chord_pcs))   # never drop a chord tone (e.g. root + b9)


# ---------------------------------------------------------------------------
# Parts. Mono parts are lists of events: {start, len (in steps), note, vel, slide}
# ---------------------------------------------------------------------------

def vel_of(acc):
    return {1: ACC, 0: NORM, -1: GHOST, True: ACC, False: NORM}[acc]


def E(start, length, note, acc=0, slide=False):
    return {"start": start, "len": length, "note": note, "vel": vel_of(acc), "slide": bool(slide)}


def gate(length):
    return int(STEP * 0.55) if length == 1 else length * STEP - 30


def chords_part(voicings, rhythm, bass_events):
    spec = CHORD_RHYTHMS[rhythm]
    notes = []
    for bar, v in enumerate(voicings):
        if spec.get("follow"):
            hits = [(e["start"] - bar * 16, min(e["len"], 2)) for e in bass_events
                    if bar * 16 <= e["start"] < bar * 16 + 16]
        else:
            hits = spec["hits"]
        for i, (st, ln) in enumerate(hits):
            vel = 96 if i == 0 else 84
            for m in v:
                notes.append((bar * BAR + st * STEP, gate(ln), m, vel))
    return notes


ARP_ORDER = {
    "up": lambda L: list(range(L)),
    "down": lambda L: list(range(L - 1, -1, -1)),
    "updown": lambda L: list(range(L)) + list(range(L - 2, 0, -1)),
}


def arp_pool(kind, voicing, chord):
    if kind == "voicing":
        return sorted(voicing) + [min(voicing) + 12]
    r = min(m for m in range(48, 60) if m % 12 == chord["root_pc"])
    if kind == "octave":
        return [r, r + 12]
    tones = [r + i for i in QUALITY[chord["quality"]][0] if i < 12][:3]
    return tones + [r + 12]


def arp_part(voicings, chords, name):
    spec = ARPS[name]
    period = spec.get("period", 16)
    ln = spec.get("len", 1)
    ev, k = [], 0
    starts = [c + h for c in range(0, STEPS, period) for h in spec["hits"] if c + h < STEPS]
    for s in starts:
        bar = s // 16
        pool = arp_pool(spec["pool"], voicings[bar], chords[bar])
        seq = ARP_ORDER[spec["order"]](len(pool))
        if period == 16 and s % 16 == spec["hits"][0]:
            k = 0                                   # 16-step arps restart on each chord
        idx = k % len(seq)
        acc = (s % 4 == 0) if spec.get("accent", "beat") == "beat" else (s % period == spec["hits"][0])
        ev.append(E(s, min(ln, STEPS - s), pool[seq[idx]], int(acc)))
        k += 1
    return ev


def resolve(off, root, tonic_note, nxt_root, prev, float_=False):
    lo, hi = RANGES["bass"]
    if off == "a":      # half-step approach into the next bar's root
        targets = (nxt_root, nxt_root + 12) if float_ else (nxt_root,)
        cands = [t + d for t in targets for d in (-1, 1)]
        cands = [x for x in cands if lo <= x <= hi and x != prev]
        return min(cands, key=lambda x: (abs(x - (prev if prev is not None else x)), x))
    n = tonic_note + int(off[1:]) if isinstance(off, str) else root + off
    while n > hi:
        n -= 12
    while n < lo:
        n += 12
    return n


def bass_part(chords, tonic_note, name):
    spec = BASSES[name]
    n = len(chords)
    roots = [24 + c["root_pc"] for c in chords]
    ev = []
    if "lanes" in spec:            # polymetric note / accent / slide lanes
        L = spec["lanes"]
        for s in range(STEPS):
            bar = s // 16
            note = resolve(L["notes"][s % len(L["notes"])], roots[bar], tonic_note, roots[(bar + 1) % n], None)
            ev.append(E(s, 1, note, L["accent"][s % len(L["accent"])], L["slide"][s % len(L["slide"])]))
        return ev
    if "cell" in spec:             # a cell repeating every `period` steps (drifts if period doesn't divide 16)
        for start in range(0, STEPS, spec["period"]):
            for off, sym, ln, acc, sl in spec["cell"]:
                s = start + off
                if s >= STEPS:
                    continue
                bar = s // 16
                note = resolve(sym, roots[bar], tonic_note, roots[(bar + 1) % n], ev[-1]["note"] if ev else None)
                ev.append(E(s, min(ln, STEPS - s), note, acc, sl))
        return ev
    fl = spec.get("float", False)
    lo, hi = RANGES["bass"]
    prev = None
    alts_all = spec["grid"] if isinstance(spec["grid"][0], list) else [spec["grid"]]
    for bar in range(n):
        nxt = roots[(bar + 1) % n]
        best = None
        for tpl in alts_all:
            for r in ((roots[bar], roots[bar] + 12) if fl else (roots[bar],)):
                p, notes = prev, []
                for st, off, ln, acc, sl in tpl:
                    p = resolve(off, r, tonic_note, nxt, p, fl)
                    if fl and not lo <= r + (off if isinstance(off, int) else 0) <= hi:
                        p = None
                        break
                    notes.append(E(bar * 16 + st, ln, p, acc, sl))
                if p is None:
                    continue
                land = min(abs(notes[-1]["note"] - t) for t in ((nxt, nxt + 12) if fl else (nxt,)))
                score = land + (abs(notes[0]["note"] - prev) if prev else 0)
                if best is None or score < best[0]:
                    best = (score, notes)
        if best is None:
            raise SystemExit(f"bass style {name}: no variant fits the range in bar {bar + 1}")
        ev += best[1]
        prev = ev[-1]["note"]
    if spec.get("tie"):            # one note tied across the whole pattern
        ev = [dict(ev[0], len=STEPS, slide=False)] if len({e["note"] for e in ev}) == 1 else ev
    return ev


def fold(m, lo=52, hi=84):
    while m > hi:
        m -= 12
    while m < lo:
        m += 12
    return m


def lead_part(name, key_pcs, tonic, chords, rng):
    spec = LEADS[name]
    kind = spec["kind"]
    ev = []
    if kind in ("tonic", "cycle"):
        snotes = [m for m in range(36, 100) if m % 12 in key_pcs]
        t = min((m for m in snotes if m % 12 == tonic), key=lambda m: (abs(m - spec["center"]), m))
        ti = snotes.index(t)
        if kind == "tonic":
            for bar, (rh, con, shift) in enumerate(spec["bars"]):
                for (st, ln), c in zip(rh, con):
                    ev.append(E(bar * 16 + st, ln, fold(snotes[ti + c + shift]), int(st % 8 == 0)))
        else:
            for start in range(0, STEPS, spec["period"]):
                for k, (off, ln, c) in enumerate(spec["notes"]):
                    s = start + off
                    if s < STEPS:
                        ev.append(E(s, min(ln, STEPS - s), fold(snotes[ti + c]), int(k == 0)))
        return ev
    conA = spec["A_contour"]
    conA3 = conA[:-2] + [c + rng.choice([-2, -1, 1, 2]) for c in conA[-2:]]
    plan = [(spec["A"], conA), (spec["A"], conA), (spec["A"], conA3), (spec["B"], spec["B_contour"])]
    octs = spec.get("octaves", [0, 0, 0, 0])
    anchor = spec.get("center", 67)
    for bar, ((rh, con), ch) in enumerate(zip(plan, chords)):
        pcs = ch["pcs"]
        sc = bar_scale(key_pcs, pcs)
        tones = [m for m in range(anchor - 8, anchor + 9) if m % 12 in pcs]
        anchor = min(tones, key=lambda m: (abs(m - anchor), m))
        snotes = [m for m in range(24, 110) if m % 12 in sc]
        ai = snotes.index(anchor)
        all_tones = [m for m in range(40, 96) if m % 12 in pcs]
        for (st, ln), c in zip(rh, con):
            m = snotes[ai + c]
            if spec.get("snap", True) and st % 4 == 0 and m % 12 not in pcs:
                m = min(all_tones, key=lambda t: (abs(t - m), t))
            ev.append(E(bar * 16 + st, ln, fold(m + octs[bar], 52 if not octs[bar] else 55), int(st % 8 == 0)))
    for a, b in zip(ev, ev[1:]):
        if (a["start"] + a["len"] == b["start"] and 0 < abs(a["note"] - b["note"]) <= 7
                and rng.random() < spec.get("slide", 0)):
            a["slide"] = True
    return ev


def render_mono(events):
    """Mono events -> (tick, dur, note, vel). Slides overlap the next note by 1/32."""
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
        out.append((tick, dur, e["note"], e["vel"]))
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
            if len(offs) < 3 or len(set(offs)) != 1:  # 3+ notes, one shared length
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
PART_NAMES = ("chords", "arp", "bass", "lead")


def check_data():
    """Refuse to build from entries that are not traceable to RESEARCH.md."""
    def need(label, spec, prog=False):
        conf = spec.get("confidence")
        if conf not in CONFIDENCE:
            raise SystemExit(f"{label}: confidence must be one of {CONFIDENCE}, got {conf!r}")
        if conf != "common-practice" and not spec.get("source"):
            raise SystemExit(f"{label}: {conf} entries need a source URL")
        if not spec.get("ref") or not spec.get("why"):
            raise SystemExit(f"{label}: needs `ref` (RESEARCH.md item) and `why`")
    for part, table in PART_TABLES.items():
        for key, spec in table.items():
            need(f"{part}:{key}", spec)
    for g, spec in GENRES.items():
        if not spec.get("source") or g not in J6_SETS:
            raise SystemExit(f"genre {g}: needs a source and a J-6 set hint")
    for i, p in enumerate(PROGRESSIONS):
        label = f"PROGRESSIONS[{i}] {p['ref']} {p['name']}"
        need(label, p)
        if p["genre"] not in GENRES:
            raise SystemExit(f"{label}: unknown genre {p['genre']!r}")
        for part, table in PART_TABLES.items():
            if p[part] not in table:
                raise SystemExit(f"{label}: unknown {part} style {p[part]!r}")
        if len(p["bars"]) != BARS:
            raise SystemExit(f"{label}: needs exactly {BARS} bars")
        if p.get("scale", p["mode"]) not in SCALES:
            raise SystemExit(f"{label}: unknown scale")


def style_meta(table, name):
    spec = table[name]
    out = {"ref": spec["ref"], "confidence": spec["confidence"], "source": spec.get("source", []),
           "why": spec["why"]}
    if spec.get("poly"):
        out["poly"] = spec["poly"]
    return out


def kit_poly(prog):
    return [part for part in PART_NAMES if PART_TABLES[part][prog[part]].get("poly")]


def kit_id(n, prog):
    return f"{n:02d}-{prog['genre']}-{safe(prog['roman'])}" + ("-poly" if kit_poly(prog) else "")


def build_kit(tonic, prog, kid, key_dir):
    mode = prog["mode"]
    t_pc = tonic_pc(tonic)
    key_pcs = [(t_pc + s) % 12 for s in SCALES[prog.get("scale", mode)]]
    chords = []
    for roman in prog["bars"]:
        deg, semis, qual = parse_roman(roman)
        rname, rpc = spell(tonic, deg, semis)
        ivs, suffix = QUALITY[qual]
        chords.append({"roman": roman, "name": rname + suffix, "root_pc": rpc, "quality": qual,
                       "pcs": [(rpc + i) % 12 for i in ivs]})
    voicings = voice_lead([c["pcs"] for c in chords])
    rng = random.Random(zlib.crc32(f"{key_dir}/{kid}".encode()))
    bass_ev = bass_part(chords, 24 + t_pc, prog["bass"])
    parts = {
        "chords": chords_part(voicings, prog["chords"], bass_ev),
        "arp": render_mono(arp_part(voicings, chords, prog["arp"])),
        "bass": render_mono(bass_ev),
        "lead": render_mono(lead_part(prog["lead"], key_pcs, t_pc, chords, rng)),
    }
    return chords, voicings, parts


def clean_output():
    """Remove generated key folders and index.json; keep hand-kept files (RESEARCH.md)."""
    os.makedirs(OUT_DIR, exist_ok=True)
    for name in os.listdir(OUT_DIR):
        path = os.path.join(OUT_DIR, name)
        if os.path.isdir(path) and re.fullmatch(r"[A-G][bs]?-(major|minor)", name):
            shutil.rmtree(path)
        elif name == "index.json":
            os.remove(path)


def main():
    check_data()
    clean_output()
    kits_meta = {"minor": [], "major": []}
    for mode in kits_meta:
        progs = [p for p in PROGRESSIONS if p["mode"] == mode]
        for n, prog in enumerate(progs, 1):
            genre = GENRES[prog["genre"]]
            kits_meta[mode].append({
                "n": n, "id": kit_id(n, prog), "genre": prog["genre"], "genre_name": genre["name"],
                "ref": prog["ref"], "name": prog["name"], "roman": prog["roman"], "bars": prog["bars"],
                "scale": prog.get("scale", mode), "bpm": prog.get("bpm", genre["bpm"]),
                "confidence": prog["confidence"], "source": prog["source"], "why": prog["why"],
                "pairing": prog["pairing"], "j6": J6_SETS[prog["genre"]],
                "parts": {part: prog[part] for part in PART_NAMES}, "poly": kit_poly(prog),
                "_prog": prog,
            })

    keys, nfiles, nbytes = [], 0, 0
    for tonic_i in range(12):
        for mode in ("minor", "major"):
            tonic = TONICS[mode][tonic_i]
            key_dir = f"{safe(tonic)}-{mode}"
            key_entry = {"id": key_dir, "name": f"{tonic} {mode}", "tonic": tonic,
                         "tonic_pc": tonic_pc(tonic), "mode": mode, "kits": []}
            keys.append(key_entry)
            for meta_ in kits_meta[mode]:
                prog, kid, bpm = meta_["_prog"], meta_["id"], meta_["bpm"]
                chords, voicings, parts = build_kit(tonic, prog, kid, key_dir)
                folder = os.path.join(OUT_DIR, key_dir, kid)
                os.makedirs(folder, exist_ok=True)
                title = f"{tonic} {mode} - {meta_['genre_name']} - {' '.join(c['name'] for c in chords)}"
                for part in PART_NAMES:
                    data = smf_single(f"{title} - {part}", bpm, parts[part])
                    with open(os.path.join(folder, f"{part}.mid"), "wb") as fh:
                        fh.write(data)
                    nfiles += 1
                    nbytes += len(data)
                data = smf_all(title, bpm, parts)
                with open(os.path.join(folder, "all.mid"), "wb") as fh:
                    fh.write(data)
                nfiles += 1
                nbytes += len(data)
                validate_kit(folder, bpm, parts)
                key_entry["kits"].append({"id": kid, "dir": f"{key_dir}/{kid}",
                                          "chords": [c["name"] for c in chords], "voicings": voicings})
    for mode in kits_meta:
        for m in kits_meta[mode]:
            del m["_prog"]

    index = {
        "generated_by": "tools/build_library.py",
        "research": "RESEARCH.md",
        "ppq": TPQ,
        "bars": BARS,
        "steps": STEPS,
        "files": "{dir}/{part}.mid with part in chords, arp, bass, lead, all",
        "channels": {"all.mid": {"chords": 1, "bass": 2, "lead": 3, "arp": 4}, "single files": 1},
        "velocity": {"accent": ACC, "normal": NORM, "ghost": GHOST},
        "slide": f"note overlaps the next note by {SLIDE_OVERLAP} ticks (1/32) at {TPQ} ppq",
        "s1_note": "How the S-1 maps velocity/overlap to its own accent and slide is not verified.",
        "confidence": {"sourced": "stated at the linked source",
                       "constructed": "concrete notes built from a rule the source states",
                       "common-practice": "no source found; standard practice"},
        "genres": {k: dict(g, j6=J6_SETS[k]) for k, g in GENRES.items()},
        "styles": {part: {name: style_meta(table, name) for name in sorted(table)}
                   for part, table in PART_TABLES.items()},
        "kits": kits_meta,
        "keys": keys,
    }
    text = json.dumps(index, indent=1, ensure_ascii=False)
    # keep short lists of numbers / strings on one line so the file stays diffable
    text = re.sub(r"\[\s*((?:-?\d+|\"[^\"\n]*\")(?:,\s*(?:-?\d+|\"[^\"\n]*\"))*)\s*\]",
                  lambda m: "[" + ", ".join(x.strip() for x in m.group(1).split(",")) + "]", text)
    text = re.sub(r"\[\s*(\[[^\[\]\n]*\](?:,\s*\[[^\[\]\n]*\])*)\s*\]",
                  lambda m: "[" + re.sub(r",\s*\[", ", [", m.group(1)) + "]", text)
    with open(os.path.join(OUT_DIR, "index.json"), "w") as fh:
        fh.write(text + "\n")

    nkits = sum(len(k["kits"]) for k in keys)
    print(f"{len(keys)} keys, {nkits} kits, {nfiles} .mid files, {nbytes} bytes of MIDI -> {OUT_DIR}")
    for mode, ms in kits_meta.items():
        print(f"  {mode}: {len(ms)} kits per key")
    print("all files parsed back and validated (ranges, monophony, block chords, 4-bar length).")


if __name__ == "__main__":
    main()
