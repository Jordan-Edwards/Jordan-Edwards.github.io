# S-1 / J-6 Songbook

Eight songs arranged for the Roland AIRA Compact **J-6 Chord Synthesizer** (chords)
and **S-1 Tweak Synth** (bass / lead).

Open `index.html` — or the published page at `/s1-j6/` — for the playable version.

## What's here

| File | What it is |
|---|---|
| `index.html` | The songbook: setup directions, step grids, Web MIDI player, speaker preview |
| `songs.js` | Generated song data (do not hand-edit) |
| `midi/*.mid` | One Standard MIDI File per song — 3 tracks: tempo, J-6 on ch 1, S-1 on ch 2 |
| `../tools/build_songs.py` | The generator. Everything above is derived from it. |

## Three ways to play them

1. **Live over USB** — plug both synths in, open the page in Chrome or Edge, hit
   *Connect MIDI*, assign each device, press Play. Each device enumerates as its own
   USB MIDI port, so both stay on their default channel 1 and nothing needs
   reconfiguring.
2. **Punch into the S-1** — follow the step grid so the pattern lives in the device
   standalone. Accents and slides are marked per step.
3. **Drag the `.mid` into a DAW** — route track 2 to the J-6 and track 3 to the S-1.

### A note on drive mode

AIRA Compacts *do* mount as USB mass storage: power the unit off, hold **PLAY**, power
it back on, and it shows up as an external disk with `BACKUP` and `RESTORE` folders.

That is Roland's own backup mechanism — it moves patterns you already made between a
unit and a computer. The binary layout of those files isn't publicly documented, so it
is not a drop-box for arbitrary new patterns, and the songs here cannot simply be
copied into it. Option 2 above is still by hand; the grid is laid out to make that fast.

## Running it locally (`tools/aira_local.py`)

The page drives the synths from a browser. `tools/aira_local.py` does the same job
from a terminal **on the computer the synths are plugged into**, plus two things a
browser cannot do: copy a unit's `BACKUP` folder off while it's in drive mode, and
pull those files apart so the pattern format can be worked out.

```sh
python3 tools/aira_local.py ports                  # list MIDI outs, guess the two units
python3 tools/aira_local.py play acid-rain --loop  # stream it to the synths
python3 tools/aira_local.py rec  acid-rain         # same, with a 4-beat count-in
python3 tools/aira_local.py backup /Volumes/J-6 ~/aira-backups
python3 tools/aira_local.py analyze ~/aira-backups/J-6-20260915-0638
```

`ports`, `play` and `rec` need `pip install mido python-rtmidi`.
**`backup` and `analyze` are pure standard library — nothing to install.**

`backup` only ever reads from the unit; it never writes to it.

`analyze` reports each file's magic bytes, padding, and the repeating record size,
ranked. It reports the *smallest* stride that divides the data exactly, because every
multiple of a record size also scores — a "768-byte record" is usually eight 96-byte
ones. It is validated both ways: it recovers a planted record structure with its exact
header bytes, and claims nothing at all on random noise.

## Rebuilding

```sh
python3 tools/build_songs.py
```

Pure stdlib, no dependencies. It validates that every song's step count exactly fills
its bars and stays within the S-1's 64-step limit, then writes `songs.js` and the
MIDI files together so the page and the files can't drift apart.

## Songs

| Song | Genre | BPM | Key | S-1 part |
|---|---|---|---|---|
| Neon Mile | Synthwave | 100 | A minor | Octave bass |
| Acid Rain | Acid techno | 130 | A minor | 303-style acid bass |
| Deep End | Deep house | 122 | F minor | Sub bass |
| Lo-Fi Sunday | Lo-fi / chill | 78 | C major | Soft lead |
| Midnight Drive | Dark techno | 140 | D minor | Driving bass |
| Greensleeves | Traditional | 90 | A minor | Lead melody |
| Ode to Joy | Traditional | 120 | C major | Lead melody |
| House of the Rising Sun | Traditional | 72 | A minor | Rolling arpeggio |

The three traditional tunes are public domain. The other five are originals written
for these two boxes.
