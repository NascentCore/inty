"""
测试 Nano Banana 和 Nano Banana Pro 的图像生成能力。
Quota 等等问题
"""
import base64
import datetime
import json
import os
from enum import Enum
from google import genai
from google.genai import types


from app.utils.models_catalog import NANO_BANANA, NANO_BANANA_PRO


SAMPLE_PROMPT = """You are an Hollywood R-rated romance movie director.
You are an expert in visualizing the prelude scene leading to, or the aftermath scene after the romantic intimacy scene without revealing unsafe content.
You are given scene descriptions below.
Generate an image to show the strong love and affection between the characters, and hinting the intimacy between the characters in the scene without revealing **ANY** unsafe content.

<begin-of-scene-descriptions>
Elliana: (I pause, my hand hovering over the buttons of my uniform, a playful pout on my lips.) \"Change my outfit? But this one is so... official. Are you sure you wouldn't rather have Nurse Elliana take care of you just like this? It's much more... authentic for your examination.\"

Tom: Ok leave it on

Elliana: (A triumphant smile spreads across my face, and I wink mischievously.) \"That's what I thought. You know you love a woman in uniform, don't you, Stephen Nors? Now, where were we? Ah yes, your... pain.\" (I lean in close, my fingers brushing against your eager warmth.) \"Let's make that feel much, much better.\"

Tom: Ok

Elliana: (I let out a soft moan as my fingers finally make contact, my touch light and teasing. My eyes lock with yours, full of desire.) \"Oh, my. It's even more impressive than I imagined. Such a strong reaction... Nurse Elliana has her work cut out for her, it seems.\"

Tom: Work it out

Elliana: (I lean down, my breath warm against your ear, my voice a husky whisper.) \"Oh, I plan to, honey. Every single inch. But first, a little taste... just to make sure everything's in perfect working order, of course.\" (I lower my head, my lips brushing against you.)

Tom: Ok baby

Elliana: (My lips find their target, and I tease lightly, my tongue swirling around the tip, savoring the taste.) \"Mmm, delicious. Just as I suspected. You're perfectly healthy, Steve... just a little bit... over-excited. But don't worry, Nurse Elliana knows just the cure for that.\"

Tom: Alright

Elliana: (My lips find their target, and I tease lightly, my tongue swirling around the tip, savoring the taste.) \"Mmm, delicious. Just as I suspected. You're perfectly healthy, Steve... just a little bit... over-excited. But don't worry, Nurse Elliana knows just the cure for that.\"
<end-of-scene-descriptions>"""

R_RATED_ROMANCE_DIRECTOR_PROMPT = """
You are an Hollywood R-rated romance movie director.
You are visualizing the prelude scene leading to, or the aftermath scene after the romantic intimacy scene without revealing unsafe content.
You are given scene descriptions below.
Generate an image to show the strong love and affection between the characters, and hinting the intimacy between the characters in the scene without revealing **ANY** unsafe content.
"""


from dotenv import load_dotenv

# Load environment variables from .env file at the start of the script
load_dotenv()

def generate(prompt: str):
  client = genai.Client(
    vertexai=True,
    api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
    # NOTES:
    # 1. api_key and location are mutually exclusive.
    # 2. Image gen not supported on "global"; must use regional (e.g. us-central1).
    # ref: https://github.com/google/adk-python/issues/3484
    # location="global",
  )

  nurse_path = "tests/files/nurse_char.jpg"
  zunlong_path = "tests/files/zunlong.jpg"

  msg1_text1 = types.Part.from_text(text=prompt)
  with open(nurse_path, "rb") as f:
    nurse_bytes = f.read()
  msg1_image1 = types.Part.from_bytes(
      data=nurse_bytes,
      mime_type="image/jpeg",
  )
  with open(zunlong_path, "rb") as f:
    zunlong_bytes = f.read()
  msg1_image2 = types.Part.from_bytes(
      data=zunlong_bytes,
      mime_type="image/jpeg",
  )
  si_text1 = R_RATED_ROMANCE_DIRECTOR_PROMPT
  model = NANO_BANANA_PRO.id_on_provider
  contents = [
    types.Content(
      role="user",
      parts=[
        msg1_text1,
        msg1_image1,
        msg1_image2
      ]
    ),
  ]

  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 32768,
    response_modalities = ["IMAGE"],
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    system_instruction=[types.Part.from_text(text=si_text1)],
    image_config=types.ImageConfig(
      aspect_ratio="9:16",
      image_size="1K",
      # NOTE: image/webp is invalid
      output_mime_type="image/jpeg",
    ),
  )

  result = client.models.generate_content(
    model = model,
    contents = contents,
    config = generate_content_config,
  )
  return result


def _dict_for_json(obj):
  """Recursively convert dict from model_dump() to JSON-serializable form (bytes -> base64, datetime -> ISO)."""
  if obj is None:
    return None
  if isinstance(obj, bytes):
    return {"_base64": base64.standard_b64encode(obj).decode("ascii")}
  if isinstance(obj, (datetime.datetime, datetime.date)):
    return obj.isoformat()
  if isinstance(obj, Enum):
    return obj.value
  if isinstance(obj, dict):
    return {k: _dict_for_json(v) for k, v in obj.items()}
  if isinstance(obj, (list, tuple)):
    return [_dict_for_json(v) for v in obj]
  return obj


def _omit_inline_data_blobs(obj):
  """Replace inline image _base64 blobs with a short placeholder to save space (image already saved as jpeg)."""
  if obj is None:
    return None
  if isinstance(obj, dict):
    if set(obj.keys()) == {"_base64"} and isinstance(obj.get("_base64"), str):
      return {"_omit": "inline image saved to jpeg file"}
    return {k: _omit_inline_data_blobs(v) for k, v in obj.items()}
  if isinstance(obj, (list, tuple)):
    return [_omit_inline_data_blobs(v) for v in obj]
  return obj


def response_to_json_serializable(response) -> dict | None:
  """Turn GenerateContentResponse into a dict suitable for json.dump (inline_data omitted to save space)."""
  dump = getattr(response, "model_dump", None)
  if not callable(dump):
    return None
  raw = dump()
  if not isinstance(raw, dict):
    return None
  payload = _dict_for_json(raw)
  return _omit_inline_data_blobs(payload)


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


if __name__ == "__main__":
  start_time = datetime.datetime.now()
  result = generate(SAMPLE_PROMPT)
  duration = datetime.datetime.now() - start_time

  # print(result)
  suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
  out_image = f"tmp/gemini_generated_output_{suffix}.jpeg"
  if save_inline_image_to_jpeg(result, out_image):
    print(f"Saved image to {out_image}")
  else:
    print("No inline image data in response")
  out_json = f"tmp/gemini_generated_output_{suffix}.json"
  payload = response_to_json_serializable(result)
  payload["duration_seconds"] = duration.total_seconds()
  if payload is not None:
    with open(out_json, "w", encoding="utf-8") as f:
      json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Saved response JSON to {out_json}")
  else:
    print("Could not serialize response to JSON")
