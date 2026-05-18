import logging
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY_MODULES = os.path.join(ROOT, "py_modules")
if PY_MODULES not in sys.path:
    sys.path.insert(0, PY_MODULES)


def _make_decky_stub() -> types.ModuleType:
    mod = types.ModuleType("decky")
    mod.DECKY_PLUGIN_DIR = ROOT
    mod.DECKY_PLUGIN_LOG_DIR = os.path.join(ROOT, ".test-logs")
    mod.DECKY_PLUGIN_RUNTIME_DIR = os.path.join(ROOT, ".test-runtime")
    mod.DECKY_PLUGIN_SETTINGS_DIR = os.path.join(ROOT, ".test-settings")
    mod.logger = logging.getLogger("amneziawg.test")

    async def _emit(_event, *_args, **_kwargs):
        return None

    mod.emit = _emit
    return mod


if "decky" not in sys.modules:
    sys.modules["decky"] = _make_decky_stub()
