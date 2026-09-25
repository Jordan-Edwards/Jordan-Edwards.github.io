#!/usr/bin/env python3
"""
aira_local.py - run this ON THE COMPUTER THE SYNTHS ARE PLUGGED INTO.

The songbook page can already drive the S-1 and J-6 from a browser. This is the
same job from a terminal, plus the things a browser cannot do: copy a unit's
BACKUP folder off while it is mounted in drive mode, and pull those files apart
so the pattern format can be worked out.

    python3 aira_local.py ports
    python3 aira_local.py play acid-rain
    python3 aira_local.py rec  acid-rain --count-in 4
    python3 aira_local.py backup /Volumes/J-6 ~/aira-backups
    python3 aira_local.py analyze ~/aira-backups/J-6

    python3 aira_local.py capture --list
    python3 aira_local.py capture --unit j6 --bars 4 --quantize 16
    python3 aira_local.py harvest --unit s1
    python3 aira_local.py scan ~/aira-library ~/op-xy-exports

Building a pattern library:

  capture  records what a unit plays (USB MIDI out) into a .mid file. Tempo
           and bar lines come from the unit's MIDI clock when it sends one,
           otherwise from --bpm. Stops on Ctrl-C, --bars N or --silence.
  harvest  loops capture over patterns: select pattern N on the unit, press
           Enter, it saves j6-p01-Amin.mid and moves on until you type q.
           --send-start starts/stops the unit for you; --program-change
           (experimental) also tries to select the pattern over MIDI.
  scan     detects key and chords in .mid files you already have (OP-XY
           exports too) and writes index.csv next to them.

Every capture prints the detected key (Krumhansl-Schmuckler), the J-6 chord
progression or the S-1 note line, and adds a row to index.csv
(file, unit, key, bpm, bars, chords, notes) in the output folder, which
defaults to ~/aira-library/<unit>/.

`ports`, `play`, `rec`, `capture` and `harvest` need a MIDI backend:

    pip install mido python-rtmidi

`backup`, `analyze` and `scan` are pure standard library - nothing to install.
Start there if you just want to see what is on the units.

Drive mode: power the unit OFF, hold PLAY, power it back ON. It mounts as a
disk with BACKUP and RESTORE folders.
"""

import argparse
import bisect
import csv
import os
import queue
import shutil
import struct
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
MIDI_DIR = os.path.join(os.path.dirname(HERE), "s1-j6", "midi")

# Track index -> which synth. Matches how build_songs.py writes the files:
# track 0 is the conductor, track 1 is the J-6, track 2 is the S-1.
TRACK_ROLE = {1: "j6", 2: "s1"}


# ---------------------------------------------------------------------------
# Standard MIDI File reader (stdlib only)
# ---------------------------------------------------------------------------

def _varlen(buf, i):
    val = 0
    while True:
        b = buf[i]; i += 1
        val = (val << 7) | (b & 0x7F)
        if not b & 0x80:
            return val, i


def read_smf(path):
    """Return (ticks_per_quarter, [(track_index, abs_tick, status, d1, d2)], tempo_map)."""
    data = open(path, "rb").read()
    if data[:4] != b"MThd":
        raise ValueError(f"{path}: not a MIDI file")
    _, fmt, ntrk, tpq = struct.unpack(">IHHH", data[4:14])
    if tpq & 0x8000:
        raise ValueError(f"{path}: SMPTE time division is not supported")

    events, tempos = [], []
    pos = 14
    for tidx in range(ntrk):
        if data[pos:pos+4] != b"MTrk":
            raise ValueError(f"{path}: track {tidx} is malformed")
        length = struct.unpack(">I", data[pos+4:pos+8])[0]
        body = data[pos+8:pos+8+length]
        pos += 8 + length

        i, tick, running = 0, 0, None
        while i < len(body):
            delta, i = _varlen(body, i)
            tick += delta
            status = body[i]
            if status == 0xFF:                       # meta
                mtype = body[i+1]
                mlen, j = _varlen(body, i+2)
                if mtype == 0x51:                    # set tempo
                    tempos.append((tick, int.from_bytes(body[j:j+3], "big")))
                i = j + mlen
                if mtype == 0x2F:
                    break
                continue
            if status in (0xF0, 0xF7):               # sysex - skip
                slen, j = _varlen(body, i+1)
                i = j + slen
                continue
            if status & 0x80:
                running = status
                i += 1
            else:
                status = running
                if status is None:
                    raise ValueError(f"{path}: running status with no preceding status byte")
            high = status & 0xF0
            if high in (0xC0, 0xD0):
                events.append((tidx, tick, status, body[i], 0)); i += 1
            else:
                events.append((tidx, tick, status, body[i], body[i+1])); i += 2

    if not tempos:
        tempos = [(0, 500000)]
    tempos.sort()
    events.sort(key=lambda e: e[1])
    return tpq, events, tempos


def ticks_to_seconds(tick, tpq, tempos):
    """Convert an absolute tick to seconds, honouring every tempo change."""
    secs, prev_tick, micros = 0.0, 0, tempos[0][1]
    for t_tick, t_micros in tempos:
        if t_tick >= tick:
            break
        secs += (t_tick - prev_tick) / tpq * (micros / 1_000_000)
        prev_tick, micros = t_tick, t_micros
    secs += (tick - prev_tick) / tpq * (micros / 1_000_000)
    return secs


def schedule(path):
    """Flatten a MIDI file into [(seconds, role, status, d1, d2)], time-ordered."""
    tpq, events, tempos = read_smf(path)
    out = []
    for tidx, tick, status, d1, d2 in events:
        role = TRACK_ROLE.get(tidx)
        if role is None:
            continue
        if status & 0xF0 not in (0x80, 0x90, 0xB0, 0xC0):
            continue
        out.append((ticks_to_seconds(tick, tpq, tempos), role, status, d1, d2))
    out.sort(key=lambda e: e[0])
    return out, tempos[0][1]


def notes_from_smf(path, drum_channel=10):
    """Pair note on/off events -> (tpq, bpm, [(start, end, pitch, vel, part)]).

    `part` is track*16 + channel so separate tracks/channels stay apart.
    Notes on `drum_channel` (1-16, 0 = keep everything) are dropped so a drum
    track in an OP-XY export does not skew the key.
    """
    tpq, events, tempos = read_smf(path)
    held, notes = {}, []
    for tidx, tick, status, d1, d2 in events:
        kind, ch = status & 0xF0, status & 0x0F
        if drum_channel and ch == drum_channel - 1:
            continue
        key = (tidx, ch, d1)
        if kind == 0x90 and d2 > 0:
            if key in held:                          # re-struck while held
                s, v = held.pop(key)
                notes.append((s, max(s + 1, tick), d1, v, tidx * 16 + ch))
            held[key] = (tick, d2)
        elif kind == 0x80 or (kind == 0x90 and d2 == 0):
            if key in held:
                s, v = held.pop(key)
                notes.append((s, max(s + 1, tick), d1, v, tidx * 16 + ch))
    last = max((e[1] for e in events), default=0)
    for (tidx, ch, p), (s, v) in held.items():
        notes.append((s, max(s + 1, last), p, v, tidx * 16 + ch))
    notes.sort()
    return tpq, 60_000_000 / tempos[0][1], notes


# ---------------------------------------------------------------------------
# Standard MIDI File writer (stdlib only)
# ---------------------------------------------------------------------------

TPQ = 480
BAR = TPQ * 4          # everything here is 4/4, as on both units and the OP-XY


def _vlq(value):
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def _meta(mtype, payload):
    return bytes([0xFF, mtype]) + _vlq(len(payload)) + payload


def _mtrk(events, end_tick=0):
    """events: [(tick, bytes)]. Metas first, then note-offs, then note-ons on a tick."""
    def prio(ev):
        b = ev[1]
        if b[0] == 0xFF:
            return 0
        if b[0] & 0xF0 == 0x80:
            return 1
        return 2
    data, prev = bytearray(), 0
    for tick, payload in sorted(events, key=lambda e: (e[0], prio(e))):
        data += _vlq(tick - prev) + payload
        prev = tick
    data += _vlq(max(0, end_tick - prev)) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def write_smf(path, notes, bpm, name="", tpq=TPQ, fmt=0, end_tick=0):
    """Write [(start, end, pitch, velocity, channel 0-15)] as a Standard MIDI File.

    Format 0 = one track holding tempo, name and notes (what most samplers and
    the OP-XY import happily). Format 1 = conductor track + one note track.
    `end_tick` pads the end-of-track so a loop keeps its full bar length even
    when the last bar ends in a rest.
    """
    micros = max(1, min(0xFFFFFF, int(round(60_000_000 / bpm))))
    title = _meta(0x03, name.encode("utf-8", "replace"))
    head = [(0, title),
            (0, _meta(0x58, b"\x04\x02\x18\x08")),       # 4/4
            (0, _meta(0x51, micros.to_bytes(3, "big")))]
    body = []
    for s, e, p, v, ch in notes:
        ch &= 0x0F
        body.append((s, bytes([0x90 | ch, p & 0x7F, max(1, min(127, v))])))
        body.append((max(e, s + 1), bytes([0x80 | ch, p & 0x7F, 0])))
    end_tick = max(end_tick, max((t for t, _ in body), default=0))
    if fmt == 0:
        chunks = [_mtrk(head + body, end_tick)]
    else:
        chunks = [_mtrk(head, end_tick), _mtrk([(0, title)] + body, end_tick)]
    blob = b"MThd" + struct.pack(">IHHH", 6, fmt, len(chunks), tpq) + b"".join(chunks)
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)
    return path


# ---------------------------------------------------------------------------
# Key and chord detection (stdlib only)
# ---------------------------------------------------------------------------

SHARPS = "C C# D D# E F F# G G# A A# B".split()
FLATS = "C Db D Eb E F Gb G Ab A Bb B".split()

# Krumhansl-Kessler probe-tone profiles, tonic first.
KS_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KS_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

# Tonics whose key signature uses flats - spell notes with flats in those keys.
FLAT_KEYS = {"maj": {5, 10, 3, 8, 1}, "min": {2, 7, 0, 5, 10, 3}}
KEY_TONIC = {"maj": "C Db D Eb E F F# G Ab A Bb B".split(),
             "min": "C C# D Eb E F F# G G# A Bb B".split()}

# (suffix, intervals above the root). Earlier entries win ties.
CHORD_TYPES = [
    ("", {0, 4, 7}), ("m", {0, 3, 7}), ("dim", {0, 3, 6}), ("aug", {0, 4, 8}),
    ("sus4", {0, 5, 7}), ("sus2", {0, 2, 7}), ("5", {0, 7}),
    ("7", {0, 4, 7, 10}), ("maj7", {0, 4, 7, 11}), ("m7", {0, 3, 7, 10}),
    ("m7b5", {0, 3, 6, 10}), ("dim7", {0, 3, 6, 9}), ("mMaj7", {0, 3, 7, 11}),
    ("6", {0, 4, 7, 9}), ("m6", {0, 3, 7, 9}), ("7sus4", {0, 5, 7, 10}),
    ("add9", {0, 2, 4, 7}), ("madd9", {0, 2, 3, 7}), ("aug7", {0, 4, 8, 10}),
    ("9", {0, 2, 4, 7, 10}), ("maj9", {0, 2, 4, 7, 11}), ("m9", {0, 2, 3, 7, 10}),
    ("7b9", {0, 1, 4, 7, 10}), ("7#9", {0, 3, 4, 7, 10}), ("6/9", {0, 2, 4, 7, 9}),
    ("9sus4", {0, 2, 5, 7, 10}), ("11", {0, 2, 4, 5, 7, 10}),
    ("m11", {0, 2, 3, 5, 7, 10}), ("13", {0, 2, 4, 7, 9, 10}),
    # voicings with the fifth left out, common on chord machines
    ("7", {0, 4, 10}), ("maj7", {0, 4, 11}), ("m7", {0, 3, 10}),
    ("9", {0, 2, 4, 10}), ("maj9", {0, 2, 4, 11}), ("m9", {0, 2, 3, 10}),
]


def note_name(pitch, flats=False, octave=True):
    nm = (FLATS if flats else SHARPS)[pitch % 12]
    return f"{nm}{pitch // 12 - 1}" if octave else nm


def _pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else 0.0


def estimate_key(notes, downbeat_weight=0.2):
    """Krumhansl-Schmuckler over duration-weighted pitch classes.

    notes: [(start, end, pitch, ...)]. Returns [(r, tonic_pc, 'maj'|'min')]
    best first, or [] when there is nothing to go on.

    Plain K-S cannot tell a key from its relative major/minor when both use
    the same notes (Am-F-C-G reads as C major). Loops nearly always start on
    the home chord, so the lowest note of the first onset gets a bonus worth
    `downbeat_weight` of the total duration. 0 gives textbook K-S.
    """
    hist = [0.0] * 12
    for n in notes:
        hist[n[2] % 12] += max(1, n[1] - n[0])
    total = sum(hist)
    if total == 0:
        return []
    first = min(n[0] for n in notes)
    bass = min(n[2] for n in notes if n[0] - first <= TPQ // 8)
    hist[bass % 12] += downbeat_weight * total
    ranked = []
    for tonic in range(12):
        rot = hist[tonic:] + hist[:tonic]
        ranked.append((_pearson(rot, KS_MAJOR), tonic, "maj"))
        ranked.append((_pearson(rot, KS_MINOR), tonic, "min"))
    ranked.sort(key=lambda k: -k[0])
    return ranked


def key_label(tonic, mode):
    return KEY_TONIC[mode][tonic] + mode


def key_uses_flats(tonic, mode):
    return tonic in FLAT_KEYS[mode]


def name_chord(pitches, flats=False):
    """Name a set of simultaneous MIDI pitches: 'Am', 'Fmaj7', 'C/E', 'G7sus4'.

    The lowest note decides between equally good readings (C6 vs Am7/C) and a
    bass that is not the root becomes a slash chord. Unknown sets come back as
    their note names in brackets.
    """
    if not pitches:
        return ""
    pcs = sorted({p % 12 for p in pitches})
    bass = min(pitches) % 12
    spell = FLATS if flats else SHARPS
    if len(pcs) == 1:
        return spell[pcs[0]]
    best = None
    for rank, (suffix, ivs) in enumerate(CHORD_TYPES):
        if len(ivs) != len(pcs):
            continue
        for root in pcs:
            if {(p - root) % 12 for p in pcs} == ivs:
                cand = ((root != bass, rank), root, suffix)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "(" + " ".join(spell[p] for p in pcs) + ")"
    _, root, suffix = best
    name = spell[root] + suffix
    return name if root == bass else f"{name}/{spell[bass]}"


def _onset_clusters(notes, tol):
    clusters = []
    for n in sorted(notes):
        if clusters and n[0] - clusters[-1][0][0] <= tol:
            clusters[-1].append(n)
        else:
            clusters.append([n])
    return clusters


def chord_progression(notes, tpq=TPQ, flats=False):
    """Group simultaneous notes into chords -> [(tick, name)], repeats merged.

    Block chords are read per onset (plus notes still held from before). When
    the part is mostly single notes - an arpeggio or a strum style - each bar's
    notes are read as one chord instead.
    """
    if not notes:
        return []
    tol = tpq // 8
    clusters = _onset_clusters(notes, tol)
    readings = []
    for cl in clusters:
        t = cl[0][0]
        sounding = [n[2] for n in cl]
        sounding += [n[2] for n in notes if n[0] < t and n[1] > t + tpq // 4]
        readings.append((t, sounding))
    thin = sum(1 for _, s in readings if len({p % 12 for p in s}) < 3)
    if thin > len(readings) / 2:
        bars = {}
        for n in notes:
            bars.setdefault(n[0] // (tpq * 4), []).append(n[2])
        readings = [(b * tpq * 4, ps) for b, ps in sorted(bars.items())]
    prog = []
    for t, ps in readings:
        nm = name_chord(ps, flats)
        if not prog or prog[-1][1] != nm:
            prog.append((t, nm))
    return prog


def is_polyphonic(notes, tpq=TPQ):
    """True when at least a third of the onsets are 3+ note chords."""
    clusters = _onset_clusters(notes, tpq // 8)
    if not clusters:
        return False
    fat = sum(1 for cl in clusters if len({n[2] % 12 for n in cl}) >= 3)
    return fat >= len(clusters) / 3


def analyze_notes(notes, tpq=TPQ, force=None):
    """Key + per-part reading. force='chords'|'line' overrides the poly test.

    Returns {'key', 'key_alt', 'flats', 'parts': [{'part', 'kind', 'summary', ...}]}.
    """
    ranked = estimate_key(notes)
    out = {"key": "", "key_alt": "", "key_r": 0.0, "flats": False, "parts": []}
    if ranked:
        r, tonic, mode = ranked[0]
        out.update(key=key_label(tonic, mode), key_r=r,
                   key_alt=key_label(ranked[1][1], ranked[1][2]),
                   flats=key_uses_flats(tonic, mode))
    flats = out["flats"]
    parts = {}
    for n in notes:
        parts.setdefault(n[4], []).append(n)
    for pid in sorted(parts):
        pn = sorted(parts[pid])
        kind = force or ("chords" if is_polyphonic(pn, tpq) else "line")
        info = {"part": pid, "kind": kind, "count": len(pn)}
        if kind == "chords":
            prog = chord_progression(pn, tpq, flats)
            info["chords"] = [nm for _, nm in prog]
            info["summary"] = " - ".join(info["chords"])
        else:
            seq = [note_name(n[2], flats) for n in pn]
            roots = []
            by_bar = {}
            for n in pn:
                by_bar.setdefault(n[0] // (tpq * 4), []).append(n[2])
            for b in range(max(by_bar) + 1):
                ps = by_bar.get(b)
                roots.append(note_name(min(ps), flats, octave=False) if ps else "-")
            info["notes"] = seq
            info["roots"] = roots
            short = " ".join(seq[:32]) + (" ..." if len(seq) > 32 else "")
            info["summary"] = f"roots {' | '.join(roots)}  notes {short}"
        out["parts"].append(info)
    return out


def describe(analysis, indent="  "):
    lines = []
    if analysis["key"]:
        lines.append(f"{indent}key      {analysis['key']}  (r={analysis['key_r']:.2f}, "
                     f"runner-up {analysis['key_alt']})")
    for p in analysis["parts"]:
        label = "chords  " if p["kind"] == "chords" else "line    "
        lines.append(f"{indent}{label} {p['summary']}")
    return "\n".join(lines)


INDEX_FIELDS = ["file", "unit", "key", "bpm", "bars", "chords", "notes"]


def index_row(file, unit, analysis, bpm, bars):
    chords = [p["summary"] for p in analysis["parts"] if p["kind"] == "chords"]
    lines = [" ".join(p["notes"][:64]) + (" ..." if len(p["notes"]) > 64 else "")
             for p in analysis["parts"] if p["kind"] == "line"]
    return {"file": file, "unit": unit, "key": analysis["key"],
            "bpm": f"{bpm:g}", "bars": bars,
            "chords": " / ".join(chords), "notes": " / ".join(lines)}


def update_index(index_path, rows):
    """Merge rows into index.csv, one row per file (a re-capture replaces it)."""
    table = {}
    if os.path.isfile(index_path):
        with open(index_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("file"):
                    table[r["file"]] = {k: r.get(k, "") for k in INDEX_FIELDS}
    for r in rows:
        table[r["file"]] = r
    os.makedirs(os.path.dirname(os.path.abspath(index_path)), exist_ok=True)
    with open(index_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
        w.writeheader()
        for k in sorted(table):
            w.writerow(table[k])
    return index_path


# ---------------------------------------------------------------------------
# MIDI ports
# ---------------------------------------------------------------------------

def open_backend():
    try:
        import mido                                   # noqa
        return "mido", mido
    except ImportError:
        pass
    try:
        import rtmidi                                 # noqa
        return "rtmidi", rtmidi
    except ImportError:
        return None, None


def list_ports():
    kind, mod = open_backend()
    if kind is None:
        return None
    if kind == "mido":
        return list(mod.get_output_names())
    out = mod.MidiOut()
    return list(out.get_ports())


def guess(names, *patterns):
    for pat in patterns:
        for nm in names:
            if pat.lower() in nm.lower():
                return nm
    return None


class Port:
    """Thin wrapper so mido and raw rtmidi look the same."""

    def __init__(self, kind, mod, name):
        self.kind, self.name = kind, name
        if kind == "mido":
            self._p = mod.open_output(name)
        else:
            self._p = mod.MidiOut()
            self._p.open_port(mod.MidiOut().get_ports().index(name))

    def send(self, status, d1, d2):
        if self.kind == "mido":
            import mido
            self._p.send(mido.Message.from_bytes([status, d1, d2]))
        else:
            self._p.send_message([status, d1, d2])

    def panic(self):
        for ch in range(16):
            try:
                self.send(0xB0 | ch, 123, 0)
                self.send(0xB0 | ch, 120, 0)
            except Exception:
                pass

    def send_raw(self, data):
        """Send any message, e.g. [0xFA] (Start) or [0xC0, 5] (Program Change)."""
        if self.kind == "mido":
            import mido
            self._p.send(mido.Message.from_bytes(list(data)))
        else:
            self._p.send_message(list(data))

    def close(self):
        try:
            if self.kind == "mido":
                self._p.close()
            else:
                self._p.close_port()
        except Exception:
            pass


def list_inputs():
    kind, mod = open_backend()
    if kind is None:
        return None
    if kind == "mido":
        return list(mod.get_input_names())
    return list(mod.MidiIn().get_ports())


class InPort:
    """MIDI input that timestamps every message on arrival and queues it.

    get(timeout) -> (seconds, [bytes]) or None. That is the whole interface the
    capture loop needs, so a test can hand it any object with the same get().
    Clock/Start/Stop are NOT filtered out - they carry the tempo.
    """

    def __init__(self, kind, mod, name):
        self.kind, self.name = kind, name
        self.q = queue.Queue()
        if kind == "mido":
            # mido's rtmidi backend already passes timing messages through
            self._p = mod.open_input(name, callback=self._on_mido)
        else:
            self._p = mod.MidiIn()
            self._p.ignore_types(sysex=True, timing=False, active_sense=True)
            self._p.set_callback(self._on_rtmidi)
            self._p.open_port(self._p.get_ports().index(name))

    def _on_mido(self, msg):
        self.q.put((time.perf_counter(), list(msg.bytes())))

    def _on_rtmidi(self, event, data=None):
        self.q.put((time.perf_counter(), list(event[0])))

    def get(self, timeout):
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self):
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break

    def close(self):
        try:
            if self.kind == "mido":
                self._p.close()
            else:
                self._p.cancel_callback()
                self._p.close_port()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Capture: live MIDI -> notes on a 480-TPQ grid (no I/O, testable)
# ---------------------------------------------------------------------------

CLOCK_PPQ = 24          # MIDI clock pulses per quarter note
CLOCK_TIMEOUT = 0.5     # seconds without a clock before we stop trusting it


class Capture:
    """Record what a unit plays.

    Feed it raw messages with feed(bytes, seconds) and call poll(seconds)
    regularly; it sets .done to 'bars', 'silence', 'stop' or 'ctrl-c' when the
    take is over. finish() then turns the take into ticks:

    * MIDI clock present -> positions come from counting clock pulses (tempo
      is measured, drift-free). With a Start message the first clock after it
      is bar 1 beat 1; without one the first note is rounded to the nearest
      16th and becomes the downbeat.
    * no clock -> positions come from wall time at `bpm`, starting at Start,
      at arm() (the moment we sent Start ourselves) or at the first note.
    """

    def __init__(self, bpm=120.0, bars=None, silence=4.0, tpq=TPQ):
        self.bpm, self.bars, self.silence, self.tpq = float(bpm), bars, silence, tpq
        self.clock_times = []
        self.start_t = self.arm_t = self.first_note_t = self.last_note_t = None
        self.held = {}                 # (ch, pitch) -> (t_on, vel)
        self.raw = []                  # (t_on, t_off, pitch, vel, ch)
        self.done = None
        self.end_t = None

    # -- live side ---------------------------------------------------------

    def arm(self, t):
        self.arm_t = t

    def origin(self):
        for t in (self.start_t, self.arm_t, self.first_note_t):
            if t is not None:
                return t
        return None

    def _clocking(self, t):
        return len(self.clock_times) >= 2 and t - self.clock_times[-1] < CLOCK_TIMEOUT

    def feed(self, data, t):
        if not data or self.done:
            return
        st = data[0]
        if st == 0xF8:                                   # clock
            self.clock_times.append(t)
        elif st == 0xFA:                                 # start
            if self.first_note_t is None:
                self.start_t = t
                self.clock_times = []
        elif st == 0xFC:                                 # stop
            if self.first_note_t is not None:
                self._end(t, "stop")
                return
        elif st < 0xF0 and len(data) >= 3:
            kind, key = st & 0xF0, (st & 0x0F, data[1])
            if kind == 0x90 and data[2] > 0:
                if key in self.held:
                    self._close(key, t)
                self.held[key] = (t, data[2])
                if self.first_note_t is None:
                    self.first_note_t = t
                self.last_note_t = t
            elif kind == 0x80 or kind == 0x90:
                if key in self.held:
                    self._close(key, t)
                    self.last_note_t = t
        self._check_bars(t)

    def poll(self, t):
        if self.done:
            return
        self._check_bars(t)
        if (not self.done and self.silence and self.first_note_t is not None
                and not self.held and t - self.last_note_t >= self.silence):
            self._end(t, "silence")

    def _check_bars(self, t):
        if self.done or not self.bars or self.first_note_t is None:
            return
        org = self.origin()
        need = self.bars * 4 * CLOCK_PPQ
        if self._clocking(t):
            if self.start_t is not None:
                # clock #0 after Start is the downbeat; clock #need starts bar N+1
                if len(self.clock_times) > need:
                    self._end(self.clock_times[need], "bars")
            else:
                after = len(self.clock_times) - bisect.bisect_left(self.clock_times, org)
                if after >= need:
                    self._end(self.clock_times[-1], "bars")
        else:
            span = self.bars * 4 * 60.0 / self.bpm
            if t - org >= span:
                self._end(org + span, "bars")

    def _close(self, key, t):
        t_on, vel = self.held.pop(key)
        self.raw.append((t_on, t, key[1], vel, key[0]))

    def _end(self, t, reason):
        self.done, self.end_t = reason, t
        for key in list(self.held):
            self._close(key, t)

    def stop(self, t, reason="ctrl-c"):
        if not self.done:
            self._end(t, reason)

    # -- after the take ----------------------------------------------------

    def finish(self, quantize=0):
        """-> dict(notes=[(start, end, pitch, vel, ch)], bpm, bars, end_tick, clocked)."""
        if self.done is None:
            self._end(self.last_note_t or 0.0, "stopped")
        tpq = self.tpq
        clocks = self.clock_times
        if self.start_t is not None:
            clocks = [c for c in clocks if c >= self.start_t]
        clocked = len(clocks) >= CLOCK_PPQ
        if clocked:
            gaps = sorted(b - a for a, b in zip(clocks, clocks[1:]))
            iv = gaps[len(gaps) // 2]
            bpm = 60.0 / (CLOCK_PPQ * iv)

            def pos(t):
                i = bisect.bisect_right(clocks, t) - 1
                if i < 0:
                    return (t - clocks[0]) / iv
                if i >= len(clocks) - 1:
                    return i + (t - clocks[-1]) / iv
                return i + (t - clocks[i]) / (clocks[i + 1] - clocks[i])

            if self.start_t is not None:
                org = 0.0
            elif self.arm_t is not None:
                org = pos(self.arm_t)
            elif self.first_note_t is not None:
                org = round(pos(self.first_note_t) / 6) * 6
            else:
                org = 0.0

            def tick(t):
                return int(round((pos(t) - org) * tpq / CLOCK_PPQ))
        else:
            bpm = self.bpm
            org_t = self.origin() or 0.0

            def tick(t):
                return int(round((t - org_t) * bpm / 60.0 * tpq))

        if abs(bpm - round(bpm)) < 0.25:
            bpm = float(round(bpm))
        else:
            bpm = round(bpm, 1)

        notes = []
        for t_on, t_off, p, v, ch in self.raw:
            s = max(0, tick(t_on))
            notes.append((s, max(s + 1, tick(t_off)), p, v, ch))
        notes.sort()

        bar = tpq * 4
        if self.bars:
            end_tick = self.bars * bar
        elif notes:
            end_tick = (max(n[0] for n in notes) // bar + 1) * bar
        else:
            end_tick = 0
        if quantize:
            notes = quantize_notes(notes, quantize, tpq)
        kept, seen = [], set()
        for s, e, p, v, ch in notes:
            if s >= end_tick or (s, p, ch) in seen:
                continue
            seen.add((s, p, ch))
            kept.append((s, min(e, end_tick), p, v, ch))
        return {"notes": kept, "bpm": bpm, "bars": end_tick // bar,
                "end_tick": end_tick, "clocked": clocked, "reason": self.done}


def quantize_notes(notes, division, tpq=TPQ):
    """Snap note starts to a 1/division grid; lengths are kept as played."""
    grid = max(1, tpq * 4 // division)
    out = []
    for s, e, p, v, ch in notes:
        q = int(round(s / grid)) * grid
        out.append((q, q + (e - s), p, v, ch))
    return sorted(out)


def run_capture(source, cap, now=time.perf_counter, idle=0.02):
    """Pump source.get() into cap until it is done. Ctrl-C ends the take."""
    try:
        while not cap.done:
            item = source.get(idle)
            if item is not None:
                cap.feed(item[1], item[0])
            cap.poll(now())
    except KeyboardInterrupt:
        cap.stop(now(), "ctrl-c")
    return cap


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def song_path(name):
    if os.path.isfile(name):
        return name
    p = os.path.join(MIDI_DIR, name if name.endswith(".mid") else name + ".mid")
    if not os.path.isfile(p):
        avail = sorted(f[:-4] for f in os.listdir(MIDI_DIR)) if os.path.isdir(MIDI_DIR) else []
        raise SystemExit(f"No song '{name}'. Available: {', '.join(avail) or '(none found)'}")
    return p


def cmd_ports(args):
    names = list_ports()
    if names is None:
        print("No MIDI backend installed.\n  pip install mido python-rtmidi")
        return 1
    if not names:
        print("No MIDI outputs found.")
        print("Check: USB-C data cable (not a charge-only one), unit powered on,")
        print("and plugged straight into the computer rather than through a hub.")
        return 1
    print(f"{len(names)} MIDI output(s):")
    for i, nm in enumerate(names):
        print(f"  [{i}] {nm}")
    j6 = guess(names, "j-6", "j6")
    s1 = guess(names, "s-1", "s1")
    print(f"\n  J-6 -> {j6 or 'not found - pass --j6 <name>'}")
    print(f"  S-1 -> {s1 or 'not found - pass --s1 <name>'}")
    ins = list_inputs() or []
    print()
    _print_inputs(ins)
    return 0


def cmd_play(args):
    path = song_path(args.song)
    events, micros = schedule(path)
    bpm = round(60_000_000 / micros)
    notes = sum(1 for e in events if e[2] & 0xF0 == 0x90 and e[4] > 0)
    span = max((e[0] for e in events), default=0)
    print(f"{os.path.basename(path)}  {bpm} BPM  {notes} notes  {span:.1f}s/loop")

    ports = {}
    if not args.dry_run:
        kind, mod = open_backend()
        if kind is None:
            raise SystemExit("No MIDI backend.\n  pip install mido python-rtmidi")
        names = list_ports()
        want = {"j6": args.j6 or guess(names, "j-6", "j6"),
                "s1": args.s1 or guess(names, "s-1", "s1")}
        for role, nm in want.items():
            if nm is None:
                print(f"  ! no port for {role.upper()} - that part will be silent")
                continue
            if nm not in names:
                raise SystemExit(f"Port '{nm}' not found. Run `ports` to list them.")
            ports[role] = Port(kind, mod, nm)
            print(f"  {role.upper()} -> {nm}")

    count_in = getattr(args, "count_in", 0) or 0
    beat = 60.0 / bpm
    try:
        if count_in:
            print(f"  count-in {count_in} beats...", flush=True)
            for b in range(count_in):
                print(f"    {b+1}", flush=True)
                time.sleep(beat)
        loops = 0
        while True:
            t0 = time.perf_counter()
            for when, role, status, d1, d2 in events:
                delay = when - (time.perf_counter() - t0)
                if delay > 0:
                    time.sleep(delay)
                p = ports.get(role)
                if p:
                    p.send(status, d1, d2)
            # let the last note ring out before looping
            tail = span - (time.perf_counter() - t0)
            if tail > 0:
                time.sleep(tail)
            loops += 1
            print(f"  loop {loops} done", flush=True)
            if not args.loop:
                break
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        for p in ports.values():
            p.panic(); p.close()
    return 0


UNIT_PATTERNS = {"j6": ("j-6", "j6"), "s1": ("s-1", "s1")}


def unit_of(name):
    for unit, pats in UNIT_PATTERNS.items():
        if guess([name or ""], *pats):
            return unit
    return None


def default_library(unit):
    return os.path.join(os.path.expanduser("~"), "aira-library", unit or "other")


def _need_backend():
    kind, mod = open_backend()
    if kind is None:
        raise SystemExit("No MIDI backend.\n  pip install mido python-rtmidi")
    return kind, mod


def _print_inputs(names):
    if not names:
        print("No MIDI inputs found. Check the USB-C cable carries data and the unit is on.")
        return
    print(f"{len(names)} MIDI input(s):")
    for i, nm in enumerate(names):
        tag = unit_of(nm)
        print(f"  [{i}] {nm}" + (f"   <- {tag.upper()}" if tag else ""))


def open_capture_ports(args):
    """-> (unit, InPort, Port-or-None). Honours --port/--unit/--out-port."""
    kind, mod = _need_backend()
    names = list_inputs()
    if args.port:
        name = args.port if args.port in names else guess(names, args.port)
        if name is None:
            _print_inputs(names)
            raise SystemExit(f"No input matching '{args.port}'.")
    else:
        pats = UNIT_PATTERNS[args.unit] if args.unit else ("j-6", "j6", "s-1", "s1")
        name = guess(names, *pats)
        if name is None:
            _print_inputs(names)
            raise SystemExit("Could not spot a J-6 or S-1 input - pass --port <name>.")
    unit = args.unit or unit_of(name) or "other"
    inp = InPort(kind, mod, name)
    print(f"  listening on {name}  ({unit.upper()})")

    out = None
    if getattr(args, "send_start", False) or getattr(args, "program_change", False):
        outs = list_ports()
        oname = args.out_port or guess(outs, *UNIT_PATTERNS.get(unit, (name,)))
        if oname is None or oname not in outs:
            raise SystemExit(f"No output port for {unit.upper()} - pass --out-port <name>. "
                             f"Outputs: {', '.join(outs) or '(none)'}")
        out = Port(kind, mod, oname)
        print(f"  sending to   {oname}")
    return unit, inp, out


def _unique(path):
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{stem}-{i}{ext}"):
        i += 1
    return f"{stem}-{i}{ext}"


def save_take(res, out_dir, stem, unit, fmt=0):
    """Analyse a finished take, write <stem>.mid (stem may hold {key}) and index it.

    Returns the path written, or None when the take held no notes.
    """
    notes = res["notes"]
    if not notes:
        print("  nothing captured - no notes arrived.")
        return None
    analysis = analyze_notes(notes, TPQ, force="chords" if unit == "j6" else None)
    key = analysis["key"] or "nokey"
    path = _unique(os.path.join(out_dir, stem.format(key=key) + ".mid"))
    name = os.path.splitext(os.path.basename(path))[0]
    write_smf(path, notes, res["bpm"], name=name, fmt=fmt, end_tick=res["end_tick"])
    tempo = f"{res['bpm']:g} BPM" + ("" if res["clocked"] else " (assumed - no MIDI clock seen)")
    print(f"  saved  {path}")
    print(f"         {len(notes)} notes, {res['bars']} bar(s), {tempo}, ended by {res['reason']}")
    print(describe(analysis, indent="         "))
    update_index(os.path.join(out_dir, "index.csv"),
                 [index_row(os.path.basename(path), unit, analysis, res["bpm"], res["bars"])])
    return path


def _take(inp, args, out=None, program=None):
    """One capture pass. Sends Program Change / Start / Stop if asked."""
    if out is not None and program is not None:
        out.send_raw([0xC0 | ((args.channel - 1) & 0x0F), (program - 1) & 0x7F])
        time.sleep(0.3)
    inp.drain()
    cap = Capture(bpm=args.bpm, bars=args.bars, silence=args.silence)
    if out is not None and args.send_start:
        cap.arm(time.perf_counter())
        out.send_raw([0xFA])
    try:
        run_capture(inp, cap)
    finally:
        if out is not None and args.send_start:
            out.send_raw([0xFC])
    return cap


def cmd_capture(args):
    if args.list:
        names = list_inputs()
        if names is None:
            print("No MIDI backend installed.\n  pip install mido python-rtmidi")
            return 1
        _print_inputs(names)
        return 0
    unit, inp, out = open_capture_ports(args)
    out_dir = os.path.expanduser(args.out or default_library(unit))
    stops = ["Ctrl-C"]
    if args.bars:
        stops.append(f"{args.bars} bar(s)")
    if args.silence:
        stops.append(f"{args.silence:g}s of silence")
    print("  press PLAY on the unit" + (" (sending Start)" if args.send_start else "")
          + f" - stops on {', '.join(stops)}", flush=True)
    try:
        cap = _take(inp, args, out)
    finally:
        inp.close()
        if out:
            out.close()
    res = cap.finish(quantize=args.quantize)
    stem = args.name or (unit + "-" + time.strftime("%Y%m%d-%H%M%S") + "-{key}")
    return 0 if save_take(res, out_dir, stem, unit, fmt=args.format) else 1


def cmd_harvest(args):
    unit, inp, out = open_capture_ports(args)
    out_dir = os.path.expanduser(args.out or default_library(unit))
    print(f"  saving to    {out_dir}")
    if args.program_change:
        print("  EXPERIMENTAL: sending Program Change to pick each pattern. Not all "
              "firmware honours it - check the unit's display, and fall back to "
              "selecting by hand if it does not follow.")
    how = ("Enter starts it" if args.send_start
           else "press Enter, then PLAY on the unit")
    n, saved = args.first, []
    try:
        while True:
            try:
                ans = input(f"\n[{unit.upper()} pattern {n:02d}] stop the unit, select pattern "
                            f"{n}, {how}.  (s=skip, <number>=jump, q=quit) ").strip().lower()
            except EOFError:
                break
            if ans in ("q", "quit", "exit"):
                break
            if ans == "s":
                n += 1
                continue
            if ans.isdigit():
                n = int(ans)
                continue
            print(f"  recording {args.bars} bar(s)... Ctrl-C abandons this pattern", flush=True)
            cap = _take(inp, args, out, program=n if args.program_change else None)
            if cap.done == "ctrl-c":
                print("  abandoned - nothing saved.")
                continue
            res = cap.finish(quantize=args.quantize)
            path = save_take(res, out_dir, f"{unit}-p{n:02d}-{{key}}", unit, fmt=args.format)
            if path:
                saved.append(path)
                n += 1
    except KeyboardInterrupt:
        print()
    finally:
        inp.close()
        if out:
            out.close()
    print(f"\n{len(saved)} pattern(s) saved to {out_dir} (see index.csv there).")
    return 0


def _midi_files(paths):
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for f in sorted(files):
                    if f.lower().endswith((".mid", ".midi")) and not f.startswith("."):
                        yield os.path.join(root, f)
        elif os.path.isfile(p):
            yield p
        else:
            print(f"  ! {p}: not found")


def cmd_scan(args):
    files = sorted(set(_midi_files(args.paths)))
    if not files:
        raise SystemExit("No .mid files found.")
    if args.index:
        index = os.path.expanduser(args.index)
    else:
        first = os.path.expanduser(args.paths[0])
        index = os.path.join(first if os.path.isdir(first) else os.path.dirname(first) or ".",
                             "index.csv")
    base = os.path.dirname(os.path.abspath(index))
    rows = []
    for path in files:
        try:
            tpq, bpm, notes = notes_from_smf(path, drum_channel=args.drum_channel)
        except (ValueError, IndexError, struct.error) as e:
            print(f"\n{path}\n  ! unreadable: {e}")
            continue
        unit = unit_of(os.path.basename(path)) or ""
        # read everything at 480 TPQ so the chord/bar maths is the same
        if tpq != TPQ:
            notes = [(s * TPQ // tpq, e * TPQ // tpq, p, v, c) for s, e, p, v, c in notes]
        analysis = analyze_notes(notes, TPQ, force="chords" if unit == "j6" else None)
        bars = (max(n[0] for n in notes) // BAR + 1) if notes else 0
        bpm = round(bpm, 1)
        if not unit and analysis["parts"]:
            unit = "+".join(sorted({p["kind"] for p in analysis["parts"]}))
        print(f"\n{os.path.relpath(path)}  {bpm:g} BPM  {bars} bar(s)  {len(notes)} notes")
        print(describe(analysis))
        rel = os.path.relpath(os.path.abspath(path), base)
        if rel.startswith(".."):
            rel = os.path.abspath(path)          # outside the index folder
        rows.append(index_row(rel.replace(os.sep, "/"), unit, analysis, bpm, bars))
    if rows and not args.no_index:
        update_index(index, rows)
        print(f"\n{len(rows)} file(s) indexed -> {index}")
    return 0


def cmd_backup(args):
    src = args.source
    if not os.path.isdir(src):
        raise SystemExit(f"{src} is not a mounted folder. Put the unit in drive mode: "
                         "power OFF, hold PLAY, power ON.")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(args.dest, os.path.basename(src.rstrip("/\\")) + "-" + stamp)
    os.makedirs(dest, exist_ok=True)
    n = 0
    for root, _dirs, files in os.walk(src):
        for f in files:
            if f.startswith("."):
                continue
            s = os.path.join(root, f)
            rel = os.path.relpath(s, src)
            d = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
            print(f"  {rel}  ({os.path.getsize(s)} bytes)")
    print(f"\nCopied {n} file(s) -> {dest}")
    print("This only reads from the unit. Nothing was written to it.")
    return 0


def cmd_analyze(args):
    root = args.path
    if not os.path.isdir(root):
        raise SystemExit(f"{root} is not a folder")
    files = []
    for dirpath, _dirs, names in os.walk(root):
        for nm in names:
            if nm.startswith("."):
                continue
            files.append(os.path.join(dirpath, nm))
    if not files:
        raise SystemExit(f"No files under {root}")

    print(f"{len(files)} file(s) under {root}\n" + "=" * 68)
    for path in sorted(files):
        blob = open(path, "rb").read()
        rel = os.path.relpath(path, root)
        print(f"\n{rel}")
        print(f"  size    {len(blob)} bytes")
        if not blob:
            continue
        head = blob[:16]
        print(f"  magic   {head[:8].hex(' ')}  |{_printable(head[:8])}|")
        counts = Counter(blob)
        top = counts.most_common(3)
        print(f"  bytes   {len(counts)} distinct, most common "
              + ", ".join(f"0x{b:02x}x{c}" for b, c in top))
        runs = _trailing_run(blob)
        if runs:
            print(f"  tail    {runs[1]} bytes of 0x{runs[0]:02x} padding at the end")
        cands, body_len, pad = _stride_candidates(blob)
        if cands:
            print(f"  records (over {body_len} bytes once padding is dropped):")
            for c in cands:
                if c.get("multiple"):
                    flags = ["a multiple - same structure seen again"]
                elif c["round"]:
                    flags = ["divides exactly, round count"]
                elif c["exact"]:
                    flags = ["divides exactly"]
                else:
                    flags = ["does not divide exactly - weaker"]
                print(f"    {c['stride']:>4}-byte records x {c['rows']:<4} "
                      f"({c['const_cols']} constant column"
                      f"{'' if c['const_cols']==1 else 's'})  <- {flags[0]}")
            best = cands[0]
            print(f"    best guess: {best['stride']}-byte records, "
                  f"{best['rows']} of them")
            for col in range(min(best["stride"], 64)):
                vals = {_strip_padding(blob)[r * best["stride"] + col]
                        for r in range(best["rows"])}
                if len(vals) == 1:
                    print(f"      byte {col:>3} is always 0x{vals.pop():02x}")
        print("  head    " + blob[:32].hex(' '))
    print("\n" + "=" * 68)
    print("Send this output (and the files) back to Claude to work out the layout.")
    return 0


def _printable(b):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in b)


def _strip_padding(blob):
    """Drop a trailing run of one repeated byte - it skews every column test."""
    if not blob:
        return blob
    last = blob[-1]
    i = len(blob) - 1
    while i >= 0 and blob[i] == last:
        i -= 1
    return blob[:i + 1] if len(blob) - 1 - i >= 16 else blob


def _stride_candidates(blob, lo=4, hi=1024, top=5):
    """Rank record sizes by how many byte columns hold the same value in every row.

    Real pattern data is mostly varying, so a handful of constant columns is a
    strong signal - across 8+ rows a column staying constant by chance is
    vanishingly unlikely. Multiples of the true stride score too, so prefer the
    smallest stride that scores, and flag strides that divide the data exactly
    into a round number of records (these units hold 64 patterns).
    """
    body = _strip_padding(blob)
    n = len(body)
    out = []
    for stride in range(lo, min(hi, n // 8) + 1):
        rows = n // stride
        if rows < 8:
            continue
        const = sum(
            1 for col in range(stride)
            if len({body[r * stride + col] for r in range(rows)}) == 1
        )
        if const < 2:
            continue
        out.append({
            "stride": stride,
            "rows": rows,
            "const_cols": const,
            "exact": n % stride == 0,
            "round": (n % stride == 0) and rows in (8, 16, 32, 64, 100, 128, 256),
        })
    # Any multiple of the true record size also scores, and scores higher, so the
    # fundamental unit is the SMALLEST stride that divides the data exactly. Rank
    # those by size; treat everything else as weaker supporting evidence.
    exact = sorted((c for c in out if c["exact"]), key=lambda c: c["stride"])
    rest = sorted((c for c in out if not c["exact"]),
                  key=lambda c: (-c["const_cols"], c["stride"]))
    ranked = exact + rest
    if exact:
        base = exact[0]["stride"]
        for c in ranked:
            c["multiple"] = c is not exact[0] and c["exact"] and c["stride"] % base == 0
    else:
        for c in ranked:
            c["multiple"] = False
    return ranked[:top], len(body), len(blob) - len(body)


def _trailing_run(blob):
    last = blob[-1]
    i = len(blob) - 1
    while i >= 0 and blob[i] == last:
        i -= 1
    run = len(blob) - 1 - i
    return (last, run) if run >= 16 else None


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Drive and inspect Roland AIRA Compact S-1 / J-6 locally.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ports", help="list MIDI outputs/inputs and guess the two units")

    for name, helptext in (("play", "stream a song to the synths"),
                           ("rec", "same, with a count-in for recording")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("song", help="song id (e.g. acid-rain) or path to a .mid")
        p.add_argument("--j6", help="exact J-6 port name")
        p.add_argument("--s1", help="exact S-1 port name")
        p.add_argument("--loop", action="store_true", help="repeat until Ctrl-C")
        p.add_argument("--dry-run", action="store_true",
                       help="work out the timing but open no ports")
        if name == "rec":
            p.add_argument("--count-in", type=int, default=4, metavar="BEATS")

    def capture_opts(p, bars_default):
        p.add_argument("--port", help="MIDI input name (or part of it); default: "
                       "the first input that looks like a J-6 or S-1")
        p.add_argument("--unit", choices=("j6", "s1"),
                       help="which unit is playing (default: from the port name)")
        p.add_argument("--out", metavar="DIR",
                       help="folder for .mid files + index.csv (default ~/aira-library/<unit>)")
        p.add_argument("--bpm", type=float, default=120.0,
                       help="tempo to assume when the unit sends no MIDI clock (default 120)")
        p.add_argument("--bars", type=int, default=bars_default,
                       help="stop after this many 4/4 bars"
                       + (f" (default {bars_default})" if bars_default else ""))
        p.add_argument("--silence", type=float, default=4.0, metavar="SECONDS",
                       help="stop after this long with no notes, once notes have "
                       "arrived (default 4, 0 = never)")
        p.add_argument("--quantize", type=int, default=0, choices=(0, 4, 8, 16, 32),
                       metavar="N", help="snap note starts to 1/N notes (4, 8, 16, 32; "
                       "default 0 = as played)")
        p.add_argument("--format", type=int, default=0, choices=(0, 1),
                       help="SMF format to write (default 0 - one track)")
        p.add_argument("--send-start", action="store_true",
                       help="send MIDI Start to the unit to begin, Stop when done")
        p.add_argument("--out-port", help="MIDI output for --send-start / --program-change "
                       "(default: guessed from the unit)")

    p = sub.add_parser("capture", help="record what a unit plays into a .mid file",
                       description="Record the notes a J-6 / S-1 sends while it plays. "
                       "Uses the unit's MIDI clock for tempo and bar lines when it "
                       "sends one, otherwise --bpm.")
    p.add_argument("--list", action="store_true", help="list MIDI inputs and exit")
    p.add_argument("--name", help="file name without .mid; {key} is replaced by the "
                   "detected key (default <unit>-<date>-<time>-{key})")
    capture_opts(p, None)

    p = sub.add_parser("harvest", help="capture pattern after pattern into a library",
                       description="Prompts you to select each pattern on the unit, "
                       "records one pass of it and saves e.g. j6-p01-Amin.mid, "
                       "until you type q.")
    p.add_argument("--first", type=int, default=1, help="pattern number to start at")
    p.add_argument("--program-change", action="store_true",
                   help="EXPERIMENTAL: also send Program Change N-1 to select pattern N. "
                   "Some firmware ignores or remaps it - watch the unit's display")
    p.add_argument("--channel", type=int, default=1,
                   help="MIDI channel for --program-change (default 1)")
    capture_opts(p, 4)

    p = sub.add_parser("scan", help="detect key/chords in existing .mid files and "
                       "write index.csv")
    p.add_argument("paths", nargs="+", help=".mid files and/or folders (searched recursively)")
    p.add_argument("--index", help="where to write the index (default: index.csv in "
                   "the first folder given)")
    p.add_argument("--no-index", action="store_true", help="just print, write nothing")
    p.add_argument("--drum-channel", type=int, default=10, metavar="CH",
                   help="ignore notes on this channel (default 10; 0 keeps all)")

    p = sub.add_parser("backup", help="copy a mounted unit's files somewhere safe")
    p.add_argument("source", help="the mounted unit, e.g. /Volumes/J-6 or E:\\")
    p.add_argument("dest", help="folder to copy into")

    p = sub.add_parser("analyze", help="inspect backup files and report structure")
    p.add_argument("path", help="folder of files copied off a unit")

    args = ap.parse_args()
    if args.cmd == "ports":
        return cmd_ports(args)
    if args.cmd in ("play", "rec"):
        if args.cmd == "play":
            args.count_in = 0
        return cmd_play(args)
    if args.cmd == "capture":
        return cmd_capture(args)
    if args.cmd == "harvest":
        return cmd_harvest(args)
    if args.cmd == "scan":
        return cmd_scan(args)
    if args.cmd == "backup":
        return cmd_backup(args)
    if args.cmd == "analyze":
        return cmd_analyze(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
