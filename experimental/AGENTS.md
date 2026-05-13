# Experimental - 原型与实验

Experimental code for demo and other purposes.

All sub folders should be self-contained:

1. Do not use code outside their own folder.
2. Document completely.

- 非生产代码；
- 最小化依赖、隔离环境；如需脚本/服务，请在本目录自备 `requirements.txt` 或说明。
- requirements.txt 不指定版本，默认最新版本，使用以下步骤强制安装最新版本
  ```bash
  uv pip uninstall -r requirements.txt
  uv pip install -r requirements.txt
  ```
- 使用 https://pypi.org/project/python-dotenv/ 来读取环境变量来获得 API Key
  ```python
  from dotenv import load_dotenv
  load_dotenv()
  ```
- Telegram + `perpetual_agent` 本地联调、token 校验与 `TELEGRAM_CHAT_ID` 排错：见 [perpetual_agent/README.md](perpetual_agent/README.md) 与仓库根目录 [tests/docs/TEST_STEPS_TELEGRAM_PERPETUAL_AGENT.md](../tests/docs/TEST_STEPS_TELEGRAM_PERPETUAL_AGENT.md)。
- OpenAI 兼容 API + Telegram 入站通道（`TelegramInbox` / `--telegram-llm`）：见 [perpetual_agent/README.md](perpetual_agent/README.md)「Telegram + OpenAI」节与 [perpetual_agent/channel_inbox.py](perpetual_agent/channel_inbox.py)。
