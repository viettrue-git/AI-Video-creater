#!/usr/bin/env bash
# Download model files into ComfyUI/models with resume + size verification.
# Usage: scripts/download-model-files-with-size-check.sh <list-file>
#   list-file lines: <url> <path relative to ComfyUI/models>   (# = comment)
# A lock dir prevents two downloaders writing the same .part file (that corrupted a file on 2026-10-05).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODELS="$ROOT/ComfyUI/models"
LOCK="$MODELS/.download.lock"

if ! mkdir "$LOCK" 2>/dev/null; then
  echo "Another download is running (remove $LOCK if it is stale)"; exit 1
fi
trap 'rmdir "$LOCK"' EXIT

status=0
while read -r url rel; do
  [[ -z "${url:-}" || "$url" == \#* ]] && continue
  dest="$MODELS/$rel"
  expected=$(curl -sIL -m 30 "$url" | tr -d '\r' | awk 'tolower($1)=="content-length:"{v=$2} END{print v}')
  if [[ -z "$expected" ]]; then echo "FAIL no size from server: $rel"; status=1; continue; fi
  if [[ -f "$dest" ]]; then
    actual=$(stat -c %s "$dest")
    [[ "$actual" == "$expected" ]] && { echo "OK (already have) $rel"; continue; }
    echo "BAD SIZE $rel ($actual != $expected) -> re-download"; rm -f "$dest"
  fi
  mkdir -p "$(dirname "$dest")"
  part="$dest.part"
  [[ -f "$part" && $(stat -c %s "$part") -gt "$expected" ]] && rm -f "$part"  # oversized = corrupt
  curl -sSL --retry 5 --retry-delay 5 -C - -o "$part" "$url" || { echo "FAIL download $rel"; status=1; continue; }
  actual=$(stat -c %s "$part")
  if [[ "$actual" == "$expected" ]]; then mv "$part" "$dest"; echo "DONE $rel ($actual bytes)"
  else echo "FAIL size $rel ($actual != $expected)"; status=1; fi
done < "$1"
exit $status
