#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:?usage: patch_awg_quick.sh <path/to/awg-quick>}"

if [[ ! -f "$TARGET" ]]; then
  echo "not found: $TARGET" >&2
  exit 1
fi

if [[ ! -f "${TARGET}.orig" ]]; then
  cp "$TARGET" "${TARGET}.orig"
fi

if grep -q "AMNEZIAWG_DECKY_LOG" "$TARGET"; then
  echo "already patched"
  exit 0
fi

python3 - "$TARGET" <<'PY'
import re
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

pattern = re.compile(
    r'(cmd\s+"\$\{WG_QUICK_USERSPACE_IMPLEMENTATION:-amneziawg-go\}"\s+"\$INTERFACE")',
)

if not pattern.search(src):
    sys.stderr.write("warning: userspace launch line not found; leaving file unchanged\n")
    sys.exit(0)

replacement = (
    'cmd sh -c '
    '\'exec "${WG_QUICK_USERSPACE_IMPLEMENTATION:-amneziawg-go}" "$1" '
    '>>"${AMNEZIAWG_DECKY_LOG:-/dev/null}" 2>&1\' '
    'awg-userspace "$INTERFACE"'
)
patched = pattern.sub(lambda _m: replacement, src, count=1)

with open(path, "w", encoding="utf-8") as f:
    f.write(patched)

print("patched")
PY
