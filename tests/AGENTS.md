# AGENTS.md · tests/（测试）

- Do not write unit tests
- Write feature tests: call backend service running locally to test a feature end-to-end
- WebSocket chat handler tests in `tests/app/api/v1/endpoints/test_chat.py` may monkeypatch auth and `agent_chat_completions` for isolation; prefer real server plus token for new contract-critical paths when feasible (aligns with `app/AGENTS.md` "Avoid using monkepatch" as a documented narrow exception).
- Access real database, and do not patch sqlalchemy
- Use [fake external services](/app/external_services/fakes) when writing tests.

## Running tests require starting local server

- Use the API Endpoints from the local backend server and postgres,
  started with:

  ```bash:launch-backend-for-testing
  # Start database
  docker run --rm --name pg-inty -p 5432:5432 \
    -e POSTGRES_PASSWORD=sxwl666! \
    -e POSTGRES_DB=inty \
    -d postgres:16

  # Launch server
  cp devops/config.yaml.test config.yaml
  backend/inty/start.sh
  
  # Create a admin bearer token, and write the token to a .txt file
  python scripts/init_admin_user.py --token-file ./admin_token.txt

  # 运行测试
  pytest -m "not noci" -v -s tests/
  ```

- Chat WebSocket against **real LLM** (optional): set `INTY_CHAT_WS_REAL_TEST=1`, set `INTY_DEV_CONFIG_PATH` to the server YAML (e.g. `devops/config.yaml.local` or `devops/config.yaml.dev`; `app.environment` must be `dev` or `local`). See [tests/docs/TEST_STEPS_CHAT_WEBSOCKET_DEV_E2E.md](docs/TEST_STEPS_CHAT_WEBSOCKET_DEV_E2E.md).

- Agentic kernel companion `run_turn` with **real LLM** on OpenRouter (optional): set `INTY_AGENTIC_KERNEL_REAL_LLM_TEST=1` and `OPENROUTER_API_KEY`; run `pytest tests/real_agents/test_agentic_kernel_run_turn_tool_call.py -m noci`. Model: `nvidia/nemotron-3-super-120b-a12b:free`. Optional `OPENROUTER_API_BASE` (default `https://openrouter.ai/api/v1`).

## 新功能 / API+客户端联调时的防遗漏

以下适用于「后端 API 与客户端（如 Android）共同参与」的新功能，用于减少契约不一致、漏测、静默失败等问题。

- **契约单一来源**  
  枚举、查询参数取值（如 sort）、错误码等若在后端有定义（如 [app/schemas](/app/schemas)），客户端必须使用与后端完全一致的字面值或类型。  
  新增或改名时：同时改后端定义与客户端调用处，并在 [app/schemas/AGENTS.md](/app/schemas/AGENTS.md) 等文档中注明对应关系；有 OpenAPI 时优先用生成客户端避免手写字符串。

- **覆盖新路径的测试**  
  新增或修改 API 入参（如新 sort、新 query 参数）时，在 [tests/](/tests/) 中增加或更新功能测试：用真实请求调用该 API，断言返回 200 及预期结构（至少无 422）。  
  若该 API 对应某一具体 UI 区块（如某列表、某分区），测试应体现「该请求参数组合」被覆盖，便于日后重构或改枚举时回归。

- **本地与 PR 验证**  
  改动 API 契约或客户端调用后，在 PR 中注明已用本地后端 + 客户端验证过相关流程（如对应界面是否正常展示或明确报错）。  
  可选：为关键 API 提供小型 smoke 脚本（请求固定参数、断言 200），在 CI 或推送前运行。

- **避免静默失败**  
  客户端请求失败（如 422）时，不要仅用「空数据」表现：应设错误状态或日志，便于区分「接口报错」与「接口成功但无数据」。
  新增/修改 API 的测试中，可顺带断言「非法参数返回 4xx」以便契约变更时能暴露问题。
