import os

_FALLBACK_PLUGIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _from_env_or_decky(env_name: str, decky_attr: str, fallback: str) -> str:
    val = os.environ.get(env_name) or ""
    if val:
        return val
    try:
        import decky
        attr = getattr(decky, decky_attr, "") or ""
        if attr:
            return attr
    except Exception:
        pass
    return fallback


PLUGIN_DIR = _from_env_or_decky(
    "DECKY_PLUGIN_DIR", "DECKY_PLUGIN_DIR", _FALLBACK_PLUGIN_DIR
)
LOG_DIR = _from_env_or_decky(
    "DECKY_PLUGIN_LOG_DIR", "DECKY_PLUGIN_LOG_DIR",
    os.path.join(PLUGIN_DIR, "logs"),
)
RUNTIME_DIR = _from_env_or_decky(
    "DECKY_PLUGIN_RUNTIME_DIR", "DECKY_PLUGIN_RUNTIME_DIR",
    os.path.join(PLUGIN_DIR, "runtime"),
)
SETTINGS_DIR = _from_env_or_decky(
    "DECKY_PLUGIN_SETTINGS_DIR", "DECKY_PLUGIN_SETTINGS_DIR",
    os.path.join(PLUGIN_DIR, "settings"),
)

BIN_DIR = os.path.join(PLUGIN_DIR, "bin")
CONF_DIR = os.path.join(SETTINGS_DIR, "configs")
LEGACY_CONF_DIR = os.path.join(PLUGIN_DIR, "configs")
DEFAULTS_DIR = os.path.join(PLUGIN_DIR, "defaults")

AWG_QUICK = os.path.join(BIN_DIR, "awg-quick")
AWG = os.path.join(BIN_DIR, "awg")
AWG_GO = os.path.join(BIN_DIR, "amneziawg-go")
AWG_LOG_FILE = os.path.join(LOG_DIR, "amneziawg-go.log")

IFACE = "wg0"
POLL_INTERVAL_S = 2
STALE_HANDSHAKE_S = 180
STALE_REUP_THROTTLE_S = 60
SUBPROC_TIMEOUT_S = 10

EVENT_STATUS_UPDATE = "status_update"
EVENT_UPDATE_AVAILABLE = "update_available"

REPO_OWNER = "basuev"
REPO_NAME = "amneziawg-deck"
UPDATE_ASSET_NAME = "AmneziaWG.zip"
UPDATE_CHECK_INTERVAL_S = 24 * 3600
