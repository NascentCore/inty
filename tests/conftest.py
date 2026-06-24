import os
import sys

# pytest default: devops/config.yaml.test — unit/integration tests with faked external services.
# REPL regression E2E uses devops/config.yaml.regression_tests (real LLM/GitHub).
# Engineer local Ops/REPL uses devops/config.yaml.local.
os.environ.setdefault("INTY_CONFIG_YAML", "devops/config.yaml.test")
from loguru import logger

pytest_plugins = ["tests.fixtures.async_db_engine"]

logger.remove()
logger.add(sys.stderr, level="INFO")
