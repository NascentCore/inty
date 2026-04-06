# INTY v2 本地文本聊天原型

## 架构

本 prototype 是 `app/core/agentic_kernel/companion/` (companion kernel) 的 **REPL 外壳**,
用于产品经理持续迭代核心智能体陪伴体验.

- **核心组件** (models / prompts / workspace / file_store / utc / memory_store) 来自 companion kernel
- **本目录保留** REPL 壳 (main.py)、LLM 客户端 (client.py)、双路编排 (orchestrator.py)、
  异步工具后台 (tool_background.py)、生图/改图 (fal_z_image_tool.py)、联网检索 (google_web_search.py)、
  LLM trace (llm_trace.py) 等实验/REPL 特有模块
- 已有 `_ws/` workspace 目录完全兼容

详见 [companion kernel](/app/core/agentic_kernel/companion/) 和本目录 AGENTS.md.

## 安装

首先，在命令行安装 `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

拷贝默认配置文件到代码仓库的顶层目录（在代码库顶层目录运行）：

```bash
cp devops/config.yaml.dev config.yaml
```

依赖与 `.env`（在原型目录执行一次即可）：

```bash
cd experimental/inty_v2_text_chat_prototype
cp .env.example .env

# 编辑 .env 中这一行：LANGSMITH_PROJECT=inty-v2-text-chat-prototype-<USER>
# 将 <USER> 替换为你自己的名字

uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

**必须从仓库根目录启动 REPL**：`app.core.config` 在导入时要求**当前工作目录**下存在 `config.yaml`（上文 `cp devops/config.yaml.dev config.yaml` 已在根目录提供该文件）。若在 `experimental/inty_v2_text_chat_prototype` 里直接 `python main.py`，会因找不到 `config.yaml` 而失败。

```bash
# 回到代码库的根目录
cd ../../
python experimental/inty_v2_text_chat_prototype/main.py repl \
  --workspace experimental/inty_v2_text_chat_prototype/_ws
```

bootstrap 阶段会由 AI 自然询问并确认用户期望的 companionship 类型（如朋友/爱人/亲人/自定义），无需命令行强制指定。

`--workspace` 使用相对**仓库根**的路径。`load_prototype_dotenv()` 会读取 cwd 的 `.env` 以及包目录下的 `.env`，因此在根目录启动时仍能加载 `experimental/inty_v2_text_chat_prototype/.env` 里的 API Key。
