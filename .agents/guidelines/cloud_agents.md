# Cursor Cloud Agent 执行契约

> 在 Cursor Cloud VM 里跑自动化 Agent 时用。配置入口：[`.cursor/environment.json`](../../.cursor/environment.json)。

## 先读这个

VM 启动后 Cursor 会自动跑 `install` 和 `start`，你通常只需：

1. `source .venv/bin/activate`（Python 工具都在 venv 里，不 activate 会误报「未安装」）
2. 确认 Postgres 已就绪（`start` hook 会跑；见下方验证命令）
3. 按需启动 backend，再跑测试

**端口**：`8000` Inty API · `8001` Ops/REPL · `15432` PostgreSQL

**install 脚本会装什么**（[`cloud-agent-install.sh`](../../.cursor/cloud-agent-install.sh)）：Python 3.12 + `.venv`、`config.yaml`（从 `devops/config.yaml.test` 复制）、apt 依赖（见 [`cloud-agent-apt.sh`](../../.cursor/cloud-agent-apt.sh)）。

**不在 install 里**（需 snapshot 或手动）：Android SDK、`evaluation/node_modules`、emulator AVD。缺了再装或存 dashboard snapshot。

## Agent 工作流（强制）

1. **分支**：只在任务指定分支开发；本地没有就先建同名分支。
2. **提交**：一次逻辑变更一个 commit；message = 一句话总结 + 详细描述。
3. **推送**：`git push -u origin <branch>`；除非用户明确要求，禁止 force push / amend 已推送提交。
4. **PR**：每轮实现-测试后更新远端并创建/更新 PR；描述里附测试证据。
5. **交付前**：检查 diff（无无关改动、无调试代码、无密钥）；若影响目录规范，同步更新对应 `AGENTS.md` / `README.md` / `TODOS.md`。

## 常用命令

### 验证环境

```bash
source .venv/bin/activate && uv --version && ruff --version
PGPASSWORD='sxwl666!' psql -h localhost -U postgres -d inty -c 'SELECT 1'
```

缺工具时重跑：`bash .cursor/cloud-agent-install.sh`

### 启动服务

**PostgreSQL**（boot 时 `.cursor/cloud-agent-start.sh` 已调用；手动：`./tools/scripts/ensure_postgres_for_tests.sh`）

**Inty backend (8000)**

```bash
export INTY_CONFIG_YAML=devops/config.yaml.test
source .venv/bin/activate
./backend/inty/start.sh --test    # CI 模式，无 reload
# ./backend/inty/start.sh --dev   # 开发模式，带 reload
```

**Ops / REPL (8001，可选)**

```bash
source .venv/bin/activate
./backend/ops/start.sh --local --no-build-frontend
# REPL 调试加：--debug --log-file ./inty-ops-local.log
```

`start.sh` 不会帮你 activate venv。Python 里 `Environment.TEST` 来自 `config.yaml`，不是 `--test` CLI flag。

### 测试

**Backend**（需 backend 先跑着；见 [`tests/AGENTS.md`](/tests/AGENTS.md)）

```bash
source .venv/bin/activate
pytest -m "not noci" -v -s tests/
```

**Lint**（activate 后或 `uv run …`）

```bash
uv run ruff check <paths>
uv run black --check app/ backend/
```

**Android / evaluation**：见 [`backend/README.md`](/backend/README.md)、[`.github/workflows/ci_android_app.yaml`](/.github/workflows/ci_android_app.yaml)、[`evaluation/AGENTS.md`](/evaluation/AGENTS.md)。evaluation 需先 `cd evaluation && npm install`。

### 测试用 auth token

```bash
PYTHONPATH=. python3 -c "from app.core.security import create_access_token; print(create_access_token('user-testing'))"
```

（需已有 `config.yaml`）

## 常见坑

- **venv**：`uv` / `ruff` / `black` 等在 `.venv/bin/`，用 `source .venv/bin/activate` 或 `uv run …`。
- **Docker**：Cloud VM 需手动起 daemon：`sudo dockerd &>/tmp/dockerd.log &`（fuse-overlayfs + iptables-legacy）。
- **远程日志**：IntelliMate VM 容器日志走 SSH + [`devops/fetch_inty_vm_container_logs.sh`](/devops/fetch_inty_vm_container_logs.sh)（见 [`DEPLOYMENT_STATE.md`](/devops/DEPLOYMENT_STATE.md)），不是 `gcloud logging read`。
- **Android emulator**：Cloud VM 无 KVM，必须 `-no-accel -gpu swiftshader_indirect`，冷启动约 4 分钟；AVD 名 `test_avd`，SDK 通常在 `/opt/android-sdk`（snapshot 才有）。完整命令见 [`cloud_agents_android.md`](cloud_agents_android.md)。

## 可选：加速冷启动

首次手动配好 Android SDK / node_modules 等 heavyweight 依赖后，可在 dashboard 存 snapshot，并在 `environment.json` 加 `"snapshot": "snapshot-…"`。更重系统依赖可用 `.cursor/Dockerfile` + `"build"`（见 [Cursor docs](https://cursor.com/docs/cloud-agent/setup#environment-setup-options)）。
