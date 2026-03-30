# INTY v2 本地文本聊天原型

首先，在命令行安装 `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
cd experimental/inty_v2_text_chat_prototype
cp .env.example .env

# 编辑 .env 将自己的名字替补掉 LANGSMITH_PROJECT=inty-v2-text-chat-prototype-<USER>
# 如：LANGSMITH_PROJECT=inty-v2-text-chat-prototype-yaxiongzhao
# 这样方便区分 langsmith 内容

uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python main.py repl --workspace _ws
```
