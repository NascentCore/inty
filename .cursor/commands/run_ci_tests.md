# Run backend CI tests locally

## Overview

在本地复现 GitHub workflow **`CI - Inty 后端`**（[`.github/workflows/ci_backend.yaml`](/.github/workflows/ci_backend.yaml)）的检查序列，合并 PR 前或调试 CI 失败时使用。

权威步骤、脚本路径与起停 backend 规则见 skill：[`.cursor/skills/inty-backend-ci-local/SKILL.md`](/.cursor/skills/inty-backend-ci-local/SKILL.md)。**必须先读该 skill，再按序执行。**

## Prerequisites

- **Python 3.12**，当前工作目录为**仓库根目录**
- **PostgreSQL** 可连（CI 等价：`postgres:16`，`PG_USER=postgres`，`PG_PASSWORD=sxwl666!`，`PG_DB=inty`，端口 **5432**）；本机无 PG 时按 skill 用 Docker 起库
- `tests/alembic/test_custom_config.sh` 需要 **`psql`**、`openssl`、`devops/config.yaml.local`

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

   **智能体必做**（skill 全文为准，此处为硬约束）：
   - **禁止**因 `:8000` 已有响应就跳过 `start.sh` 直接 `pytest`
   - 起服前用 [`.cursor/skills/scripts/inty_ci_backend_stop.sh`](/.cursor/skills/scripts/inty_ci_backend_stop.sh) 清占用 **8000** 的 `backend.inty.main`
   - 设 `INTY_CI_BACKEND_STARTED=1` 与 `trap stop_ci_backend EXIT`；**pytest 结束或失败后必须 stop**，确认 `lsof -i :8000` 无 `backend.inty.main`

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

6. **Push worker 启动自检**（选做，对应 workflow `Start push worker...`；同一 shell 顺序跑时注意端口/进程冲突，见 skill §6）

## Report

- 逐步列出每步 **pass / fail** 与失败时的关键输出
- 给出 **pytest** 汇总（通过数、失败用例）
- 确认 **:8000 backend 已清理**（`lsof -i :8000` 或无 `backend.inty.main`）
- 若某步因环境缺失（无 PG、无 `psql` 等）无法执行，说明缺什么及如何补齐

## Checklist

- [ ] 已读 `inty-backend-ci-local` skill
- [ ] 前置环境满足（Python 3.12、PG、仓库根目录）
- [ ] layer check、Alembic head、test_custom_config 通过
- [ ] backend 按 `INTY_CONFIG_YAML` 起停，pytest 与 log scan 完成
- [ ] CI 流程结束后 :8000 无残留 `backend.inty.main`
- [ ] 报告含各步结果与 pytest 汇总
