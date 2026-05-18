import os
import re
import stat
from pathlib import Path
from typing import Tuple, Dict, List

REQUIRED_INTERFACE_KEYS = {"PrivateKey", "Address"}
REQUIRED_PEER_KEYS = {"PublicKey", "Endpoint", "AllowedIPs"}
AMNEZIA_KEYS = {"Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4"}
SECTION_RE = re.compile(r"^\[(\w+)\]$")

EMPTY_AWG2_LINE_RE = re.compile(r"^\s*[Ii][2-5]\s*=\s*$")


def list_confs(conf_dir: str) -> List[str]:
    p = Path(conf_dir)
    if not p.is_dir():
        return []
    return sorted(str(f) for f in p.glob("*.conf"))


def parse_conf(path: str) -> Dict[str, List[Dict[str, str]]]:
    sections: Dict[str, List[Dict[str, str]]] = {}
    current: Dict[str, str] | None = None
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = SECTION_RE.match(line)
        if m:
            current = {}
            sections.setdefault(m.group(1), []).append(current)
            continue
        if "=" in line and current is not None:
            key, value = (x.strip() for x in line.split("=", 1))
            current[key] = value
    return sections


def validate_conf(path: str) -> Tuple[bool, str]:
    if not os.path.isfile(path):
        return False, "file not found"

    try:
        st = os.stat(path)
        if stat.S_IMODE(st.st_mode) & 0o077:
            try:
                os.chmod(path, 0o600)
            except OSError as e:
                return False, f"cannot chmod 600: {e}"
    except OSError as e:
        return False, f"stat failed: {e}"

    try:
        sec = parse_conf(path)
    except Exception as e:
        return False, f"parse error: {e}"

    if not sec.get("Interface"):
        return False, "missing [Interface] section"
    if not sec.get("Peer"):
        return False, "missing [Peer] section"

    iface_keys = sec["Interface"][0].keys()
    missing_i = REQUIRED_INTERFACE_KEYS - iface_keys
    if missing_i:
        return False, f"missing Interface keys: {sorted(missing_i)}"

    peer_keys = sec["Peer"][0].keys()
    missing_p = REQUIRED_PEER_KEYS - peer_keys
    if missing_p:
        return False, f"missing Peer keys: {sorted(missing_p)}"

    return True, "ok"


def has_amnezia_params(path: str) -> bool:
    try:
        sec = parse_conf(path)
    except Exception:
        return False
    iface = sec["Interface"][0] if sec.get("Interface") else {}
    return bool(AMNEZIA_KEYS & iface.keys())


def sanitize_conf(src_path: str, dst_path: str) -> int:
    """
    Workaround for amneziawg-tools v1.0.20260223 bug in get_value():
    `if (keylen >= linelen) return NULL` returns NULL for `I2=` (empty value),
    so `awg setconf` reports `Line unrecognized: 'I2='` even though parse_awg_string
    accepts empty strings. Stripping empty I2..I5 lines is safe per AWG2 spec
    (these obfuscation params are optional).

    Writes a sanitized copy to dst_path with 0600 perms, returns number of lines
    removed.
    """
    src_text = Path(src_path).read_text(encoding="utf-8", errors="replace")
    removed = 0
    out_lines = []
    for line in src_text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        if EMPTY_AWG2_LINE_RE.match(body):
            removed += 1
            continue
        out_lines.append(line)
    if src_text and not src_text.endswith("\n"):
        out_lines.append("\n")

    dst_dir = os.path.dirname(dst_path)
    if dst_dir:
        os.makedirs(dst_dir, exist_ok=True)
    fd = os.open(dst_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, "".join(out_lines).encode("utf-8"))
    finally:
        os.close(fd)
    return removed
