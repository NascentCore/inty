#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated

import cyclopts
from loguru import logger

app = cyclopts.App(help="Check forbidden cross-layer imports in app/")

ARCH_LAYERS = {
    "api",
    "schemas",
    "services",
    "models",
    "utils",
    "middleware",
    "external_services",
}

FORBIDDEN_LAYER_DEPENDENCIES: dict[tuple[str, str], str] = {
    ("api", "middleware"): "API layer must not depend on middleware layer.",
    ("services", "middleware"): "Services must not depend on middleware layer.",
    ("models", "services"): "Models must not depend on services layer.",
    ("models", "schemas"): "Models must not depend on schemas layer.",
    (
        "models",
        "external_services",
    ): "Models must not depend on external services layer.",
    ("models", "middleware"): "Models must not depend on middleware layer.",
    (
        "schemas",
        "external_services",
    ): "Schemas must not depend on external services layer.",
    ("schemas", "middleware"): "Schemas must not depend on middleware layer.",
    ("utils", "models"): "Utils must not depend on models layer.",
    ("utils", "middleware"): "Utils must not depend on middleware layer.",
    ("external_services", "api"): "External services must not depend on API layer.",
    (
        "external_services",
        "services",
    ): "External services must not depend on services layer.",
    (
        "external_services",
        "models",
    ): "External services must not depend on models layer.",
    (
        "external_services",
        "middleware",
    ): "External services must not depend on middleware layer.",
}


@dataclass(frozen=True)
class Violation:
    file_path: str
    line_number: int
    source_layer: str
    target_layer: str
    imported_module: str
    rule: str


def _source_layer(file_path: Path, app_root: Path) -> str | None:
    relative = file_path.relative_to(app_root)
    if not relative.parts:
        return None
    first = relative.parts[0]
    if first in ARCH_LAYERS:
        return first
    return None


def _target_layer(module: str) -> str | None:
    if not module.startswith("app."):
        return None
    parts = module.split(".")
    if len(parts) < 2:
        return None
    layer = parts[1]
    if layer in ARCH_LAYERS:
        return layer
    return None


def _resolve_from_module(
    file_path: Path, app_root: Path, node: ast.ImportFrom
) -> str | None:
    if node.level == 0:
        return node.module

    relative_file = file_path.relative_to(app_root.parent).with_suffix("")
    package_parts = list(relative_file.parts[:-1])

    up_levels = node.level - 1
    if up_levels > len(package_parts):
        return None
    if up_levels:
        package_parts = package_parts[: len(package_parts) - up_levels]

    if node.module:
        package_parts += node.module.split(".")

    if not package_parts:
        return None
    return ".".join(package_parts)


def _iter_imports(file_path: Path, app_root: Path) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        module = _resolve_from_module(file_path, app_root, node)
        if not module:
            continue

        if module == "app":
            for alias in node.names:
                candidate = f"app.{alias.name}"
                imports.append((candidate, node.lineno))
            continue

        imports.append((module, node.lineno))
    return imports


def _scan(app_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    scanned_files = 0
    for file_path in sorted(app_root.rglob("*.py")):
        source_layer = _source_layer(file_path, app_root)
        if not source_layer:
            continue
        scanned_files += 1

        try:
            imported_modules = _iter_imports(file_path, app_root)
        except SyntaxError as exc:
            logger.error(f"Failed to parse {file_path}: {exc}")
            raise

        for imported_module, line_number in imported_modules:
            target_layer = _target_layer(imported_module)
            if not target_layer:
                continue

            rule_key = (source_layer, target_layer)
            if rule_key not in FORBIDDEN_LAYER_DEPENDENCIES:
                continue

            violations.append(
                Violation(
                    file_path=file_path.relative_to(app_root.parent).as_posix(),
                    line_number=line_number,
                    source_layer=source_layer,
                    target_layer=target_layer,
                    imported_module=imported_module,
                    rule=FORBIDDEN_LAYER_DEPENDENCIES[rule_key],
                )
            )
    logger.debug(f"Scanned python files: {scanned_files}")
    return violations


@app.default
def main(
    app_root: Annotated[
        str,
        cyclopts.Parameter(name="--app-root", help="Path to app root directory."),
    ] = "app",
    json_output: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--json-output", help="Optional JSON report file path."
        ),
    ] = None,
) -> None:
    root = Path(app_root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] app root does not exist: {root}")
        raise SystemExit(2)

    violations = _scan(root)

    if json_output:
        output_path = Path(json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps([asdict(v) for v in violations], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote JSON report: {output_path}")

    if not violations:
        print("Layer dependency check passed.")
        print(f"Rules checked: {len(FORBIDDEN_LAYER_DEPENDENCIES)}")
        raise SystemExit(0)

    print("Layer dependency check failed.")
    print(f"Violations: {len(violations)}")
    for violation in violations:
        print(
            "{path}:{line} {src}->{dst} import={module} rule={rule}".format(
                path=violation.file_path,
                line=violation.line_number,
                src=violation.source_layer,
                dst=violation.target_layer,
                module=violation.imported_module,
                rule=violation.rule,
            )
        )
    raise SystemExit(1)


if __name__ == "__main__":
    app()
