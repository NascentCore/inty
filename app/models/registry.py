"""Helpers for loading table model modules into the SQLAlchemy registry."""

import importlib
import pkgutil

import app.models


def load_model_modules() -> None:
    """Load every table model module so string relationships can be resolved."""
    for module_info in pkgutil.iter_modules(
        app.models.__path__, f"{app.models.__name__}."
    ):
        if module_info.name in {"app.models.base", "app.models.registry"}:
            continue
        importlib.import_module(module_info.name)
