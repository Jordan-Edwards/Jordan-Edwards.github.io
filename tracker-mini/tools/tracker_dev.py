#!/usr/bin/env python3
"""Talk to a Tracker Mini / Tracker+ running a development-console build.

The console is part of Polyend's Tracker CE (docs/developer_guide.md, section 8).
It only exists when BOTH are true:
  * the firmware was built with -DENABLE_DEV_CONSOLE (our *dev.ptf builds), and
  * an empty file named ".develop" is in the root of the SD card.

Usage (needs "pip install pyserial"):
  tracker_dev.py ping                      find the device, print its build id
  tracker_dev.py log [seconds]             print the firmware log (default 10 s)
  tracker_dev.py storage on|off            enter / leave USB storage mode
  tracker_dev.py deploy FILE.ptf           copy FILE to /Firmware, flash it, wait,
                                           and report the build id that comes back
  tracker_dev.py reboot

NOT YET RUN AGAINST A REAL DEVICE. Written from the protocol in the CE source.
deploy never deletes or overwrites: it refuses if /Firmware already has a file
with the same name and different contents.
"""
import hashlib
import os
import shutil
import string
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial is missing: pip install pyserial")

MAX_NAME = 31
PREFIXES = ("TrackerMini", "TrackerPlus")


def _ask(port, command, wait=2.0):
    """Send one command; return (reply line starting with '@', other log lines)."""
    port.reset_input_buffer()
    port.write((command + "\n").encode("ascii"))
    port.flush()
    deadline = time.time() + wait
    logs, buf = [], b""
    while time.time() < deadline:
        buf += port.read(256)
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            text = line.decode("utf-8", "replace").rstrip("\r")
            if text.startswith("@"):
                return text, logs
            if text:
                logs.append(text)
    return None, logs


def find_port(timeout=30.0, quiet=False):
    """Probe every serial port with 'ping' until one answers as a Tracker."""
    deadline = time.time() + timeout
    while True:
        for info in list_ports.comports():
            try:
                with serial.Serial(info.device, 115200, timeout=0.2, write_timeout=1) as port:
                    reply, _ = _ask(port, "ping", wait=1.0)
            except (OSError, serial.SerialException):
                continue
            if reply and reply.startswith("@tracker-dev"):
                if not quiet:
                    print(f"{info.device}: {reply}")
                return info.device, reply
        if time.time() > deadline:
            return None, None
        time.sleep(1.0)


def command(device, text, wait=2.0):
    with serial.Serial(device, 115200, timeout=0.2, write_timeout=1) as port:
        reply, logs = _ask(port, text, wait)
    for line in logs:
        print("  log:", line)
    return reply


def card_roots():
    """Mounted volumes that look like a Tracker SD card (have a Firmware folder)."""
    if os.name == "nt":
        candidates = [f"{letter}:\\" for letter in string.ascii_uppercase if letter not in "ABC"]
    else:
        candidates = []
        for base in ("/Volumes", "/media", "/run/media", "/mnt"):
            for root, dirs, _ in os.walk(base):
                depth = root[len(base):].count(os.sep)
                candidates += [os.path.join(root, d) for d in dirs]
                if depth >= 1:
                    dirs[:] = []
    found = []
    for root in candidates:
        try:
            if os.path.isdir(os.path.join(root, "Firmware")) and (
                os.path.isdir(os.path.join(root, "Projects")) or os.path.isdir(os.path.join(root, "Samples"))
            ):
                found.append(root)
        except OSError:
            pass
    return found


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def deploy(path):
    name = os.path.basename(path)
    if not name.endswith(".ptf") or not name.startswith(PREFIXES) or len(name) > MAX_NAME:
        sys.exit(f"{name}: must start with TrackerMini/TrackerPlus, end in .ptf, and be <= {MAX_NAME} characters")
    want = sha256(path)

    device, before = find_port()
    if not device:
        sys.exit("no Tracker development console found (dev build flashed? .develop on the card?)")

    already = card_roots()
    reply = command(device, "storage on", wait=5.0)
    print("storage on ->", reply)
    if not reply or not reply.startswith("@ok"):
        sys.exit("device refused storage mode")
    # The port is closed now; the device re-enumerates with the storage class.

    root, deadline = None, time.time() + 60
    while time.time() < deadline and root is None:
        time.sleep(1.0)
        fresh = [r for r in card_roots() if r not in already] or card_roots()
        if len(fresh) == 1:
            root = fresh[0]
    if root is None:
        sys.exit("the SD card did not show up as exactly one volume; nothing copied")

    target = os.path.join(root, "Firmware", name)
    if os.path.exists(target) and sha256(target) != want:
        sys.exit(f"{target} already exists with different contents; pick another file name")
    if not os.path.exists(target):
        shutil.copyfile(path, target)
        with open(target, "rb+") as handle:
            os.fsync(handle.fileno())
    if sha256(target) != want:
        sys.exit("copy does not match the source file; not flashing")
    print(f"copied to {target} and verified")
    time.sleep(3.0)  # let the host finish writing before the device remounts

    device, _ = find_port(quiet=True)
    if not device:
        sys.exit("console did not come back after storage mode; flash it from Config > Firmware instead")
    reply = command(device, f"flash {name}", wait=5.0)
    print("flash ->", reply)
    if not reply or not reply.startswith("@ok"):
        sys.exit("device refused to flash")

    print("waiting for the device to come back (the bootloader is flashing)...")
    time.sleep(20.0)
    device, after = find_port(timeout=180.0)
    if not device:
        sys.exit("device did not come back with a console. If the screen is stuck, use the reset pinhole "
                 "with a known-good .ptf in /Firmware.")
    print("before:", before)
    print("after: ", after)


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    action = argv[1]
    if action == "deploy" and len(argv) == 3:
        return deploy(argv[2])
    device, _ = find_port(quiet=(action != "ping"))
    if not device:
        sys.exit("no Tracker development console found")
    if action == "ping":
        return
    if action == "log":
        seconds = float(argv[2]) if len(argv) > 2 else 10.0
        with serial.Serial(device, 115200, timeout=0.2) as port:
            end = time.time() + seconds
            while time.time() < end:
                data = port.read(512)
                if data:
                    sys.stdout.write(data.decode("utf-8", "replace"))
                    sys.stdout.flush()
        return
    if action == "storage" and len(argv) == 3 and argv[2] in ("on", "off"):
        print(command(device, f"storage {argv[2]}", wait=5.0))
        return
    if action == "reboot":
        print(command(device, "reboot"))
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
