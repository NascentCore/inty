from loguru import logger
from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.android_publisher import create_android_publisher_service


service_account_key = global_config_loaded_from_config_yaml.google_play.service_account_key
debug = global_config_loaded_from_config_yaml.app.debug

try:
    android_publisher_service = create_android_publisher_service(service_account_key)
except Exception as e:
    logger.error(f"Failed to create Android publisher service: {e}")
    if debug:
        logger.error("Failure ignored in debug mode")
        android_publisher_service = None
    else:
        raise e
