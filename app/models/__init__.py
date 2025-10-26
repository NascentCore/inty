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
from app.models.chat import Chat as Chat
from app.models.chat_history import ChatHistory as ChatHistory
from app.models.chat_settings import ChatSettings as ChatSettings
from app.models.evaluation import (
    EvaluationInteraction as EvaluationInteraction,
    EvaluationResult as EvaluationResult,
    EvaluationSession as EvaluationSession,
    EvaluationStatus as EvaluationStatus,
    EvaluationTemplate as EvaluationTemplate,
)
from app.models.message import Message as Message
from app.models.notification import (
    NotificationTemplate as NotificationTemplate,
    UserNotification as UserNotification,
)
from app.models.report import Report as Report
from app.models.resource import Resource as Resource
from app.models.settings import Settings as Settings
from app.models.subscription import (
    SubscriptionPlan as SubscriptionPlan,
    SubscriptionPlanType as SubscriptionPlanType,
    SubscriptionStatus as SubscriptionStatus,
    SubscriptionTransaction as SubscriptionTransaction,
    SubscriptionUsage as SubscriptionUsage,
    TransactionType as TransactionType,
    UserSubscription as UserSubscription,
)
from app.models.system_settings import (
    SettingCategory as SettingCategory,
    SettingType as SettingType,
    SystemSettings as SystemSettings,
)
from app.models.user import (
    AuthType as AuthType,
    DeviceToken as DeviceToken,
    Gender as Gender,
    User as User,
)
from app.models.verification_code import VerificationCode as VerificationCode
from app.models.voice_cache import VoiceCache as VoiceCache
