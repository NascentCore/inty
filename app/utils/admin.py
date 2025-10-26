from loguru import logger
# 关联 Google 帐户被视为超级用户的电子邮件列表。
SUPER_USER_EMAILS = [
#“anonymoussocialforreal@gmail。com”，
#“arthurzhang0521@gmail.com”，
#“donggangcj@gmail。com”，
#“justicezyx@gmail。com”，
#“zhiwei9001@gmail.com”，
#“xheuyyuki@gmail。com”，
# 这是 pr 提供给 Google Play 审核者的。
# 他们要求不受任何限制地访问所有功能。
    "test.heartmate@gmail.com",
]

SHARED_EMAILS = [
# 公司 IT 电子邮件，拥有 Google 帐户
    "it@sxwl.ai",
# 通用测试账户
    "sxwlai001@gmail.com",
    "sxwlai002@gmail.com",
]

logger.debug(f"SUPER_USER_EMAILS: {SUPER_USER_EMAILS}")


def is_superuser_based_on_email(email: str) -> bool:
    """Read the email from the request and check if it is in the SUPER_USER_EMAILS list."""
    if email is None:
        return False
    return email.lower() in [email.lower() for email in SUPER_USER_EMAILS]
