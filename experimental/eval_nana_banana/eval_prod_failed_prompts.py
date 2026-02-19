"""
For each prompt files under @tmp/scene_prompt_*.txt,
Read its content and set it as the prompt for generating images.
"""

import cyclopts
import glob

from app.utils.models_catalog import NANO_BANANA
from experimental.eval_nana_banana.lib import generate


def main() -> None:
    prompt_files = sorted(glob.glob("tmp/scene_prompt_*.txt"))
    for prompt_file in prompt_files:
        files_prefix = prompt_file.split("/")[-1].split(".")[0]
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read()
        out_image, out_json = generate(
            prompt,
            model=NANO_BANANA.id_on_provider,
            files_prefix=files_prefix,
        )
        print(f"Saved: {out_image}, {out_json}")


if __name__ == "__main__":
  cyclopts.run(main)
