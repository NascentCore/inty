from loguru import logger

from app.core.config import Environment, global_config_loaded_from_config_yaml
from app.external_services.android_publisher import (
    create_android_publisher_service,
)
from app.external_services.fakes.android_publisher import FakeAndroidPublisher
from app.external_services.fakes.telegram_bot import FakeTelegramBotService
from app.external_services.google_play_service import GooglePlayService
from app.external_services.telegram_bot import TelegramBotService
from app.utils.config import resolved_telegram_bot_token

env = global_config_loaded_from_config_yaml.app.environment
debug = global_config_loaded_from_config_yaml.app.debug

try:
    telegram_bot_service = None
    if env == Environment.TEST:
        android_publisher_service = FakeAndroidPublisher()
        telegram_bot_service = FakeTelegramBotService()
    else:
        service_account_key = (
            global_config_loaded_from_config_yaml.app.gcp_service_account_key
        )
        android_publisher_service = create_android_publisher_service(
            service_account_key
        )
        telegram_bot_token = resolved_telegram_bot_token(
            global_config_loaded_from_config_yaml.agent
        )
        if telegram_bot_token:
            telegram_bot_service = TelegramBotService(
                bot_token=telegram_bot_token
            )
    google_play_service = GooglePlayService(
        android_publisher_service,
        global_config_loaded_from_config_yaml.google_play,
    )
except Exception as e:
    logger.error(f"Failed to create one of the external services: {e}")
    if debug:
        logger.error("Failure ignored in debug mode")
        android_publisher_service = None
        google_play_service = None
        telegram_bot_service = None
    else:
        raise e
