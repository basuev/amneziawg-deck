# AmneziaWG for Steam Deck (Decky plugin)

One-toggle AmneziaWG VPN client for Steam Deck Game Mode. Adds a Quick Access Menu panel that connects to your AmneziaVPN server using the obfuscated WireGuard protocol exported from the desktop Amnezia client.

- Bundles statically-linked `amneziawg-go` (userspace) + `awg`/`awg-quick` — nothing is written to the read-only `/usr`.
- Survives SteamOS updates (lives under `/home/deck/homebrew/`).
- Watchdog re-establishes the tunnel after sleep/resume if the last handshake gets stale.

## Install

1. On the Deck (Desktop Mode, one-time): install [Decky Loader](https://decky.xyz).
2. In QAM (Game Mode): **Decky → Settings → Developer → Install Plugin from URL** → paste either form (both 302-redirect to the latest release zip):

   - Short (easy to type on the Deck keyboard): `clck.ru/3ThymB`
   - Full: `https://github.com/basuev/amneziawg-deck/releases/latest/download/AmneziaWG.zip`
3. Drop your `.conf` (see below) into `/home/deck/homebrew/settings/AmneziaWG/configs/`.
4. Open QAM → **AmneziaWG** → toggle ON.

## Update

Paste the **same URL** in **Install Plugin from URL** again. Decky removes the previous version, unpacks the new one, and hot-reloads — no SSH, no Steam restart. Your `.conf` files in `~/homebrew/settings/AmneziaWG/configs/` survive because they live outside the plugin tree.

The plugin checks GitHub Releases once per day and shows a badge in **Diagnostics → Update** when a newer version is available. The badge gives you the same URL to paste.

### Build & deploy from source

```bash
# 1. build static binaries (Docker required)
bash scripts/build_bin.sh

# 2. build frontend
pnpm install
pnpm run build

# 3. ship to the Deck over SSH
DECK_HOST=deck@steamdeck.local bash scripts/deploy_to_deck.sh
```

## Getting your `.conf` from the Amnezia desktop client

1. Open the desktop Amnezia client on Windows/macOS/Linux.
2. Connection card → **Share VPN** → choose **AmneziaWG native config** → **Save** to `wg0.conf`.
3. Copy to the Deck (any method works):
   ```bash
   scp wg0.conf deck@<deck-ip>:/home/deck/homebrew/settings/AmneziaWG/configs/
   ```
4. Reopen the QAM panel. The file will be picked up automatically and `chmod 600`-ed.

Configs in `~/homebrew/settings/AmneziaWG/configs/` survive plugin reinstalls and updates.
The plugin uses the first `*.conf` found (alphabetically). Both Amnezia-obfuscated configs (with `Jc/Jmin/Jmax/S1/S2/H1..H4`) and plain WireGuard configs work.

If you upgrade from an older build that kept configs in `/home/deck/homebrew/plugins/AmneziaWG/configs/`, the plugin moves them to the new path on first start.

## Verify it works (Deck)

```bash
ssh deck@<deck-ip> bash /home/deck/homebrew/plugins/AmneziaWG/scripts/healthcheck.sh
```

Should print `PASS` for: binaries present + static, config found, interface up, handshake fresh, egress IP routed through the tunnel.

## Develop without a Deck

Backend runs on any Linux x86_64 (an Arch VM matches SteamOS most closely):

```bash
# unit tests on macOS/Linux — no root, no network
python3 -m pytest tests/ -v

# integration test in an Arch VM (after build_bin.sh on the host)
bash scripts/vm_setup.sh                      # installs deps, generates a loopback config
sudo PYTHONPATH=py_modules python3 -c \
  'import asyncio; from plugin import Plugin; p=Plugin(); print(asyncio.run(p.connect()))'
```

Frontend builds with `pnpm watch`; visual smoke is done on the Deck (no jsdom mock of `@decky/ui`).

## Security

- `.conf` files are auto-`chmod 600`. Logs are scrubbed of `PrivateKey` / `PresharedKey`.
- No external HTTP from the backend; no telemetry; no auto-update.
- Binary integrity: every release publishes `SHA256SUMS` and Docker-reproducible build instructions (`scripts/build_bin.sh`).
- The plugin requires `_root` (declared in `plugin.json`) — Decky Loader already runs as root and forks the backend with uid=0, no extra prompts.

## Troubleshooting

- **Toggle does nothing / "No config found"** — drop a `*.conf` into `~/homebrew/settings/AmneziaWG/configs/`, reopen the panel.
- **Connected but no internet** — likely a DNS issue. Add to your `[Interface]` section:
  ```ini
  PostUp = resolvectl dns %i 1.1.1.1
  ```
- **View logs** — QAM → AmneziaWG → **Diagnostics → View logs** shows the last 300 lines of `~/homebrew/logs/AmneziaWG/amneziawg-go.log`.

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).

Bundles unmodified `amneziawg-go` and `amneziawg-tools` (GPL-2.0) from the [amnezia-vpn](https://github.com/amnezia-vpn) project; `awg-quick` carries a minimal one-line patch to redirect the userspace daemon's stderr to the plugin log file (see `scripts/patch_awg_quick.sh`; `bin/awg-quick.orig` retains the upstream version).
