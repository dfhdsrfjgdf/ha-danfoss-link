#!/usr/bin/env bash
# Pull Danfoss Link app credentials from a connected Android device/emulator.
# Usage: ./pull_danfoss_creds.sh [output_directory]
set -euo pipefail

PKG="com.danfoss.linkapp"
OUT="${1:-./danfoss_link_creds}"

if ! command -v adb >/dev/null 2>&1; then
  echo "ERROR: adb not found. Install Android SDK platform-tools and add to PATH."
  echo "  Mac example: ~/Library/Android/sdk/platform-tools"
  exit 1
fi

DEVICES="$(adb devices | awk 'NR>1 && $2=="device" {print $1}')"
COUNT="$(echo "$DEVICES" | grep -c . || true)"
if [[ "$COUNT" -eq 0 ]]; then
  echo "ERROR: No adb device connected. Start the emulator or plug in a rooted phone."
  adb devices
  exit 1
fi
if [[ "$COUNT" -gt 1 ]]; then
  echo "WARNING: Multiple devices connected; using the first one."
fi

echo "==> Requesting adb root (required; works on emulator, rooted phones only)"
if ! adb root 2>/dev/null; then
  echo "WARNING: adb root command failed — continuing anyway."
fi
sleep 1

BASE="/data/data/${PKG}/files"
LUADATA="${BASE}/luadata"

echo "==> Detecting app data path on device..."
if adb shell "test -f ${LUADATA}/app_cert.pem" 2>/dev/null; then
  REMOTE_DIR="$LUADATA"
elif adb shell "test -f ${BASE}/app_cert.pem" 2>/dev/null; then
  REMOTE_DIR="$BASE"
else
  echo "ERROR: Could not find app_cert.pem under:"
  echo "  ${LUADATA}/"
  echo "  ${BASE}/"
  echo ""
  echo "Open Danfoss Link on the device, wait until rooms load, then run this script again."
  exit 1
fi

mkdir -p "$OUT"
echo "==> Pulling from ${REMOTE_DIR} -> ${OUT}"
adb pull "${REMOTE_DIR}/app_cert.pem" "$OUT/" 
adb pull "${REMOTE_DIR}/app_key.pem" "$OUT/"
if adb shell "test -d ${REMOTE_DIR}/pairings" 2>/dev/null; then
  mkdir -p "$OUT/pairings"
  adb pull "${REMOTE_DIR}/pairings/" "$OUT/pairings/"
fi

PEER_ID=""
if [[ -d "$OUT/pairings" ]]; then
  for f in "$OUT/pairings"/*; do
    [[ -f "$f" ]] || continue
    if grep -q 'peer_id' "$f" 2>/dev/null; then
      PEER_ID="$(grep -oE '\["peer_id"\]="[^"]+"' "$f" | head -1 | sed 's/\["peer_id"\]="//;s/"$//')"
    fi
    if [[ -z "$PEER_ID" ]]; then
      base="$(basename "$f")"
      PEER_ID="$(echo "$base" | tr '_' ':')"
    fi
    break
  done
fi

SUMMARY="$OUT/SUMMARY.txt"
{
  echo "Danfoss Link credential export"
  echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo ""
  echo "Files:"
  echo "  app_cert.pem"
  echo "  app_key.pem"
  echo ""
  if [[ -n "$PEER_ID" ]]; then
    echo "CC peer ID (paste into Home Assistant):"
    echo "  ${PEER_ID}"
  else
    echo "CC peer ID: not found — check pairings/ manually."
  fi
  echo ""
  echo "Next: docs/home-assistant-setup.md"
  echo "Keep these files private. Do not commit to git."
} > "$SUMMARY"

echo ""
echo "=============================================="
echo "SUCCESS. Credentials saved to: ${OUT}"
echo "=============================================="
cat "$SUMMARY"
echo ""
echo "Tip: Shut down Danfoss Link on this device before using Home Assistant."
