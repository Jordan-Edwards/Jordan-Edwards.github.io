#!/usr/bin/env bash
# m8-transfer.sh — add sample packs to a Dirtywave M8 / M8 Model:02 SD card, safely.
#
# Safety contract:
#   * NEVER formats, partitions, or deletes anything.
#   * Refuses to run unless the target volume carries an M8 folder signature.
#   * Only copies .wav audio. MIDI and synth-patch files are never installed.
#   * Skips byte-identical files; never overwrites a file whose contents differ.
#   * Verifies every copied file by SHA-256 before reporting success.
#
# Usage:
#   bash m8-transfer.sh                 # detect, transfer, verify, eject
#   bash m8-transfer.sh --dry-run       # show the plan, write nothing
#   bash m8-transfer.sh --volume /Volumes/M8
#   bash m8-transfer.sh --source ~/Music/Packs   # extra place to look for archives
#   bash m8-transfer.sh --no-download   # never fetch the jungle pack from the web
#   bash m8-transfer.sh --no-eject
#
# Portable to bash 3.2 (stock macOS) and bash 5 (Linux). No non-standard deps.

set -uo pipefail

JUNGLE_URL="https://cdn.mos.musicradar.com/audio/musicradar-90s-jungle-samples.zip"

DRY_RUN=0
DO_DOWNLOAD=1
DO_EJECT=1
VOLUME=""
EXTRA_SOURCES=""

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)     DRY_RUN=1 ;;
    --no-download) DO_DOWNLOAD=0 ;;
    --no-eject)    DO_EJECT=0 ;;
    --volume)      VOLUME="${2:-}"; shift ;;
    --source)      EXTRA_SOURCES="$EXTRA_SOURCES
${2:-}"; shift ;;
    -h|--help)     sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

STAGING="$(mktemp -d "${TMPDIR:-/tmp}/m8transfer.XXXXXX")" || exit 1
LOG="$STAGING/transfer.log"
trap 'rm -rf "$STAGING"' EXIT

say()  { printf '%s\n' "$*" | tee -a "$LOG"; }
warn() { printf '!! %s\n' "$*" | tee -a "$LOG" >&2; }
die()  { printf '\nBLOCKED: %s\n' "$*" | tee -a "$LOG" >&2; exit 1; }
rule() { say "------------------------------------------------------------"; }

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" 2>/dev/null | awk '{print $1}'
  elif command -v shasum  >/dev/null 2>&1; then shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
  else echo "NOHASH"; fi
}

file_size() { wc -c < "$1" 2>/dev/null | tr -d ' '; }

avail_kb() { df -Pk "$1" 2>/dev/null | awk 'NR==2 {print $4}'; }

# ---------------------------------------------------------------- WAV probing
# Emits "<fmtcode> <channels> <rate> <bits>"; non-zero exit if not a parseable WAV.
probe_wav() {
  local f="$1" b n pos size o fmt ch rate bits
  b=($(od -An -v -tu1 -N 4096 "$f" 2>/dev/null))
  n=${#b[@]}
  [ "$n" -lt 44 ] && return 1
  [ "${b[0]}" = 82 ] && [ "${b[1]}" = 73 ] && [ "${b[2]}" = 70 ] && [ "${b[3]}" = 70 ] || return 1   # RIFF
  [ "${b[8]}" = 87 ] && [ "${b[9]}" = 65 ] && [ "${b[10]}" = 86 ] && [ "${b[11]}" = 69 ] || return 1 # WAVE
  pos=12
  while [ $((pos + 8)) -le "$n" ]; do
    size=$(( b[pos+4] + b[pos+5]*256 + b[pos+6]*65536 + b[pos+7]*16777216 ))
    [ "$size" -lt 0 ] && return 1
    if [ "${b[pos]}" = 102 ] && [ "${b[pos+1]}" = 109 ] && [ "${b[pos+2]}" = 116 ] && [ "${b[pos+3]}" = 32 ]; then
      o=$((pos + 8))
      [ $((o + 16)) -gt "$n" ] && return 1
      fmt=$((  b[o]    + b[o+1]*256 ))
      ch=$((   b[o+2]  + b[o+3]*256 ))
      rate=$(( b[o+4]  + b[o+5]*256 + b[o+6]*65536 + b[o+7]*16777216 ))
      bits=$(( b[o+14] + b[o+15]*256 ))
      printf '%s %s %s %s\n' "$fmt" "$ch" "$rate" "$bits"
      return 0
    fi
    pos=$(( pos + 8 + size + (size % 2) ))
  done
  return 1
}

# M8 plays uncompressed PCM WAV. Anything else is converted rather than shipped raw.
wav_is_m8_ready() {
  local fmt=$1 ch=$2 rate=$3 bits=$4
  [ "$fmt" = 1 ] || return 1
  [ "$ch" -ge 1 ] && [ "$ch" -le 2 ] || return 1
  [ "$bits" = 8 ] || [ "$bits" = 16 ] || [ "$bits" = 24 ] || return 1
  [ "$rate" -ge 8000 ] && [ "$rate" -le 48000 ] || return 1
  return 0
}

CONVERTER=""
command -v ffmpeg >/dev/null 2>&1 && CONVERTER=ffmpeg
[ -z "$CONVERTER" ] && command -v sox >/dev/null 2>&1 && CONVERTER=sox

convert_wav() { # src dst -> 0 on success
  case "$CONVERTER" in
    ffmpeg) ffmpeg -v error -y -i "$1" -ar 44100 -c:a pcm_s16le "$2" >/dev/null 2>&1 ;;
    sox)    sox "$1" -b 16 -e signed-integer "$2" rate 44100 >/dev/null 2>&1 ;;
    *)      return 1 ;;
  esac
}

# FAT32/exFAT reject these characters outright.
sanitize_name() {
  printf '%s' "$1" \
    | tr '*?:<>|"\\' '________' \
    | sed -e 's/[ .]*$//' -e 's/^ *//'
}

# ------------------------------------------------------- M8 volume detection
# An M8 card always carries Samples plus the firmware's other top-level folders.
find_dir_ci() { # root name -> prints path if a case-insensitive dir match exists
  local root="$1" want; want="$(lower "$2")" 
  local e
  for e in "$root"/*; do
    [ -d "$e" ] || continue
    [ "$(lower "$(basename "$e")")" = "$want" ] && { printf '%s' "$e"; return 0; }
  done
  return 1
}

m8_signature() { # root -> prints "<score> <matched dirs>"; exit 1 if not M8-shaped
  local root="$1" score=0 matched="" d name
  for name in Samples Songs Instruments Eqs Themes Scales Renders; do
    if d="$(find_dir_ci "$root" "$name")"; then
      score=$((score + 1)); matched="$matched $(basename "$d")"
    fi
  done
  find_dir_ci "$root" Samples >/dev/null || return 1   # Samples is mandatory
  [ "$score" -ge 3 ] || return 1                       # plus at least two siblings
  printf '%s %s\n' "$score" "$matched"
  return 0
}

candidate_volumes() {
  local v
  for v in /Volumes/*; do [ -d "$v" ] && printf '%s\n' "$v"; done 2>/dev/null
  for v in /media/*/* /media/* /run/media/*/* /mnt/*; do
    [ -d "$v" ] && printf '%s\n' "$v"
  done 2>/dev/null
  if command -v lsblk >/dev/null 2>&1; then
    lsblk -nr -o MOUNTPOINT,RM,TRAN 2>/dev/null \
      | awk '$1 != "" && ($2 == "1" || $3 == "usb") {print $1}'
  fi
}

describe_device() { # mountpoint -> human-readable device identity
  local mp="$1" dev=""
  if command -v diskutil >/dev/null 2>&1; then
    diskutil info "$mp" 2>/dev/null \
      | grep -E 'Device Node|Volume Name|File System Personality|Protocol|Device / Media Name|Removable Media|Disk Size' \
      | sed 's/^ */    /'
    return
  fi
  if command -v findmnt >/dev/null 2>&1; then dev="$(findmnt -no SOURCE --target "$mp" 2>/dev/null)"; fi
  [ -z "$dev" ] && dev="$(df -P "$mp" 2>/dev/null | awk 'NR==2{print $1}')"
  printf '    Device node: %s\n' "${dev:-unknown}"
  if command -v lsblk >/dev/null 2>&1 && [ -b "$dev" ]; then
    lsblk -no NAME,SIZE,FSTYPE,LABEL,TRAN,VENDOR,MODEL "$dev" 2>/dev/null | sed 's/^/    /'
  fi
  if command -v udevadm >/dev/null 2>&1 && [ -b "$dev" ]; then
    udevadm info --query=property --name="$dev" 2>/dev/null \
      | grep -E '^(ID_VENDOR|ID_MODEL|ID_SERIAL_SHORT|ID_BUS)=' | sed 's/^/    /'
  fi
}

rule; say "STEP 1 — Identify the M8 storage volume"; rule

if [ -n "$VOLUME" ]; then
  [ -d "$VOLUME" ] || die "--volume '$VOLUME' is not a mounted directory."
  m8_signature "$VOLUME" >/dev/null || die "'$VOLUME' has no M8 folder signature (needs Samples plus Songs/Instruments/Eqs/...). Refusing to write to an unidentified volume."
  M8_ROOT="$VOLUME"
else
  MATCHES=""; COUNT=0
  while IFS= read -r v; do
    [ -n "$v" ] || continue
    case "
$MATCHES" in *"
$v"*) continue ;; esac
    if sig="$(m8_signature "$v" 2>/dev/null)"; then
      MATCHES="$MATCHES
$v"; COUNT=$((COUNT + 1))
      say "  candidate: $v   [signature score ${sig%% *}:${sig#* }]"
    fi
  done <<EOF
$(candidate_volumes | sort -u)
EOF
  if [ "$COUNT" -eq 0 ]; then
    say ""
    say "Mounted volumes seen:"
    candidate_volumes | sort -u | sed 's/^/    /'
    die "No volume carries an M8 folder signature. Put the M8 into USB-disk mode (System settings on the device) so its SD card mounts, then re-run. Not guessing a drive."
  fi
  [ "$COUNT" -gt 1 ] && die "$COUNT volumes look like an M8. Re-run with --volume <path> to name the right one. Not guessing."
  M8_ROOT="$(printf '%s' "$MATCHES" | sed -n '2p')"
fi

say ""
say "Identified M8 storage: $M8_ROOT"
describe_device "$M8_ROOT" | tee -a "$LOG"
[ -w "$M8_ROOT" ] || die "$M8_ROOT is not writable. Remount read-write, then re-run."

SAMPLES_DIR="$(find_dir_ci "$M8_ROOT" Samples)" || die "No Samples directory on $M8_ROOT."
say "Sample directory in use: $SAMPLES_DIR"

# ------------------------------------------------------------ locate archives
rule; say "STEP 2 — Locate the prepared archives"; rule

SEARCH_DIRS="$HOME/Downloads
$HOME/Desktop
$HOME/Documents
$HOME/Music
$HOME/Projects
$HOME/Samples
$HOME"
[ -n "$EXTRA_SOURCES" ] && SEARCH_DIRS="$SEARCH_DIRS$EXTRA_SOURCES"

find_archive() { # glob -> first matching readable file
  local pat="$1" d hit
  while IFS= read -r d; do
    [ -d "$d" ] || continue
    hit="$(find "$d" -maxdepth 3 -iname "$pat" -type f -size +100k 2>/dev/null | head -1)"
    [ -n "$hit" ] && { printf '%s' "$hit"; return 0; }
  done <<EOF
$SEARCH_DIRS
EOF
  return 1
}

validate_zip() { # path -> 0 if a sane, intact zip containing audio
  local z="$1" magic
  [ -f "$z" ] || return 1
  [ "$(file_size "$z")" -gt 102400 ] || { warn "$(basename "$z"): too small to be a real pack"; return 1; }
  magic="$(od -An -c -N4 "$z" 2>/dev/null | tr -d ' \n')"
  case "$magic" in PK*) ;; *) warn "$(basename "$z"): not a ZIP archive (magic '$magic')"; return 1 ;; esac
  unzip -tqq "$z" >/dev/null 2>&1 || { warn "$(basename "$z"): failed integrity test"; return 1; }
  unzip -Z1 "$z" 2>/dev/null | grep -qi '\.wav$' || { warn "$(basename "$z"): contains no .wav files"; return 1; }
  return 0
}

# name|glob|destination collection|subtree filter (empty = whole archive)
PACKS="jungle|*musicradar*jungle*.zip|MusicRadar/90s Jungle|
chordlab|*Electronic_Chord_Lab*.zip|Electronic Chord Lab|CHORD_WAV STABS_WAV
drumbreaks|*musicradar*drum*break*.zip|MusicRadar/Drum Breaks|
deephouse|*deep*house*.zip|MusicRadar/Deep House|
frenchhouse|*french*house*.zip|MusicRadar/French House|
ambient|*ambient*.zip|MusicRadar/Ambient|"

FOUND_LIST=""
while IFS='|' read -r key glob coll subtrees; do
  [ -n "$key" ] || continue
  if path="$(find_archive "$glob")"; then
    say "  found  $key -> $path"
    FOUND_LIST="$FOUND_LIST
$key|$path|$coll|$subtrees"
  else
    say "  MISSING $key (no match for '$glob')"
  fi
done <<EOF
$PACKS
EOF

# Jungle is the priority pack; fetch it if the prepared copy is absent.
if ! printf '%s' "$FOUND_LIST" | grep -q '^jungle|'; then
  if [ "$DO_DOWNLOAD" = 1 ]; then
    say ""
    say "  jungle pack absent locally — downloading the original free archive"
    say "  $JUNGLE_URL"
    dl="$STAGING/musicradar-90s-jungle-samples.zip"
    if curl -fL --retry 3 --retry-delay 2 --connect-timeout 30 -o "$dl" "$JUNGLE_URL" 2>>"$LOG"; then
      if validate_zip "$dl"; then
        say "  downloaded OK  size=$(file_size "$dl") bytes  sha256=$(hash_file "$dl")"
        FOUND_LIST="$FOUND_LIST
jungle|$dl|MusicRadar/90s Jungle|"
      else
        warn "downloaded jungle archive failed validation — not extracting it"
      fi
    else
      warn "jungle download failed (network or egress policy). Continuing with what is present."
    fi
  else
    warn "jungle pack missing and --no-download was given"
  fi
fi

[ -n "$(printf '%s' "$FOUND_LIST" | tr -d '\n')" ] || die "No usable sample archives found. Put them in ~/Downloads (or pass --source DIR) and re-run."

# ------------------------------------------------------------------- staging
rule; say "STEP 3 — Validate and stage audio"; rule

STAGE_ROOT="$STAGING/stage"; mkdir -p "$STAGE_ROOT"
PLAN="$STAGING/plan.tsv"; : > "$PLAN"
SKIPPED_NONAUDIO=0

while IFS='|' read -r key path coll subtrees; do
  [ -n "$key" ] || continue
  validate_zip "$path" || { warn "$key: archive failed validation — skipped entirely"; continue; }
  say "  $key: validated (sha256 $(hash_file "$path"))"
  ex="$STAGE_ROOT/$key"; mkdir -p "$ex"
  unzip -qq -o "$path" -d "$ex" >>"$LOG" 2>&1 || { warn "$key: extraction failed — skipped"; continue; }

  # Count what we are deliberately NOT installing.
  n_other=$(find "$ex" -type f ! -iname '*.wav' ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')
  SKIPPED_NONAUDIO=$((SKIPPED_NONAUDIO + n_other))

  # Restrict to the requested subtrees when the pack calls for it.
  roots=""
  if [ -n "$subtrees" ]; then
    for sub in $subtrees; do
      while IFS= read -r hit; do [ -n "$hit" ] && roots="$roots
$hit"; done <<EOF
$(find "$ex" -type d -iname "$sub" 2>/dev/null)
EOF
    done
    [ -n "$(printf '%s' "$roots" | tr -d '\n')" ] || { warn "$key: none of the requested folders ($subtrees) are in this archive — skipped"; continue; }
  else
    roots="$ex"
  fi

  while IFS= read -r base; do
    [ -n "$base" ] || continue
    while IFS= read -r w; do
      [ -n "$w" ] || continue
      case "$(basename "$w")" in .*|._*) continue ;; esac
      case "$w" in *__MACOSX*) continue ;; esac
      rel="${w#$base/}"
      # Label the chord-lab subtrees by musical role instead of raw folder names.
      case "$(lower "$(basename "$base")")" in
        chord_wav) rel="Chords/$rel" ;;
        stabs_wav) rel="Stabs/$rel" ;;
      esac
      printf '%s\t%s\t%s\n' "$w" "$coll" "$rel" >> "$PLAN"
    done <<EOF
$(find "$base" -type f -iname '*.wav' 2>/dev/null | sort)
EOF
  done <<EOF
$(printf '%s' "$roots" | sed '/^$/d')
EOF
done <<EOF
$FOUND_LIST
EOF

TOTAL_PLANNED=$(wc -l < "$PLAN" | tr -d ' ')
[ "$TOTAL_PLANNED" -gt 0 ] || die "No .wav files survived validation. Nothing to copy."
say "  staged $TOTAL_PLANNED wav files for transfer"
say "  ignored $SKIPPED_NONAUDIO non-audio files (MIDI / patch / docs) — never installed as M8 samples"

# -------------------------------------------------------------- space check
NEED_KB=$(awk -F'\t' '{print $1}' "$PLAN" | tr '\n' '\0' | xargs -0 wc -c 2>/dev/null | awk '/total$/{t=$1} END{print int((t?t:0)/1024)+1}')
[ -z "$NEED_KB" ] && NEED_KB=0
HAVE_KB=$(avail_kb "$M8_ROOT")
say "  space needed ~$((NEED_KB / 1024)) MB   available $((HAVE_KB / 1024)) MB on $M8_ROOT"
[ "$HAVE_KB" -gt $((NEED_KB + 51200)) ] || die "Not enough free space on the M8 card (need ~$((NEED_KB/1024)) MB plus 50 MB headroom, have $((HAVE_KB/1024)) MB)."

# -------------------------------------------------------------------- copy
rule
if [ "$DRY_RUN" = 1 ]; then say "STEP 4 — DRY RUN (nothing will be written)"; else say "STEP 4 — Copy, skipping duplicates"; fi
rule

COPIED=0; SKIPPED_SAME=0; CONFLICTS=0; CONVERTED=0; FAILED=0; INCOMPAT=0
DEST_ROOT_REPORT=""

while IFS="$(printf '\t')" read -r src coll rel; do
  [ -n "$src" ] || continue

  if ! info="$(probe_wav "$src")"; then
    warn "unreadable WAV header, skipped: $(basename "$src")"; FAILED=$((FAILED + 1)); continue
  fi
  set -- $info; fmt=$1; ch=$2; rate=$3; bits=$4

  # Rebuild the relative path with FAT-safe components.
  safe_rel=""
  OLDIFS=$IFS; IFS='/'
  for part in $rel; do
    [ -z "$part" ] && continue
    sp="$(sanitize_name "$part")"
    safe_rel="${safe_rel:+$safe_rel/}$sp"
  done
  IFS=$OLDIFS

  safe_coll=""
  OLDIFS=$IFS; IFS='/'
  for part in $coll; do
    [ -z "$part" ] && continue
    safe_coll="${safe_coll:+$safe_coll/}$(sanitize_name "$part")"
  done
  IFS=$OLDIFS

  dest="$SAMPLES_DIR/$safe_coll/$safe_rel"
  case "
$DEST_ROOT_REPORT" in
    *"
$safe_coll"*) ;;
    *) DEST_ROOT_REPORT="$DEST_ROOT_REPORT
$safe_coll" ;;
  esac

  staged_src="$src"
  if ! wav_is_m8_ready "$fmt" "$ch" "$rate" "$bits"; then
    if [ -n "$CONVERTER" ]; then
      conv="$STAGING/conv_$$_$COPIED.wav"
      if convert_wav "$src" "$conv"; then
        staged_src="$conv"; CONVERTED=$((CONVERTED + 1))
      else
        warn "conversion failed, skipped: $(basename "$src") (fmt=$fmt ${bits}bit ${rate}Hz)"
        INCOMPAT=$((INCOMPAT + 1)); continue
      fi
    else
      warn "incompatible and no ffmpeg/sox to convert, skipped: $(basename "$src") (fmt=$fmt ${bits}bit ${rate}Hz)"
      INCOMPAT=$((INCOMPAT + 1)); continue
    fi
  fi

  src_hash="$(hash_file "$staged_src")"

  if [ -f "$dest" ]; then
    if [ "$(hash_file "$dest")" = "$src_hash" ]; then
      SKIPPED_SAME=$((SKIPPED_SAME + 1)); continue
    fi
    # Different contents: never overwrite. Land it beside the original.
    stem="${dest%.*}"; ext="${dest##*.}"; n=2
    while [ -f "${stem}-${n}.${ext}" ]; do
      [ "$(hash_file "${stem}-${n}.${ext}")" = "$src_hash" ] && break
      n=$((n + 1))
    done
    if [ -f "${stem}-${n}.${ext}" ]; then SKIPPED_SAME=$((SKIPPED_SAME + 1)); continue; fi
    dest="${stem}-${n}.${ext}"
    CONFLICTS=$((CONFLICTS + 1))
    warn "name clash with different audio, kept both: $(basename "$dest")"
  fi

  if [ "$DRY_RUN" = 1 ]; then COPIED=$((COPIED + 1)); continue; fi

  mkdir -p "$(dirname "$dest")" 2>/dev/null
  if cp "$staged_src" "$dest" 2>>"$LOG"; then
    COPIED=$((COPIED + 1))
  else
    warn "copy failed: $dest"; FAILED=$((FAILED + 1))
  fi
  printf '%s\t%s\n' "$src_hash" "$dest" >> "$STAGING/verify.tsv"
done < "$PLAN"

sync 2>/dev/null

# ------------------------------------------------------------------ verify
rule; say "STEP 5 — Verify copied files against their sources"; rule
VERIFIED=0; MISMATCH=0
if [ "$DRY_RUN" = 0 ] && [ -f "$STAGING/verify.tsv" ]; then
  while IFS="$(printf '\t')" read -r want dest; do
    [ -n "$dest" ] || continue
    if [ "$(hash_file "$dest")" = "$want" ]; then VERIFIED=$((VERIFIED + 1))
    else MISMATCH=$((MISMATCH + 1)); warn "VERIFY FAILED: $dest"; fi
  done < "$STAGING/verify.tsv"
  say "  verified $VERIFIED files by SHA-256, $MISMATCH mismatches"
else
  say "  (dry run — nothing to verify)"
fi

# ------------------------------------------------------------------- eject
EJECTED="no"
if [ "$DRY_RUN" = 0 ] && [ "$DO_EJECT" = 1 ]; then
  rule; say "STEP 6 — Safely eject the M8 volume"; rule
  sync 2>/dev/null
  if command -v diskutil >/dev/null 2>&1; then
    diskutil eject "$M8_ROOT" >>"$LOG" 2>&1 && EJECTED="yes"
  elif command -v udisksctl >/dev/null 2>&1; then
    dev="$(findmnt -no SOURCE --target "$M8_ROOT" 2>/dev/null)"
    [ -n "$dev" ] && udisksctl unmount -b "$dev" >>"$LOG" 2>&1 && EJECTED="yes"
  elif umount "$M8_ROOT" >>"$LOG" 2>&1; then
    EJECTED="yes"
  fi
  [ "$EJECTED" = yes ] && say "  ejected $M8_ROOT cleanly" || warn "could not auto-eject; unmount it yourself before unplugging"
fi

rule; say "M8 MILESTONE REPORT"; rule
say "  Sample directory   : $SAMPLES_DIR"
say "  Collections written:"
printf '%s\n' "$DEST_ROOT_REPORT" | sed '/^$/d' | sed "s|^|    $SAMPLES_DIR/|" | tee -a "$LOG"
say "  Volume             : $M8_ROOT"
say "  WAVs copied        : $COPIED"
say "  Verified by hash   : $VERIFIED"
say "  Already present    : $SKIPPED_SAME (identical, skipped)"
say "  Name clashes kept  : $CONFLICTS (both versions retained)"
say "  Converted          : $CONVERTED"
say "  Incompatible       : $INCOMPAT"
say "  Failed             : $FAILED"
say "  Non-audio ignored  : $SKIPPED_NONAUDIO (no MIDI or synth patches installed)"
say "  Volume ejected     : $EJECTED"
say ""
say "  NEXT, ON THE DEVICE: ejecting does NOT take the M8 out of USB-disk mode."
say "  Exit it on the M8 itself (same System settings entry you used to enable it,"
say "  or power-cycle the unit). The tracker cannot read the card until you do."
cp "$LOG" "${TMPDIR:-/tmp}/m8-transfer-last.log" 2>/dev/null
say "  Full log: ${TMPDIR:-/tmp}/m8-transfer-last.log"
[ "$MISMATCH" = 0 ] && [ "$FAILED" = 0 ]
