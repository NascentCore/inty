import json
from types import SimpleNamespace

from experimental.agent_multi_tool_loop_demo.main import run_demo


class _FakeCompletions:
    def __init__(self) -> None:
        self._calls = 0
        self._generated_image_url = (
            "https://z-image.local/generated/professional-male-portra.png"
        )

    def create(self, **kwargs):
        self._calls += 1
        if self._calls == 1:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="先生成头像。",
                            tool_calls=[
                                SimpleNamespace(
                                    id="call_1",
                                    type="function",
                                    function=SimpleNamespace(
                                        name="z_image_generate",
                                        arguments=json.dumps(
                                            {
                                                "prompt": "professional male portrait",
                                                "style": "photorealistic",
                                            }
                                        ),
                                    ),
                                )
                            ],
                        )
                    )
                ]
            )
        if self._calls == 2:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="再更新头像。",
                            tool_calls=[
                                SimpleNamespace(
                                    id="call_2",
                                    type="function",
                                    function=SimpleNamespace(
                                        name="update_profile_picture",
                                        arguments=json.dumps(
                                            {
                                                "image_url": self._generated_image_url
                                            }
                                        ),
                                    ),
                                )
                            ],
                        )
                    )
                ]
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="头像已更新完成。",
                        tool_calls=[],
                    )
                )
            ]
        )


class _FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())


def test_llm_driven_tool_calls_update_profile_image_sequentially() -> None:
    result = run_demo(
        user_request="I want to update my profile image",
        max_steps=6,
        client=_FakeClient(),
    )

    assert result.loop_steps == 3
    assert len(result.executed_tools) == 2
    assert result.executed_tools[0].step == 1
    assert result.executed_tools[0].name == "z_image_generate"
    assert result.executed_tools[1].step == 2
    assert result.executed_tools[1].name == "update_profile_picture"
    assert (
        result.executed_tools[1].input_arguments["image_url"]
        == result.executed_tools[0].output["image_url"]
    )
    assert (
        result.final_profile_image_url
        == result.executed_tools[0].output["image_url"]
    )
