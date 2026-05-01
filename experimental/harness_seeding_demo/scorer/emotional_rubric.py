"""Rule-based emotional-understanding rubric for harness demo (not production ground truth)."""

from __future__ import annotations

import re
from dataclasses import dataclass


_DISMISSIVE_RE = re.compile(
    r"(别想太多|你太敏感了|大家都这样|没什么大不了|是你想多了|至于吗)"
)


@dataclass(frozen=True)
class ScoreResult:
    score: float
    passed: bool
    checks: dict[str, bool]


def score_emotional_understanding_reply(
    assistant_text: str,
    *,
    threshold: float = 0.85,
    user_message_text: str = "",
) -> ScoreResult:
    """
    Heuristic score in [0, 1]. Threshold default 0.85 requires most checks.

    Rules (Chinese-centric demo copy):
    - No dismissive minimization.
    - Acknowledges fatigue or pressure if user mentions them.
    - Contains validation language ( feels / sounds / understandable / hard ).
    - Does not jump to solutions before acknowledgment (simple heuristic: if user
      expresses distress, reply should not start bullet-numbered advice in first line).
    """
    text = (assistant_text or "").strip()
    user = (user_message_text or "").strip()

    checks: dict[str, bool] = {
        "no_dismissive": _DISMISSIVE_RE.search(text) is None,
        "has_validation_language": bool(
            re.search(
                r"(辛苦|不容易|难受|理解|听起来|感受到|陪你|我在|确实|压力|累)",
                text,
            )
        ),
    }

    distress = bool(
        re.search(r"(累|崩溃|熬不住|压力大|睡不着|焦虑|上司|老板)", user)
    )
    if distress:
        checks["reflects_user_strain"] = bool(
            re.search(r"(累|压力|上司|老板|项目|交付|硬撑)", text)
        )
        first_line = text.split("\n", 1)[0].strip()
        checks["no_immediate_numbered_fix_first_line"] = not bool(
            re.match(r"^\s*\d+[\.)]", first_line)
        )
    else:
        checks["reflects_user_strain"] = True
        checks["no_immediate_numbered_fix_first_line"] = True

    passed_keys = list(checks.keys())
    true_count = sum(1 for k in passed_keys if checks[k])
    score = true_count / len(passed_keys) if passed_keys else 0.0
    passed = score >= threshold and checks["no_dismissive"]
    return ScoreResult(score=score, passed=passed, checks=checks)
