import asyncio
import os
import re
import shlex
from dataclasses import dataclass
from typing import List, Optional, Tuple

import constants as C

try:
    import decky
    _logger = decky.logger
except Exception:
    import logging
    _logger = logging.getLogger("amneziawg")

REDACT_RE = re.compile(r"(PrivateKey|PresharedKey)\s*=\s*\S+", re.IGNORECASE)


class WgError(RuntimeError):
    pass


@dataclass
class Peer:
    public_key: str
    endpoint: str
    last_handshake: int
    rx_bytes: int
    tx_bytes: int


def _redact(text: str) -> str:
    return REDACT_RE.sub(r"\1=<redacted>", text)


_DECKY_LEAKED_ENV_VARS = (
    "LD_LIBRARY_PATH", "LD_PRELOAD",
    "PYTHONHOME", "PYTHONPATH",
    "VIRTUAL_ENV",
)


def _build_env(extra: Optional[dict] = None) -> dict:
    env = os.environ.copy()
    for var in _DECKY_LEAKED_ENV_VARS:
        env.pop(var, None)
    env["PATH"] = f"{C.BIN_DIR}:/usr/sbin:/usr/bin:/sbin:/bin"
    env["WG_QUICK_USERSPACE_IMPLEMENTATION"] = C.AWG_GO
    env["WG_SUDO"] = "0"
    env["AMNEZIAWG_DECKY_LOG"] = C.AWG_LOG_FILE
    if extra:
        env.update(extra)
    return env


async def _run(
    cmd: List[str],
    timeout: int = C.SUBPROC_TIMEOUT_S,
    extra_env: Optional[dict] = None,
    quiet: bool = False,
) -> Tuple[int, str, str]:
    env = _build_env(extra_env)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except (FileNotFoundError, PermissionError, OSError) as e:
        raise WgError(f"cannot spawn {cmd[0]}: {e}") from e
    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise WgError(f"timeout running: {' '.join(shlex.quote(c) for c in cmd)}")

    out = out_b.decode(errors="replace")
    err = err_b.decode(errors="replace")
    if proc.returncode != 0 and not quiet:
        _logger.warning("cmd rc=%s: %s | stderr=%s",
                        proc.returncode,
                        ' '.join(shlex.quote(c) for c in cmd),
                        _redact(err.strip()))
    return proc.returncode or 0, out, err


async def is_interface_up(name: str) -> bool:
    try:
        rc, _, _ = await _run(["ip", "link", "show", name], timeout=3, quiet=True)
        return rc == 0
    except WgError:
        return False
    except Exception:
        return False


def sanitized_path_for(iface: str) -> str:
    return os.path.join(C.RUNTIME_DIR, f"{iface}.conf")


async def _ip_link_del(iface: str) -> bool:
    try:
        rc, _, _ = await _run(["ip", "link", "del", "dev", iface], timeout=5, quiet=True)
        return rc == 0
    except Exception:
        return False


async def up(iface: str, conf_path: str) -> None:
    os.makedirs(os.path.dirname(C.AWG_LOG_FILE), exist_ok=True)
    os.makedirs(C.RUNTIME_DIR, exist_ok=True)

    sanitized = sanitized_path_for(iface)
    from config import sanitize_conf  # local import to avoid cycle in tests
    sanitize_conf(conf_path, sanitized)

    try:
        rc, out, err = await _run([C.AWG_QUICK, "up", sanitized], timeout=30)
    except WgError as e:
        if await is_interface_up(iface):
            _logger.warning("awg-quick up stalled (%s) but iface is up — treating as success", e)
            return
        raise
    if rc != 0:
        raise WgError(_redact(err.strip() or out.strip() or f"awg-quick up exit={rc}"))


async def down(iface: str) -> None:
    sanitized = sanitized_path_for(iface)
    target = sanitized if os.path.isfile(sanitized) else iface
    last_err: Optional[str] = None
    try:
        rc, out, err = await _run([C.AWG_QUICK, "down", target], timeout=30)
        if rc == 0:
            return
        last_err = _redact(err.strip() or out.strip() or f"awg-quick down exit={rc}")
    except WgError as e:
        last_err = str(e)

    if not await is_interface_up(iface):
        _logger.info("awg-quick down rc!=0 (%s) but iface already gone — ok", last_err)
        return

    _logger.warning("awg-quick down failed (%s) — forcing 'ip link del %s'", last_err, iface)
    if await _ip_link_del(iface):
        return
    if not await is_interface_up(iface):
        return
    raise WgError(last_err or f"failed to bring {iface} down")


async def dump(iface: str) -> List[Peer]:
    rc, out, err = await _run([C.AWG, "show", iface, "dump"], timeout=5)
    if rc != 0:
        raise WgError(_redact(err.strip() or f"awg show dump exit={rc}"))
    return parse_awg_dump(out)


def parse_awg_dump(stdout: str) -> List[Peer]:
    peers: List[Peer] = []
    for i, line in enumerate(stdout.strip().splitlines()):
        if i == 0:
            continue
        parts = line.split("\t")
        if len(parts) < 8:
            continue
        try:
            peers.append(
                Peer(
                    public_key=parts[0],
                    endpoint=parts[2],
                    last_handshake=int(parts[4] or 0),
                    rx_bytes=int(parts[5] or 0),
                    tx_bytes=int(parts[6] or 0),
                )
            )
        except (ValueError, IndexError):
            continue
    return peers


async def read_logs(tail: int) -> str:
    if not os.path.isfile(C.AWG_LOG_FILE):
        return ""
    try:
        rc, out, _ = await _run(["tail", "-n", str(int(tail)), C.AWG_LOG_FILE], timeout=3)
    except WgError:
        return ""
    return _redact(out) if rc == 0 else ""
