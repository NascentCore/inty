"""
测试 Nano Banana 和 Nano Banana Pro 的图像生成能力。
Quota 等等问题
"""

import base64
import cyclopts
import datetime
import cyclopts
from app.utils.models_catalog import NANO_BANANA_PRO
from experimental.eval_nana_banana.lib import NURSE_CHAR_AVATAR_PATH, SAMPLE_PROMPT, generate, save_result_to_files


def main(char_avatar_path: str = NURSE_CHAR_AVATAR_PATH):
  start_time = datetime.datetime.now()
  result = generate(SAMPLE_PROMPT, char_avatar_path=char_avatar_path, model=NANO_BANANA_PRO.id_on_provider)
  duration = datetime.datetime.now() - start_time

  save_result_to_files(result, "sample", duration)


if __name__ == "__main__":
    cyclopts.run(main)
