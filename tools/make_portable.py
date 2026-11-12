#!/usr/bin/env python3
"""Build the take-anywhere copy of the S-1 / J-6 songbook.

Writes two things into dist/:

  s1-j6-songbook.html   The whole songbook in ONE file. Song data is inlined and
                        every .mid is embedded as a data: URI, so it opens from a
                        USB stick, an email attachment or a locked-down machine
                        with no network and no web server.

  s1-j6-portable.zip    That file, plus the loose MIDI files (for a DAW), the
                        terminal tool aira_local.py, and a START-HERE.txt.

Pure stdlib. The zip is byte-for-byte reproducible: fixed timestamps, sorted
entries - rebuilding without changing a song produces no diff.

    python3 tools/make_portable.py
"""

import base64
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "s1-j6")
DIST = os.path.join(ROOT, "dist")
TOP = "s1-j6-portable"                 # folder name inside the zip
STAMP = (2026, 1, 1, 0, 0, 0)          # fixed, so the zip is reproducible

SCRIPT_TAG = '<script src="songs.js"></script>'

START_HERE = """\
S-1 / J-6 SONGBOOK - PORTABLE COPY
==================================

Everything here works with no internet connection and nothing to install.

1. THE SONGBOOK
   Double-click  s1-j6-songbook.html
   It is one self-contained file: setup directions, step grids, speaker
   preview and the MIDI downloads are all inside it.

   To drive the synths from the page, open it in Chrome or Edge (Web MIDI
   is not in Firefox or Safari), plug both units in over USB, press
   "Connect MIDI" and allow the MIDI prompt. Everything else - reading the
   grids, the speaker preview, downloading .mid files - works in any browser.

2. THE MIDI FILES
   midi/ holds one Standard MIDI File per song for dragging into a DAW.
   Track 2 is the J-6 (channel 1), track 3 is the S-1 (channel 2).

3. THE TERMINAL TOOL (optional, needs Python 3)
   python3 aira_local.py ports                 list MIDI outs
   python3 aira_local.py play acid-rain --loop stream a song to the synths
   python3 aira_local.py backup <drive> <dest> copy a unit's BACKUP folder
   python3 aira_local.py analyze <folder>      inspect backup files

   backup and analyze need nothing installed.
   ports / play / rec need:  pip install mido python-rtmidi
   If pip is blocked where you are, install those at home first - or just
   use the songbook page, which needs neither.

SONGS
-----
"""


def read(path, mode="r"):
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def build_single_file():
    """Return index.html with songs.js and every MIDI file folded into it."""
    html = read(os.path.join(SRC, "index.html"))
    if html.count(SCRIPT_TAG) != 1:
        sys.exit("index.html no longer loads songs.js the way make_portable.py expects.")

    songs_js = read(os.path.join(SRC, "songs.js"))
    midi_dir = os.path.join(SRC, "midi")
    names = sorted(f for f in os.listdir(midi_dir) if f.endswith(".mid"))
    if not names:
        sys.exit("No MIDI files found - run tools/build_songs.py first.")

    uris = {
        "midi/" + n: "data:audio/midi;base64,"
        + base64.b64encode(read(os.path.join(midi_dir, n), "rb")).decode("ascii")
        for n in names
    }
    # Swap each song's relative MIDI path for the embedded copy.
    patch = (
        "(function(m){(window.SONGS||[]).forEach(function(s){"
        "if(m[s.midi]){s.midi=m[s.midi];}});})(%s);" % json.dumps(uris, sort_keys=True)
    )
    body = (songs_js.rstrip() + "\n" + patch).replace("</", "<\\/")
    inline = "<script>\n%s\n</script>" % body
    return html.replace(SCRIPT_TAG, inline), names


def song_table():
    """One line per song for START-HERE.txt, read from the generated data."""
    js = read(os.path.join(SRC, "songs.js"))
    data = json.loads(js[js.index("["): js.rindex("]") + 1])
    missing = [s["id"] for s in data
               if not os.path.isfile(os.path.join(SRC, s["midi"]))]
    if missing:
        sys.exit("Songs with no MIDI file: " + ", ".join(missing))
    return "".join(
        "  %-26s %-14s %3s BPM  %s\n" % (s["title"], s["genre"], s["bpm"], s["key"])
        for s in data
    ), len(data)


def add(z, arcname, data):
    info = zipfile.ZipInfo(TOP + "/" + arcname, date_time=STAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, data)


def main():
    page, midi_names = build_single_file()
    table, count = song_table()
    os.makedirs(DIST, exist_ok=True)

    html_path = os.path.join(DIST, "s1-j6-songbook.html")
    with open(html_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)

    # aira_local.py looks for songs in ../s1-j6/midi; in the flat bundle the
    # MIDI folder sits right beside it.
    tool = read(os.path.join(ROOT, "tools", "aira_local.py"))
    marker = 'MIDI_DIR = '
    line = next((l for l in tool.splitlines() if l.startswith(marker)), None)
    if line is None:
        sys.exit("aira_local.py no longer defines MIDI_DIR at top level.")
    tool = tool.replace(
        line,
        'MIDI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "midi")',
    )

    zip_path = os.path.join(DIST, TOP + ".zip")
    with zipfile.ZipFile(zip_path, "w") as z:
        add(z, "START-HERE.txt", (START_HERE + table).replace("\n", "\r\n"))
        add(z, "s1-j6-songbook.html", page)
        add(z, "aira_local.py", tool)
        for n in midi_names:
            add(z, "midi/" + n, read(os.path.join(SRC, "midi", n), "rb"))

    for p in (html_path, zip_path):
        print("%7d bytes  %s" % (os.path.getsize(p), os.path.relpath(p, ROOT)))
    print("%d songs, %d MIDI files" % (count, len(midi_names)))


if __name__ == "__main__":
    main()
