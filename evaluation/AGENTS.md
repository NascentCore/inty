# AGENTS.md · evaluation/（Web 前端评测工具）

本文件覆盖并补充根 `backend/AGENTS.md`，仅适用于 `evaluation/`。

## 技术栈

- Vite + React + TypeScript；接口封装在 `services/`，组件放 `components/`，页面在 `pages/`。

## 约定

- 只经由统一 API 层访问后端；避免在组件内直接拼接请求。
- 变更需更新对应测试（vitest），并保持类型无误与构建通过。

## Claude 模型支持

- 默认评分模型清单分别维护在前端 `services/api.ts`（请求失败时的兜底列表）、`services/modelCache.ts`（本地缓存缺失时的兜底列表）以及后端 `app/services/scoring_service.py` 和 `app/api/v1/endpoints/agents.py`；列表中已经包含 `Claude 3.5 Sonnet`（context length 200k）与 `Claude 3.5 Haiku`（context length 200k），用于评测和 OpenRouter 模型浏览。
- 评测界面的模型下拉依赖 `modelCacheService.getScoringModels()`，命中本地缓存时不会重新请求；调试或更新默认列表后，请调用 `modelCacheService.clearScoringCache()` 或清空浏览器 `localStorage` 中 `inty_scoring_models_*` 相关键值，确保看到最新 Claude 列表。

### 更新触点

1. 后端：`ScoringService.get_available_models()`、`ScoringService._get_default_openrouter_models()` 与 `GET /api/v1/ai/agents/models/openrouter` 的兜底数据必须同步，字段包括 `id`、`name`、`description`、`context_length`、`provider`。
2. 前端：`evaluation/services/api.ts` 的 5 秒超时 fallback 以及 `evaluation/services/modelCache.ts` 的 `getDefaultScoringModels()` 需要与后端保持 1:1 对齐。
3. 测试：`tests/app/services/test_agent_service.py`、`evaluation/test_integration.py`、以及任何显式引用 `anthropic/claude-3.5-sonnet`/`openrouter/anthropic/claude-3-haiku` 的测试数据都要一起更新。
4. 文档：根目录 `backend/AGENTS.md` 需记录最新 Claude 支持情况，方便其它目录复用；必要时补充 `evaluation/docs/` 下的说明。

### 验证建议

- 后端：运行 `pytest tests/app/services/test_agent_service.py -k scoring`，确认默认模型列表与 API 层返回一致。
- 前端：`cd evaluation && npm run test -- tests/emotionBackgrounds.test.ts`（或任一 vitest 套件）确保基础测试通过，再通过 `npm run dev` 打开评测页面验证模型下拉展示与缓存清理逻辑。
