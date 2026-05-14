from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from extractor import (
    MemoryCategory,
    extract_candidates_llm,
    llm_extract_memory_slots,
    parse_route_memory_json,
    route_memory_categories_llm,
)
from main import (
    LayeredMemoryAgent,
    NaiveWindowAgent,
    build_benchmark_episodic_llm_call,
    build_benchmark_route_llm_call,
    build_benchmark_slot_llm_extract_fn,
    build_dataset,
    evaluate_agent,
    run_experiment,
)


def _fake_slot_llm_preferred_阿哲(_: str) -> str:
    return json.dumps(
        [
            {
                "key": "preferred_name",
                "value": "阿哲",
                "confidence": 0.93,
                "evidence": "请叫我阿哲",
                "is_negative": False,
            }
        ],
        ensure_ascii=False,
    )


class MemoryExperimentTests(unittest.TestCase):
    def test_llm_extractor_parses_json_response(self) -> None:
        candidates = extract_candidates_llm(
            "以后请叫我阿哲，我现在住在上海。",
            turn_idx=7,
            llm_call=_fake_slot_llm_preferred_阿哲,
        )
        kv = {(c.key, c.value) for c in candidates}
        self.assertIn(("preferred_name", "阿哲"), kv)
        self.assertTrue(all(c.turn_idx == 7 for c in candidates))

    def test_llm_extractor_invalid_json_raises(self) -> None:
        class _BrokenLLM:
            def __call__(self, _: str) -> str:
                return "{not-json"

        with self.assertRaises(json.JSONDecodeError):
            extract_candidates_llm(
                "请不要叫我宝贝。", turn_idx=3, llm_call=_BrokenLLM()
            )

    def test_baseline_loses_early_memory_when_window_small(self) -> None:
        slot_fn = build_benchmark_slot_llm_extract_fn(
            {
                "我喜欢你叫我阿哲。": json.dumps(
                    [
                        {
                            "key": "preferred_name",
                            "value": "阿哲",
                            "confidence": 0.9,
                            "evidence": "喜欢我叫我阿哲",
                            "is_negative": False,
                        }
                    ],
                    ensure_ascii=False,
                ),
                "今天天气还行。": "[]",
            }
        )
        agent = NaiveWindowAgent(window_size=1, llm_extract_fn=slot_fn)
        agent.ingest_user_turn("我喜欢你叫我阿哲。")
        agent.ingest_user_turn("今天天气还行。")
        ans, _, _ = agent.answer("preferred_name")
        self.assertEqual(ans, "不知道")

    def test_layered_retains_key_fact_beyond_short_window(self) -> None:
        slot_fn = build_benchmark_slot_llm_extract_fn(
            {
                "我喜欢你叫我阿哲。": json.dumps(
                    [
                        {
                            "key": "preferred_name",
                            "value": "阿哲",
                            "confidence": 0.9,
                            "evidence": "喜欢我叫我阿哲",
                            "is_negative": False,
                        }
                    ],
                    ensure_ascii=False,
                ),
                "今天天气还行。": "[]",
            }
        )
        route = build_benchmark_route_llm_call(
            {
                "我喜欢你叫我阿哲。": json.dumps(
                    {"active_subsystems": ["semantic"]}, ensure_ascii=False
                ),
                "今天天气还行。": json.dumps(
                    {"active_subsystems": ["episodic"]}, ensure_ascii=False
                ),
            }
        )
        episodic = build_benchmark_episodic_llm_call(
            {"今天天气还行。": json.dumps({"events": []}, ensure_ascii=False)}
        )
        agent = LayeredMemoryAgent(
            window_size=1,
            slot_llm_extract_fn=slot_fn,
            route_llm_call=route,
            episodic_llm_call=episodic,
        )
        agent.ingest_user_turn("我喜欢你叫我阿哲。")
        agent.ingest_user_turn("今天天气还行。")
        ans, _, _ = agent.answer("preferred_name")
        self.assertEqual(ans, "阿哲")

    def test_boundary_negation_blocks_conflicting_name_candidate(self) -> None:
        payload = json.dumps(
            [
                {
                    "key": "boundary",
                    "value": "不要叫我宝贝",
                    "confidence": 0.97,
                    "evidence": "不要叫我宝贝",
                    "is_negative": False,
                },
                {
                    "key": "preferred_name",
                    "value": "宝贝",
                    "confidence": 0.5,
                    "evidence": "叫我宝贝",
                    "is_negative": False,
                },
            ],
            ensure_ascii=False,
        )
        candidates = llm_extract_memory_slots("请不要叫我宝贝。", 1, lambda _: payload)
        keys = {c.key for c in candidates}
        self.assertIn("boundary", keys)
        preferred_values = [c.value for c in candidates if c.key == "preferred_name"]
        self.assertEqual(preferred_values, [])

    def test_semantic_memory_is_stable_under_boundary_and_followup_noise(self) -> None:
        slot_map = {
            "以后请叫我阿辰。": json.dumps(
                [
                    {
                        "key": "preferred_name",
                        "value": "阿辰",
                        "confidence": 0.93,
                        "evidence": "叫我阿辰",
                        "is_negative": False,
                    }
                ],
                ensure_ascii=False,
            ),
            "请不要叫我宝贝。": json.dumps(
                [
                    {
                        "key": "boundary",
                        "value": "不要叫我宝贝",
                        "confidence": 0.97,
                        "evidence": "不要叫我宝贝",
                        "is_negative": False,
                    }
                ],
                ensure_ascii=False,
            ),
            "我们聊点电影吧。": "[]",
        }
        route_map = {
            "以后请叫我阿辰。": json.dumps(
                {"active_subsystems": ["semantic"]}, ensure_ascii=False
            ),
            "请不要叫我宝贝。": json.dumps(
                {"active_subsystems": ["self_schema"]}, ensure_ascii=False
            ),
            "我们聊点电影吧。": json.dumps(
                {"active_subsystems": ["episodic"]}, ensure_ascii=False
            ),
        }
        slot_fn = build_benchmark_slot_llm_extract_fn(slot_map)
        agent = LayeredMemoryAgent(
            window_size=2,
            slot_llm_extract_fn=slot_fn,
            route_llm_call=build_benchmark_route_llm_call(route_map),
            episodic_llm_call=build_benchmark_episodic_llm_call(
                {
                    "我们聊点电影吧。": json.dumps(
                        {
                            "events": [
                                {
                                    "gist": "movies",
                                    "salience_hint": 0.5,
                                    "evidence": "聊电影",
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                }
            ),
        )
        agent.ingest_user_turn("以后请叫我阿辰。")
        agent.ingest_user_turn("请不要叫我宝贝。")
        agent.ingest_user_turn("我们聊点电影吧。")
        ans, _, _ = agent.answer("preferred_name")
        self.assertEqual(ans, "阿辰")
        b, _, _ = agent.answer("boundary")
        self.assertEqual(b, "不要叫我宝贝")

    def test_layered_improves_accuracy_over_small_window_baseline(self) -> None:
        episodes = build_dataset()
        slot_fn = build_benchmark_slot_llm_extract_fn()
        route_call = build_benchmark_route_llm_call()
        episodic_call = build_benchmark_episodic_llm_call()
        baseline = evaluate_agent(
            NaiveWindowAgent(window_size=2, llm_extract_fn=slot_fn), episodes
        )
        layered = evaluate_agent(
            LayeredMemoryAgent(
                window_size=2,
                slot_llm_extract_fn=slot_fn,
                route_llm_call=route_call,
                episodic_llm_call=episodic_call,
            ),
            episodes,
        )
        self.assertGreater(layered.accuracy, baseline.accuracy)

    def test_experiment_meets_minimum_success_thresholds(self) -> None:
        result = run_experiment()
        self.assertGreaterEqual(result["accuracy_gain_vs_small"], 0.30)
        self.assertGreaterEqual(result["context_reduction_vs_large"], 0.40)
        self.assertGreaterEqual(result["layered_accuracy"], 0.80)

    def test_route_llm_json_parsing(self) -> None:
        cats = route_memory_categories_llm(
            "x",
            route_llm_call=lambda _: json.dumps(
                {"active_subsystems": ["semantic", "episodic"]}, ensure_ascii=False
            ),
        )
        self.assertIn(MemoryCategory.SEMANTIC, cats)
        self.assertIn(MemoryCategory.EPISODIC, cats)
        self.assertNotIn(MemoryCategory.SELF_SCHEMA, cats)

    def test_parse_route_memory_json(self) -> None:
        cats = parse_route_memory_json(
            json.dumps({"active_subsystems": ["self_schema"]}, ensure_ascii=False)
        )
        self.assertIn(MemoryCategory.SELF_SCHEMA, cats)

    def test_benchmark_slot_stub_covers_dataset_lines(self) -> None:
        from main import benchmark_slot_json_by_line, build_dataset

        table = benchmark_slot_json_by_line()
        for ep in build_dataset():
            for line in ep.user_turns:
                self.assertIn(line, table, f"missing stub for dataset line: {line!r}")

    def test_episodic_consolidation_promotes_semantic_after_repeated_traces(
        self,
    ) -> None:
        from main import benchmark_route_json_by_line, benchmark_slot_json_by_line

        slot_map = dict(benchmark_slot_json_by_line())
        slot_map["我现在住在深圳。"] = json.dumps(
            [
                {
                    "key": "city",
                    "value": "深圳",
                    "confidence": 0.9,
                    "evidence": "住在深圳",
                    "is_negative": False,
                }
            ],
            ensure_ascii=False,
        )
        route_map = dict(benchmark_route_json_by_line())
        route_map["刚刚在看电影。"] = json.dumps(
            {"active_subsystems": ["episodic"]}, ensure_ascii=False
        )
        route_map["剧情还不错。"] = json.dumps(
            {"active_subsystems": ["episodic"]}, ensure_ascii=False
        )

        def _episodic(text: str) -> str:
            if text == "刚刚在看电影。":
                return json.dumps(
                    {
                        "events": [
                            {
                                "gist": "movie",
                                "salience_hint": 0.9,
                                "evidence": "我现在住在深圳。",
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
            if text == "剧情还不错。":
                return json.dumps(
                    {
                        "events": [
                            {
                                "gist": "plot",
                                "salience_hint": 0.9,
                                "evidence": "我现在住在深圳。",
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
            return json.dumps({"events": []}, ensure_ascii=False)

        agent = LayeredMemoryAgent(
            window_size=1,
            slot_llm_extract_fn=build_benchmark_slot_llm_extract_fn(slot_map),
            route_llm_call=build_benchmark_route_llm_call(route_map),
            episodic_llm_call=_episodic,
        )
        agent.ingest_user_turn("刚刚在看电影。")
        self.assertNotIn("city", agent.semantic_memory)
        agent.ingest_user_turn("剧情还不错。")
        self.assertEqual(agent.semantic_memory.get("city"), "深圳")


if __name__ == "__main__":
    unittest.main()
