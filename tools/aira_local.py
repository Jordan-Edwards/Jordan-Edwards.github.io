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

`ports`, `play` and `rec` need a MIDI backend:

    pip install mido python-rtmidi

`backup` and `analyze` are pure standard library - nothing to install. Start
there if you just want to see what is on the units.

Drive mode: power the unit OFF, hold PLAY, power it back ON. It mounts as a
disk with BACKUP and RESTORE folders.
"""

import argparse
import os
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

    def close(self):
        try:
            if self.kind == "mido":
                self._p.close()
            else:
                self._p.close_port()
        except Exception:
            pass


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

    sub.add_parser("ports", help="list MIDI outputs and guess the two units")

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
    if args.cmd == "backup":
        return cmd_backup(args)
    if args.cmd == "analyze":
        return cmd_analyze(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
