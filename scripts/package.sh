#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
NAME="AmneziaWG"
STAGE="$HERE/.stage"
ZIP="$HERE/$NAME.zip"

cd "$HERE"

if [[ ! -f dist/index.js ]]; then
  echo "dist/index.js missing — run pnpm run build" >&2
  exit 1
fi
if [[ ! -x bin/amneziawg-go || ! -x bin/awg || ! -f bin/awg-quick ]]; then
  echo "bin/ incomplete — run scripts/build_bin.sh" >&2
  exit 1
fi

rm -rf "$STAGE" "$ZIP"
mkdir -p "$STAGE/$NAME"

rsync -a --delete \
  --exclude='configs' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='bin/*.orig' \
  --include='dist/' --include='dist/***' \
  --include='py_modules/' --include='py_modules/***' \
  --include='bin/' --include='bin/***' \
  --include='defaults/' --include='defaults/***' \
  --include='main.py' --include='plugin.json' --include='package.json' \
  --include='README.md' --include='LICENSE' \
  --exclude='*' \
  "$HERE/" "$STAGE/$NAME/"

(cd "$STAGE" && zip -r "$ZIP" "$NAME" >/dev/null)

echo "==> $ZIP"
sha256sum "$ZIP"
rm -rf "$STAGE"
