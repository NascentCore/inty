#!/usr/bin/env python3
"""AST checks for companion AwakeTurn / DreamingBatch memory-phase invariants."""
from __future__ import annotations

import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated

import cyclopts
from loguru import logger

_REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FOR_IMPORT))

from app.core.companion_harness.runtime.turn_invariants import (  # noqa: E402
    AWAKE_TURN_FORBIDDEN_STORE_MUTATIONS,
    AWAKE_TURN_ORCHESTRATOR_RELATIVE_PATHS,
    AWAKE_TURN_TRANSCRIPT_ONLY_RELATIVE_PATH,
    CONSOLIDATE_MEMORY_DURING_DREAMING_IMPORT_ALLOWLIST,
    DREAMING_BATCH_CURATION_ENTRY,
    DREAMING_CURATOR_CALLABLES,
    DREAMING_CURATOR_CALLER_RELATIVE_PATHS,
    FORBIDDEN_LEGACY_MEMORY_SYMBOLS,
)

app = cyclopts.App(
    help="Check companion AwakeTurn / DreamingBatch memory-phase invariants."
)

_DREAMING_CONSOLIDATION_MODULE = (
    "app.core.companion_harness.memory.dreaming_consolidation"
)


@dataclass(frozen=True)
class Violation:
    file_path: str
    line_number: int
    rule: str
    detail: str


def _relative_posix(file_path: Path, repo_root: Path) -> str:
    return file_path.relative_to(repo_root).as_posix()


def _module_path_from_file(file_path: Path, repo_root: Path) -> str | None:
    rel = file_path.relative_to(repo_root)
    if rel.parts[0] != "app" or rel.suffix != ".py":
        return None
    return ".".join(rel.with_suffix("").parts)


def _is_test_file(relative_path: str) -> bool:
    return relative_path.startswith("tests/")


def _resolve_from_module(
    file_path: Path, repo_root: Path, node: ast.ImportFrom
) -> str | None:
    if node.level == 0:
        return node.module

    relative_file = file_path.relative_to(repo_root).with_suffix("")
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


def _imported_modules(file_path: Path, repo_root: Path) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        module = _resolve_from_module(file_path, repo_root, node)
        if not module:
            continue
        if module == "app":
            for alias in node.names:
                imports.append((f"app.{alias.name}", node.lineno))
            continue
        for alias in node.names:
            if alias.name == "*":
                imports.append((module, node.lineno))
            else:
                imports.append((f"{module}.{alias.name}", node.lineno))
                imports.append((module, node.lineno))
    return imports


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_store_receiver(node: ast.expr) -> bool:
    if isinstance(node, ast.Name) and node.id == "store":
        return True
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id == "store"
    return False


def _scan_consolidate_imports(
    file_path: Path, repo_root: Path, relative_path: str
) -> list[Violation]:
    if _is_test_file(relative_path):
        return []

    module_path = _module_path_from_file(file_path, repo_root)
    if module_path is None:
        return []

    violations: list[Violation] = []
    for imported_module, line_number in _imported_modules(file_path, repo_root):
        references_consolidate = (
            imported_module == DREAMING_BATCH_CURATION_ENTRY
            or imported_module.endswith(f".{DREAMING_BATCH_CURATION_ENTRY}")
            or imported_module == _DREAMING_CONSOLIDATION_MODULE
            or imported_module.startswith(f"{_DREAMING_CONSOLIDATION_MODULE}.")
        )
        if not references_consolidate:
            continue
        if module_path in CONSOLIDATE_MEMORY_DURING_DREAMING_IMPORT_ALLOWLIST:
            continue
        violations.append(
            Violation(
                file_path=relative_path,
                line_number=line_number,
                rule="dreaming_batch_curation_import",
                detail=(
                    f"{module_path} must not import {_DREAMING_CONSOLIDATION_MODULE} "
                    f"or {DREAMING_BATCH_CURATION_ENTRY}; allowlist only."
                ),
            )
        )
    return violations


def _scan_consolidate_calls(
    file_path: Path, repo_root: Path, relative_path: str
) -> list[Violation]:
    if _is_test_file(relative_path):
        return []

    module_path = _module_path_from_file(file_path, repo_root)
    if module_path is None:
        return []

    violations: list[Violation] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name != DREAMING_BATCH_CURATION_ENTRY:
            continue
        if module_path in CONSOLIDATE_MEMORY_DURING_DREAMING_IMPORT_ALLOWLIST:
            continue
        violations.append(
            Violation(
                file_path=relative_path,
                line_number=node.lineno,
                rule="dreaming_batch_curation_call",
                detail=(
                    f"{module_path} must not call {DREAMING_BATCH_CURATION_ENTRY}; "
                    "DreamingBatch orchestrator only."
                ),
            )
        )
    return violations


def _scan_curator_calls(
    file_path: Path, repo_root: Path, relative_path: str
) -> list[Violation]:
    if _is_test_file(relative_path):
        return []

    if relative_path in DREAMING_CURATOR_CALLER_RELATIVE_PATHS:
        return []

    violations: list[Violation] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name not in DREAMING_CURATOR_CALLABLES:
            continue
        violations.append(
            Violation(
                file_path=relative_path,
                line_number=node.lineno,
                rule="dreaming_curator_call",
                detail=(
                    f"{name} may only be called from "
                    f"{sorted(DREAMING_CURATOR_CALLER_RELATIVE_PATHS)}."
                ),
            )
        )
    return violations


def _scan_forbidden_legacy_symbols(
    file_path: Path, repo_root: Path, relative_path: str
) -> list[Violation]:
    if _is_test_file(relative_path):
        return []

    violations: list[Violation] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_LEGACY_MEMORY_SYMBOLS:
                    violations.append(
                        Violation(
                            file_path=relative_path,
                            line_number=node.lineno,
                            rule="forbidden_legacy_memory",
                            detail=f"Legacy symbol {root!r} must not be imported.",
                        )
                    )
            continue
        if isinstance(node, ast.ImportFrom):
            module = _resolve_from_module(file_path, repo_root, node) or ""
            root = module.split(".")[-1]
            if root in FORBIDDEN_LEGACY_MEMORY_SYMBOLS:
                violations.append(
                    Violation(
                        file_path=relative_path,
                        line_number=node.lineno,
                        rule="forbidden_legacy_memory",
                        detail=f"Legacy module {module!r} must not be imported.",
                    )
                )
            for alias in node.names:
                if alias.name in FORBIDDEN_LEGACY_MEMORY_SYMBOLS:
                    violations.append(
                        Violation(
                            file_path=relative_path,
                            line_number=node.lineno,
                            rule="forbidden_legacy_memory",
                            detail=f"Legacy symbol {alias.name!r} must not be imported.",
                        )
                    )
            continue
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_LEGACY_MEMORY_SYMBOLS:
            violations.append(
                Violation(
                    file_path=relative_path,
                    line_number=node.lineno,
                    rule="forbidden_legacy_memory",
                    detail=f"Legacy symbol {node.id!r} must not appear in production code.",
                )
            )
    return violations


def _scan_awake_orchestrator_dreaming_imports(
    file_path: Path, repo_root: Path, relative_path: str
) -> list[Violation]:
    if relative_path not in AWAKE_TURN_ORCHESTRATOR_RELATIVE_PATHS:
        return []

    violations: list[Violation] = []
    for imported_module, line_number in _imported_modules(file_path, repo_root):
        if _DREAMING_CONSOLIDATION_MODULE not in imported_module:
            continue
        violations.append(
            Violation(
                file_path=relative_path,
                line_number=line_number,
                rule="awake_turn_no_dreaming_consolidation_import",
                detail=(
                    "AwakeTurn orchestrator must not import dreaming_consolidation."
                ),
            )
        )
    return violations


def _scan_turn_transcript_only_store_mutations(
    file_path: Path, repo_root: Path, relative_path: str
) -> list[Violation]:
    if relative_path != AWAKE_TURN_TRANSCRIPT_ONLY_RELATIVE_PATH:
        return []

    violations: list[Violation] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if not _is_store_receiver(node.func.value):
            continue
        method = node.func.attr
        if method not in AWAKE_TURN_FORBIDDEN_STORE_MUTATIONS:
            continue
        violations.append(
            Violation(
                file_path=relative_path,
                line_number=node.lineno,
                rule="awake_turn_transcript_only",
                detail=(
                    f"run_turn must not call store.{method}(); "
                    "AwakeTurn only appends transcript via append_jsonl_record."
                ),
            )
        )
    return violations


def _scan_memory_pipeline_file(repo_root: Path) -> list[Violation]:
    legacy_path = (
        repo_root / "app/core/companion_harness/memory/memory_pipeline.py"
    )
    if not legacy_path.is_file():
        return []
    return [
        Violation(
            file_path=_relative_posix(legacy_path, repo_root),
            line_number=1,
            rule="forbidden_legacy_memory",
            detail="memory_pipeline.py must not exist; use dreaming_consolidation.",
        )
    ]


def collect_violations(repo_root: Path) -> list[Violation]:
    """Return all companion turn invariant violations under ``repo_root``."""
    app_root = repo_root / "app"
    violations: list[Violation] = []
    violations.extend(_scan_memory_pipeline_file(repo_root))

    if not app_root.is_dir():
        return violations

    for file_path in sorted(app_root.rglob("*.py")):
        relative_path = _relative_posix(file_path, repo_root)
        try:
            violations.extend(_scan_consolidate_imports(file_path, repo_root, relative_path))
            violations.extend(_scan_consolidate_calls(file_path, repo_root, relative_path))
            violations.extend(_scan_curator_calls(file_path, repo_root, relative_path))
            violations.extend(
                _scan_forbidden_legacy_symbols(file_path, repo_root, relative_path)
            )
            violations.extend(
                _scan_awake_orchestrator_dreaming_imports(
                    file_path, repo_root, relative_path
                )
            )
            violations.extend(
                _scan_turn_transcript_only_store_mutations(
                    file_path, repo_root, relative_path
                )
            )
        except SyntaxError as exc:
            logger.error(f"Failed to parse {file_path}: {exc}")
            raise

    return violations


@app.default
def main(
    repo_root: Annotated[
        str,
        cyclopts.Parameter(
            name="--repo-root",
            help="Repository root (contains app/).",
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

    violations = collect_violations(root)

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

    if not violations:
        print("Companion turn invariant check passed.")
        raise SystemExit(0)

    print("Companion turn invariant check failed.")
    print(f"Violations: {len(violations)}")
    for violation in violations:
        print(
            "{path}:{line} rule={rule} detail={detail}".format(
                path=violation.file_path,
                line=violation.line_number,
                rule=violation.rule,
                detail=violation.detail,
            )
        )
    raise SystemExit(1)


if __name__ == "__main__":
    app()
