import json
import os
import re
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional

try:
    import google.genai as genai
    from google.genai import types
except Exception as e:
    print("[ERROR] google-genai 未安装或导入失败，请先在虚拟环境中安装 requirements.txt", file=sys.stderr)
    raise

# 固定情绪列表（20项）
EMOTIONS = [
    "Neutral", "Happy", "Surprise", "Angry", "Sad",
    "Confused", "Shy", "Excited", "Pleased", "Bored",
    "Disgust", "Fear", "Embarrassed", "Tired", "Sleepy",
    "Thinking", "Curious", "Skeptical", "Flirt", "Determined",
]

RE_EMO_BASENAME = re.compile(r"^(?P<name>[A-Za-z]+)(?P<ext>\.[A-Za-z0-9]+)$")

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
INDEX_FILE = ROOT / "index.html"

# 配置：图片目录与 Gemini API Key
EMOTION_IMAGES_DIR = Path(os.getenv("EMOTION_IMAGES_DIR", ROOT / "emotions")).resolve()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8080"))

if not GOOGLE_API_KEY:
    print("[WARN] 未设置 GOOGLE_API_KEY（或 GEMINI_API_KEY）。如需真实调用，请导出环境变量。将以无 Key 运行并返回占位响应。")

# 预扫描图片目录，构建情绪->文件名映射
# 命名规范：文件名以情绪名开头（大小写不敏感），如 Happy.png、angry.jpg

def build_emotion_file_map(images_dir: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not images_dir.exists():
        return mapping
    for entry in images_dir.iterdir():
        if not entry.is_file():
            continue
        m = RE_EMO_BASENAME.match(entry.name)
        if not m:
            continue
        base = m.group("name").strip()
        # 与标准情绪名大小写无关匹配
        for emo in EMOTIONS:
            if emo.lower() == base.lower():
                mapping[emo] = entry.name  # 仅保存文件名，实际通过 /emotions/ 路由访问
                break
    return mapping

EMOTION_FILES = build_emotion_file_map(EMOTION_IMAGES_DIR)


def get_image_url_for_emotion(emotion: str) -> Optional[str]:
    canonical = next((e for e in EMOTIONS if e.lower() == (emotion or "").lower()), None)
    if not canonical:
        return None
    filename = EMOTION_FILES.get(canonical)
    if not filename:
        return None
    return f"/emotions/{filename}"


def make_gemini_client() -> Optional[genai.Client]:
    if not GOOGLE_API_KEY:
        return None
    return genai.Client(api_key=GOOGLE_API_KEY)


SYSTEM_PROMPT = (
    "你是一个 Live2D 角色情绪控制器兼聊天助手。\n"
    "请先给出对用户输入的自然回复，然后从指定情绪列表中选择一个最合适的情绪。\n"
    "只能输出 JSON，包含两个键：assistant（文本回复），emotion（严格为下列之一，大小写一致）。\n"
    "无法判断时 emotion 选 Neutral。\n\n"
    "可用情绪列表（20）：\n"
    + "\n".join(f"- {e}" for e in EMOTIONS)
)

# 结构化输出 Schema
RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "assistant": types.Schema(type=types.Type.STRING),
        "emotion": types.Schema(type=types.Type.STRING),
    },
    required=["assistant", "emotion"],
)


def call_gemini_chat(user_text: str, context: Optional[str], character_state: Optional[str]) -> Dict[str, str]:
    # 允许在无 API Key 情况下跑通 UI 流程（返回占位回复与 Neutral）
    if not GOOGLE_API_KEY:
        return {"assistant": f"[本地占位回复] {user_text}", "emotion": "Neutral"}

    client = make_gemini_client()
    contents = [SYSTEM_PROMPT, "\n当前情境：", context or "(无)", "\n角色状态：", character_state or "(无)", "\n用户：", user_text]

    resp = client.models.generate_content(
        model=MODEL,
        contents="".join(contents),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        ),
    )

    raw = getattr(resp, "text", None)
    if not raw and getattr(resp, "candidates", None):
        parts = getattr(resp.candidates[0].content, "parts", [])
        texts = [p.text for p in parts if getattr(p, "text", None)]
        raw = "\n".join(texts).strip() if texts else None

    if not raw:
        return {"assistant": "抱歉，我没有听清楚。", "emotion": "Neutral"}

    try:
        data = json.loads(raw)
        assistant = str(data.get("assistant", "")).strip() or "好的。"
        emotion = str(data.get("emotion", "")).strip() or "Neutral"
        # 规范化情绪名
        canonical = next((e for e in EMOTIONS if e.lower() == emotion.lower()), "Neutral")
        return {"assistant": assistant, "emotion": canonical}
    except Exception:
        return {"assistant": "好的。", "emotion": "Neutral"}


class DemoHandler(SimpleHTTPRequestHandler):
    def _set_json(self, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

    def _serve_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        ctype = "text/plain"
        if path.suffix in {".html"}:
            ctype = "text/html; charset=utf-8"
        elif path.suffix in {".js"}:
            ctype = "application/javascript; charset=utf-8"
        elif path.suffix in {".css"}:
            ctype = "text/css; charset=utf-8"
        elif path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            ctype = f"image/{path.suffix.lower().lstrip('.')}"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        with open(path, "rb") as f:
            self.wfile.write(f.read())

    def do_GET(self):  # noqa: N802
        if self.path == "/" or self.path == "/index.html":
            return self._serve_file(INDEX_FILE)
        if self.path.startswith("/static/"):
            return self._serve_file((STATIC_DIR / self.path[len("/static/"):]).resolve())
        if self.path.startswith("/emotions/"):
            rel = self.path[len("/emotions/"):]
            return self._serve_file((EMOTION_IMAGES_DIR / rel).resolve())
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        if self.path != "/chat":
            return self.send_error(HTTPStatus.NOT_FOUND)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(body.decode("utf-8"))
            user_text = str(data.get("utterance", "")).strip()
            context = data.get("context")
            character_state = data.get("character_state")
            if not user_text:
                return self._respond_error("utterance 不能为空")

            result = call_gemini_chat(user_text, context, character_state)
            image_url = get_image_url_for_emotion(result["emotion"]) or get_image_url_for_emotion("Neutral")
            resp = {
                "assistant": result["assistant"],
                "emotion": result["emotion"],
                "image_url": image_url,
            }
            self._set_json(200)
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self._respond_error(f"服务器错误: {e}")

    def _respond_error(self, message: str, code: int = 400):
        self._set_json(code)
        self.wfile.write(json.dumps({"error": message}).encode("utf-8"))


def main():
    print("=== Live2D Emotion Demo (Gemini) ===")
    print(f"Serving on http://{HOST}:{PORT}")
    print(f"Model: {MODEL}")
    print(f"Images dir: {EMOTION_IMAGES_DIR}")
    if not EMOTION_FILES:
        print("[WARN] 图片目录未找到匹配文件。请放置以情绪名命名的图片，如 Happy.png、Angry.jpg。")
    httpd = ThreadingHTTPServer((HOST, PORT), DemoHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
