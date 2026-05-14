"""
测试 Nano Banana 和 Nano Banana Pro 的图像生成能力。
Quota 等等问题
"""

import cyclopts
from app.utils.models_catalog import NANO_BANANA_PRO
from experimental.eval_nana_banana.lib import (
    NURSE_CHAR_AVATAR_PATH,
    SAMPLE_PROMPT,
    generate,
)


def main(char_avatar_path: str = NURSE_CHAR_AVATAR_PATH):
    out_image, out_json = generate(
        SAMPLE_PROMPT,
        char_avatar_path=char_avatar_path,
        model=NANO_BANANA_PRO.id_on_provider,
        files_prefix="sample",
    )
    print(f"Saved: {out_image}, {out_json}")


if __name__ == "__main__":
    cyclopts.run(main)
