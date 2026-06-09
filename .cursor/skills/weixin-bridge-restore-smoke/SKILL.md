---
name: weixin-bridge-restore-smoke
description: >-
  Manual release smoke and automated checks for Ops Weixin bridge Postgres
  persistence and Ops-restart restore (no QR). Use when verifying weixin bridge
  resume, ops_wechat_demo_bridges, restore_persisted_sessions, release smoke before
  merge, or when tests reference weixin restore instructions.
---

# Weixin bridge restore：smoke 验证

## 何时使用

- 发布前验证 **Postgres bridge 持久化** 与 **Ops 重启后无 QR 恢复**。
- 用户问「weixin restore 怎么测」「bridge smoke」。
- CI 已覆盖 mock restore；本 skill 描述 **真 QR + 真微信 DM** 的手动流程。

## 与自动化测试的分工

| 层级 | 命令 / 入口 | 覆盖 |
|------|-------------|------|
| CI（默认） | `pytest tests/backend/ops/test_weixin_session_restore.py tests/backend/ops/test_weixin_session_persistence.py -q` | `restore_persisted_sessions`、peer upsert、DB roundtrip（**mock** Weixin） |
| 本 skill | `GET /weixin` + 微信扫码 + Ops 重启 | Hermes/iLink、真实 peer、`last_peer_id` 落库 |

自动化测试模块 docstring 指向本文件。

## 前置条件

1. **Postgres** 已起，且 migration 含 `ops_wechat_demo_bridges`（`backend/ops/start.sh` 会 `alembic upgrade head`）。
2. **Ops** 本地：`export INTY_CONFIG_YAML=devops/config.yaml.local`（或你的 local yaml），仓库根执行  
   `./backend/ops/start.sh --local --no-build-frontend`  
   默认 **`http://127.0.0.1:8001`**。
3. **Inty API Base**：onboard 页默认 `http://127.0.0.1:8001`（扫码后自动 provision user/agent）。
4. **单 Ops 实例**：多 Pod 会重复 restore 同一行（`TODO(weixin-bridge-multi-replica)`）。

先跑 CI 相关用例（可选但推荐）：

```bash
cd /path/to/inty
source .venv/bin/activate
export PYTHONPATH=.
pytest tests/backend/ops/test_weixin_session_restore.py \
  tests/backend/ops/test_weixin_session_persistence.py -q
```

## 手动 release smoke（主流程）

在浏览器打开 **`http://127.0.0.1:8001/weixin`**（`PORT` 非默认时改 host/port）。

### 1. 建立 bridge

1. 点 **Start QR Login**，用微信扫 QR，等到页面状态 **`bridge_running: true`**（`phase` 为 `bridge_running`）。
2. **DB 应有一行**（`session_id` = 页面显示的 UUID）：

```sql
SELECT session_id, agent_id, last_peer_id, updated_at
FROM ops_wechat_demo_bridges
ORDER BY updated_at DESC
LIMIT 5;
```

连接串从仓库根 `config.yaml`（或 `INTY_CONFIG_YAML`）的 `database.async_url` / `database.url` 取。

### 2. Inbound DM 与 peer 持久化

1. 用已登录的微信账号给 bot **发一条 DM**。
2. 再查 DB：`last_peer_id` 应非空，`updated_at` 应刷新。
3. 页面 poll 仍应显示 `bridge_running: true`。

### 3. Ops 重启恢复（核心）

1. **只重启 Ops**（停掉 `backend/ops/start.sh` 起的 uvicorn 再启动；勿清 Postgres）。
2. 启动日志应出现 **`Weixin bridge restore scheduled`**。
3. 若浏览器仍开着旧 `session_id`：poll 可能短暂 **404**，随后应回到 **`bridge_running`**，**无需重新扫码**。
4. 再发一条微信 DM：应仍能收到 companion 回复。

### 4. 停止与清理

1. 点 **Stop**。
2. DB：`SELECT COUNT(*) FROM ops_wechat_demo_bridges WHERE session_id = '<uuid>'` 应为 **0**。

## 通过标准（Agent 汇报用）

- [ ] `pytest` restore + persistence 用例通过（若已跑）
- [ ] QR 后 `ops_wechat_demo_bridges` 有行且 `bridge_running`
- [ ] 微信 DM 后 `last_peer_id` 更新
- [ ] **仅 Ops 重启** 后无 QR 恢复，DM 仍通
- [ ] Stop 后对应 `session_id` 行已删除

汇报结尾：

- 全过：`[weixin-bridge-restore-smoke] RESULT: PASS`
- 任一步失败：`[weixin-bridge-restore-smoke] RESULT: FAIL (<一步>)`

## 常见失败

| 现象 | 可能原因 |
|------|----------|
| QR 后无 DB 行 | bridge 未进入 `BRIDGE_RUNNING`；看 Ops 日志 `weixin` |
| Ops 重启后一直 404 | restore `channel.start()` 失败（行会被 delete）；查 `weixin restore channel start failed` |
| DM 无回复 | `inty_jwt` 过期（`TODO(weixin-bridge-jwt)`）、`inty_api_base_url` 指错端口 |
| 多份 Weixin 连接 | 多个 Ops 实例同时 restore（违反单 runner） |

## 代码真源

- 持久化：[`backend/ops/weixin_session/session_persistence.py`](../../../backend/ops/weixin_session/session_persistence.py)
- 内存 + restore：[`backend/ops/weixin_session/session_store.py`](../../../backend/ops/weixin_session/session_store.py)
- 启动 restore：[`backend/ops/main.py`](../../../backend/ops/main.py) `startup_event`
- Onboard UI：[`backend/ops/api/weixin_web.py`](../../../backend/ops/api/weixin_web.py)
