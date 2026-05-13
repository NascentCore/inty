"""
Check if a user has privilege to access premium features.
"""

from app import models
from app.core.user_privilege.superuser_check import is_superuser
from app.schemas.user import User as UserSchema


def is_eligible_for_premium(
    user: UserSchema, subscription_status: models.SubscriptionStatus
) -> bool:
    """
    Check if a user has privilege to access premium features.
    """
    return is_superuser(user) or subscription_status.is_subscribed
