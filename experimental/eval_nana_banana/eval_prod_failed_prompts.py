"""
For each prompt files under @tmp/scene_prompt_*.txt,
Read its content and set it as the prompt for generating images.
"""

import datetime
import cyclopts
import glob

from app.utils.models_catalog import NANO_BANANA
from experimental.eval_nana_banana.lib import generate, save_result_to_files


def main():
  prompt_files = glob.glob("tmp/scene_prompt_*.txt")
  
  for prompt_file in prompt_files:
    files_prefix = prompt_file.split("/")[-1].split(".")[0]
    with open(prompt_file, "r") as f:
      prompt = f.read()
    start_time = datetime.datetime.now()
    result = generate(prompt, model=NANO_BANANA.id_on_provider)
    duration = datetime.datetime.now() - start_time
    save_result_to_files(result, files_prefix, duration)


if __name__ == "__main__":
  cyclopts.run(main)
