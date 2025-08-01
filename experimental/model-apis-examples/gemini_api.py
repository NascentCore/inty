import json
from google import genai
from google.genai import types

client = genai.Client()

# response = client.models.generate_content(
#     model="gemini-2.5-flash",
#     contents="Write a plot summary of a novel on AI causing human extinction",
#     config=types.GenerateContentConfig(
#         thinking_config=types.ThinkingConfig(
#             thinking_budget=1024,
#             include_thoughts=True
#         )
#         # Turn off thinking:
#         # thinking_config=types.ThinkingConfig(thinking_budget=0)
#         # Turn on dynamic thinking:
#         # thinking_config=types.ThinkingConfig(thinking_budget=-1)
#     ),
# )

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

# The output has different parts, each part can be a thought or answer.
# The thought part is the reasoning part.
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
