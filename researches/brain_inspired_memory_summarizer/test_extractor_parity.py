from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from extractor import extract_candidates, extract_candidates_llm
from main import build_dataset


def _to_slot_dict(candidates) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in candidates:
        out[c.key] = c.value
    return out


def _mock_llm_from_regex(text: str, turn_idx: int) -> str:
    """
    Simulate an LLM response payload using regex extractor output.
    This validates that the LLM extraction path can reproduce regex-equivalent slots.
    """
    candidates = extract_candidates(text, turn_idx, mode="regex")
    payload = []
    for c in candidates:
        payload.append(
            {
                "key": c.key,
                "value": c.value,
                "confidence": c.confidence,
                "evidence": c.evidence,
                "is_negative": c.is_negative,
            }
        )
    return json.dumps(payload, ensure_ascii=False)


class ExtractorParityTests(unittest.TestCase):
    def test_llm_extractor_matches_regex_on_benchmark_turns(self) -> None:
        episodes = build_dataset()
        self.assertGreater(len(episodes), 0)
        total = 0
        mismatches: list[tuple[str, int, dict[str, str], dict[str, str], str]] = []

        for ep in episodes:
            for idx, text in enumerate(ep.user_turns, start=1):
                regex_slots = _to_slot_dict(extract_candidates(text, idx, mode="regex"))
                llm_slots = _to_slot_dict(
                    extract_candidates_llm(
                        text,
                        idx,
                        llm_call=lambda t, i=idx: _mock_llm_from_regex(t, i),
                    )
                )
                total += 1
                if regex_slots != llm_slots:
                    mismatches.append((ep.episode_id, idx, regex_slots, llm_slots, text))

        if mismatches:
            msg_lines = ["Extractor parity mismatches:"]
            for ep_id, idx, reg, llm, text in mismatches:
                msg_lines.append(
                    f"- {ep_id} turn#{idx}: text={text!r} regex={reg} llm={llm}"
                )
            self.fail("\n".join(msg_lines))
        self.assertGreater(total, 0)


if __name__ == "__main__":
    unittest.main()
