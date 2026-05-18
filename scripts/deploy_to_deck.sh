#!/usr/bin/env bash
set -euo pipefail

: "${DECK_HOST:?set DECK_HOST=deck@<deck-ip-or-hostname>}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_DIR="/home/deck/homebrew/plugins/AmneziaWG"
SETTINGS_DIR="/home/deck/homebrew/settings/AmneziaWG"

cd "$HERE"

if [[ ! -f dist/index.js ]]; then
  echo "==> building frontend"
  pnpm run build
fi

if [[ ! -x bin/amneziawg-go || ! -x bin/awg || ! -f bin/awg-quick || ! -x bin/resolvconf ]]; then
  echo "==> bin/ missing or incomplete — run scripts/build_bin.sh first" >&2
  exit 1
fi

if ! grep -q AMNEZIAWG_DECKY_LOG bin/awg-quick; then
  echo "==> applying awg-quick patch (redirects amneziawg-go stdout/stderr to log file)"
  bash scripts/patch_awg_quick.sh bin/awg-quick
fi

echo "==> preparing $REMOTE_DIR + $SETTINGS_DIR on $DECK_HOST"
ssh -t "$DECK_HOST" "
  sudo mkdir -p '$REMOTE_DIR' '$SETTINGS_DIR/configs' &&
  sudo chown -R deck:deck '$REMOTE_DIR' '$SETTINGS_DIR'
"

echo "==> rsync plugin tree (configs live in $SETTINGS_DIR, never overwritten here)"
rsync -avz \
  --exclude='configs' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='bin/*.orig' \
  --include='dist/' --include='dist/***' \
  --include='py_modules/' --include='py_modules/***' \
  --include='bin/' --include='bin/***' \
  --include='defaults/' --include='defaults/***' \
  --include='scripts/' --include='scripts/***' \
  --include='main.py' --include='plugin.json' --include='package.json' \
  --include='README.md' --include='LICENSE' \
  --exclude='*' \
  "$HERE/" "$DECK_HOST:$REMOTE_DIR/"

echo "==> aligning ownership (root:root plugin dir + plugin.json, deck:deck files, 700 settings/configs)"
ssh -t "$DECK_HOST" "
  sudo chown root:root '$REMOTE_DIR' '$REMOTE_DIR/plugin.json' &&
  sudo find '$REMOTE_DIR' -mindepth 1 -name plugin.json -prune -o -exec chown deck:deck {} + &&
  sudo chmod 755 '$REMOTE_DIR'/bin/* &&
  sudo chown -R deck:deck '$SETTINGS_DIR' &&
  sudo chmod 700 '$SETTINGS_DIR/configs' || true
"

echo "==> done."
echo "    Drop .conf files into $SETTINGS_DIR/configs/ (survives plugin reinstalls)."
echo "    Python-only changes need a full loader restart (hot-reload watches main.py + dist/index.js):"
echo "      ssh -t $DECK_HOST sudo systemctl restart plugin_loader.service"
echo "    If the toggle in QAM looks stale after restart, also restart Steam (resets frontend Promises)."
