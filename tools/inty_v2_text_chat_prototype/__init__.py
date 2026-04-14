"""Legacy import path: same module object as ``tools.inty_v2_repl`` (tests, old scripts)."""

from __future__ import annotations

import importlib
import sys

_impl = importlib.import_module("tools.inty_v2_repl")
sys.modules[__name__] = _impl
