from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from app.models.agent import Agent
from app.models.associations import agent_followers
from app.models.chat import Chat
from app.models.chat_settings import ChatSettings
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
from app.models.user_deletion_log import UserDeletionLog
from app.models.verification_code import VerificationCode
from app.models.report import Report
from app.models.notification import UserNotification, NotificationTemplate
from app.models.subscription import (
    SubscriptionPlan,
    UserSubscription,
    SubscriptionTransaction,
    SubscriptionUsage,
    SubscriptionPlanType,
    SubscriptionStatus,
    TransactionType,
)
from app.models.user_deletion_log import UserDeletionLog
from app.models.evaluation import (
    EvaluationSession,
    EvaluationResult,
    EvaluationInteraction,
    EvaluationTemplate,
    EvaluationStatus,
)
