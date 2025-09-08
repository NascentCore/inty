"""
Check if a user has privilege to access premium features.
"""

from app import models, schemas
from app.core.user_privilege.superuser_check import is_superuser


def is_eligible_for_premium(
    user: schemas.User, subscription_status: models.SubscriptionStatus
) -> bool:
    """
    Check if a user has privilege to access premium features.
    """
    return is_superuser(user) or subscription_status.is_subscribed
