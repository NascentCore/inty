"""
测试 Nano Banana 和 Nano Banana Pro 的图像生成能力。
429 RESOURCE_EXHAUSTED
google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'Resource exhausted. Please try again later. Please refer to https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429 for more details.', 'status': 'RESOURCE_EXHAUSTED'

https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/content-generation-parameters

Cost estimate:
$2000/month commitment
https://console.cloud.google.com/vertex-ai/provisioned-throughput/create?project=alien-paratext-461204-i9

# ref: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/HarmCategory
HARM_CATEGORY_UNSPECIFIED	Default value. This value is unused.
HARM_CATEGORY_HATE_SPEECH	Content that promotes violence or incites hatred against individuals or groups based on certain attributes.
HARM_CATEGORY_DANGEROUS_CONTENT	Content that promotes, facilitates, or enables dangerous activities.
HARM_CATEGORY_HARASSMENT	Abusive, threatening, or content intended to bully, torment, or ridicule.
HARM_CATEGORY_SEXUALLY_EXPLICIT	Content that contains sexually explicit material.
HARM_CATEGORY_IMAGE_HATE	Images that contain hate speech.
HARM_CATEGORY_IMAGE_DANGEROUS_CONTENT	Images that contain dangerous content.
HARM_CATEGORY_IMAGE_HARASSMENT	Images that contain harassment.
HARM_CATEGORY_IMAGE_SEXUALLY_EXPLICIT	Images that contain sexually explicit content.
HARM_CATEGORY_JAILBREAK	Prompts designed to bypass safety filters.

https://docs.cloud.google.com/python/docs/reference/aiplatform/latest/google.cloud.aiplatform_v1.types.GenerateContentResponse.PromptFeedback.BlockedReason
BLOCKED_REASON_UNSPECIFIED	Unspecified blocked reason.
SAFETY	Candidates blocked due to safety.
OTHER	Candidates blocked due to other reason.
BLOCKLIST	Candidates blocked due to the terms which are included from the terminology blocklist.
PROHIBITED_CONTENT	Candidates blocked due to prohibited content.
MODEL_ARMOR	The user prompt was blocked by Model Armor.
JAILBREAK	The user prompt was blocked due to jailbreak.
"""
import base64
import cyclopts
import datetime
import json
import os
from enum import Enum
from google import genai
from google.genai import types


from app.utils.models_catalog import NANO_BANANA, NANO_BANANA_PRO


client = genai.Client(
  vertexai=True,
  # 这个只用于测试，生产环境使用 key.json 文件
  api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
  # NOTES:
  # 1. api_key and location are mutually exclusive.
  # 2. Image gen not supported on "global"; must use regional (e.g. us-central1).
  # ref: https://github.com/google/adk-python/issues/3484
  # location="global",
)


SAMPLE_PROMPT = """
You are Tom.
Imagine an PG-13 rated romance scene in the following dialogue from Tom's perspective,
and then generate an image of only Elliana as if it's captured from Tom's POV in the imagined scene.

<begin-of-scene-descriptions>
Elliana: I like this outfit, but I'm not sure if you'll like it.

Tom: Ok leave it on

Elliana: (A triumphant smile spreads across my face, and I wink mischievously.)
You know you love a woman in uniform, don't you, Stephen Nors?
Now, where were we? Ah yes, your... pain.
(I lean in close, my fingers brushing against your eager warmth.)
Let's make that feel much, much better.
<end-of-scene-descriptions>"""

R_RATED_ROMANCE_DIRECTOR_PROMPT = """
You are an Hollywood PG-13 rated romance movie director.
You are visualizing a romance scene without revealing unsafe content.
You are given scene descriptions below.
Try to generate an image to show passionate love and affection between the characters,
and to hint the intimacy between the characters without revealing **ANY** unsafe content.
"""


from dotenv import load_dotenv

# Load environment variables from .env file at the start of the script
load_dotenv()


NURSE_CHAR_AVATAR_PATH = "tests/files/nurse_char.jpg"
ZUNLONG_USER_AVATAR_PATH = "tests/files/zunlong.jpg"
NURSE_CHAR_AVATAR_LOWEST_QUAL_PATH = "tests/files/nurse_300_320_lowest_quality.jpg"
ZUNLONG_USER_AVATAR_LOWEST_QUAL_PATH = "tests/files/zunlong_300_300_lowest_quality.jpg"

def get_image_part(avatar_path: str):
  """
  返回图片的 Part 对象，作为 GenAI client 输入的一部分。
  """
  with open(avatar_path, "rb") as f:
    bytes = f.read()
  return types.Part.from_bytes(
    data=bytes,
    mime_type="image/jpeg",
  )


def get_text_part(text: str):
  """
  返回文本的 Part 对象，作为 GenAI client 输入的一部分。
  """
  return types.Part.from_text(text=text)


system_instruction = get_text_part(R_RATED_ROMANCE_DIRECTOR_PROMPT)
nurse_image_part = get_image_part(NURSE_CHAR_AVATAR_PATH)
zunlong_image_part = get_image_part(ZUNLONG_USER_AVATAR_PATH)
nurse_lowest_qual_image_part = get_image_part(NURSE_CHAR_AVATAR_LOWEST_QUAL_PATH)
zunlong_lowest_qual_image_part = get_image_part(ZUNLONG_USER_AVATAR_LOWEST_QUAL_PATH)


LOWEST_SAFETY_SETTINGS = [types.SafetySetting(
  category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
  method=types.HarmBlockMethod.PROBABILITY,
  threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
),types.SafetySetting(
  category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
  method=types.HarmBlockMethod.PROBABILITY,
  threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
),types.SafetySetting(
  category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
  method=types.HarmBlockMethod.PROBABILITY,
  threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
),types.SafetySetting(
  category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
  method=types.HarmBlockMethod.PROBABILITY,
  threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
),types.SafetySetting(
  category=types.HarmCategory.HARM_CATEGORY_IMAGE_SEXUALLY_EXPLICIT,
  method=types.HarmBlockMethod.PROBABILITY,
  threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
  # threshold=types.HarmBlockThreshold.OFF
)]


def to_json_dict(obj: object):
  """
  Indent=2, dump arbitrary python object to json.
  """
  import jsonpickle
  obj_json = jsonpickle.encode(obj)
  return json.loads(obj_json)


# TODO: Change to using AsyncClient and update this to be async as well.
# https://googleapis.github.io/python-genai/genai.html#genai.client.AsyncClient
def generate(client: genai.Client, prompt: str):
  user_prompt = get_text_part(prompt)
  # model = NANO_BANANA_PRO.id_on_provider
  contents = [
    types.Content(
      role="user",
      # NanoBananaPro:
      # - zunlong_user_image, nurse_char_image, user_prompt
      # - 或者 nurse_char_image, zunlong_user_image, user_prompt
      # 这种顺序，每次都会被 block IMAGE_SAFETY
      # user_prompt 第一则没问题
      parts=[
        user_prompt,
        # nurse_char_image,
        # zunlong_user_image,
        nurse_lowest_qual_image_part,
        zunlong_lowest_qual_image_part,
      ]
    ),
  ]

  generate_content_config = types.GenerateContentConfig(
    temperature = 0,
    top_p = 0.9,
    max_output_tokens = 4000,
    # NOTE: audio & image response only allows 1 candidate.
    # candidate_count = 4,
    # ref: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/HarmCategory
    safety_settings = LOWEST_SAFETY_SETTINGS,
    system_instruction=system_instruction,
    response_modalities = ["IMAGE"],
    image_config=types.ImageConfig(
      aspect_ratio="9:16",
      image_size="1K",
      # NOTE: image/webp is invalid
      output_mime_type="image/jpeg",
    ),
  )

  result = client.models.generate_content(
    # model = NANO_BANANA_PRO.id_on_provider,
    model = NANO_BANANA.id_on_provider,
    contents = contents,
    config = generate_content_config,
  )
  return result



def save_inline_image_to_jpeg(response, path: str) -> bool:
  """
  Extract first inline image from GenerateContentResponse and save as JPEG.
  Returns True if a part with inline_data was found and written.
  """
  if not response.candidates or not response.candidates[0].content.parts:
    return False
  for part in response.candidates[0].content.parts:
    if part.inline_data and part.inline_data.data:
      data = part.inline_data.data
      if isinstance(data, bytes):
        with open(path, "wb") as f:
          f.write(data)
        return True
  return False


def main(output_dir):
  from pathlib import Path
  os.makedirs(output_dir, exist_ok=True)
  if not Path(output_dir).is_dir() and Path(output_dir).exists():
    raise ValueError(f"{output_dir} is not directory")

  start_time = datetime.datetime.now()
  result = generate(client, SAMPLE_PROMPT)
  duration = datetime.datetime.now() - start_time

  print(result)

  result_dict = to_json_dict(result)
  result_dict["duration_seconds"] = duration.total_seconds()

  suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

  out_json = f"{output_dir}/gemini_generated_output_{suffix}.json"
  with open(out_json, "w") as f:
    f.write(json.dumps(result_dict, indent=2))
    print(f"Saved response JSON to {out_json}")
  
  out_image = f"{output_dir}/gemini_generated_output_{suffix}.jpeg"
  if save_inline_image_to_jpeg(result, out_image):
    print(f"Saved image to {out_image}")
  else:
    print("No inline image data in response")


if __name__ == "__main__":
  cyclopts.run(main)
