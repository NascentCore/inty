from loguru import logger

# A list of emails whose associated Google account treated as super users.
SUPER_USER_EMAILS = [
    # "anonymoussocialforreal@gmail.com",
    # "arthurzhang0521@gmail.com",
    # "donggangcj@gmail.com",
    # "justicezyx@gmail.com",
    # "zhiwei9001@gmail.com",
    # "xheuyyuki@gmail.com",
    # This is provided to Google Play reviewers.
    # They require to access all features without any restrictions.
    "test.heartmate@gmail.com",
]

SHARED_EMAILS = [
    # Company IT email, has Google Account
    "it@sxwl.ai",
    # Generic testing accounts
    "sxwlai001@gmail.com",
    "sxwlai002@gmail.com",
]

logger.debug(f"SUPER_USER_EMAILS: {SUPER_USER_EMAILS}")


def is_superuser_based_on_email(email: str) -> bool:
    """Read the email from the request and check if it is in the SUPER_USER_EMAILS list."""
    if email is None:
        return False
    return email.lower() in [email.lower() for email in SUPER_USER_EMAILS]
