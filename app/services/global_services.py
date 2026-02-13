from app.external_services.globals import google_play_service

from app.services.subscription_service import SubscriptionService
from app.services.voice_service import VoiceService

subscription_service = SubscriptionService(google_play_service)
voice_service = VoiceService(subscription_service)
