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

# Only this pure logic is tested here. If a patched build tree exists (./build.sh loops), say so
# when the source under test is not what that build used.
BUILT="$WORK/tracker-ce-loops/core/interface/loops"
if [ "$LOGIC_DIR" != "$BUILT" ] && [ -f "$BUILT/loopsLogic.cpp" ]; then
  if ! cmp -s "$LOGIC_DIR/loopsLogic.cpp" "$BUILT/loopsLogic.cpp" ||
     ! cmp -s "$LOGIC_DIR/loopsLogic.h" "$BUILT/loopsLogic.h"; then
    echo "!! warning: $LOGIC_DIR differs from the last patched build ($BUILT)."
    echo "!!          To test what the patches hold: CE_SRC=$WORK/tracker-ce-loops/core tests/run.sh"
  fi
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
