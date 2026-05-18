# MiniMax 音频 API 最小演示

## 原始需求备忘

> 在 `experimental/` 下实现一个最小 demo，使用 https://www.minimax.io/audio 所指向生态中的 **TTS** 与 **音乐生成** HTTP API。

产品页用于能力概览；**可机器解析的契约**以开放平台文档为准（`platform.minimax.io`）。

## 结论与设计

- **鉴权**：`Authorization: Bearer <MINIMAX_API_KEY>`，与官方 OpenAPI 一致。
- **TTS**：同步 HTTP `POST https://api.minimax.io/v1/t2a_v2`，请求体字段名与 [speech-t2a-http](https://platform.minimax.io/docs/api-reference/speech-t2a-http.md) 对齐；演示使用 `output_format: hex` 与 `audio_setting.format: mp3`，在本地 `bytes.fromhex` 后落盘。
- **音乐**：`POST https://api.minimax.io/v1/music_generation`，见 [music-generation](https://platform.minimax.io/docs/api-reference/music-generation.md)。为减少演示参数面，默认 **`music-2.6-free` + `is_instrumental: true`**（仅需 `prompt`，无需歌词）。
- **CLI**：`cyclopts` 子命令 `tts` / `music`；不做错误分支与重试（与 `experimental/AGENTS.md` 一致）。

## 运行

在仓库根目录：

```bash
cd experimental/minimax_audio
cp .env.sample .env
# 编辑 .env，填入 MINIMAX_API_KEY（见 https://platform.minimax.io/user-center/basic-information/interface-key）

uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

cd /workspace   # 回到仓库根，保证 namespace import
python -m experimental.minimax_audio.main tts
python -m experimental.minimax_audio.main music
```

生成文件默认在 `experimental/minimax_audio/outputs/`；也可用 `--output /绝对或相对路径.mp3` 指定输出路径。

## 目录

- `main.py`：Pydantic 请求体 + httpx 调用 + Cyclopts CLI
- `requirements.txt`：本目录自包含依赖 pin
- `.env.sample`：环境变量模板
