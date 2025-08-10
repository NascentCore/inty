import logging

logger = logging.getLogger(__name__)

# A list of emails whose associated Google account treated as super users.
SUPER_USER_EMAILS = [
    "anonymoussocialforreal@gmail.com",
    "arthurzhang0521@gmail.com",
    "donggangcj@gmail.com",
    "it@sxwl.ai",
    "justicezyx@gmail.com",
    "zhiwei9001@gmail.com",
    # Generic testing accounts
    "sxwlai001@gmail.com",
    "sxwlai002@gmail.com",
]

logger.info(f"SUPER_USER_EMAILS: {SUPER_USER_EMAILS}")


def is_superuser_based_on_email(email: str) -> bool:
    """Read the email from the request and check if it is in the SUPER_USER_EMAILS list."""
    return email.lower() in [email.lower() for email in SUPER_USER_EMAILS]
