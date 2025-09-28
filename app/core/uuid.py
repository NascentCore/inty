from typing import Optional

from ulid import ULID


def get_new_user_id() -> str:
    """
    生成一个新的用户 ID。
    """
    return uid(prefix="user")


def get_new_report_id() -> str:
    """
    生成一个新的报告 ID。
    """
    return uid(prefix="report")


def uid(prefix: Optional[str] = None) -> str:
    """
    生成一个带可选前缀的 ULID。

    Args:
        prefix: 可选的前缀字符串。如果提供，生成的 ID 将形如 "prefix-{ulid}"

    Returns:
        str: 生成的 ID 字符串
    """
    ulid_str = str(ULID())
    if prefix:
        return f"{prefix}-{ulid_str}"
    return ulid_str
