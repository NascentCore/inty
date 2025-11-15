"""
evaluation 前端基础 CI 测试
--------------------------------

通过在 pytest 流程中执行 npm 指令（type-check / lint / vitest / build），
在 CI 层面捕捉常见的前端问题，避免 evaluation 模块的改动破坏构建。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = REPO_ROOT / "evaluation"
NODE_MODULES_DIR = EVALUATION_DIR / "node_modules"
SDK_DIST_DIR = EVALUATION_DIR / "inty_sdk" / "dist"
DEFAULT_NODE_OPTIONS = "--max-old-space-size=4096"

if not EVALUATION_DIR.exists():
    pytest.skip(
        "evaluation 目录不存在，跳过前端 CI 检查",
        allow_module_level=True,
    )

if shutil.which("npm") is None:
    pytest.skip(
        "未检测到 npm，跳过 evaluation 前端 CI 检查",
        allow_module_level=True,
    )


def _run_in_evaluation(command: list[str]) -> None:
    env = os.environ.copy()
    env.setdefault("CI", "1")
    env.setdefault("NODE_OPTIONS", DEFAULT_NODE_OPTIONS)
    subprocess.run(
        command,
        cwd=EVALUATION_DIR,
        check=True,
        env=env,
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_evaluation_dependencies() -> None:
    if not SDK_DIST_DIR.exists():
        pytest.skip(
            "缺少 evaluation/inty_sdk/dist，请先运行 "
            "`git submodule update --init --recursive` 并构建 SDK。",
            allow_module_level=True,
        )

    if NODE_MODULES_DIR.exists():
        return

    _run_in_evaluation(["npm", "install", "--no-progress"])


@pytest.mark.slow
def test_evaluation_type_check(ensure_evaluation_dependencies) -> None:
    _run_in_evaluation(["npm", "run", "type-check"])


@pytest.mark.slow
def test_evaluation_lint(ensure_evaluation_dependencies) -> None:
    _run_in_evaluation(["npm", "run", "lint:check"])


@pytest.mark.slow
def test_evaluation_unit_tests(ensure_evaluation_dependencies) -> None:
    _run_in_evaluation(["npm", "run", "test"])


@pytest.mark.slow
def test_evaluation_build(ensure_evaluation_dependencies) -> None:
    _run_in_evaluation(["npm", "run", "build"])
