from dotenv import load_dotenv
from promptlayer import PromptLayer

load_dotenv()


pl = PromptLayer()

# PromptLayer only support well-known providers, it's kind of try to be openrouter.
# It does not want to expose prompts, which makes it impossible to use it with custom models.
response = pl.run(
    prompt_name="Character chatting",
    input_variables={"char": "John", "user": "Jane"},
    provider="openai",
    model="google/gemini-2.5-flash",
)
print(f"Retrieved prompt: {response}")
