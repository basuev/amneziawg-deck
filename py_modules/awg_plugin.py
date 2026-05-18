import asyncio
import os
import shutil
from typing import Any, Dict, List, Optional

import constants as C
import config as cfg
import wg_manager as wg
from status_loop import StatusLoop
from update_check import UpdateChecker

try:
    import decky
    _logger = decky.logger
except Exception:
    import logging
    _logger = logging.getLogger("amneziawg")


class Plugin:
    def __init__(self) -> None:
        self._loop_task: Optional[asyncio.Task] = None
        self._status_loop: Optional[StatusLoop] = None
        self._update_task: Optional[asyncio.Task] = None
        self._update_checker: Optional[UpdateChecker] = None

    async def _main(self) -> None:
        _logger.info("AmneziaWG plugin: starting (plugin_dir=%s, log_dir=%s, conf_dir=%s)",
                     C.PLUGIN_DIR, C.LOG_DIR, C.CONF_DIR)
        for d in (C.LOG_DIR, C.CONF_DIR, C.RUNTIME_DIR):
            try:
                if d:
                    os.makedirs(d, exist_ok=True)
            except Exception as e:
                _logger.error("makedirs(%r) failed: %s", d, e)

        self._migrate_legacy_configs()

        try:
            self._status_loop = StatusLoop(
                iface=C.IFACE,
                interval=C.POLL_INTERVAL_S,
                stale_handshake_s=C.STALE_HANDSHAKE_S,
                reup_throttle_s=C.STALE_REUP_THROTTLE_S,
                adopted_conf_path=None,
            )
            self._loop_task = asyncio.create_task(self._status_loop.run())
            asyncio.create_task(self._adopt_running_iface())
        except Exception as e:
            _logger.exception("AmneziaWG _main bootstrap failed: %s", e)

        try:
            self._update_checker = UpdateChecker()
            self._update_task = asyncio.create_task(self._update_checker.run())
        except Exception as e:
            _logger.warning("update checker bootstrap failed: %s", e)

    def _migrate_legacy_configs(self) -> None:
        legacy = C.LEGACY_CONF_DIR
        target = C.CONF_DIR
        if legacy == target:
            return
        try:
            if not os.path.isdir(legacy):
                return
            legacy_confs = [f for f in os.listdir(legacy) if f.endswith(".conf")]
            if not legacy_confs:
                return
            os.makedirs(target, exist_ok=True)
            for name in legacy_confs:
                src = os.path.join(legacy, name)
                dst = os.path.join(target, name)
                if os.path.exists(dst):
                    _logger.info("migrate: skip %s (already present in settings)", name)
                    continue
                shutil.move(src, dst)
                try:
                    os.chmod(dst, 0o600)
                except OSError:
                    pass
                _logger.info("migrate: moved %s -> %s", src, dst)
        except Exception as e:
            _logger.warning("legacy config migration failed: %s", e)

    async def _adopt_running_iface(self) -> None:
        try:
            if not await wg.is_interface_up(C.IFACE):
                return
            confs = cfg.list_confs(C.CONF_DIR)
            adopted = confs[0] if confs else None
            if self._status_loop and adopted:
                self._status_loop.set_active_conf(adopted)
                _logger.info("interface %s already up — adopted %s", C.IFACE, adopted)
        except Exception as e:
            _logger.warning("adopt-running-iface failed: %s", e)

    async def _unload(self) -> None:
        _logger.info("AmneziaWG plugin: unloading")
        if self._update_task:
            self._update_task.cancel()
            try:
                await asyncio.wait_for(self._update_task, timeout=0.5)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                pass
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await asyncio.wait_for(self._loop_task, timeout=1.5)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                pass
        try:
            await asyncio.wait_for(self._best_effort_down(), timeout=2.5)
        except asyncio.TimeoutError:
            _logger.warning("down on unload timed out (>2.5s); tunnel may remain "
                            "up — clean up via `awg-quick down wg0` over ssh")
        except Exception as e:
            _logger.error("down on unload failed: %s", e)

    async def _best_effort_down(self) -> None:
        if await wg.is_interface_up(C.IFACE):
            await wg.down(C.IFACE)

    async def _uninstall(self) -> None:
        _logger.info("AmneziaWG plugin: uninstall (no-op; _unload already called)")

    async def connect(self) -> Dict[str, Any]:
        _logger.info("connect: called")
        confs = cfg.list_confs(C.CONF_DIR)
        if not confs:
            _logger.info("connect: no conf, returning early")
            return {"ok": False, "error": f"no .conf in {C.CONF_DIR}"}

        conf_path = confs[0]
        ok, reason = cfg.validate_conf(conf_path)
        if not ok:
            _logger.info("connect: invalid conf, returning early: %s", reason)
            return {"ok": False, "error": f"invalid conf: {reason}"}

        if await wg.is_interface_up(C.IFACE):
            _logger.info("connect: iface already up, adopting")
            if self._status_loop:
                self._status_loop.set_active_conf(conf_path)
                self._status_loop.set_error(None)
                await self._status_loop.kick()
            _logger.info("connect: returning ok (already up)")
            return {"ok": True, "note": "already up"}

        _logger.info("connect: calling wg.up(%s)", conf_path)
        try:
            await wg.up(C.IFACE, conf_path)
        except wg.WgError as e:
            _logger.error("connect: wg.up failed: %s", e)
            if self._status_loop:
                self._status_loop.set_error(str(e))
                await self._status_loop.kick()
            return {"ok": False, "error": str(e)}

        _logger.info("connect: wg.up returned, kicking status")
        if self._status_loop:
            self._status_loop.set_active_conf(conf_path)
            self._status_loop.set_error(None)
            await self._status_loop.kick()
        _logger.info("connect: returning ok")
        return {"ok": True}

    async def disconnect(self) -> Dict[str, Any]:
        _logger.info("disconnect: called")
        try:
            if await wg.is_interface_up(C.IFACE):
                _logger.info("disconnect: calling wg.down")
                await wg.down(C.IFACE)
                _logger.info("disconnect: wg.down returned")
            else:
                _logger.info("disconnect: iface not up, skipping wg.down")
            if self._status_loop:
                self._status_loop.set_active_conf(None)
                self._status_loop.set_error(None)
                await self._status_loop.kick()
            _logger.info("disconnect: returning ok")
            return {"ok": True}
        except wg.WgError as e:
            _logger.error("disconnect: wg.down failed: %s", e)
            if self._status_loop:
                self._status_loop.set_error(str(e))
                await self._status_loop.kick()
            return {"ok": False, "error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        if self._status_loop:
            return await self._status_loop.snapshot()
        return {
            "connected": False,
            "interface": C.IFACE,
            "public_endpoint": "",
            "last_handshake_age": None,
            "rx_bytes": 0,
            "tx_bytes": 0,
            "error": "plugin not initialized",
        }

    async def list_configs(self) -> List[str]:
        return [os.path.basename(p) for p in cfg.list_confs(C.CONF_DIR)]

    async def get_logs(self, tail: int = 200) -> str:
        try:
            tail_n = max(1, min(int(tail), 5000))
        except (TypeError, ValueError):
            tail_n = 200
        return await wg.read_logs(tail_n)

    async def get_plugin_dir(self) -> str:
        return C.PLUGIN_DIR

    async def get_configs_dir(self) -> str:
        return C.CONF_DIR

    async def get_update_info(self) -> Dict[str, Any]:
        if self._update_checker:
            return self._update_checker.snapshot()
        return {"current": "", "latest": None, "url": None, "newer": False}

    async def check_update_now(self) -> Dict[str, Any]:
        if self._update_checker:
            await self._update_checker.poll_once()
            return self._update_checker.snapshot()
        return {"current": "", "latest": None, "url": None, "newer": False}
