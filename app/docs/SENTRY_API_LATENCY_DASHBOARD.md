CREATED_BY_AGENT: GPT-5.2 (Cursor Cloud Agent)

## 目标

为 `app/` 的 FastAPI 后端在 Sentry 中建立一个「API 延迟」Dashboard，能按 **路由模板**（例如 `GET /api/v1/users/{user_id}`）聚合查看 p50/p95/p99 延迟、吞吐量与错误率，便于快速定位慢接口。

## 前置条件

- **Sentry 项目已创建**，并开启 Performance（Transactions）。
- **后端已启用 tracing**：在 `config.yaml` 配置 `sentry.dsn` 且 `sentry.enabled=true`，并设置合适的 `sentry.traces_sample_rate`。

示例（按你们现有 `app/core/config.py` 的结构）：

```yaml
sentry:
  enabled: true
  dsn: "https://<public_key>@o<org_id>.ingest.sentry.io/<project_id>"
  traces_sample_rate: 0.1  # 线上建议从 0.05~0.2 起步，按量再调
```

## 代码侧说明（保证 Dashboard 聚合稳定）

项目里使用了两层命名策略来保证所有 HTTP endpoint 都稳定聚合：

1. `route_class=LoggerRoute`（大部分 `api/v1` 路由）
2. `app/main.py` 中的全局 HTTP middleware（兜底覆盖未使用 `LoggerRoute` 的路由）

两者都会把 transaction 名称统一设置为：

- `METHOD + 空格 + self.path`
- 例如：`POST /api/v1/chat`、`GET /api/v1/users/{user_id}`

同时会写入 tag：

- `api.route=<self.path>`

这能让 Sentry Dashboard 用 `transaction` 或 `api.route` 做稳定分组（避免 path 参数导致高基数）。

### WebSocket 端点

对于 WebSocket 端点，代码中使用手动 transaction：

- `op = websocket.server`
- `name = WEBSOCKET /api/v1/live-chat/{agent_id}`（示例）
- tag: `api.route`, `api.protocol=websocket`

这样可以在 Sentry Performance 里单独查看 WebSocket 会话耗时与错误。

## Sentry Dashboard（手动创建步骤）

在 Sentry Web：

- 进入 **Dashboards** → **Create Dashboard**
- Dashboard 名称建议：`API Latency (app backend)`

下面每个 Widget 都建议使用 **Discover / Transactions** 数据集（Performance）。如果你们的 UI 里是「Data Set: Transactions」，就选 Transactions。

### Widget 1：Top 慢接口（p95）

- **Query**：
  - `event.type:transaction transaction.op:http.server`
  - 可选：加环境过滤 `environment:prod`（按你们实际 environment 名称）
  - 可选：排除预检 `!http.method:OPTIONS`
- **Y-Axis**：`p95(transaction.duration)`
- **Display**：Table
- **Group by**：优先用 `transaction`（或 `api.route` 如果你们的 Discover 能直接选到这个 tag）
- **Sort**：按 `p95(transaction.duration)` 降序
- **Limit**：20

### Widget 2：延迟趋势（p95 / 全量）

- **Query**：同上
- **Y-Axis**：`p95(transaction.duration)`
- **Display**：Line
- **Interval**：auto（或 1m/5m 视流量）

### Widget 3：吞吐量（RPM）

- **Query**：同上
- **Y-Axis**：`count()`
- **Display**：Area/Line
- **Unit**：按默认即可（通常可理解为每个时间桶的请求数）

### Widget 4：5xx 错误率

- **Query**：`event.type:transaction transaction.op:http.server http.status_code:[500 TO 599]`
- **Y-Axis**：`count()`
- **Display**：Line
- 可选再加一个对比 Widget：全量 `count()`，再用 Dashboard 视觉对比

### Widget 5：按状态码/接口看分布（可选）

- **Query**：同上
- **Y-Axis**：`p95(transaction.duration)`
- **Group by**：`http.status_code` 或 `transaction`
- **Display**：Bar/Table

### Widget 6：WebSocket 会话延迟（可选）

- **Query**：`event.type:transaction transaction.op:websocket.server`
- **Y-Axis**：`p95(transaction.duration)`
- **Display**：Line/Table
- **Group by**：`transaction` 或 `api.route`

## 常见排查建议（可选）

- 如果发现同一路由被拆成很多条（高基数），优先检查 Dashboard 是否用了 `url`/`request.url` 这类字段分组；应使用 `transaction`（路由模板）分组。
- 如果看不到 Transactions：
  - 检查 `sentry.traces_sample_rate` 是否为 0
  - 检查 Sentry 项目是否开启 Performance
  - 检查环境过滤是否写错（environment 名称需一致）

