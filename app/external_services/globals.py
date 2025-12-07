from loguru import logger

from app.core.config import Environment, global_config_loaded_from_config_yaml
from app.external_services.android_publisher import create_android_publisher_service
from app.external_services.fakes.android_publisher import FakeAndroidPublisher
from app.external_services.google_play_service import GooglePlayService

env = global_config_loaded_from_config_yaml.app.environment
debug = global_config_loaded_from_config_yaml.app.debug

try:
    if env == Environment.TEST:
        android_publisher_service = FakeAndroidPublisher()
    else:
        service_account_key = (
            global_config_loaded_from_config_yaml.app.gcp_service_account_key
        )
        android_publisher_service = create_android_publisher_service(
            service_account_key
        )
    google_play_service = GooglePlayService(
        android_publisher_service, global_config_loaded_from_config_yaml.google_play
    )
except Exception as e:
    logger.error(f"Failed to create one of the external services: {e}")
    if debug:
        logger.error("Failure ignored in debug mode")
        android_publisher_service = None
        google_play_service = None
    else:
        raise e
