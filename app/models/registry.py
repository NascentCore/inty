"""Helpers for loading table model modules into the SQLAlchemy registry."""

import importlib
import pkgutil

import app.models


def load_model_modules() -> None:
    """Load every table model module (recursively, incl. subpackages) so relationships resolve."""
    # walk_packages recurses into subpackages (e.g. app.models.agentic_companion.*),
    # which iter_modules does not; subpackage __init__ stays docstring-only per repo rule.
    for module_info in pkgutil.walk_packages(
        app.models.__path__, f"{app.models.__name__}."
    ):
        if module_info.ispkg:
            continue
        if module_info.name in {"app.models.base", "app.models.registry"}:
            continue
        importlib.import_module(module_info.name)
