from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from main import (
    LayeredMemoryAgent,
    NaiveWindowAgent,
    build_dataset,
    evaluate_agent,
    extract_candidates,
    run_experiment,
)


class MemoryExperimentTests(unittest.TestCase):
    def test_baseline_loses_early_memory_when_window_small(self) -> None:
        agent = NaiveWindowAgent(window_size=1)
        agent.ingest_user_turn("我喜欢你叫我阿哲。")
        agent.ingest_user_turn("今天天气还行。")
        ans, _, _ = agent.answer("preferred_name")
        self.assertEqual(ans, "不知道")

    def test_layered_retains_key_fact_beyond_short_window(self) -> None:
        agent = LayeredMemoryAgent(window_size=1)
        agent.ingest_user_turn("我喜欢你叫我阿哲。")
        agent.ingest_user_turn("今天天气还行。")
        ans, _, _ = agent.answer("preferred_name")
        self.assertEqual(ans, "阿哲")

    def test_boundary_negation_blocks_conflicting_name_candidate(self) -> None:
        candidates = extract_candidates("请不要叫我宝贝。", turn_idx=1)
        keys = {c.key for c in candidates}
        self.assertIn("boundary", keys)
        preferred_values = [c.value for c in candidates if c.key == "preferred_name"]
        self.assertEqual(preferred_values, [])

    def test_semantic_memory_is_stable_under_boundary_and_followup_noise(self) -> None:
        agent = LayeredMemoryAgent(window_size=2)
        agent.ingest_user_turn("以后请叫我阿辰。")
        agent.ingest_user_turn("请不要叫我宝贝。")
        agent.ingest_user_turn("我们聊点电影吧。")
        ans, _, _ = agent.answer("preferred_name")
        self.assertEqual(ans, "阿辰")
        b, _, _ = agent.answer("boundary")
        self.assertEqual(b, "不要叫我宝贝")

    def test_layered_improves_accuracy_over_small_window_baseline(self) -> None:
        episodes = build_dataset()
        baseline = evaluate_agent(NaiveWindowAgent(window_size=2), episodes)
        layered = evaluate_agent(LayeredMemoryAgent(window_size=2), episodes)
        self.assertGreater(layered.accuracy, baseline.accuracy)

    def test_experiment_meets_minimum_success_thresholds(self) -> None:
        result = run_experiment()
        self.assertGreaterEqual(result["accuracy_gain_vs_small"], 0.30)
        self.assertGreaterEqual(result["context_reduction_vs_large"], 0.40)
        self.assertGreaterEqual(result["layered_accuracy"], 0.80)


if __name__ == "__main__":
    unittest.main()
