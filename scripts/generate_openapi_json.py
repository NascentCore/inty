import json
import os
import subprocess

import cyclopts

from app.main import app


def main(output: str = "app/openapi.json", no_commit: bool = False) -> None:
    json_str = json.dumps(app.openapi(), indent=4)

    with open(output, "w", encoding="utf-8") as f:
        f.write(json_str)

    print(f"OpenAPI JSON saved to {output}")

    if no_commit:
        return

    subprocess.run(["git", "add", output], check=True)
    this_filename = os.path.basename(__file__)
    subprocess.run(
        ["git", "commit", "-m", f"使用 {this_filename} 更新 openapi.json"],
        check=True,
    )

    print("OpenAPI JSON 更新并提交 git commit 到本地仓库")
    print(
        "你还需要更新 app/stainless.yml 中的 openapi_spec 字段来触发新的 api endpoint 构建"
    )


if __name__ == "__main__":
    cyclopts.run(main)
