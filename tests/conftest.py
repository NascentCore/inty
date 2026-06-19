import os
import sys

os.environ.setdefault("INTY_CONFIG_YAML", "devops/config.yaml.test")
from loguru import logger

pytest_plugins = ["tests.fixtures.async_db_engine"]

logger.remove()
logger.add(sys.stderr, level="INFO")
