import os
import sys
from pathlib import Path

# pytest default: devops/config.yaml.test — unit/integration tests with faked external services.
# REPL regression E2E uses devops/config.yaml.regression_tests (real LLM/GitHub).
# Engineer local Ops/REPL uses devops/config.yaml.local.
os.environ.setdefault("INTY_CONFIG_YAML", "devops/config.yaml.test")


def _ensure_repo_tools_package() -> None:
    """Repo ``tools/`` must win over unrelated site-packages ``tools`` modules."""
    repo_root = Path(__file__).resolve().parent.parent
    repo_tools_init = repo_root / "tools" / "__init__.py"
    tools_mod = sys.modules.get("tools")
    if tools_mod is not None:
        mod_file = getattr(tools_mod, "__file__", None)
        if mod_file != str(repo_tools_init):
            for name in list(sys.modules):
                if name == "tools" or name.startswith("tools."):
                    del sys.modules[name]
    repo_root_str = str(repo_root)
    if repo_root_str in sys.path:
        sys.path.remove(repo_root_str)
    sys.path.insert(0, repo_root_str)


_ensure_repo_tools_package()

from loguru import logger

pytest_plugins = ["tests.fixtures.async_db_engine"]


def pytest_runtest_setup(item: object) -> None:
    """Re-assert repo ``tools/`` before each test (earlier tests may load site-packages)."""
    _ensure_repo_tools_package()


logger.remove()
logger.add(sys.stderr, level="INFO")
