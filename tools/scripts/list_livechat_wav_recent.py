#!/usr/bin/env python3
"""
在 GCS 桶 inty-static 的 live_chat/ 前缀下，按对象创建时间筛选最新的若干条 .wav 并打印；第三列为可公开访问时的 HTTPS 地址（storage.googleapis.com）。

使用仓库根目录的 inty-backend-key.json（可通过环境变量 GOOGLE_APPLICATION_CREDENTIALS 覆盖）。

运行（需在已安装 google-cloud-storage 的环境中，如仓库 venv）:
  python experimental/list_livechat_wav_recent.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import quote

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_KEY = _REPO_ROOT / "inty-backend-key.json"

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(_DEFAULT_KEY),
)

from google.cloud import storage  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="List the most recently created .wav under live_chat/ in GCS."
    )
    p.add_argument(
        "--bucket",
        default="inty-static",
        help="GCS bucket name (default: inty-static)",
    )
    p.add_argument(
        "--prefix",
        default="live_chat/",
        help='Object name prefix, should end with "/" (default: live_chat/)',
    )
    p.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of files to show (default: 20)",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    cred = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    if not cred.is_file():
        print(f"Credentials file not found: {cred}", file=sys.stderr)
        return 1

    client = storage.Client()
    items: list[tuple[object, str, int]] = []
    for blob in client.list_blobs(args.bucket, prefix=args.prefix):
        if not blob.name.lower().endswith(".wav"):
            continue
        t = blob.time_created
        if t is None:
            t = blob.updated
        items.append((t, blob.name, int(blob.size or 0)))

    base = f"https://storage.googleapis.com/{args.bucket}/"
    items.sort(key=lambda x: x[0], reverse=True)
    for t, name, size in items[: max(0, args.limit)]:
        ts = t.isoformat() if hasattr(t, "isoformat") else str(t)
        public_url = base + quote(name, safe="/")
        print(f"{ts}\t{size}\t{public_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
