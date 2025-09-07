from app.services.google_play_service import GooglePlayService
from app.services.subscription_service import SubscriptionService


google_play_service = GooglePlayService()
subscription_service = SubscriptionService(google_play_service)
