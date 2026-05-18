#!/usr/bin/env bash
set -euo pipefail

if [[ "$EUID" -ne 0 ]] && ! command -v sudo >/dev/null; then
  echo "must be root or have sudo" >&2
  exit 1
fi

SUDO="sudo"
[[ "$EUID" -eq 0 ]] && SUDO=""

echo "==> installing deps (Arch)"
$SUDO pacman -Sy --noconfirm --needed python python-pip git base-devel iproute2 openresolv bash curl

HERE="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -x "$HERE/bin/amneziawg-go" ]]; then
  echo "==> bin/amneziawg-go missing — run scripts/build_bin.sh on a host with docker first" >&2
  exit 1
fi

echo "==> installing bins to /opt/amneziawg-dev/bin"
$SUDO mkdir -p /opt/amneziawg-dev/bin
$SUDO install -m755 "$HERE/bin/amneziawg-go" /opt/amneziawg-dev/bin/
$SUDO install -m755 "$HERE/bin/awg"          /opt/amneziawg-dev/bin/
$SUDO install -m755 "$HERE/bin/awg-quick"    /opt/amneziawg-dev/bin/

echo "==> generating a local test keypair"
TEST_DIR="/etc/amneziawg-dev"
$SUDO mkdir -p "$TEST_DIR"
if [[ ! -f "$TEST_DIR/server.key" ]]; then
  $SUDO sh -c "/opt/amneziawg-dev/bin/awg genkey | tee '$TEST_DIR/server.key' | /opt/amneziawg-dev/bin/awg pubkey > '$TEST_DIR/server.pub'"
  $SUDO sh -c "/opt/amneziawg-dev/bin/awg genkey | tee '$TEST_DIR/client.key' | /opt/amneziawg-dev/bin/awg pubkey > '$TEST_DIR/client.pub'"
  $SUDO chmod 600 "$TEST_DIR"/*.key
fi

CLIENT_PRIV=$($SUDO cat "$TEST_DIR/client.key")
SERVER_PUB=$($SUDO cat "$TEST_DIR/server.pub")

echo "==> writing $HERE/configs/wg-local-test.conf (loopback server)"
cat >"$HERE/configs/wg-local-test.conf" <<EOF
[Interface]
PrivateKey = $CLIENT_PRIV
Address = 10.66.66.2/24
Jc = 4
Jmin = 40
Jmax = 70
S1 = 50
S2 = 100
H1 = 1
H2 = 2
H3 = 3
H4 = 4

[Peer]
PublicKey = $SERVER_PUB
AllowedIPs = 10.66.66.0/24
Endpoint = 127.0.0.1:51820
PersistentKeepalive = 25
EOF
chmod 600 "$HERE/configs/wg-local-test.conf"

echo "==> done."
echo "    python tests:  cd $HERE && PYTHONPATH=py_modules python -m pytest tests/"
echo "    manual e2e:    cd $HERE && sudo PYTHONPATH=py_modules python -c 'import asyncio; from plugin import Plugin; p=Plugin(); print(asyncio.run(p.connect()))'"
