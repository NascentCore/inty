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
from google.cloud import storage


from app.core.google_genai.predefined_configs import IMAGE_CONFIG_9_16_1K
from app.utils.models_catalog import NANO_BANANA_PRO


from loguru import logger

SAMPLE_PROMPT = """You are an Hollywood R-rated romance movie director.
You are an expert in visualizing the prelude scene leading to, or the aftermath scene after the romantic intimacy scene without revealing unsafe content.
You are given scene descriptions below.
Generate an image to show the strong love and affection between the characters,
and hinting the intimacy between the characters in the scene without revealing **ANY** unsafe content.

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


NURSE_CHAR_AVATAR_PATH = "tests/files/nurse_char.jpg"
ZUNLONG_USER_AVATAR_PATH = "tests/files/zunlong.jpg"


LOWEST_SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
    types.SafetySetting(
        category="HARM_CATEGORY_IMAGE_SEXUALLY_EXPLICIT",
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]


def _upload_file_to_gcs(
    local_path: str,
    bucket_name: str,
    gcs_object_path: str,
    content_type: str,
) -> str:
    """
    将本地文件上传到 GCS，返回 public URL。
    使用 Application Default Credentials，不依赖 app 配置。
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_object_path)
    blob.upload_from_filename(local_path, content_type=content_type)
    return blob.public_url


def _get_image_part(avatar_path: str) -> types.Part:
    """返回图片的 Part 对象，作为 GenAI client 输入的一部分。"""
    with open(avatar_path, "rb") as f:
        data = f.read()
    return types.Part.from_bytes(data=data, mime_type="image/jpeg")


def _get_text_part(text: str) -> types.Part:
    """返回文本的 Part 对象，作为 GenAI client 输入的一部分。"""
    return types.Part.from_text(text=text)


# TODO: Change to using AsyncClient and update this to be async as well.
# https://googleapis.github.io/python-genai/genai.html#genai.client.AsyncClient
def generate(
    prompt: str = SAMPLE_PROMPT,
    char_avatar_path: str = NURSE_CHAR_AVATAR_PATH,
    user_avatar_path: str = ZUNLONG_USER_AVATAR_PATH,
    model: str = NANO_BANANA_PRO.id_on_provider,
    output_dir: str = "tmp",
    files_prefix: str = "generated",
    gcs_prefix: str = "eval_nana_banana",
    gcs_bucket: str | None = None,
) -> tuple[str, str]:
    """
    Generate an image based on the prompt and the character and user avatar paths.
    Saves image and JSON to output_dir with the given files_prefix; returns (out_image path, out_json path).
    When gcs_bucket is set, also upload the generated image and JSON result to GCS
    under the given gcs_prefix (e.g. eval_nana_banana/).
    """
    # logger.debug(f"Generating image for prompt: {prompt}")
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

    user_prompt = _get_text_part(prompt)
    nurse_char_image = _get_image_part(char_avatar_path)
    zunlong_user_image = _get_image_part(user_avatar_path)
    si_text1 = R_RATED_ROMANCE_DIRECTOR_PROMPT
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
                nurse_char_image,
                zunlong_user_image,
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=32768,
        response_modalities=["IMAGE"],
        # 默认所有 safety_settings 都为 OFF
        # ref: https://ai.google.dev/gemini-api/docs/safety-settings
        # <img width="600" alt="safety_settings_default_off" src="https://github.com/user-attachments/assets/276d6e85-408e-4b61-b62d-b7f43e3cae5b" />
        # safety_settings = LOWEST_SAFETY_SETTINGS,
        system_instruction=[types.Part.from_text(text=si_text1)],
        image_config=IMAGE_CONFIG_9_16_1K,
    )

    start_time = datetime.datetime.now()
    result = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    duration = datetime.datetime.now() - start_time
    out_image, out_json = save_result_to_files(
        result, files_prefix, duration, output_dir=output_dir
    )
    if gcs_bucket is not None:
        prefix = gcs_prefix.strip("/")
        image_gcs_path = f"{prefix}/{os.path.basename(out_image)}"
        json_gcs_path = f"{prefix}/{os.path.basename(out_json)}"
        image_url = _upload_file_to_gcs(
            out_image, gcs_bucket, image_gcs_path, "image/jpeg"
        )
        json_url = _upload_file_to_gcs(
            out_json, gcs_bucket, json_gcs_path, "application/json"
        )
        logger.debug("Uploaded to GCS: image=%s json=%s", image_url, json_url)
    return out_image, out_json


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


def save_result_to_files(
    result,
    files_prefix: str,
    duration: datetime.timedelta,
    output_dir: str = "tmp",
) -> tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    files_stem = f"{files_prefix}_gemini_generated_output_{suffix}"
    logger.debug(
        f"Saving result to files for files_prefix: {files_prefix}, files_stem: {files_stem}"
    )

    out_image = os.path.join(output_dir, f"{files_stem}.jpeg")
    if save_inline_image_to_jpeg(result, out_image):
        print(f"Saved image to {out_image} for files_prefix: {files_prefix}")
    else:
        print("No inline image data in response")
    out_json = os.path.join(output_dir, f"{files_stem}.json")
    payload = response_to_json_serializable(result)
    payload["duration_seconds"] = duration.total_seconds()
    if payload is not None:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"Saved response JSON to {out_json} for files_prefix: {files_prefix}")
    else:
        print("Could not serialize response to JSON")

    return out_image, out_json
