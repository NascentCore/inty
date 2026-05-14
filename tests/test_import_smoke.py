from __future__ import annotations

import importlib
import pkgutil
from typing import Iterable

EXCLUDES: tuple[str, ...] = (
    # known side-effectful modules on import
    "app.main",
)


def _iter_app_modules() -> Iterable[str]:
    root = importlib.import_module("app")
    for module_info in pkgutil.walk_packages(root.__path__, root.__name__ + "."):
        name = module_info.name
        if name.startswith(EXCLUDES):
            continue
        yield name


def test_import_all_app_modules():
    failures: list[tuple[str, str]] = []
    for name in sorted(set(_iter_app_modules())):
        try:
            importlib.import_module(name)
        except (
            Exception
        ) as exc:  # noqa: BLE001 - We want to catch any import error surface
            failures.append((name, repr(exc)))
    assert not failures, "\n".join(f"IMPORT FAILED: {m}: {e}" for m, e in failures)
