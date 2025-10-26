import json
from google import genai
from google.genai import types

client = genai.Client()
# 响应 = client.models.生成内容（
# 模型=“gemini-2.5-闪光”，
# content="写一篇关于人工智能导致人类灭绝的小说的情节摘要",
#配置=类型。生成内容配置(
#thinking_config=类型。思维配置(
#thinking_budget=1024，
# include_thoughts=True
＃）
# # 关闭思考：
# # Thinking_config=类型。ThinkingConfig(thinking_budget=0)
# #开启动态思维：
# # Thinking_config=类型。ThinkingConfig(thinking_budget=-1)
＃），
＃）

prompt = "What is the sum of the first 50 prime numbers?"
response = client.models.generate_content(
  model="gemini-2.5-flash",
  contents=prompt,
  config=types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
      include_thoughts=True
    )
  )
)

response_dict = response.model_dump()
print(json.dumps(response_dict, indent=4))
# 输出有不同的部分，每个部分都可以是一个想法或答案。
# 思考部分是推理部分。
for part in response.candidates[0].content.parts:
  if not part.text:
    continue
  if part.thought:
    print("Thought summary:")
    print(part.text)
    print()
  else:
    print("Answer:")
    print(part.text)
    print()
