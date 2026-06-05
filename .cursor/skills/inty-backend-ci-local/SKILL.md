---
name: inty-backend-ci-local
description: >-
  Replicate GitHub workflow `.github/workflows/ci_backend.yaml` locally: venv, layer
  checks, single Alembic head, `tests/alembic/test_custom_config.sh`, test config via
  `INTY_CONFIG_YAML` (or cp like CI), Inty server on :8000, `pytest -m "not noci"`, backend
  cleanup, optional log scan and push worker smoke. Use when running the same checks as backend CI before a
  PR, or when debugging CI failures.
---

# Run Inty backend CI tests locally (mirror `ci_backend.yaml`)

## When to use

- When users ask to run ci tests
- When you want to verify your chagens by running the affected tests

## 前提

- **Python 3.12**（与 workflow 中 `actions/setup-python` 一致）
- **仓库根目录**为当前工作目录（所有路径相对根目录）
- **PostgreSQL** 可连：CI 使用 `postgres:16`，`PG_USER=postgres`，`PG_PASSWORD=sxwl666!`，`PG_DB=inty`，端口 **5432**。`devops/config.yaml.test` 只改 `database.host: localhost`；`app` 的默认 `DatabaseSettings` 与上述用户/库/密码一致。若本机 5432 无 PG，可用 Docker 起一只与 CI 等价的库：

```bash
docker run --rm --name inty-ci-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD='sxwl666!' \
  -e POSTGRES_DB=inty \
  -p 5432:5432 -d postgres:16
```

- `tests/alembic/test_custom_config.sh` 需要 **`psql`（客户端）**、`openssl`，以及模板 **`devops/config.yaml.local`**（仓库中应有；若缺失会报错）

## 1) 虚拟环境与依赖

与 CI 相同：根目录 `.venv`，安装 `requirements.txt` 与 `tests/requirements.txt`：

```bash
cd /path/to/inty
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r tests/requirements.txt
```

## 2) 架构层依赖检查

```bash
python .cursor/skills/scripts/check_layer_dependencies.py
```

## 3) 单一 Alembic head

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

## 4) Alembic 自定义配置测试

```bash
export PYTHONPATH=.
./tests/alembic/test_custom_config.sh
```

## 5) 起 Inty 后端并跑 Pytest（与 `Run python tests` 步一致）

### 智能体必做（本地跑本节时）

- **禁止**因 `:8000` 已有响应就跳过 `start.sh` 直接 `pytest`；须用测试配置**自行起停**一轮 backend。
- **起服前**：[`inty_ci_backend_stop.sh`](.cursor/skills/scripts/inty_ci_backend_stop.sh) 清掉占用 **8000** 的 `backend.inty.main`（不误杀其他进程）。
- **起服后**：设 `INTY_CI_BACKEND_STARTED=1`，并对当前 shell 设 `trap`，在 **pytest 结束或失败**、log scan 之后**必须**执行 stop（GHA runner 会销毁 VM，本地不会）。
- **禁止**在 CI 流程结束后仍占用 `:8000`；若你启动了 backend，用户问「有没有关掉」时应能确认 `lsof -i :8000` 已无 `backend.inty.main`。

```bash
chmod +x .cursor/skills/scripts/inty_ci_backend_stop.sh

stop_ci_backend() {
  if [ "${INTY_CI_BACKEND_STARTED:-}" = "1" ]; then
    .cursor/skills/scripts/inty_ci_backend_stop.sh 8000
    unset INTY_CI_BACKEND_STARTED
  fi
}
trap stop_ci_backend EXIT
```

### 配置路径：推荐 `INTY_CONFIG_YAML`（不覆盖 `config.yaml`）

[`app/core/config.py`](app/core/config.py)：`INTY_CONFIG_YAML` 优先；未设置时才读仓库根 `config.yaml`。本地跑 CI 同款测试叠层时，**推荐**导出：

```bash
export INTY_CONFIG_YAML=devops/config.yaml.test
```

路径为**相对当前工作目录**（在仓库根执行即为 `devops/config.yaml.test`）。**起 `./backend/inty/start.sh` 与 `pytest` 的 shell 都要带上该变量**（子进程继承即可）。

Alembic：`backend/alembic/env.py` 在未传 `-x config=...` 时会回落到 **`app.core.config` 已加载的那份全局配置**；因此 `start.sh` 里 `python -m alembic upgrade head` 与随后 uvicorn **与上述 `INTY_CONFIG_YAML` 一致**，无需再 `cp` 成 `config.yaml`。

### 与 GHA 文案差异（可选 `cp`）

<!-- TODO(INTY_CONFIG_YAML): align ci_backend.yaml to INTY_CONFIG_YAML only; remove cp recommendation here -->

[`ci_backend.yaml`](.github/workflows/ci_backend.yaml) 里仍是 `cp devops/config.yaml.test config.yaml`；若你要**逐字对齐 workflow 的 shell**，可继续用复制；与 `INTY_CONFIG_YAML=devops/config.yaml.test` **在行为上等价**（只要在任何进程首次 `import app.core.config` 之前定好其一）。

先**停掉**本机占用 **8000** 的 Inty `uvicorn`（仅 `backend.inty.main`），再启 CI 测试服。若还要跑 [`.cursor/skills/scripts/check_ci_backend_logs.py`](.cursor/skills/scripts/check_ci_backend_logs.py)，建议**删旧日志再起服**，避免历史 ERROR 误报：

```bash
.cursor/skills/scripts/inty_ci_backend_stop.sh 8000
rm -f inty_backend.log
export INTY_CONFIG_YAML=devops/config.yaml.test
export PYTHONPATH=.
./backend/inty/start.sh --test >> inty_backend.log 2>&1 &
backend_pid=$!
export INTY_CI_BACKEND_STARTED=1
# stop_ci_backend + trap EXIT：见上文「智能体必做」
```

等待服务就绪（与 workflow 中循环等价）：

```bash
for i in {1..30}; do
  if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo "Server is ready!"
    break
  fi
  echo "Attempt $i: waiting..."
  sleep 2
done
curl --verbose --fail http://localhost:8000
```

`pytest` 与 CI 相同：跳过 `noci` 标记的用例（见 `pytest.ini`）；workflow 里对日志级别有 `env`，本地可对齐抄入：

```bash
export INTY_CONFIG_YAML=devops/config.yaml.test
export PYTHONPATH=.
export INTY_LOGGING_LEVEL=INFO
export INTY_CONSOLE_LOGGING_LEVEL=INFO
export UVICORN_LOG_LEVEL=warning
python -m pytest -m "not noci" -v -s tests/ --capture=fd --show-capture=no
```

可选：与 workflow 该 job 内一致扫后端日志（依赖上面的 `inty_backend.log`）：

```bash
python .cursor/skills/scripts/check_ci_backend_logs.py inty_backend.log --context-name "Inty backend test server"
```

测试与日志检查完成后，**必须**结束本次启动的 backend（`trap` 在 shell 退出时也会跑；pytest 失败时同样要清理）：

```bash
stop_ci_backend
trap - EXIT
# 可选确认：lsof -i :8000 应无 backend.inty.main
```

## 6) Push worker 启动自检（选做，对应 workflow `Start push worker...`）

同样导出 `INTY_CONFIG_YAML` 即可与「不覆盖 `config.yaml`」一致；就绪判定与断言以 [`.github/workflows/ci_backend.yaml`](.github/workflows/ci_backend.yaml) 该 step 为准（`tee push_worker.log`、`grep` 循环等）。

```bash
export INTY_CONFIG_YAML=devops/config.yaml.test
export PYTHONPATH=.
./backend/push_worker/start.sh 2>&1 | tee push_worker.log &
# … 见 ci_backend.yaml …
```

## 与真实 CI 的差异（心里有数即可）

- **配置落地**：CI job 写 `cp ... config.yaml`；本地推荐 **`INTY_CONFIG_YAML`**，避免动默认 `config.yaml`。
- **Runner**：你本机的 OS/文件句柄/负载与 `ubuntu-latest` 可能不同；**偶发**的时序/端口问题在 CI 上可能不出现或相反。
- **cache**：CI 会 cache `~/.cache/pip` 与 `.venv`；本地可省略，结果应一致。
- **服务编排**：若你在一条 shell 里顺序执行 5) 和 6)，`start.sh` 的进程通常仍在，与 GHA 同一 job 内多 step **共享**一台机器、后台进程不清理的行为类似；若你分开终端跑，**注意** 8000/重复迁移等冲突。

## 权威来源

- 工作流定义：`.github/workflows/ci_backend.yaml`（`jobs.test` 各 step 名称与 `run:` 即上面对应关系）
- 配置路径语义：`app/core/config.py`（`INTY_CONFIG_YAML`）
