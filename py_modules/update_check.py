import asyncio
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

import constants as C

try:
    import decky
    _logger = decky.logger
    _emit = decky.emit
except Exception:
    import logging
    _logger = logging.getLogger("amneziawg")

    async def _emit(*_args, **_kwargs):
        return None


VERSION_RE = re.compile(r"^v?(\d+(?:\.\d+){0,3})")


def _current_version() -> str:
    val = os.environ.get("DECKY_PLUGIN_VERSION") or ""
    if val:
        return val
    try:
        import decky as _d
        v = getattr(_d, "DECKY_PLUGIN_VERSION", "") or ""
        if v:
            return v
    except Exception:
        pass
    try:
        with open(os.path.join(C.PLUGIN_DIR, "package.json"), "r", encoding="utf-8") as f:
            return json.load(f).get("version", "") or ""
    except Exception:
        return ""


def _parse(v: str) -> Tuple[int, ...]:
    m = VERSION_RE.match(v.strip())
    if not m:
        return ()
    return tuple(int(x) for x in m.group(1).split("."))


def _is_newer(latest: str, current: str) -> bool:
    a, b = _parse(latest), _parse(current)
    if not a or not b:
        return False
    return a > b


def _fetch_latest_sync(owner: str, name: str, timeout: float) -> Dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{name}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{name}-update-check",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class UpdateChecker:
    def __init__(
        self,
        owner: str = C.REPO_OWNER,
        repo: str = C.REPO_NAME,
        asset_name: str = C.UPDATE_ASSET_NAME,
        interval_s: int = C.UPDATE_CHECK_INTERVAL_S,
        initial_delay_s: float = 30.0,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.asset_name = asset_name
        self.interval_s = interval_s
        self.initial_delay_s = initial_delay_s
        self._current = _current_version()
        self._latest: Optional[str] = None
        self._url: Optional[str] = None
        self._last_check_ts = 0.0

    def snapshot(self) -> Dict[str, Any]:
        return {
            "current": self._current,
            "latest": self._latest,
            "url": self._url,
            "newer": bool(self._latest and _is_newer(self._latest, self._current)),
            "last_check_ts": self._last_check_ts,
        }

    async def poll_once(self) -> None:
        try:
            data = await asyncio.to_thread(
                _fetch_latest_sync, self.owner, self.repo, 10.0
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            _logger.debug("update check network error: %s", e)
            return
        except Exception as e:
            _logger.warning("update check failed: %s", e)
            return

        tag = (data.get("tag_name") or "").strip()
        if not tag:
            return
        self._latest = tag
        self._last_check_ts = time.time()
        self._url = self._pick_asset_url(data) or data.get("html_url")

        if _is_newer(tag, self._current):
            _logger.info("update available: %s -> %s", self._current, tag)
            try:
                await _emit(C.EVENT_UPDATE_AVAILABLE, self.snapshot())
            except Exception as e:
                _logger.debug("emit update_available failed: %s", e)

    def _pick_asset_url(self, data: Dict[str, Any]) -> Optional[str]:
        for asset in data.get("assets") or []:
            if asset.get("name") == self.asset_name:
                return asset.get("browser_download_url")
        return (
            f"https://github.com/{self.owner}/{self.repo}/releases/latest/"
            f"download/{self.asset_name}"
        )

    async def run(self) -> None:
        if not self._current:
            _logger.info("update checker: no current version known, skipping")
            return
        try:
            await asyncio.sleep(self.initial_delay_s)
        except asyncio.CancelledError:
            raise
        while True:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                _logger.warning("update checker iter failed: %s", e)
            try:
                await asyncio.sleep(self.interval_s)
            except asyncio.CancelledError:
                raise
