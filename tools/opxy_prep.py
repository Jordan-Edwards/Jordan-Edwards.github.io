#!/usr/bin/env python3
"""OP-XY prep: back up the device, verify the copy, and inventory sample libraries.

Run on the computer the OP-XY is plugged into (with the OP-XY mounted as a disk).
Nothing on the device is modified or deleted.

  python3 opxy_prep.py backup  <opxy_mount> <backup_dir>
  python3 opxy_prep.py inventory <out.tsv> <sample_dir> [<sample_dir> ...]

The inventory TSV (path, size_kb, seconds, channels, rate) is compact on purpose:
hand it to Claude to curate and rename without listing folders file by file.
"""
import hashlib, os, shutil, sys, time, wave

AUDIO = {".wav", ".aif", ".aiff", ".flac", ".mp3"}


def files(root):
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.startswith("._"):
                yield os.path.join(d, f)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def backup(src, dst_root):
    dst = os.path.join(dst_root, "opxy-backup-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("._*", ".Spotlight-V100", ".Trashes", ".fseventsd"))
    bad, n, total = [], 0, 0
    for p in files(src):
        rel = os.path.relpath(p, src)
        if any(part.startswith(".") and part != "." for part in rel.split(os.sep)):
            continue
        q = os.path.join(dst, rel)
        n += 1
        total += os.path.getsize(p)
        if not os.path.exists(q) or os.path.getsize(p) != os.path.getsize(q) or sha(p) != sha(q):
            bad.append(rel)
    print(f"backup: {dst}\nfiles: {n}  size: {total / 1e6:.1f} MB")
    if bad:
        print(f"VERIFY FAILED for {len(bad)} files (do NOT wipe the device):")
        print("\n".join(bad[:20]))
        sys.exit(1)
    print("VERIFIED: every file matches by size and SHA-256. Safe to wipe the device.")


def inventory(out, roots):
    rows = 0
    with open(out, "w") as fh:
        fh.write("path\tsize_kb\tseconds\tchannels\trate\n")
        for root in roots:
            for p in files(root):
                if os.path.splitext(p)[1].lower() not in AUDIO and not p.endswith("patch.json"):
                    continue
                secs = ch = rate = ""
                if p.lower().endswith(".wav"):
                    try:
                        with wave.open(p) as w:
                            rate, ch = w.getframerate(), w.getnchannels()
                            secs = f"{w.getnframes() / rate:.2f}"
                    except Exception:
                        pass
                fh.write(f"{p}\t{os.path.getsize(p) // 1024}\t{secs}\t{ch}\t{rate}\n")
                rows += 1
    print(f"inventory: {rows} entries -> {out}")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "backup":
        backup(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 4 and sys.argv[1] == "inventory":
        inventory(sys.argv[2], sys.argv[3:])
    else:
        print(__doc__)
