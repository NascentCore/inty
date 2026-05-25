import sys

# TODO(INTY_CONFIG_YAML): os.environ.setdefault("INTY_CONFIG_YAML", "devops/config.yaml.test") when unset
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")
