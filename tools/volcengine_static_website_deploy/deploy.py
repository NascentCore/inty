#!/usr/bin/env python3
"""
Upload a static site directory to Volcengine TOS and set static website default index
(PutBucketWebsite). Console equivalent:
https://www.volcengine.com/docs/6349/114714?lang=zh

Objects are uploaded with public-read ACL. Bind a custom domain in TOS if default
bucket domain forces HTML download (see same doc).
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path


def _credentials() -> tuple[str, str]:
    ak = os.environ.get("VOLC_ACCESSKEY") or os.environ.get("TOS_ACCESS_KEY")
    sk = (
        os.environ.get("VOLC_SECRET_ACCESSKEY")
        or os.environ.get("VOLC_SECRETKEY")
        or os.environ.get("TOS_SECRET_KEY")
    )
    if not ak or not sk:
        print(
            "Missing credentials. Set VOLC_ACCESSKEY and VOLC_SECRET_ACCESSKEY "
            "(or TOS_ACCESS_KEY / TOS_SECRET_KEY).",
            file=sys.stderr,
        )
        sys.exit(1)
    return ak, sk


def _content_type(path: Path) -> str:
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    ct, _enc = mimetypes.guess_type(path.name)
    if not ct:
        return "application/octet-stream"
    if ct.startswith("text/") or ct in ("application/javascript", "application/json"):
        return f"{ct}; charset=utf-8"
    return ct


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy a static directory to Volcengine TOS with optional website config."
    )
    parser.add_argument(
        "site_root",
        type=Path,
        help="Local directory containing the static site (document root).",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        metavar="REL_PATH",
        help="Files to upload, paths relative to site_root (e.g. index.html dist/app.js).",
    )
    parser.add_argument(
        "--bucket",
        default=os.environ.get("TOS_BUCKET"),
        help="TOS bucket name (or env TOS_BUCKET).",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("TOS_REGION", "cn-beijing"),
        help="Region id, e.g. cn-beijing (env TOS_REGION).",
    )
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("TOS_ENDPOINT"),
        help="TOS API endpoint URL, e.g. https://tos-cn-beijing.volces.com (env TOS_ENDPOINT). "
        "If omitted, https://tos-<region>.volces.com is used.",
    )
    parser.add_argument(
        "--create-bucket",
        action="store_true",
        help="Create the bucket if missing (public-read ACL on bucket).",
    )
    parser.add_argument(
        "--skip-website-config",
        action="store_true",
        help="Only upload objects; do not call PutBucketWebsite.",
    )
    parser.add_argument(
        "--index-suffix",
        default="index.html",
        help="Default index document suffix for PutBucketWebsite (default: index.html).",
    )
    args = parser.parse_args()

    if not args.bucket:
        print("Pass --bucket or set TOS_BUCKET.", file=sys.stderr)
        sys.exit(1)

    try:
        import tos
        from tos.enum import ACLType
        from tos.exceptions import TosServerError
        from tos.models2 import ErrorDocument, IndexDocument
    except ImportError:
        print(
            "Python package `tos` not installed. Run:\n"
            "  pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    root = args.site_root.resolve()
    if not root.is_dir():
        print(f"site_root is not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    uploads: list[tuple[str, Path]] = []
    for rel in args.paths:
        p = (root / rel).resolve()
        if not p.is_relative_to(root):
            print(f"Path escapes site_root: {rel}", file=sys.stderr)
            sys.exit(1)
        if not p.is_file():
            print(f"Missing file (relative to site root): {rel}", file=sys.stderr)
            sys.exit(1)
        uploads.append((Path(rel).as_posix(), p))

    endpoint = args.endpoint or f"https://tos-{args.region}.volces.com"
    ak, sk = _credentials()
    client = tos.TosClientV2(ak, sk, endpoint, args.region)

    if args.create_bucket:
        try:
            client.create_bucket(args.bucket, acl=ACLType.ACL_Public_Read)
            print("Created bucket:", args.bucket)
        except TosServerError as e:
            if e.status_code != 409:
                raise
            print("Bucket already exists:", args.bucket)

    for key, path in uploads:
        client.put_object_from_file(
            args.bucket,
            key,
            str(path),
            acl=ACLType.ACL_Public_Read,
            content_type=_content_type(path),
        )
        print("Uploaded", key)

    if not args.skip_website_config:
        err_key = os.environ.get("TOS_WEBSITE_ERROR_KEY")
        err_doc = ErrorDocument(key=err_key) if err_key else None
        client.put_bucket_website(
            args.bucket,
            index_document=IndexDocument(suffix=args.index_suffix),
            error_document=err_doc,
        )
        print("PutBucketWebsite: index suffix", args.index_suffix)

    print()
    print("Next (see https://www.volcengine.com/docs/6349/114714?lang=zh ):")
    print("- Ensure bucket or objects allow anonymous read for your visitors.")
    print(
        "- Bind a custom domain on the bucket if default domain downloads HTML instead of rendering."
    )


if __name__ == "__main__":
    main()
