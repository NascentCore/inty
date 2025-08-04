from app.core.agent.prompts import StructuredPrompt


def test_construct_structured_prompt():
    structured_prompt = StructuredPrompt(
        main_prompt="main prompt",
        mode_prompt="mode prompt",
        output_format_prompt="output format prompt",
        sample_dialogues=["sample dialogue 1", "sample dialogue 2"],
        auxiliary_prompts=["auxiliary prompt 1", "auxiliary prompt 2"],
    )
    assert (
        structured_prompt.assemble()
        == """main prompt
mode prompt
output format prompt
sample dialogue 1
sample dialogue 2
auxiliary prompt 1
auxiliary prompt 2"""
    )
