#!/usr/bin/env python3
"""Forbidden imports: app/ layer boundaries and app/tests.app intra-repo package rules."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import cyclopts
from loguru import logger

from python_import_scan import (
    INTRA_REPO_PACKAGE_ROOTS,
    iter_imports,
)

app = cyclopts.App(
    help="Check app/ layer boundaries and app + tests/app intra-repo import rules."
)

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
    (
        "external_services",
        "api",
    ): "External services must not depend on API layer.",
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

# ``app/`` and ``tests/app/`` may import these intra-repo roots only.
ALLOWED_INTRA_REPO_IMPORT_ROOTS = frozenset(
    {
        "app",
    }
)

SCAN_TREES: tuple[tuple[str, str], ...] = (
    ("app", "app"),
    ("tests/app", "tests.app"),
)


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


def _intra_repo_import_rule(importer_label: str, module: str) -> str | None:
    root = module.split(".", 1)[0]
    if root not in INTRA_REPO_PACKAGE_ROOTS:
        return None
    if root in ALLOWED_INTRA_REPO_IMPORT_ROOTS:
        return None
    if importer_label == "tests.app" and root == "tests":
        parts = module.split(".")
        if len(parts) >= 2 and parts[1] == "app":
            return None
    return (
        f"{importer_label}/ must only depend on app/ "
        f"and external packages; must not import intra-repo {root!r}."
    )


def _scan_layer_violations(app_root: Path, repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    scanned_files = 0
    for file_path in sorted(app_root.rglob("*.py")):
        source_layer = _source_layer(file_path, app_root)
        if not source_layer:
            continue
        scanned_files += 1

        try:
            imported_modules = iter_imports(file_path, repo_root)
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
                    file_path=file_path.relative_to(repo_root).as_posix(),
                    line_number=line_number,
                    source_layer=source_layer,
                    target_layer=target_layer,
                    imported_module=imported_module,
                    rule=FORBIDDEN_LAYER_DEPENDENCIES[rule_key],
                )
            )
    logger.debug(f"Scanned app layer python files: {scanned_files}")
    return violations


def _scan_intra_repo_violations(
    tree_root: Path,
    importer_label: str,
    repo_root: Path,
) -> list[Violation]:
    violations: list[Violation] = []
    if not tree_root.is_dir():
        return violations

    scanned_files = 0
    for file_path in sorted(tree_root.rglob("*.py")):
        scanned_files += 1
        try:
            imported_modules = iter_imports(file_path, repo_root)
        except SyntaxError as exc:
            logger.error(f"Failed to parse {file_path}: {exc}")
            raise

        for imported_module, line_number in imported_modules:
            rule = _intra_repo_import_rule(importer_label, imported_module)
            if rule is None:
                continue
            root = imported_module.split(".", 1)[0]
            violations.append(
                Violation(
                    file_path=file_path.relative_to(repo_root).as_posix(),
                    line_number=line_number,
                    source_layer=importer_label,
                    target_layer=root,
                    imported_module=imported_module,
                    rule=rule,
                )
            )
    logger.debug(
        f"Scanned {importer_label} intra-repo python files: {scanned_files}"
    )
    return violations


def _scan(repo_root: Path) -> list[Violation]:
    app_root = repo_root / "app"
    violations: list[Violation] = []
    violations.extend(_scan_layer_violations(app_root, repo_root))
    for tree_rel, importer_label in SCAN_TREES:
        violations.extend(
            _scan_intra_repo_violations(
                repo_root / tree_rel,
                importer_label,
                repo_root,
            )
        )
    return violations


@app.default
def main(
    repo_root: Annotated[
        str,
        cyclopts.Parameter(
            name="--repo-root",
            help="Repository root (contains app/ and tests/app/).",
        ),
    ] = ".",
    json_output: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--json-output", help="Optional JSON report file path."
        ),
    ] = None,
) -> None:
    root = Path(repo_root).resolve()
    app_dir = root / "app"
    if not app_dir.exists() or not app_dir.is_dir():
        print(f"[ERROR] app/ does not exist under repo root: {root}")
        raise SystemExit(2)

    violations = _scan(root)

    if json_output:
        output_path = Path(json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                [asdict(v) for v in violations], ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        print(f"Wrote JSON report: {output_path}")

    rules_checked = len(FORBIDDEN_LAYER_DEPENDENCIES) + len(SCAN_TREES)

    if not violations:
        print("Layer dependency check passed.")
        print(f"Rules checked: {rules_checked}")
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
