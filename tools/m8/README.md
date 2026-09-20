# M8 sample transfer

`m8-transfer.sh` adds sample packs to a Dirtywave M8 / M8 Model:02 SD card.

## Run it

```sh
bash tools/m8/m8-transfer.sh --dry-run   # show the plan, write nothing
bash tools/m8/m8-transfer.sh             # transfer, verify, eject
```

Put the M8 into USB-disk mode first so its card mounts. If auto-detection finds
no M8 — or more than one candidate — the script stops and asks rather than
guessing a volume.

Useful flags: `--volume PATH`, `--source DIR`, `--no-download`, `--no-eject`.

## What it guarantees

- Never formats, partitions, or deletes. Existing songs, instruments, samples
  and presets are left untouched.
- Writes only to a volume carrying an M8 folder signature (`Samples` plus at
  least two of `Songs`/`Instruments`/`Eqs`/`Themes`/`Scales`/`Renders`).
- Copies `.wav` audio only. MIDI files and J-6 patch files are counted and
  reported, never installed as M8 samples.
- Validates every archive (zip magic bytes, `unzip -t`, contains audio) before
  extracting.
- Checks free space with a 50 MB headroom margin before copying.
- Skips byte-identical files; on a name clash with *different* audio it keeps
  both rather than overwriting.
- Verifies every copied file by SHA-256 after the copy and reports mismatches.
- Original filenames are preserved, so tempo/key markers such as
  `Apache_165bpm_Fmin.wav` survive.

## Layout it creates

```
Samples/MusicRadar/90s Jungle/...
Samples/MusicRadar/Drum Breaks/...
Samples/MusicRadar/Deep House/...
Samples/Electronic Chord Lab/Chords/   (from CHORD_WAV)
Samples/Electronic Chord Lab/Stabs/    (from STABS_WAV)
```

## Compatibility handling

Accepted as-is: PCM WAV, 1–2 channels, 8/16/24-bit, 8–48 kHz. Anything else
(32-bit float, exotic codecs) is converted to 16-bit/44.1 kHz when `ffmpeg` or
`sox` is present, and otherwise skipped and reported — never shipped raw.

## After it finishes

Ejecting the volume does **not** take the M8 out of USB-disk mode. Exit that
mode on the device itself, or power-cycle it, before the tracker can read the
card again.
