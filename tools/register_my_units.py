#!/usr/bin/env python3
"""Copy harvested J-6/S-1 captures into s1-j6/sets/my-units/ and register the set.

Run after `aira_local.py harvest --unit j6|s1` and `aira_local.py scan`.
Only adds/updates the "my-units" entry in s1-j6/sets/index.json; the other sets
are left as they are.

    python tools/register_my_units.py [~/aira-library]
"""
import csv
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETS = os.path.join(ROOT, "s1-j6", "sets")
DEST = os.path.join(SETS, "my-units")


def main():
    src = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/aira-library")
    tracks = []
    for unit in ("j6", "s1"):
        udir = os.path.join(src, unit)
        if not os.path.isdir(udir):
            print(f"skip {unit}: {udir} not found")
            continue
        rows = {}
        idx = os.path.join(udir, "index.csv")
        if os.path.isfile(idx):
            with open(idx, newline="") as f:
                rows = {os.path.basename(r.get("file", "")): r for r in csv.DictReader(f)}
            os.makedirs(os.path.join(DEST, unit), exist_ok=True)
            shutil.copy2(idx, os.path.join(DEST, unit, "index.csv"))
        for name in sorted(os.listdir(udir)):
            if not name.lower().endswith(".mid"):
                continue
            os.makedirs(os.path.join(DEST, unit), exist_ok=True)
            shutil.copy2(os.path.join(udir, name), os.path.join(DEST, unit, name))
            r = rows.get(name, {})
            tracks.append({"id": f"{unit}-{name[:-4]}", "unit": unit,
                           "file": f"{unit}/{name}",
                           "key": r.get("key"), "bpm": r.get("bpm"),
                           "chords": r.get("chords") or r.get("notes")})
    if not tracks:
        print(f"No captures found under {src}.")
        return 1
    with open(os.path.join(DEST, "set.json"), "w") as f:
        json.dump({"id": "my-units", "tracks": tracks}, f, indent=1)

    reg_path = os.path.join(SETS, "index.json")
    with open(reg_path) as f:
        reg = json.load(f)
    entry = {"id": "my-units", "name": "My units (J-6 / S-1 captures)",
             "path": "my-units/set.json", "read_only": False,
             "built_by": "tools/register_my_units.py",
             "description": "Patterns harvested from Jordan's own J-6 and S-1 with aira_local.py harvest."}
    reg["sets"] = [s for s in reg["sets"] if s.get("id") != "my-units"] + [entry]
    with open(reg_path, "w") as f:
        json.dump(reg, f, indent=1)
        f.write("\n")

    for unit in ("j6", "s1"):
        ts = [t for t in tracks if t["unit"] == unit]
        keys = sorted({t["key"] for t in ts if t["key"]})
        print(f"{unit}: {len(ts)} patterns; keys: {', '.join(keys) or '-'}")
        for t in ts:
            print(f"   {t['id']}: {t['key'] or '?'} {t['bpm'] or '?'}bpm  {t['chords'] or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
