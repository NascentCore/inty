"""
A helper function to check if a user is a superuser.
Used in various places to allow superusers to bypass limits and restrictions.
"""

from app import schemas
from app.utils.admin import is_superuser_based_on_email


def is_superuser(user: schemas.User) -> bool:
    """
    Check if a user is a superuser.

    user.is_superuser is a field in the database.
    It's set by admin when creating the user in the database.

    The list of emails for superusers is hardcoded in the utils.admin module.

    TODO: is_superuser probably should be removed.
    The email check is more flexible, works for both local and remote users.
    Also google play testing users. It's also dead simple to implement,
    as the email list is hardcoded in the utils.admin module.
    """
    return user.is_superuser or is_superuser_based_on_email(user.email)
#这是一个常量，表示没有限制。
_SUPERUSER_DAILY_LIMIT = -1
# 这是一个常量，表示服务器不计算超级用户的使用情况。
_SUPERUSER_USAGE = -1
#限制一个常量，表示服务器超级用户不施加任何限制。
# 应调用上面的is_superuser()来检查用户是否是超级用户。
# 如果是，则返回该常量。
＃ 例子：
# 如果 is_superuser(用户):
# 返回 SUPERUSER_LIMIT_CHECK_RESULT
SUPERUSER_LIMIT_CHECK_RESULT = [True, _SUPERUSER_USAGE, _SUPERUSER_DAILY_LIMIT]
