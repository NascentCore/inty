from experimental.agent_multi_tool_loop_demo.main import run_demo


def test_single_loop_multiple_tool_calls_for_profile_image_update() -> None:
    result = run_demo(user_request="I want to update my profile image", max_steps=4)

    assert result.loop_steps == 2
    assert len(result.executed_tools) == 2

    first_call = result.executed_tools[0]
    second_call = result.executed_tools[1]

    assert first_call.step == 1
    assert first_call.name == "z_image_generate"
    assert first_call.output["provider"] == "z-image"

    assert second_call.step == 1
    assert second_call.name == "update_profile_picture"
    assert second_call.input_arguments["image_url"] == "$tool:z_image_generate.image_url"
    assert (
        second_call.resolved_arguments["image_url"] == first_call.output["image_url"]
    )
    assert result.final_profile_image_url == first_call.output["image_url"]
