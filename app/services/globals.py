from app.core.agent.agent import AgentManager
from app.external_services.globals import gcs_service, google_play_service

from app.services.cache_service import CacheService
from app.services.subscription_service import SubscriptionService
from app.services.system_settings_service import SystemSettingsService
from app.services.voice_cache_service import VoiceCacheService
from app.services.voice_service import VoiceService
from app.services.character_card_service import CharacterCardService


cache_service = CacheService()
character_card_service = CharacterCardService()
system_settings_service = SystemSettingsService()
subscription_service = SubscriptionService(google_play_service, system_settings_service)
voice_cache_service = VoiceCacheService(gcs_service)
voice_service = VoiceService(gcs_service, voice_cache_service)
agent_manager = AgentManager(cache_service=cache_service)
