#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "usage: $0 vX.Y.Z" >&2
  exit 2
fi
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "version must look like v1.2.3, got: $VERSION" >&2
  exit 2
fi

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

PKG_VERSION="${VERSION#v}"
PKG_JSON_VERSION="$(python3 -c 'import json,sys;print(json.load(open("package.json"))["version"])')"
if [[ "$PKG_VERSION" != "$PKG_JSON_VERSION" ]]; then
  echo "package.json version is $PKG_JSON_VERSION, but releasing $VERSION ($PKG_VERSION)" >&2
  echo "bump package.json first or pass the matching tag." >&2
  exit 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "working tree is dirty — commit or stash before releasing." >&2
  git status --short >&2
  exit 2
fi

if gh release view "$VERSION" >/dev/null 2>&1; then
  echo "release $VERSION already exists on GitHub." >&2
  exit 2
fi

echo "==> building frontend"
pnpm run build

if [[ ! -x bin/amneziawg-go || ! -x bin/awg || ! -f bin/awg-quick || ! -x bin/resolvconf ]]; then
  echo "==> bin/ missing or incomplete — building static binaries via Docker"
  bash scripts/build_bin.sh
fi

if ! grep -q AMNEZIAWG_DECKY_LOG bin/awg-quick; then
  echo "==> applying awg-quick patch"
  bash scripts/patch_awg_quick.sh bin/awg-quick
fi

echo "==> packaging"
bash scripts/package.sh

echo "==> computing checksums"
sha256sum AmneziaWG.zip bin/amneziawg-go bin/awg bin/awg-quick bin/resolvconf > SHA256SUMS

if ! git rev-parse "$VERSION" >/dev/null 2>&1; then
  echo "==> tagging $VERSION"
  git tag -a "$VERSION" -m "$VERSION"
  git push origin "$VERSION"
fi

REPO_FULL="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
DOWNLOAD_URL="https://github.com/${REPO_FULL}/releases/latest/download/AmneziaWG.zip"

echo "==> creating release $VERSION"
gh release create "$VERSION" AmneziaWG.zip SHA256SUMS \
  --title "$VERSION" \
  --notes "## Install / Update

In Decky → Settings → Developer → **Install Plugin from URL**, paste:

\`\`\`
$DOWNLOAD_URL
\`\`\`

This URL is permanent — paste it again on future updates and Decky pulls the latest release. Your \`.conf\` files in \`~/homebrew/settings/AmneziaWG/configs/\` survive updates.

Verify integrity against \`SHA256SUMS\`."

echo
echo "==> released: https://github.com/${REPO_FULL}/releases/tag/${VERSION}"
echo "==> permanent download URL: $DOWNLOAD_URL"
