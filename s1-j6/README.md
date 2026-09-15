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

There's no published SysEx format for writing patterns into the S-1's pattern memory,
so option 2 is genuinely by hand; the grid is laid out to make that fast.

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
