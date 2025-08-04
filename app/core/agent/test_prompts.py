import os
from app.core.agent.prompts import StructuredPrompt

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

print(os.getenv("OPENAI_API_KEY"))
client = OpenAI()


structured_prompt = StructuredPrompt(
    main_prompt="main prompt",
    mode_prompt="mode prompt",
    output_format_prompt="output format prompt",
    sample_dialogues=["sample dialogue 1", "sample dialogue 2"],
    auxiliary_prompts=["auxiliary prompt 1", "auxiliary prompt 2"],
)
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=structured_prompt.assemble(),
)

print(response)
