# Sentry 集成

## 无法观察到上报信息时的排查

本地或环境已触发错误，但 Sentry Issues 中看不到对应事件时，可按下面两点排查。

### 1. 客户端：DedupeIntegration 丢弃事件

**现象**：终端或日志里出现 `DedupeIntegration dropped duplicated error event`，或只看到 `Sending envelope [envelope with 1 items (error)]` 随后没有成功送达。

**原因**：Sentry Python SDK 默认开启 DedupeIntegration，相同指纹的重复错误（例如多次触发的同一种 `ZeroDivisionError`）会被视为重复并丢弃，不会真正发送。

**处理**：在仅用于验证上报的 demo 或测试中，可显式关闭 Dedupe 集成，例如：

```python
from sentry_sdk.integrations.dedupe import DedupeIntegration

sentry_sdk.init(
    dsn=...,
    integrations=[FastApiIntegration(), StarletteIntegration(transaction_style="endpoint")],
    disabled_integrations=[DedupeIntegration()],
    ...
)
```

生产环境一般**不要**关闭 Dedupe，以免同类错误刷爆配额。

### 2. 服务端：Errors 配额用尽（Usage Exceeded）

**现象**：终端出现 `[sentry] WARNING: Rate-limited via x-sentry-rate-limits`，或 Sentry 设置页「Usage」中 Errors 显示已用满（如 5K/5K）。

**原因**：当前计费周期内错误事件配额已耗尽，Sentry 会拒绝新事件，不再写入 Issues。

**处理**：

- 在 Sentry：**Settings → Usage** 查看 Errors 使用量与计划配额。
- 升级计划提高配额，或等待下一计费周期配额重置后，新事件才会被接受并出现在 Issues 中。

---

参考：`experimental/sentry_fastapi_demo/` 中的 FastAPI + Sentry 示例及 README 中的验证与配额说明。
