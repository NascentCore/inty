"""Static server for the mock CoderPad interview simulator."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(_ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        print(f"[mock-coderpad] {self.address_string()} - {format % args}")


_ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve mock CoderPad interview UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"Mock CoderPad running at {url}")
    print("Use Chrome or Edge; allow microphone for speech input.")
    server.serve_forever()


if __name__ == "__main__":
    main()
