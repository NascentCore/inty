import os

from dotenv import load_dotenv
from openai import OpenAI

from app.core.agent.prompts import StructuredPrompt, enhance_prompt

load_dotenv()


structured_prompt = StructuredPrompt(
    main_prompt="main prompt",
    mode_prompt="mode prompt",
    output_format_prompt="output format prompt",
    sample_dialogues=["sample dialogue 1", "sample dialogue 2"],
    auxiliary_prompts=["auxiliary prompt 1", "auxiliary prompt 2"],
)

print(structured_prompt.assemble())


def test_enhance_prompt():
    prompt = "A beautiful mountain landscape with sunset"
    gender = "male"
    enhanced_prompt = enhance_prompt(prompt, gender)
    assert "gender: male" in enhanced_prompt
    assert "age: 22 - 35" in enhanced_prompt
    assert "The image must be of a person." in enhanced_prompt
    assert (
        "It cannot be a landscape, object, or any other non-human content."
        in enhanced_prompt
    )
    assert (
        "Avoid generating images of people appearing less than 18 years old."
        in enhanced_prompt
    )
    assert "All content must be appropriate for a general audience." in enhanced_prompt
    print(enhanced_prompt)
