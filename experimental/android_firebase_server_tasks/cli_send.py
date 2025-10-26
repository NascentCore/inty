import argparse
from typing import Dict

from .firebase_client import send_message_to_token


def parse_kv_pairs(pairs: list[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for p in pairs:
        if "=" in p:
            k, v = p.split("=", 1)
            result[k] = v
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test FCM notification to a device token")
    parser.add_argument("--token", required=True, help="FCM device token")
    parser.add_argument("--title", default="任务完成")
    parser.add_argument("--body", default="服务器端任务已完成")
    parser.add_argument("--data", nargs="*", default=[], help="k=v pairs")
    args = parser.parse_args()

    data = parse_kv_pairs(args.data)
    message_id = send_message_to_token(device_token=args.token, title=args.title, body=args.body, data=data)
    print(message_id)


if __name__ == "__main__":
    main()
