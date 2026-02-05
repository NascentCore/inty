"""
Imports all models for centralized management.

Base object is used to define all tables in app/models, when importing all models,
their metadata is added to Base.metadata, which is then shared with alembic's env.py file
to get all data tables.

!!! All models must be defined with Base as their base class.
!!! All models must be imported here to be added to Base.metadata.
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from app.models.agent import Agent as Agent
from app.models.associations import agent_followers as agent_followers
from app.models.character_theme import CharacterTheme as CharacterTheme
from app.models.character_theme import CharacterThemeAgent as CharacterThemeAgent
from app.models.chat import Chat as Chat
from app.models.chat_history import ChatHistory as ChatHistory
from app.models.chat_settings import ChatSettings as ChatSettings
from app.models.evaluation import EvaluationInteraction as EvaluationInteraction
from app.models.evaluation import EvaluationResult as EvaluationResult
from app.models.evaluation import EvaluationSession as EvaluationSession
from app.models.evaluation import EvaluationStatus as EvaluationStatus
from app.models.evaluation import EvaluationTemplate as EvaluationTemplate
from app.models.feedback_push import FeedbackPushHistory as FeedbackPushHistory
from app.models.memory import FestivalMemoryConfig as FestivalMemoryConfig
from app.models.memory import Memory as Memory
from app.models.memory import MemoryExtractionLog as MemoryExtractionLog
from app.models.message import Message as Message
from app.models.notification import NotificationTemplate as NotificationTemplate
from app.models.notification import UserNotification as UserNotification
from app.models.push_notification import (
    PushNotificationHistory as PushNotificationHistory,
)
from app.models.report import Report as Report
from app.models.resource import Resource as Resource
from app.models.settings import Settings as Settings
from app.models.subscription import SubscriptionPlan as SubscriptionPlan
from app.models.subscription import SubscriptionPlanType as SubscriptionPlanType
from app.models.subscription import SubscriptionStatus as SubscriptionStatus
from app.models.subscription import SubscriptionTransaction as SubscriptionTransaction
from app.models.subscription import SubscriptionUsage as SubscriptionUsage
from app.models.subscription import TransactionType as TransactionType
from app.models.subscription import UserSubscription as UserSubscription
from app.models.system_settings import SettingCategory as SettingCategory
from app.models.system_settings import SettingType as SettingType
from app.models.system_settings import SystemSettings as SystemSettings
from app.models.user import AuthType as AuthType
from app.models.user import DeviceToken as DeviceToken
from app.models.user import Gender as Gender
from app.models.user import User as User
from app.models.user_analytics_report import UserAnalyticsReport as UserAnalyticsReport
from app.models.verification_code import VerificationCode as VerificationCode
from app.models.voice_cache import VoiceCache as VoiceCache
