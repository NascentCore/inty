from dotenv import load_dotenv
from promptlayer import PromptLayer

load_dotenv()


pl = PromptLayer()
# PromptLayer 仅支持知名的 providers，这是成为 openrouter 的一种尝试。
# 它不想公开 prompts，这使得它无法与自定义模型一起使用。
response = pl.run(
    prompt_name="Character chatting",
    input_variables={"char": "John", "user": "Jane"},
    provider="openai",
    model="google/gemini-2.5-flash",
)
print(f"Retrieved prompt: {response}")
