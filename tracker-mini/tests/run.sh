#!/usr/bin/env bash
# Host tests for the Loops logic. One command: tests/run.sh
#
# Compiles the SAME loopsLogic.cpp the firmware builds and runs it on this computer.
# The source is taken from $CE_SRC (default: the development checkout .work/dev/core).
# If that checkout is missing, a clean CE checkout with patches/*.patch applied is made in
# .work/tests-src, so the tests always run against what the patches really contain.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
WORK="${WORK:-$ROOT/.work}"
CE_SRC="${CE_SRC:-$WORK/dev/core}"
LOGIC_DIR="$CE_SRC/interface/loops"

if [ ! -f "$LOGIC_DIR/loopsLogic.cpp" ]; then
  echo ">> $LOGIC_DIR/loopsLogic.cpp not found: building a patched checkout in $WORK/tests-src"
  SRC="$WORK/tests-src"
  if [ ! -d "$SRC/.git" ]; then
    git clone --quiet https://github.com/polyend/tracker-ce "$SRC"
  fi
  git -C "$SRC" checkout --quiet --force "$(cat "$ROOT/CE_COMMIT")"
  git -C "$SRC" clean -fdxq
  for p in "$ROOT"/patches/*.patch; do
    [ -e "$p" ] || continue
    git -C "$SRC" apply --index "$p"
  done
  LOGIC_DIR="$SRC/core/interface/loops"
fi

CXX="${CXX:-}"
if [ -z "$CXX" ]; then
  if command -v g++ >/dev/null 2>&1; then CXX=g++; else CXX=clang++; fi
fi

OUT="${TMPDIR:-/tmp}/loops-tests-$$"
mkdir -p "$OUT"
trap 'rm -rf "$OUT"' EXIT

echo ">> $CXX, logic from $LOGIC_DIR"
"$CXX" -std=c++17 -O1 -g -Wall -Wextra -Werror -DLOOPS_HOST_TEST \
  -I"$LOGIC_DIR" \
  "$LOGIC_DIR/loopsLogic.cpp" "$HERE/loops/test_loops_logic.cpp" \
  -o "$OUT/test_loops_logic" -lm

"$OUT/test_loops_logic"
