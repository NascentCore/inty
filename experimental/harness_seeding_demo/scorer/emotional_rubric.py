"""Backward-compatible single-rubric module."""

from experimental.harness_seeding_demo.scorer.rubrics import (
    ScoreResult,
    score_emotional_understanding_reply,
)

__all__ = ["ScoreResult", "score_emotional_understanding_reply"]
