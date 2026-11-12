#!/usr/bin/env bash
# Rebuild the Tracker Mini firmware in this folder from Polyend's open-source
# Tracker Community Edition (https://github.com/polyend/tracker-ce).
#
#   ./build.sh            stock CE at the pinned commit  -> out/TrackerMini_CE_<sha>.ptf
#   ./build.sh loops      CE + every patch in patches/   -> out/TrackerMini_<name>.ptf
#
# Needs: git, make, python3, curl, tar, ~1.5 GB of disk. Linux x86_64.
# The Arm toolchain (GNU Arm Embedded 10.3-2021.10, the one Polyend's CI uses)
# is downloaded once into .work/toolchain.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$HERE/.work}"
CE_REPO="https://github.com/polyend/tracker-ce"
CE_COMMIT="$(cat "$HERE/CE_COMMIT")"
TC_URL="https://developer.arm.com/-/media/Files/downloads/gnu-rm/10.3-2021.10/gcc-arm-none-eabi-10.3-2021.10-x86_64-linux.tar.bz2"
TC_DIR="$WORK/toolchain/gcc-arm-none-eabi-10.3-2021.10"
MODE="${1:-stock}"

mkdir -p "$WORK" "$HERE/out"

if [ ! -x "$TC_DIR/bin/arm-none-eabi-gcc" ]; then
  echo ">> fetching Arm toolchain"
  mkdir -p "$WORK/toolchain"
  curl -sSL --fail -o "$WORK/toolchain/gcc-arm.tar.bz2" "$TC_URL"
  tar xjf "$WORK/toolchain/gcc-arm.tar.bz2" -C "$WORK/toolchain"
fi

SRC="$WORK/tracker-ce-$MODE"
if [ ! -d "$SRC/.git" ]; then
  echo ">> cloning tracker-ce"
  git clone "$CE_REPO" "$SRC"
fi
git -C "$SRC" fetch --quiet origin
git -C "$SRC" checkout --quiet --force "$CE_COMMIT"
git -C "$SRC" clean -fdxq

SHA="$(git -C "$SRC" rev-parse --short=7 HEAD)"
if [ "$MODE" = "stock" ]; then
  POSTFIX="CE_${SHA}"
else
  for p in "$HERE"/patches/*.patch; do
    [ -e "$p" ] || continue
    echo ">> applying $(basename "$p")"
    git -C "$SRC" apply --index "$p"
  done
  POSTFIX="$(cat "$HERE/LOOPS_NAME" 2>/dev/null || echo "Loops_${SHA}")"
fi

# Filenames must start with "TrackerMini", end in .ptf and stay <= 31 chars.
NAME="TrackerMini_${POSTFIX}.ptf"
if [ "${#NAME}" -gt 31 ]; then echo "!! $NAME is longer than 31 characters"; exit 1; fi

echo ">> building $NAME"
make -C "$SRC" mini TOOLCHAIN="$TC_DIR/bin/arm-none-eabi-" MINI_POSTFIX="$POSTFIX" \
  ${CUSTOM_DEFINES:+CUSTOM_DEFINES="$CUSTOM_DEFINES"} > "$WORK/build-$MODE.log" 2>&1 \
  || { tail -40 "$WORK/build-$MODE.log"; echo "!! build failed, full log: $WORK/build-$MODE.log"; exit 1; }

cp "$SRC/build/$NAME" "$HERE/out/$NAME"
( cd "$HERE/out" && sha256sum "$NAME" )
echo ">> done: $HERE/out/$NAME"
