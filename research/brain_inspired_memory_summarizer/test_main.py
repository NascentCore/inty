from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import json

from main import LayeredMemoryAgent, NaiveWindowAgent, build_dataset, evaluate_agent, run_experiment
from extractor import (
    MemoryCategory,
    extract_candidates,
    extract_candidates_llm,
    utterance_memory_categories,
)


class MemoryExperimentTests(unittest.TestCase):
    def test_llm_extractor_parses_json_response(self) -> None:
        class _FakeLLM:
            def __call__(self, _: str) -> str:
                return (
                    '[{"key":"preferred_name","value":"阿哲","confidence":0.93,'
                    '"evidence":"请叫我阿哲","is_negative":false},'
                    '{"key":"city","value":"上海","confidence":0.89,'
                    '"evidence":"现在住在上海"}]'
                )

        candidates = extract_candidates_llm(
            "以后请叫我阿哲，我现在住在上海。",
            turn_idx=7,
            llm_call=_FakeLLM(),
        )
        kv = {(c.key, c.value) for c in candidates}
        self.assertIn(("preferred_name", "阿哲"), kv)
        self.assertIn(("city", "上海"), kv)
        self.assertTrue(all(c.turn_idx == 7 for c in candidates))

    def test_llm_extractor_fallbacks_to_rule_when_json_invalid(self) -> None:
        class _BrokenLLM:
            def __call__(self, _: str) -> str:
                return "{not-json"

        candidates = extract_candidates_llm(
            "请不要叫我宝贝。", turn_idx=3, llm_call=_BrokenLLM()
        )
        keys = {c.key for c in candidates}
        self.assertIn("boundary", keys)

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

    def test_utterance_routing_maps_dialogue_to_memory_types_without_llm(self) -> None:
        """Explicit rule-based routing: chitchat → episodic, not simulated by LLM."""
        cats_movie = utterance_memory_categories("刚刚在看电影，剧情还不错。")
        self.assertIn(MemoryCategory.EPISODIC, cats_movie)
        self.assertNotIn(MemoryCategory.SEMANTIC, cats_movie)

        cats_name = utterance_memory_categories("以后请叫我阿辰。")
        self.assertIn(MemoryCategory.SEMANTIC, cats_name)
        self.assertNotIn(MemoryCategory.EPISODIC, cats_name)

        cats_both = utterance_memory_categories("今天搬家了，我现在住在上海。")
        self.assertIn(MemoryCategory.EPISODIC, cats_both)
        self.assertIn(MemoryCategory.SEMANTIC, cats_both)

    def test_episodic_consolidation_promotes_semantic_after_repeated_traces(self) -> None:
        """
        Systems-consolidation analogue: salient episodic evidence sampled twice
        promotes regex-extractable semantic slots without direct semantic turn.
        """

        def _episodic_payload(_: str) -> str:
            return json.dumps(
                [
                    {
                        "gist": "mentioned residence",
                        "salience_hint": 0.9,
                        "evidence": "我现在住在深圳。",
                    }
                ],
                ensure_ascii=False,
            )

        agent = LayeredMemoryAgent(
            window_size=1,
            extract_mode="regex",
            episodic_llm_call=_episodic_payload,
        )
        agent.ingest_user_turn("刚刚在看电影。")
        self.assertNotIn("city", agent.semantic_memory)
        agent.ingest_user_turn("剧情还不错。")
        self.assertEqual(agent.semantic_memory.get("city"), "深圳")


if __name__ == "__main__":
    unittest.main()
