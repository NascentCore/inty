from loguru import logger

# 因为正常通过 Google 认证方式登录的用户无法获得超级用户权限，因此需要根据其 Email 额外判断。
# 被作为超级用处理的 Google Account，通过其 Email 判断
SUPER_USER_EMAILS = [
    # "anonymoussocialforreal@gmail.com",
    # "arthurzhang0521@gmail.com",
    # "donggangcj@gmail.com",
    # "justicezyx@gmail.com",
    # "zhiwei9001@gmail.com",
    # "xheuyyuki@gmail.com",
    # 曾被用于 Google Play 审查员登录账户，已被用户名密码取代 test.intellimate@gmail.com
    # 用户名密码登录信息是后台直接创建，有超级用户字段为真标记，因此不需要在此处标记。
    # 保留以被不时之需。
    # TODO：2026 年 1 月删除。
    "test.heartmate@gmail.com",
    # 公司公共 IT Google Account；亚雄使用这个账户进行测试。
    "it@sxwl.ai",
    # Charles 个人 Google 账户，因测试导致被 Google 封禁，加入列表方便测试
    "charlesfengyu@gmail.com",
    # 与上面原因类似，学宝的 Google 账户 email
    "1032505449sl@gmail.com",
    # 陈平个人 Google 账户，因测试live chat，加入列表方便测试
    "kotlinaai@gmail.com",
]

# 公共的 Google Email 用于测试，目前只是记录该信息，没有在后端做特别处理。
SHARED_EMAILS = [
    "sxwlai001@gmail.com",
    "sxwlai002@gmail.com",
]

logger.debug(f"SUPER_USER_EMAILS: {SUPER_USER_EMAILS}")


def is_superuser_based_on_email(email: str | None) -> bool:
    """Check if an email is in the SUPER_USER_EMAILS allowlist."""
    if not email:
        return False
    return email.lower() in [email.lower() for email in SUPER_USER_EMAILS]
