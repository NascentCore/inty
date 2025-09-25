import argparse
import json
import os

from app.main import app

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=str, default="app/openapi.json")
args = parser.parse_args()

json_str = json.dumps(app.openapi(), indent=4)

with open(args.output, "w") as f:
    f.write(json_str)

print(f"OpenAPI JSON saved to {args.output}")

# 调用 git 来提交本地改动
import subprocess

subprocess.run(["git", "add", args.output])
this_filename = os.path.basename(__file__)
subprocess.run(["git", "commit", "-m", f"使用 {this_filename} 更新 openapi.json"])
subprocess.run(["git", "push"])
