#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$HERE/bin"
mkdir -p "$OUT"

AWG_GO_REF="${AWG_GO_REF:-v0.2.18}"
AWG_TOOLS_REF="${AWG_TOOLS_REF:-v1.0.20260223}"
GOLANG_IMAGE="${GOLANG_IMAGE:-golang:1.26-alpine}"
ALPINE_IMAGE="${ALPINE_IMAGE:-alpine:3.23}"

echo "==> Building amneziawg-go ($AWG_GO_REF)"
docker run --rm --platform linux/amd64 -v "$OUT:/out" "$GOLANG_IMAGE" sh -ec "
  apk add --no-cache git make >/dev/null
  git clone --depth 1 --branch '$AWG_GO_REF' https://github.com/amnezia-vpn/amneziawg-go /src
  cd /src
  CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags '-w -s -extldflags \"-static\"' -o /out/amneziawg-go .
  chmod +x /out/amneziawg-go
"

echo "==> Building amneziawg-tools ($AWG_TOOLS_REF)"
docker run --rm --platform linux/amd64 -v "$OUT:/out" "$ALPINE_IMAGE" sh -ec "
  apk add --no-cache git build-base bash linux-headers >/dev/null
  git clone --depth 1 --branch '$AWG_TOOLS_REF' https://github.com/amnezia-vpn/amneziawg-tools /src
  cd /src/src
  make LDFLAGS='-static' WITH_BASHCOMPLETION=no WITH_WGQUICK=yes
  cp wg /out/awg
  cp wg-quick/linux.bash /out/awg-quick
  chmod +x /out/awg /out/awg-quick
"

echo "==> Installing resolvconf shim (SteamOS has no resolvconf)"
install -m755 "$HERE/scripts/resolvconf_shim.sh" "$OUT/resolvconf"

echo "==> Sanity checks"
file "$OUT/amneziawg-go" | grep -qi "statically linked" || { echo "amneziawg-go is not statically linked!"; exit 1; }
file "$OUT/awg"          | grep -qi "statically linked" || { echo "awg is not statically linked!"; exit 1; }
head -1 "$OUT/awg-quick" | grep -q "bash"               || { echo "awg-quick is not a bash script!"; exit 1; }
head -1 "$OUT/resolvconf"| grep -q "bash"               || { echo "resolvconf shim missing shebang!"; exit 1; }

echo "==> Writing SHA256SUMS"
(cd "$OUT" && sha256sum amneziawg-go awg awg-quick resolvconf > SHA256SUMS)
cat "$OUT/SHA256SUMS"

echo "==> done: $OUT"
