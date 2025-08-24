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

from app.models.agent import Agent
from app.models.associations import agent_followers
from app.models.chat import Chat
from app.models.chat_settings import ChatSettings
from app.models.evaluation import (
    EvaluationInteraction,
    EvaluationResult,
    EvaluationSession,
    EvaluationStatus,
    EvaluationTemplate,
)
from app.models.message import Message
from app.models.notification import NotificationTemplate, UserNotification
from app.models.report import Report
from app.models.resource import Resource
from app.models.settings import Settings
from app.models.subscription import (
    SubscriptionPlan,
    SubscriptionPlanType,
    SubscriptionStatus,
    SubscriptionTransaction,
    SubscriptionUsage,
    TransactionType,
    UserSubscription,
)
from app.models.system_settings import SettingCategory, SettingType, SystemSettings
from app.models.user import AuthType, DeviceToken, Gender, User
from app.models.verification_code import VerificationCode
from app.models.voice_cache import VoiceCache
