---
name: inty-backend-ci-local
description: >-
  Replicate GitHub workflow `.github/workflows/ci_backend.yaml` locally: venv, layer
  checks, single Alembic head, `tests/alembic/test_custom_config.sh`, test config,
  Inty server on :8000, `pytest -m "not noci"`, and push worker smoke check. Use
  when the user wants to run the same checks as backend CI before opening a PR, or
  when debugging CI failures.
---

# Run backend CI locally (mirror `ci_backend.yaml`)

## When to use

- 合并 `main` 前想跑**与 `CI - Inty 后端` 同序**的检查
- CI 红了你希望在本地**复现同一套步骤**

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
python tools/scripts/check_layer_dependencies.py
```

## 3) 单一 Alembic head

```bash
export PYTHONPATH=.
export ALEMBIC_CONFIG=alembic/alembic.ini
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

先**停掉**本机占用 **8000** 的旧 `uvicorn`/旧 `./backend/inty/start.sh`（若存在），再：

```bash
cp devops/config.yaml.test config.yaml
./backend/inty/start.sh --test &
```

等待服务就绪（与 workflow 中循环等价；可用 `curl -s http://localhost:8000` 或带 `--fail`）：

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

`pytest` 与 CI 相同：跳过 `noci` 标记的用例（见 `pytest.ini`）：

```bash
python -m pytest -m "not noci" -v -s tests/
```

完成后**按需**结束后台的 `start.sh`/`uvicorn` 进程，避免与后续或日常开发占口冲突。

## 与真实 CI 的差异（心里有数即可）

- **Runner**：你本机的 OS/文件句柄/负载与 `ubuntu-latest` 可能不同；**偶发**的时序/端口问题在 CI 上可能不出现或相反。
- **cache**：CI 会 cache `~/.cache/pip` 与 `.venv`；本地可省略，结果应一致。
- **服务编排**：若你在一条 shell 里顺序执行 5) 和 6)，`start.sh` 的进程通常仍在，与 GHA 同一 job 内多 step **共享**一台机器、后台进程不清理的行为类似；若你分开终端跑，**注意** 8000/重复迁移等冲突。

## 权威来源

- 工作流定义：`.github/workflows/ci_backend.yaml`（`jobs.test` 各 step 名称与 `run:` 即上面对应关系）
