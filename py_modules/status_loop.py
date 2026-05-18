import asyncio
import time
from typing import Optional, Dict, Any

import constants as C
import wg_manager as wg

try:
    import decky
    _logger = decky.logger
    _emit = decky.emit
except Exception:
    import logging
    _logger = logging.getLogger("amneziawg")

    async def _emit(*_args, **_kwargs):
        return None


def _empty(iface: str) -> Dict[str, Any]:
    return {
        "connected": False,
        "interface": iface,
        "public_endpoint": "",
        "last_handshake_age": None,
        "rx_bytes": 0,
        "tx_bytes": 0,
        "error": None,
    }


class StatusLoop:
    def __init__(
        self,
        iface: str = C.IFACE,
        interval: int = C.POLL_INTERVAL_S,
        stale_handshake_s: int = C.STALE_HANDSHAKE_S,
        reup_throttle_s: int = C.STALE_REUP_THROTTLE_S,
        adopted_conf_path: Optional[str] = None,
    ):
        self.iface = iface
        self.interval = interval
        self.stale_handshake_s = stale_handshake_s
        self.reup_throttle_s = reup_throttle_s
        self._snapshot: Dict[str, Any] = _empty(iface)
        self._stale_count = 0
        self._last_reup_ts = 0.0
        self._active_conf: Optional[str] = adopted_conf_path

    def set_active_conf(self, path: Optional[str]) -> None:
        self._active_conf = path
        self._stale_count = 0

    def set_error(self, message: Optional[str]) -> None:
        self._snapshot["error"] = message

    async def snapshot(self) -> Dict[str, Any]:
        return dict(self._snapshot)

    async def kick(self) -> None:
        try:
            snap = await self._tick()
        except Exception as e:
            _logger.warning("kick: tick failed: %s", e)
            return
        self._snapshot = snap
        self._stale_count = 0
        asyncio.create_task(self._emit_snapshot(snap))

    async def _emit_snapshot(self, snap: Dict[str, Any]) -> None:
        try:
            await _emit(C.EVENT_STATUS_UPDATE, snap)
        except Exception as e:
            _logger.debug("emit failed: %s", e)

    async def _maybe_reup(self) -> None:
        if not self._active_conf:
            return
        now = time.time()
        if now - self._last_reup_ts < self.reup_throttle_s:
            return
        self._last_reup_ts = now
        _logger.info("handshake stale on %s, performing down+up", self.iface)
        try:
            if await wg.is_interface_up(self.iface):
                await wg.down(self.iface)
        except wg.WgError as e:
            _logger.warning("watchdog down failed: %s", e)
        try:
            await wg.up(self.iface, self._active_conf)
            self._stale_count = 0
        except wg.WgError as e:
            self._snapshot["error"] = f"reconnect failed: {e}"

    async def _tick(self) -> Dict[str, Any]:
        if not await wg.is_interface_up(self.iface):
            self._stale_count = 0
            snap = _empty(self.iface)
            if self._snapshot.get("error"):
                snap["error"] = self._snapshot["error"]
            return snap

        peers = await wg.dump(self.iface)
        peer = peers[0] if peers else None
        now = int(time.time())
        age = (now - peer.last_handshake) if peer and peer.last_handshake else None
        snap = {
            "connected": True,
            "interface": self.iface,
            "public_endpoint": peer.endpoint if peer else "",
            "last_handshake_age": age,
            "rx_bytes": peer.rx_bytes if peer else 0,
            "tx_bytes": peer.tx_bytes if peer else 0,
            "error": None,
        }

        if age is not None and age > self.stale_handshake_s:
            self._stale_count += 1
            if self._stale_count >= 2:
                await self._maybe_reup()
        else:
            self._stale_count = 0

        return snap

    async def run(self) -> None:
        while True:
            try:
                snap = await self._tick()
                if snap != self._snapshot:
                    self._snapshot = snap
                    try:
                        await _emit(C.EVENT_STATUS_UPDATE, snap)
                    except Exception as e:
                        _logger.debug("emit failed: %s", e)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                _logger.warning("status loop iter failed: %s", e)
            await asyncio.sleep(self.interval)
