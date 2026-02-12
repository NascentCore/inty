# app/ FastAPI 接入 OpenTelemetry 追踪改造说明

本文记录如何改造 `app/` 的 FastAPI 应用，使其将 HTTP 请求/响应以 OTLP 形式上报到 Uptrace（或其它 OTLP 后端），便于在 Web UI 中查看按 endpoint 聚合的延迟、错误率等。方案已在 `experimental/fastapi_otel/` 验证，可直接复用到 `app/main.py`。

## 目标

- 为每个 FastAPI RPC 请求自动生成 trace span（方法、路径、状态码、耗时等）。
- 将 trace 通过 OTLP HTTP 导出到 Uptrace（或配置的其它 endpoint），与现有 Sentry 错误监控可并存。

## 前置参考

- 最小可运行 demo：`experimental/fastapi_otel/`（含 [README](https://github.com/your-org/inty/blob/main/experimental/fastapi_otel/README.md) 与方案摘要）。
- Uptrace 认证必须用 **`UPTRACE_DSN`** 在代码里传给 exporter，不要用 `OTEL_EXPORTER_OTLP_HEADERS` 传 DSN（DSN 内含 `=` 会导致解析错误）。

## 依赖

在 `pyproject.toml`（或 `app` 所用依赖声明）中增加：

- `opentelemetry-instrumentation-fastapi`
- `opentelemetry-exporter-otlp-proto-http`

若尚未引入 OpenTelemetry 核心，还需：

- `opentelemetry-api`
- `opentelemetry-sdk`

## 配置

二选一或并存：

1. **环境变量（推荐用于 Uptrace）**  
   - `UPTRACE_DSN`：Uptrace 项目 DSN（Project Settings 复制）。  
   - 可选：`OTEL_SERVICE_NAME`（默认可用 `global_config_loaded_from_config_yaml.app.name`）。  
   - 可选：`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`（自建 OTLP 时覆盖，默认 Uptrace Cloud）。

2. **配置文件（可选）**  
   在 `app/core/config.py` 中增加例如 `OtelConfig` 或扩展现有监控配置：  
   - `enabled: bool`、`uptrace_dsn: str`、`service_name: str`（可默认取 `app.name`）、`traces_endpoint: str`（可选）。  
   由 `global_config_loaded_from_config_yaml` 读取，在初始化 tracing 时使用。

## main.py 改造步骤

### 1. 导入

在 `app/main.py` 中，在创建 `app` 之前增加（注意：tracing 初始化必须在 `app = FastAPI(...)` 之前）：

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
```

### 2. 在创建 app 之前初始化 TracerProvider

在 `init_sentry()` 之后、`app = FastAPI(...)` 之前增加一段初始化逻辑（下面以仅环境变量为例；若用 config，则从 `global_config_loaded_from_config_yaml` 读 enabled/dsn/endpoint）：

- 使用 `Resource(attributes={"service.name": service_name})`，`service_name` 建议取 `global_config_loaded_from_config_yaml.app.name` 或 `OTEL_SERVICE_NAME`。
- 创建 `TracerProvider(resource=resource)`。
- 可选：`add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))`（本地调试时可看控制台 span）。
- 若配置了 Uptrace（例如 `UPTRACE_DSN` 非空）：  
  `add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=..., headers={"uptrace-dsn": dsn})))`，  
  endpoint 默认 `https://api.uptrace.dev/v1/traces`，可被 `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` 覆盖。
- 若未用 Uptrace 但配置了通用 OTLP endpoint（如 `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`）：  
  `add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))`（从环境变量读 endpoint/headers）。
- 调用 `trace.set_tracer_provider(provider)`。

### 3. 在 app 创建并挂完路由之后执行 instrument_app

在 `app.include_router(api_router)` 以及其它路由、middleware 注册完成之后，调用：

```python
FastAPIInstrumentor.instrument_app(app)
```

这样每个 HTTP 请求会自动产生 span，并随已配置的 BatchSpanProcessor 导出到控制台和/或 OTLP（Uptrace）。

### 4. 与 Sentry 的关系

- 当前 `app/main.py` 已使用 Sentry（`FastApiIntegration`、`StarletteIntegration`、`traces_sample_rate`）。  
- OpenTelemetry 的 `FastAPIInstrumentor` 与 Sentry 的 FastAPI 集成可同时启用：两者分别做各自的 tracing/error 上报，互不替代。  
- 若希望统一在 Uptrace 看请求级 trace，可保留 Sentry 仅做错误与告警，OTEL 专做请求链路与延迟聚合。

## 验证

1. 设置 `UPTRACE_DSN`（及可选 `OTEL_SERVICE_NAME`），启动 `app`（如 `uvicorn app.main:app --reload`）。
2. 调用若干 API（如登录、聊天、订阅等）。
3. 在 Uptrace 的 Spans / Groups 中按 `service_name` 过滤，应能看到对应 endpoint 的 span、count/min、p50/p90/p99、错误率等。

## 参考

- [experimental/fastapi_otel/README.md](../experimental/fastapi_otel/README.md)（方案摘要与 Uptrace 步骤）
- [Uptrace — Direct OTLP (Python)](https://uptrace.dev/get/opentelemetry-python/otlp)
- [OpenTelemetry FastAPI Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
