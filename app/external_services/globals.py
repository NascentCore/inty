from app.core.config import global_config_loaded_from_config_yaml

from app.external_services.android_publisher import create_android_publisher_service
from app.external_services.gcs_service import GCSService
from app.external_services.google_play_service import GooglePlayService

from loguru import logger


service_account_key = global_config_loaded_from_config_yaml.google_play.service_account_key
debug = global_config_loaded_from_config_yaml.app.debug

try:
    android_publisher_service = create_android_publisher_service(service_account_key)
    google_play_service = GooglePlayService(android_publisher_service)
    gcs_service = GCSService()
except Exception as e:
    logger.error(f"Failed to create one of the external services: {e}")
    if debug:
        logger.error("Failure ignored in debug mode")
        android_publisher_service = None
        google_play_service = None
        gcs_service = None
    else:
        raise e
