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
