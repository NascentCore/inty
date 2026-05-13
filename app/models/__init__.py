"""
倒入所有的数据表模型

注意⚠️：
1. 这与代码库要求的空 __init__.py 相悖，是由于历史原因，改动较为复杂，牵连风险，所以保持。
2. 所有子类型必须是 Base 子类，否则无法被 Alembic 识别。
3. 所有表模型定义必须导入到这里，否则无法被加入到 Base.metadata 中，从而无法被 Alembic 识别。


Base对象用于定义app/models中的所有数据表；当导入所有模型时，它们的元数据会被添加到Base.metadata中，
随后该metadata会被alembic的env.py共享，用于识别所有数据表。
"""

from sqlalchemy.ext.declarative import declarative_base

# 所有表模型定义必须在 Base 后被倒入。
Base = declarative_base()

from app.models.agent import Agent as Agent
from app.models.character_theme import CharacterTheme as CharacterTheme
from app.models.character_theme import CharacterThemeAgent as CharacterThemeAgent
from app.models.companion_memory_documents import (
    CompanionMemoryDocumentVersion as CompanionMemoryDocumentVersion,
)
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
from app.models.messages_compaction import MessagesCompaction as MessagesCompaction
from app.models.notification import NotificationTemplate as NotificationTemplate
from app.models.notification import UserNotification as UserNotification
from app.models.phone_call import PhoneCallCallerBinding as PhoneCallCallerBinding
from app.models.push_notification import (
    PushNotificationHistory as PushNotificationHistory,
)
from app.models.report import Report as Report
from app.models.resource import Resource as Resource
from app.models.settings import Settings as Settings
from app.models.surprise_snap import SurpriseSnapProgress as SurpriseSnapProgress
from app.models.surprise_snap import SurpriseSnapUnlock as SurpriseSnapUnlock
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
