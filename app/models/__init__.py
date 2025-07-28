from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from app.models.user import User, Gender, AuthType, DeviceToken
from app.models.verification_code import VerificationCode
from app.models.agent import Agent
from app.models.message import Message
from app.models.chat_settings import ChatSettings
from app.models.chat import Chat
from app.models.associations import agent_followers
from app.models.resource import Resource
from app.models.settings import Settings
from app.models.report import Report
from app.models.notification import UserNotification, NotificationTemplate
from app.models.subscription import (
    SubscriptionPlan,
    UserSubscription,
    SubscriptionTransaction,
    SubscriptionUsage,
    SubscriptionPlanType,
    SubscriptionStatus,
    TransactionType
)
from app.models.user_deletion_log import UserDeletionLog
from app.models.system_settings import SystemSettings, SettingType, SettingCategory 