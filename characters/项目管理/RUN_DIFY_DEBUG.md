# Dify / run_dify_chat 调试备忘

- **run_dify_chat.py** 只调 OpenRouter（生成角色）和 Dify `POST /v1/chat-messages`，不调 Inty 后端、不调 fal。
- **fal / text-to-image 调用** 来自 Dify 工作流内部（与 `DIFY_API_KEY` 绑定的那个应用）。在 Dify Studio 里找到该应用 → 看工作流里的 HTTP 节点（是否请求 Inty）和生图/fal 节点。
- **Inty** `POST /api/v1/ai/agents/text-to-image`：prod 配置 `fal.enabled: false` 时默认走 Vertex，不走 fal。
- **定位调用源**：GitHub Actions 用的 `DIFY_API_KEY` 对应一个 Dify 应用；该应用每次跑的工作流里若有请求 Inty 或 fal，即来源。
