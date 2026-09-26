# Handoff: J-6 / S-1 work (for the Claude session on Jordan's PC)

You are picking up from a cloud Claude Code session.

- Cloud session: https://claude.ai/code/session_01UZbXbvurqDJTqdUSircjVY
  (session id `session_01UZbXbvurqDJTqdUSircjVY`, title "J6/S1 handoff - Jordan-Edwards.github.io")
- Repo: https://github.com/Jordan-Edwards/Jordan-Edwards.github.io
- Branch: `claude/codex-j6-s1-extraction-heeze5`

This is **not** in Jordan's other local projects. Get it with:

```
git clone -b claude/codex-j6-s1-extraction-heeze5 https://github.com/Jordan-Edwards/Jordan-Edwards.github.io
cd Jordan-Edwards.github.io
pip install mido python-rtmidi
```

## Read this first: what the job is

The job is **a general toolkit/library for Jordan's own music**, not songs to recreate.
It is a library of parts that combine with the J-6 and S-1: chord progressions,
chord arps, S-1 bass lines, leads and polyrhythm loops, in every key. The genres
are the ones Jordan makes and listens to (synthwave, acid, deep/Chicago house,
lo-fi, Berlin/melodic techno, UK garage, DnB, trap/dark pop, ambient/cinematic,
future garage). Jordan MIDI-copies these parts out of the OP-XY onto different
tracks and synths.

**Not the job:**
- the Zelda songs
- the old songbook tunes (Greensleeves, Ode to Joy, Rising Sun, etc.)
- transcribing any existing song

Those are older, separate work. Don't search Jordan's other local projects for this.

The library is already built on this branch (see Goals 2). What's left needs the
PC: capture the units' own patterns, then use the sets from the OP-XY.

## Goals

1. **Pull the patterns stored on the J-6 and S-1 into a MIDI library.** Both
   units are plugged into this PC over USB, and the cloud session couldn't reach
   them. `tools/aira_local.py` already does this:
   ```
   python tools/aira_local.py ports                 # confirm both units show up
   python tools/aira_local.py harvest --unit j6     # select pattern, PLAY, repeat
   python tools/aira_local.py harvest --unit s1
   python tools/aira_local.py scan ~/aira-library   # key/chords index
   ```
   Stop the unit between patterns. Pass `--bpm` if the unit isn't sending clock.
   Captures land in `~/aira-library/<unit>/` with the key in the filename, plus
   `index.csv`. This is the first run on real hardware, so report any errors.
2. **Keep the sets separate.** They are listed in `s1-j6/sets/index.json`, and
   Jordan switches between them by name:
   - `genre-kits`: `s1-j6/library/`, 50 research-sourced kits × 24 keys
     (chords, arp, S-1 bass, lead).
   - `sinnoh-style`: `s1-j6/sets/sinnoh-style/`, 8 original DS-era-feel tracks.
     These are original compositions, not transcriptions of game music.
   - Harvested captures become a third set (e.g. `my-units`) and don't replace
     the others.
3. **Don't overwrite anything on the units without a backup.** Loading a set
   onto the S-1 uses its 64 pattern slots. Back up first (drive mode, then
   `python tools/aira_local.py backup <drive> <folder>`), and ask Jordan which set
   to load before writing anything.
4. **Getting parts into the OP-XY / M8:**
   `python tools/aira_local.py play <file.mid> --to OP-XY --loop`
   streams any library or set file while the OP-XY records.

## Reference

- `s1-j6/README.md`: everything above, in detail.
- Phone printout of sinnoh-style: https://claude.ai/artifact/8YqywUXvVaf7LFUFiNop98
- The cloud session can be reached when this PC session runs under
  `claude remote-control`.
