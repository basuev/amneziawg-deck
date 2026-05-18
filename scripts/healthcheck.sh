#!/usr/bin/env bash
set -u

PLUGIN="${PLUGIN_DIR:-/home/deck/homebrew/plugins/AmneziaWG}"
IFACE="${IFACE:-wg0}"

fail=0
pass() { printf "PASS  %s\n" "$1"; }
nope() { printf "FAIL  %s  -- %s\n" "$1" "$2"; fail=1; }
check() {
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then pass "$name"; else nope "$name" "command failed: $*"; fi
}

check "plugin dir exists" test -d "$PLUGIN"
check "amneziawg-go present" test -x "$PLUGIN/bin/amneziawg-go"
check "awg present" test -x "$PLUGIN/bin/awg"
check "awg-quick present" test -f "$PLUGIN/bin/awg-quick"

if file "$PLUGIN/bin/amneziawg-go" 2>/dev/null | grep -qi "statically linked"; then
  pass "amneziawg-go statically linked"
else
  nope "amneziawg-go statically linked" "file did not report static"
fi

CONF_COUNT=$(ls "$PLUGIN"/configs/*.conf 2>/dev/null | wc -l | tr -d ' ')
if [[ "$CONF_COUNT" -ge 1 ]]; then
  pass "at least one .conf in configs/"
else
  nope "at least one .conf in configs/" "drop wg0.conf into $PLUGIN/configs/"
fi

if ip link show "$IFACE" >/dev/null 2>&1; then
  pass "interface $IFACE is up"

  HS_LINE=$("$PLUGIN/bin/awg" show "$IFACE" latest-handshakes 2>/dev/null | head -1)
  HS_TS=$(echo "$HS_LINE" | awk '{print $2}')
  if [[ -n "$HS_TS" && "$HS_TS" -gt 0 ]]; then
    AGE=$(( $(date +%s) - HS_TS ))
    if [[ "$AGE" -lt 60 ]]; then
      pass "handshake age ${AGE}s < 60s"
    else
      nope "handshake age" "stale: ${AGE}s old"
    fi
  else
    nope "handshake exists" "no handshake recorded yet"
  fi

  EXIT_IP=$(curl -s --max-time 5 https://api.ipify.org || true)
  if [[ -n "$EXIT_IP" ]]; then
    pass "egress IP reachable: $EXIT_IP"
  else
    nope "egress IP reachable" "curl ipify failed"
  fi
else
  printf "SKIP  interface checks (turn on the toggle first)\n"
fi

exit "$fail"
