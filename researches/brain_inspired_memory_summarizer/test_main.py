from __future__ import annotations

import unittest

from main import (
    LayeredMemoryAgent,
    NaiveWindowAgent,
    build_dataset,
    evaluate_agent,
)


class MemoryExperimentTests(unittest.TestCase):
    def test_naive_window_agent_has_low_recall_when_window_is_small(self) -> None:
        episodes = build_dataset()
        metrics = evaluate_agent(NaiveWindowAgent(window_size=2), episodes)
        self.assertLess(metrics.accuracy, 0.5)
        self.assertEqual(metrics.avg_context_lines, 2.0)

    def test_layered_agent_improves_accuracy_with_small_context(self) -> None:
        episodes = build_dataset()
        layered = evaluate_agent(LayeredMemoryAgent(window_size=2), episodes)
        baseline = evaluate_agent(NaiveWindowAgent(window_size=2), episodes)
        self.assertGreater(layered.accuracy, baseline.accuracy)
        self.assertEqual(layered.avg_context_lines, baseline.avg_context_lines)
        self.assertGreater(layered.accuracy, 0.95)
        self.assertEqual(layered.memory_item_count, 4)


if __name__ == "__main__":
    unittest.main()
