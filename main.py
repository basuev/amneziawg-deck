import os
import sys

_PY_MODULES = os.path.join(os.path.dirname(__file__), "py_modules")
if _PY_MODULES not in sys.path:
    sys.path.append(_PY_MODULES)

from awg_plugin import Plugin  # noqa: E402,F401
