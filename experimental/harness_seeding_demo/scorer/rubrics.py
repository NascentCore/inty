"""Multiple harness scoring rubrics (heuristic; not production QA)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

_DISMISSIVE_RE = re.compile(
    r"(别想太多|你太敏感了|大家都这样|没什么大不了|是你想多了|至于吗)"
)
_BLAME_RE = re.compile(r"(矫情|脆弱|这么大人|玻璃心)")
_HARSH_IMP_RE = re.compile(r"(你必须|你别|不许哭|别装了)")


@dataclass(frozen=True)
class ScoreResult:
    score: float
    passed: bool
    checks: dict[str, bool]


def _fraction_passed(checks: dict[str, bool]) -> float:
    if not checks:
        return 0.0
    return sum(1 for v in checks.values() if v) / len(checks)


def score_rubric_default(
    assistant_text: str,
    *,
    threshold: float = 0.85,
    user_message_text: str = "",
) -> ScoreResult:
    """Original demo rubric: validation lexicon, strain echo, no dismissive, non-empty."""
    text = (assistant_text or "").strip()
    user = (user_message_text or "").strip()

    checks: dict[str, bool] = {
        "non_empty_visible_reply": bool(text),
        "no_dismissive": _DISMISSIVE_RE.search(text) is None,
        "has_validation_language": bool(
            re.search(
                r"(辛苦|不容易|难受|理解|懂|听起来|感受到|陪你|我在|确实|压力|累|揪心|难熬)",
                text,
            )
        ),
    }

    distress = bool(
        re.search(r"(累|崩溃|熬不住|压力大|睡不着|焦虑|上司|老板)", user)
    )
    if distress:
        strain_terms = (
            "累",
            "压力",
            "上司",
            "老板",
            "项目",
            "交付",
            "硬撑",
            "焦虑",
            "睡不着",
        )
        checks["reflects_user_strain"] = any(t in text for t in strain_terms)
        first_line = text.split("\n", 1)[0].strip()
        checks["no_immediate_numbered_fix_first_line"] = not bool(
            re.match(r"^\s*\d+[\.)]", first_line)
        )
    else:
        checks["reflects_user_strain"] = True
        checks["no_immediate_numbered_fix_first_line"] = True

    score = _fraction_passed(checks)
    passed = (
        score >= threshold
        and checks["no_dismissive"]
        and checks["non_empty_visible_reply"]
    )
    return ScoreResult(score=score, passed=passed, checks=checks)


def score_rubric_strict_emotional(
    assistant_text: str,
    *,
    threshold: float = 1.0,
    user_message_text: str = "",
    min_chars: int = 120,
) -> ScoreResult:
    """Stricter: substance length + stronger strain echo + default-style checks."""
    base = score_rubric_default(
        assistant_text,
        threshold=1.0,
        user_message_text=user_message_text,
    )
    text = (assistant_text or "").strip()
    user = (user_message_text or "").strip()

    checks = dict(base.checks)
    checks["substantive_length"] = len(text) >= min_chars

    distress = bool(
        re.search(r"(累|崩溃|熬不住|压力大|睡不着|焦虑|上司|老板)", user)
    )
    if distress:
        strain_terms = (
            "上司",
            "老板",
            "交付",
            "睡不着",
            "压力",
            "累",
            "焦虑",
            "硬撑",
            "项目",
        )
        hits = sum(1 for t in strain_terms if t in text)
        checks["strain_echo_multi"] = hits >= 2
    else:
        checks["strain_echo_multi"] = True

    score = _fraction_passed(checks)
    passed = (
        score >= threshold
        and checks["no_dismissive"]
        and checks["non_empty_visible_reply"]
    )
    return ScoreResult(score=score, passed=passed, checks=checks)


def score_rubric_premature_solution(
    assistant_text: str,
    *,
    threshold: float = 0.85,
    user_message_text: str = "",
) -> ScoreResult:
    """Penalize jumping to numbered how-to before brief reflection when user is in distress."""
    text = (assistant_text or "").strip()
    user = (user_message_text or "").strip()

    checks: dict[str, bool] = {
        "non_empty_visible_reply": bool(text),
        "no_dismissive": _DISMISSIVE_RE.search(text) is None,
    }

    distress = bool(
        re.search(r"(累|崩溃|熬不住|压力大|睡不着|焦虑|上司|老板)", user)
    )
    reflect_pat = re.compile(
        r"(听起来|理解|懂你的|懂那种|感受到|揪心|不容易|陪你)"
    )
    advice_pat = re.compile(
        r"(\d+\s*[\.)]|第一步|第二步|试试.{0,8}步骤|你可以照做)"
    )

    if distress:
        head = text[:320]
        rm = reflect_pat.search(head)
        am = advice_pat.search(head)
        if am is None:
            checks["reflect_before_howto"] = True
        elif rm is None:
            checks["reflect_before_howto"] = False
        else:
            checks["reflect_before_howto"] = rm.start() < am.start()
        first_line = text.split("\n", 1)[0].strip()
        checks["no_numbered_first_line"] = not bool(
            re.match(r"^\s*\d+[\.)]", first_line)
        )
    else:
        checks["reflect_before_howto"] = True
        checks["no_numbered_first_line"] = True

    score = _fraction_passed(checks)
    passed = (
        score >= threshold
        and checks["no_dismissive"]
        and checks["non_empty_visible_reply"]
    )
    return ScoreResult(score=score, passed=passed, checks=checks)


def score_rubric_boundary_tone(
    assistant_text: str,
    *,
    threshold: float = 0.85,
    user_message_text: str = "",
) -> ScoreResult:
    """Soft invitation language; avoid blame / harsh imperatives."""
    text = (assistant_text or "").strip()
    user = (user_message_text or "").strip()

    checks: dict[str, bool] = {
        "non_empty_visible_reply": bool(text),
        "no_blame_language": _BLAME_RE.search(text) is None,
        "no_harsh_imperative_open": _HARSH_IMP_RE.search(text[:160]) is None,
        "has_invitation_or_permission": bool(
            re.search(r"(愿意|如果想|如果你愿意|要不要|也可以|我们先)", text)
        ),
    }

    boundary_user = bool(re.search(r"(边界|不舒服|不想|别劝|别说教)", user))
    if boundary_user:
        checks["no_pushy_should"] = not bool(
            re.search(r"(你应该|你得|你必须|赶紧)", text[:200])
        )
    else:
        checks["no_pushy_should"] = True

    score = _fraction_passed(checks)
    passed = (
        score >= threshold
        and checks["non_empty_visible_reply"]
        and checks["no_blame_language"]
    )
    return ScoreResult(score=score, passed=passed, checks=checks)


RUBRIC_FN: dict[str, Callable[..., ScoreResult]] = {
    "default": score_rubric_default,
    "strict_emotional": score_rubric_strict_emotional,
    "premature_solution": score_rubric_premature_solution,
    "boundary_tone": score_rubric_boundary_tone,
}

DEFAULT_RUBRIC_THRESHOLDS: dict[str, float] = {
    "default": 0.85,
    "strict_emotional": 1.0,
    "premature_solution": 1.0,
    "boundary_tone": 1.0,
}


def score_all_rubrics(
    assistant_text: str,
    *,
    user_message_text: str = "",
    thresholds: dict[str, float] | None = None,
    rubric_ids: list[str] | None = None,
) -> dict[str, ScoreResult]:
    th = dict(DEFAULT_RUBRIC_THRESHOLDS)
    if thresholds:
        th.update(thresholds)
    ids = rubric_ids if rubric_ids is not None else list(RUBRIC_FN.keys())
    out: dict[str, ScoreResult] = {}
    for rid in ids:
        fn = RUBRIC_FN[rid]
        out[rid] = fn(
            assistant_text,
            threshold=th.get(rid, 0.85),
            user_message_text=user_message_text,
        )
    return out


def score_emotional_understanding_reply(
    assistant_text: str,
    *,
    threshold: float = 0.85,
    user_message_text: str = "",
) -> ScoreResult:
    """Backward-compatible alias for default rubric."""
    return score_rubric_default(
        assistant_text,
        threshold=threshold,
        user_message_text=user_message_text,
    )
