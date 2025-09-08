"""
Check if a user has privilege to access premium features.
"""

from app import models, schemas


def is_eligible_for_premium(
    user: schemas.User, subscription_status: models.SubscriptionStatus
) -> bool:
    """
    Check if a user has privilege to access premium features.
    """
    return user.is_superuser or subscription_status.is_subscribed
