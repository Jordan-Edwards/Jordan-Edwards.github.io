#!/usr/bin/env python3
"""Fetch the pinned community firmware sources for the OP-XY and Polyend Tracker.

Everything lands in firmware/vendor/, which is gitignored: this repo is a public
GitHub Pages site and most of these builds cannot be redistributed (see README.md).

  python3 firmware/fetch.py --list                 # show the catalog, fetch nothing
  python3 firmware/fetch.py                        # fetch every pinned source
  python3 firmware/fetch.py --group opxy           # just the OP-XY side
  python3 firmware/fetch.py --only tracker-ce-mods # one source
  python3 firmware/fetch.py --machines             # + all published Open-XY machines
  python3 firmware/fetch.py --check                # report pinned vs upstream HEAD

Stdlib only. Needs git on PATH.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources.json"
VENDOR = HERE / "vendor"
MACHINE_DIR = VENDOR / "opxy-machines"


def run(cmd, cwd=None, check=True, quiet=True):
    return subprocess.run(
        cmd, cwd=cwd, check=check, text=True, capture_output=quiet
    )


def head_of(path):
    try:
        return run(["git", "rev-parse", "HEAD"], cwd=path).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def clone_at(repo, commit, dest, label):
    """Shallow-fetch exactly `commit` of `repo` into `dest`. Idempotent."""
    if dest.exists():
        if head_of(dest) == commit:
            print(f"  = {label:<34} already at {commit[:9]}")
            return True
        print(f"  ~ {label:<34} wrong/old commit, refetching")
        shutil.rmtree(dest)

    dest.mkdir(parents=True, exist_ok=True)
    try:
        run(["git", "init", "-q"], cwd=dest)
        run(["git", "remote", "add", "origin", repo], cwd=dest)
        run(["git", "fetch", "-q", "--depth", "1", "origin", commit], cwd=dest)
        run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=dest)
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(dest, ignore_errors=True)
        err = (exc.stderr or "").strip().splitlines()
        print(f"  ! {label:<34} FAILED: {err[-1] if err else exc}")
        return False

    print(f"  + {label:<34} {commit[:9]}")
    return True


def upstream_head(repo, branch):
    try:
        out = run(["git", "ls-remote", repo, f"refs/heads/{branch}"]).stdout.strip()
        return out.split()[0] if out else None
    except subprocess.CalledProcessError:
        return None


def load():
    with SOURCES.open() as fh:
        return json.load(fh)


def cmd_list(data):
    groups = data["groups"]
    for gid, gname in groups.items():
        rows = [s for s in data["sources"] if s["group"] == gid]
        if not rows:
            continue
        print(f"\n{gname}")
        print("-" * len(gname))
        for s in rows:
            flag = ""
            if s.get("artifact") == "in-repo-binary":
                flag = "  [ready-to-flash .ptf in repo]"
            elif s.get("artifact") == "release-binary":
                flag = "  [prebuilt .ptf from upstream releases]"
            elif s.get("artifact") == "none":
                flag = "  [nothing to flash]"
            elif s.get("artifact") == "build-from-patches":
                flag = "  [build: needs your own stock firmware]"
            elif s.get("artifact") == "build-from-source":
                flag = "  [build from source]"
            print(f"  {s['name']:<26} {s['title']}{flag}")
            if s.get("do_not_share"):
                print(f"  {'':<26} NOTE: {s['do_not_share']}")
    print()


def cmd_check(data, selected):
    print("\nPinned vs upstream HEAD (network):\n")
    for s in selected:
        up = upstream_head(s["repo"], s.get("default_branch", "main"))
        if up is None:
            print(f"  ? {s['name']:<26} could not reach upstream")
        elif up == s["commit"]:
            print(f"  = {s['name']:<26} current ({up[:9]})")
        else:
            print(f"  ^ {s['name']:<26} upstream moved: {s['commit'][:9]} -> {up[:9]}")
    print()


def fetch_machines():
    """Clone every published Open-XY machine at the commit its catalog pins."""
    cat = VENDOR / "open-xy" / "catalog" / "machines.json"
    if not cat.exists():
        print("\n! --machines needs open-xy fetched first; run without --group, or")
        print("  python3 firmware/fetch.py --only open-xy --machines")
        return
    with cat.open() as fh:
        raw = json.load(fh)
    entries = raw.get("machines", raw) if isinstance(raw, dict) else raw
    pub = [m for m in entries if m.get("status") == "published" and m.get("commit")]

    # Several machines share one repo, so clone each unique repo+commit once.
    byrepo = {}
    for m in pub:
        byrepo.setdefault((m["repository"], m["commit"]), []).append(m)

    print(f"\nOpen-XY published machines: {len(pub)} in {len(byrepo)} repos\n")
    MACHINE_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    manifest = []
    for (repo, commit), machines in sorted(byrepo.items()):
        slug = repo.rstrip("/").split("github.com/")[-1].replace("/", "__")
        dest = MACHINE_DIR / f"{slug}@{commit[:9]}"
        ids = ",".join(sorted(m["id"] for m in machines))
        if clone_at(repo, commit, dest, f"{slug} ({ids})"):
            ok += 1
            for m in machines:
                manifest.append({
                    "id": m["id"], "kind": m.get("kind"),
                    "maintainer": m.get("maintainer"), "tag": m.get("tag"),
                    "keywords": m.get("keywords", []),
                    "local_path": str((dest / m.get("path", ".")).relative_to(HERE)),
                })
    out = MACHINE_DIR / "machines-local.json"
    with out.open("w") as fh:
        json.dump(sorted(manifest, key=lambda x: x["id"]), fh, indent=1)
        fh.write("\n")
    print(f"\n  {ok}/{len(byrepo)} machine repos fetched")
    print(f"  index: {out.relative_to(HERE.parent)}")


def report_binaries():
    ptfs = sorted(VENDOR.rglob("*.ptf")) + sorted(VENDOR.rglob("*.ldr"))
    if not ptfs:
        return
    print("\nFlashable images now present:\n")
    for p in ptfs:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        print(f"  {p.relative_to(HERE)}")
        print(f"    {p.stat().st_size:,} bytes  sha256 {digest}")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="show the catalog and exit")
    ap.add_argument("--check", action="store_true", help="compare pins to upstream HEAD")
    ap.add_argument("--group", choices=["opxy", "tracker", "tooling"], help="limit to one group")
    ap.add_argument("--only", metavar="NAME", action="append", help="fetch just this source (repeatable)")
    ap.add_argument("--machines", action="store_true", help="also fetch all published Open-XY machines")
    args = ap.parse_args()

    data = load()
    if args.list:
        cmd_list(data)
        return 0

    selected = data["sources"]
    if args.group:
        selected = [s for s in selected if s["group"] == args.group]
    if args.only:
        want = set(args.only)
        selected = [s for s in selected if s["name"] in want]
        missing = want - {s["name"] for s in selected}
        if missing:
            print(f"! unknown source(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
    if not selected and not args.machines:
        print("! nothing selected", file=sys.stderr)
        return 2

    if args.check:
        cmd_check(data, selected)
        return 0

    if selected:
        print(f"\nFetching {len(selected)} pinned source(s) into {VENDOR}\n")
        VENDOR.mkdir(parents=True, exist_ok=True)
        ok = sum(clone_at(s["repo"], s["commit"], VENDOR / s["name"], s["name"])
                 for s in selected)
        print(f"\n  {ok}/{len(selected)} sources ready")

    if args.machines:
        fetch_machines()

    report_binaries()
    print("Read firmware/README.md before flashing anything.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
