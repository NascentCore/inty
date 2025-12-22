"""
A helper function to check if a user is a superuser.
Used in various places to allow superusers to bypass limits and restrictions.
"""

from app.utils.admin import is_superuser_based_on_email


def is_superuser(user: object) -> bool:
    """
    Check if a user is a superuser.

    Best-effort superuser detection that is safe for partially-populated user objects.

    user.is_superuser is a field in the database.
    It's set by admin when creating the user in the database.

    The list of emails for superusers is hardcoded in the utils.admin module.

    TODO: is_superuser probably should be removed.
    The email check is more flexible, works for both local and remote users.
    Also google play testing users. It's also dead simple to implement,
    as the email list is hardcoded in the utils.admin module.
    """
    if bool(getattr(user, "is_superuser", False)):
        return True
    email = getattr(user, "email", None)
    return is_superuser_based_on_email(email)


# This is a constant to mean there is no limit.
_SUPERUSER_DAILY_LIMIT = -1

# This is a constant to mean the server does not count usage for superusers.
_SUPERUSER_USAGE = -1

# This is a constant to mean the server does not apply any limit for superusers.
# One should call the above is_superuser() to check if a user is a superuser.
# If so, return this constant.
# Example:
# if is_superuser(user):
#     return SUPERUSER_LIMIT_CHECK_RESULT
SUPERUSER_LIMIT_CHECK_RESULT = [True, _SUPERUSER_USAGE, _SUPERUSER_DAILY_LIMIT]
