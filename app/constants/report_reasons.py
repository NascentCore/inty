# CREATED_BY_AGENT
"""
静态举报/反馈原因配置，替代已废弃的 report_reason 数据表。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set, Tuple


@dataclass(frozen=True)
class ReasonOption:
    """举报/反馈原因的静态配置项。"""

    id: int
    code: str
    description: str


REPORT_REASONS: Tuple[ReasonOption, ...] = (
    ReasonOption(1, "SENSITIVE_CONTENT", "Sensitive or sexual content"),
    ReasonOption(2, "MISINFORMATION", "Misinformation"),
    ReasonOption(3, "FRAUD_SCAMS", "Fraud or scams"),
    ReasonOption(4, "PRIVACY_VIOLATION", "Violation of privacy"),
    ReasonOption(5, "HARMFUL_MINORS", "Harmful to minors"),
    ReasonOption(6, "IP_VIOLATION", "Violations of my intellectual property"),
    ReasonOption(0, "OTHER", "Other, details in report description"),
)

FEEDBACK_REASONS: Tuple[ReasonOption, ...] = (
    ReasonOption(1, "CHAT_NOT_NATURAL", "Chat replies don't feel natural / off-topic"),
    ReasonOption(2, "CHARACTER_MISMATCH", "The character doesn't match its persona"),
    ReasonOption(3, "APP_SLOW", "The app is slow or gets stuck"),
    ReasonOption(4, "FEATURE_HARD_TO_FIND", "Feature is difficult to find or use"),
    ReasonOption(5, "UI_INCONVENIENT", "UI or interaction feels inconvenient"),
    ReasonOption(6, "NEW_FEATURE", "Request for a new feature or improvement"),
    ReasonOption(0, "OTHER", "Other, please describe below"),
)

REPORT_REASON_ID_TO_CODE: Dict[int, str] = {
    option.id: option.code for option in REPORT_REASONS
}
REPORT_REASON_CODE_TO_ID: Dict[str, int] = {
    option.code: option.id for option in REPORT_REASONS
}

FEEDBACK_REASON_ID_TO_CODE: Dict[int, str] = {
    option.id: option.code for option in FEEDBACK_REASONS
}
FEEDBACK_REASON_CODE_TO_ID: Dict[str, int] = {
    option.code: option.id for option in FEEDBACK_REASONS
}

ALL_REASON_OPTIONS: Tuple[ReasonOption, ...] = REPORT_REASONS + FEEDBACK_REASONS
REASON_CODE_TO_DESCRIPTION: Dict[str, str] = {
    option.code: option.description for option in ALL_REASON_OPTIONS
}
SUPPORTED_REASON_CODES: Set[str] = set(REASON_CODE_TO_DESCRIPTION.keys())
DEFAULT_REASON_CODE = "OTHER"
