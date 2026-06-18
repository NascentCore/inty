# Run backend CI tests locally

## Overview

在本地复现 GitHub workflow **`CI - Inty 后端`**（[`.github/workflows/ci_backend.yaml`](/.github/workflows/ci_backend.yaml)）的检查序列。

## When to use

- 用户要求跑 CI tests，或触发 **`/run_ci_tests`**
- 合并 PR 前想跑与 `CI - Inty 后端` 同序的检查
- CI 红了，希望在本地复现同一套步骤
- 想跑受影响测试以验证当前改动

## Prerequisites

- **Python 3.12**，当前工作目录为**仓库根目录**
- **PostgreSQL** 可连（CI 等价：`postgres:16`，`PG_USER=postgres`，`PG_PASSWORD=sxwl666!`，`PG_DB=inty`，端口 **5432**）；本机 5432 无 PG 时：

```bash
docker run --rm --name inty-ci-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD='sxwl666!' \
  -e POSTGRES_DB=inty \
  -p 5432:5432 -d postgres:16
```

- `tests/alembic/test_custom_config.sh` 需要 **`psql`**、`openssl`、`devops/config.yaml.test`

## Steps

1. **虚拟环境与依赖**（`.venv` 缺失或 requirements 变更时）
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   python -m pip install -r tests/requirements.txt
   ```

2. **架构层依赖检查**
   ```bash
   python .cursor/skills/scripts/check_layer_dependencies.py
   ```

3. **单一 Alembic head**
   ```bash
   export PYTHONPATH=.
   export ALEMBIC_CONFIG=backend/alembic/alembic.ini
   heads_count=$(python -m alembic heads | wc -l)
   if [ "$heads_count" -ne 1 ]; then
     echo "Expected exactly one alembic head, got $heads_count"
     python -m alembic heads
     exit 1
   fi
   ```

4. **Alembic 自定义配置测试**
   ```bash
   export PYTHONPATH=.
   ./tests/alembic/test_custom_config.sh
   ```

5. **起 Inty backend、跑 Pytest、扫日志、清理**（与 workflow `Run python tests` 步一致）

   **智能体必做**（硬约束）：
   - **禁止**因 `:8000` 已有响应就跳过 `start.sh` 直接 `pytest`
   - 起服前用 [`.cursor/skills/scripts/inty_ci_backend_stop.sh`](/.cursor/skills/scripts/inty_ci_backend_stop.sh) 清占用 **8000** 的 `backend.inty.main`
   - 设 `INTY_CI_BACKEND_STARTED=1` 与 `trap stop_ci_backend EXIT`；**pytest 结束或失败后必须 stop**，确认 `lsof -i :8000` 无 `backend.inty.main`
   - 推荐 `export INTY_CONFIG_YAML=devops/config.yaml.test`（不覆盖仓库根 `config.yaml`）；`start.sh` 与 `pytest` 的 shell 都要带上该变量

   ```bash
   chmod +x .cursor/skills/scripts/inty_ci_backend_stop.sh

   stop_ci_backend() {
     if [ "${INTY_CI_BACKEND_STARTED:-}" = "1" ]; then
       .cursor/skills/scripts/inty_ci_backend_stop.sh 8000
       unset INTY_CI_BACKEND_STARTED
     fi
   }
   trap stop_ci_backend EXIT

   .cursor/skills/scripts/inty_ci_backend_stop.sh 8000
   rm -f inty_backend.log
   export INTY_CONFIG_YAML=devops/config.yaml.test
   export PYTHONPATH=.
   ./backend/inty/start.sh --test >> inty_backend.log 2>&1 &
   export INTY_CI_BACKEND_STARTED=1

   for i in {1..30}; do
     if curl -s http://localhost:8000 > /dev/null 2>&1; then
       echo "Server is ready!"
       break
     fi
     echo "Attempt $i: waiting..."
     sleep 2
   done
   curl --verbose --fail http://localhost:8000

   export INTY_CONFIG_YAML=devops/config.yaml.test
   export PYTHONPATH=.
   export INTY_LOGGING_LEVEL=INFO
   export INTY_CONSOLE_LOGGING_LEVEL=INFO
   export UVICORN_LOG_LEVEL=warning
   set +e
   python -m pytest -m "not noci" -v -s tests/ --capture=fd --show-capture=no
   pytest_exit=$?
   python .cursor/skills/scripts/check_ci_backend_logs.py inty_backend.log --context-name "Inty backend test server"
   log_scan_exit=$?
   set -e

   stop_ci_backend
   trap - EXIT

   if [ "$pytest_exit" -ne 0 ]; then exit "$pytest_exit"; fi
   if [ "$log_scan_exit" -ne 0 ]; then exit "$log_scan_exit"; fi
   ```

6. **Push worker 启动自检**（选做，对应 workflow `Start push worker...`；同一 shell 顺序跑时注意端口/进程冲突，见 [`.github/workflows/ci_backend.yaml`](/.github/workflows/ci_backend.yaml)）

## 与真实 CI 的差异（心里有数即可）

- **配置落地**：CI job 写 `cp devops/config.yaml.test config.yaml`；本地推荐 **`INTY_CONFIG_YAML`**，避免动默认 `config.yaml`
- **Runner**：本机 OS/负载与 `ubuntu-latest` 可能不同；偶发时序/端口问题在 CI 上可能不出现或相反
- **cache**：CI 会 cache pip 与 `.venv`；本地可省略，结果应一致

## Report

- 逐步列出每步 **pass / fail** 与失败时的关键输出
- 给出 **pytest** 汇总（通过数、失败用例）
- 确认 **:8000 backend 已清理**（`lsof -i :8000` 或无 `backend.inty.main`）
- 若某步因环境缺失（无 PG、无 `psql` 等）无法执行，说明缺什么及如何补齐

## Checklist

- [ ] 前置环境满足（Python 3.12、PG、仓库根目录）
- [ ] layer check、Alembic head、test_custom_config 通过
- [ ] backend 按 `INTY_CONFIG_YAML` 起停，pytest 与 log scan 完成
- [ ] CI 流程结束后 :8000 无残留 `backend.inty.main`
- [ ] 报告含各步结果与 pytest 汇总
