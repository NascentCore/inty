from app.external_services.globals import (
    google_play_service,
    telegram_bot_service,
)

from app.services.subscription_service import SubscriptionService

subscription_service = SubscriptionService(google_play_service)
