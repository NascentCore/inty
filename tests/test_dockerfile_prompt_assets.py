# CREATED_BY_AGENT
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE_PATH = REPO_ROOT / "devops" / "docker" / "Dockerfile"

USER_MANUAL_COPY_LINE = "COPY docs/INTELLIMATE.md docs/INTELLIMATE.md"
CHANGE_LOGS_COPY_LINE = (
    "COPY android_app/docs/CHANGE_LOGS.md android_app/docs/CHANGE_LOGS.md"
)
LEGACY_CHANGE_LOGS_COPY_LINE = "COPY docs/CHANGE_LOGS.md docs/CHANGE_LOGS.md"


def test_dockerfile_copies_intellimate_prompt_assets() -> None:
    dockerfile_text = DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert USER_MANUAL_COPY_LINE in dockerfile_text
    assert CHANGE_LOGS_COPY_LINE in dockerfile_text
    assert LEGACY_CHANGE_LOGS_COPY_LINE not in dockerfile_text
