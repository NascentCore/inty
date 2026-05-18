"""Minimal entrypoint for Cloud Run Job: print and exit. No external APIs or DB."""

# Cloud Run Job 入口：容器 CMD 执行此脚本，打印时间戳后退出
import sys
from datetime import datetime, timezone


def main() -> None:
    print(
        "gcp_scheduled_job demo run at", datetime.now(timezone.utc).isoformat()
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
