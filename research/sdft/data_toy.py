"""Minimal toy dataset for smoke runs (matches upstream teacher_prompt shape)."""

from __future__ import annotations

from string import Template

from datasets import Dataset

_UPSTREAM_TEACHER_TEMPLATE = Template(
    """
$orig_content

This is an example for a response to the question:
$output_text

Now answer with a response of your own, including the thinking process.
"""
)


def build_toy_dataset(seed: int) -> Dataset:
    assert seed >= 0
    question = "What is 2+2?"
    golden = "4"
    teacher_body = _UPSTREAM_TEACHER_TEMPLATE.substitute(
        orig_content=question,
        output_text=golden,
    )
    row = {
        "prompt": [{"role": "user", "content": question}],
        "teacher_prompt": [{"role": "user", "content": teacher_body}],
    }
    return Dataset.from_list([row])
