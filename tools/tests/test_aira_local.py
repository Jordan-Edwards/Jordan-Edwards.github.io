"""Tests for tools/aira_local.py - no MIDI hardware or third-party packages.

    python3 -m unittest discover -s tools/tests -v

The capture tests drive Capture/run_capture with a fake input port that plays
back a scripted stream of (seconds, bytes) messages on a fake clock, then write
the take with write_smf and read it back with the existing read_smf.
"""

import argparse
import contextlib
import csv
import io
import os
import random
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(HERE))

import aira_local as A  # noqa: E402

MIDI_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "s1-j6", "midi")


class FakeSource:
    """Stands in for InPort: get(timeout) hands out scripted messages in time order."""

    def __init__(self, events):
        self.events = sorted(events, key=lambda e: e[0])
        self.t = 0.0

    def get(self, timeout):
        if self.events and self.events[0][0] <= self.t + timeout:
            ev = self.events.pop(0)
            self.t = max(self.t, ev[0])
            return ev
        self.t += timeout
        return None

    def now(self):
        return self.t


def clocks(start, bpm, beats, jitter=0.0, seed=1):
    rng = random.Random(seed)
    iv = 60.0 / bpm / 24
    # clock 0 is never jittered: a real unit always sends Start before it
    return [(start + k * iv + (rng.uniform(-jitter, jitter) if k else 0.0), [0xF8])
            for k in range(int(beats * 24) + 1)]


def note(t, dur, pitch, vel=100, ch=0):
    return [(t, [0x90 | ch, pitch, vel]), (t + dur, [0x80 | ch, pitch, 0])]


def end_of_track_tick(path):
    """Absolute tick of the first track's end-of-track meta."""
    with open(path, "rb") as f:
        data = f.read()
    length = struct.unpack(">I", data[18:22])[0]
    body, i, tick, running = data[22:22 + length], 0, 0, None
    while i < len(body):
        delta, i = A._varlen(body, i)
        tick += delta
        st = body[i]
        if st == 0xFF:
            mlen, j = A._varlen(body, i + 2)
            if body[i + 1] == 0x2F:
                return tick
            i = j + mlen
            continue
        if st & 0x80:
            running, i = st, i + 1
        i += 1 if running & 0xF0 in (0xC0, 0xD0) else 2
    return None


def note_ons(path):
    _, events, _ = A.read_smf(path)
    return [(t, d1, d2, st & 0x0F) for _, t, st, d1, d2 in events
            if st & 0xF0 == 0x90 and d2 > 0]


class CaptureTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def run_take(self, events, **kw):
        src = FakeSource(events)
        cap = A.Capture(**kw)
        A.run_capture(src, cap, now=src.now, idle=0.01)
        return cap

    def test_clock_and_start_give_exact_ticks_and_bar_stop(self):
        bpm, t0 = 120.0, 1.0
        beat = 60.0 / bpm
        ev = [(t0, [0xFA])] + clocks(t0 + 0.0005, bpm, 24, jitter=0.0015)
        # J-6 style: Am F C G, one chord per bar, notes arrive ~2ms late
        chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
        for bar, ch in enumerate(chords * 2):          # plays past the 4 bars
            for p in ch:
                ev += note(t0 + 0.002 + bar * 4 * beat, 3.8 * beat, p, 90, ch=2)
        cap = self.run_take(ev, bpm=77, bars=4, silence=4)   # --bpm ignored: clock wins
        self.assertEqual(cap.done, "bars")
        res = cap.finish()
        self.assertTrue(res["clocked"])
        self.assertEqual(res["bpm"], 120.0)
        self.assertEqual(res["bars"], 4)
        starts = sorted({n[0] for n in res["notes"]})
        self.assertEqual(len(res["notes"]), 12)
        for got, want in zip(starts, [0, 1920, 3840, 5760]):
            self.assertLessEqual(abs(got - want), 4)      # ~2ms at 120 BPM = 2 ticks

        path = os.path.join(self.tmp.name, "take.mid")
        A.write_smf(path, res["notes"], res["bpm"], name="take", end_tick=res["end_tick"])
        tpq, events, tempos = A.read_smf(path)
        self.assertEqual(tpq, 480)
        self.assertEqual(tempos, [(0, 500000)])
        ons = note_ons(path)
        self.assertEqual(sorted(ons), sorted((n[0], n[2], n[3], n[4]) for n in res["notes"]))
        self.assertTrue(all(ch == 2 for *_, ch in ons))    # channel kept
        self.assertTrue(all(v == 90 for _, _, v, _ in ons))  # velocity kept
        self.assertEqual(end_of_track_tick(path), 4 * 1920)
        a = A.analyze_notes(res["notes"], force="chords")
        self.assertEqual(a["key"], "Amin")
        self.assertEqual(a["parts"][0]["chords"], ["Am", "F", "C", "G"])

    def test_no_clock_uses_bpm_first_note_and_silence(self):
        bpm, t0 = 100.0, 5.0
        step = 60.0 / bpm / 4                              # 1/16
        line = [45, None, 45, 57, None, 48, 45, None] * 3 + [52]
        ev = []
        for i, p in enumerate(line):
            if p is not None:
                ev += note(t0 + i * step, step * 0.5, p, 80 + (i % 2) * 30, ch=1)
        cap = self.run_take(ev, bpm=bpm, bars=None, silence=2.0)
        self.assertEqual(cap.done, "silence")
        res = cap.finish()
        self.assertFalse(res["clocked"])
        self.assertEqual(res["bpm"], 100.0)
        self.assertEqual(res["bars"], 2)                  # 25 sixteenths -> 2 bars
        want = [(i * 120, p) for i, p in enumerate(line) if p is not None]
        self.assertEqual([(n[0], n[2]) for n in res["notes"]], want)
        self.assertTrue(all(n[1] - n[0] == 60 for n in res["notes"]))

        path = A.write_smf(os.path.join(self.tmp.name, "s1.mid"), res["notes"], res["bpm"],
                           name="s1", fmt=1, end_tick=res["end_tick"])
        tpq, notes = A.notes_from_smf(path)[0], A.notes_from_smf(path)[2]
        self.assertEqual([(n[0], n[1], n[2], n[3]) for n in notes],
                         [(n[0], n[1], n[2], n[3]) for n in res["notes"]])
        self.assertEqual(A.read_smf(path)[2], [(0, 600000)])

    def test_clock_without_start_snaps_first_note_to_downbeat(self):
        bpm, t0 = 130.0, 2.0
        beat = 60.0 / bpm
        ev = clocks(t0 - 3 * beat, bpm, 20)               # unit already running
        first = t0 + 0.006                                # USB latency
        for b in range(8):
            ev += note(first + b * beat, beat / 2, 45 + (b % 2) * 12)
        cap = self.run_take(ev, bars=2, silence=4)
        self.assertEqual(cap.done, "bars")
        res = cap.finish()
        self.assertTrue(res["clocked"])
        self.assertEqual(res["bpm"], 130.0)
        starts = [n[0] for n in res["notes"]]
        self.assertEqual(len(starts), 8)
        for i, s in enumerate(starts):
            self.assertLessEqual(abs(s - i * 480), 3)

    def test_quantize_snaps_jitter(self):
        rng = random.Random(7)
        bpm, t0 = 120.0, 0.5
        step = 60.0 / bpm / 4
        ev = []
        for i in range(16):
            ev += note(t0 + i * step + (rng.uniform(-0.012, 0.012) if i else 0), step / 2, 60 + i)
        cap = self.run_take(ev, bpm=bpm, bars=1, silence=4)
        res = cap.finish(quantize=16)
        self.assertEqual([n[0] for n in res["notes"]], [i * 120 for i in range(16)])

    def test_midi_stop_ends_take_and_closes_held_notes(self):
        ev = [(1.0, [0xFA])] + clocks(1.0, 120, 6)
        ev += [(1.0, [0x90, 60, 100]), (2.5, [0xFC])]     # note never released
        cap = self.run_take(ev, silence=4)
        self.assertEqual(cap.done, "stop")
        res = cap.finish()
        self.assertEqual(len(res["notes"]), 1)
        s, e = res["notes"][0][:2]
        self.assertEqual(s, 0)
        self.assertAlmostEqual(e, 1440, delta=3)          # 1.5 s at 120 BPM

    def test_save_take_names_file_by_key_and_indexes(self):
        ev = []
        for bar, ch in enumerate([[50, 53, 57], [46, 50, 53], [48, 52, 55], [50, 53, 57]]):
            for p in ch:
                ev += note(1.0 + bar * 2.0, 1.9, p)
        cap = self.run_take(ev, bpm=120, bars=4, silence=4)
        res = cap.finish()
        with contextlib.redirect_stdout(io.StringIO()):
            path = A.save_take(res, self.tmp.name, "j6-p07-{key}", "j6")
            path2 = A.save_take(res, self.tmp.name, "j6-p07-{key}", "j6")
        self.assertEqual(os.path.basename(path), "j6-p07-Dmin.mid")
        self.assertEqual(os.path.basename(path2), "j6-p07-Dmin-2.mid")
        with open(os.path.join(self.tmp.name, "index.csv"), newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r["file"] for r in rows], ["j6-p07-Dmin-2.mid", "j6-p07-Dmin.mid"])
        self.assertEqual(rows[0]["chords"], "Dm - Bb - C - Dm")
        self.assertEqual(rows[0]["bars"], "4")
        self.assertEqual(rows[0]["bpm"], "120")


class ScanTests(unittest.TestCase):

    def test_scan_builds_index_for_songbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = os.path.join(tmp, "index.csv")
            args = argparse.Namespace(paths=[MIDI_DIR], index=index, no_index=False,
                                      drum_channel=10)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(A.cmd_scan(args), 0)
            with open(index, newline="") as f:
                rows = {os.path.basename(r["file"]): r for r in csv.DictReader(f)}
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows["neon-mile.mid"]["key"], "Amin")
        self.assertEqual(rows["neon-mile.mid"]["chords"], "Am - F - C - G")
        self.assertEqual(rows["deep-end.mid"]["chords"], "Fm7 - Bbm7 - Eb7 - Abmaj7")
        self.assertEqual(rows["acid-rain.mid"]["bpm"], "130")
        self.assertEqual(rows["acid-rain.mid"]["bars"], "4")


class TheoryTests(unittest.TestCase):

    def test_chord_names(self):
        cases = {
            (57, 60, 64): "Am", (60, 64, 67): "C", (64, 67, 72): "C/E",
            (55, 60, 64): "C/G", (60, 64, 67, 70): "C7", (62, 65, 69, 72): "Dm7",
            (60, 64, 67, 71): "Cmaj7", (60, 62, 67): "Csus2", (60, 65, 67): "Csus4",
            (59, 62, 65): "Bdim", (60, 64, 68): "Caug", (60, 64, 67, 74): "Cadd9",
            (48, 64, 67, 70, 74): "C9", (57, 60, 64, 67): "Am7", (60, 64, 67, 69): "C6",
            (59, 62, 65, 69): "Bm7b5", (43, 60, 64, 67): "C/G", (60,): "C",
        }
        for pitches, want in cases.items():
            self.assertEqual(A.name_chord(list(pitches)), want, pitches)
        self.assertEqual(A.name_chord([53, 56, 60, 63], flats=True), "Fm7")
        self.assertEqual(A.name_chord([58, 62, 65], flats=True), "Bb")

    def test_songbook_keys_match_readme(self):
        want = {"neon-mile": "Amin", "acid-rain": "Amin", "deep-end": "Fmin",
                "lo-fi-sunday": "Cmaj", "midnight-drive": "Dmin",
                "greensleeves": "Amin", "ode-to-joy": "Cmaj", "rising-sun": "Amin"}
        for song, key in want.items():
            tpq, _, notes = A.notes_from_smf(os.path.join(MIDI_DIR, song + ".mid"))
            self.assertEqual(A.analyze_notes(notes, tpq)["key"], key, song)

    def test_arpeggio_is_read_per_bar(self):
        notes = []
        for bar, ch in enumerate([[57, 60, 64], [53, 57, 60]]):
            for i in range(8):
                s = bar * 1920 + i * 240
                notes.append((s, s + 200, ch[i % 3], 100, 0))
        self.assertEqual([n for _, n in A.chord_progression(notes)], ["Am", "F"])


if __name__ == "__main__":
    unittest.main()
