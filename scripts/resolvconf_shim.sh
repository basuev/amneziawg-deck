#!/usr/bin/env bash
# Drop-in `resolvconf` shim for SteamOS (which only ships `resolvectl`).
# Translates the subset of `resolvconf` calls that `awg-quick` and `wg-quick` use.
#   resolvconf -a <iface>                  # add: reads "nameserver A.B.C.D" lines from stdin
#   resolvconf -d <iface> [-f]             # delete: revert DNS for iface
# Anything else is ignored with rc=0 so PostUp/PreDown hooks don't fail the link-up.

set -eu

mode="${1:-}"
iface_raw="${2:-}"

iface="${iface_raw#tun.}"

case "$mode" in
  -a)
    if [ -z "$iface" ]; then exit 0; fi
    nameservers=""
    domains=""
    while IFS= read -r line; do
      key=$(printf '%s' "$line" | awk '{print $1}')
      val=$(printf '%s' "$line" | cut -d' ' -f2-)
      case "$key" in
        nameserver) nameservers="$nameservers $val" ;;
        search|domain) domains="$domains $val" ;;
      esac
    done
    if [ -n "$nameservers" ]; then
      # shellcheck disable=SC2086
      resolvectl dns "$iface" $nameservers >/dev/null 2>&1 || true
    fi
    if [ -n "$domains" ]; then
      # shellcheck disable=SC2086
      resolvectl domain "$iface" $domains >/dev/null 2>&1 || true
    fi
    exit 0
    ;;
  -d)
    if [ -z "$iface" ]; then exit 0; fi
    resolvectl revert "$iface" >/dev/null 2>&1 || true
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
