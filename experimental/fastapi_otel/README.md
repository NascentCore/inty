# FastAPI + OpenTelemetry 请求/响应追踪 demo

本目录为**最小化 demo**：使用纯 OpenTelemetry 对 FastAPI 的 HTTP 请求与响应做自动追踪，不依赖 Sentry 等厂商。适用于学习 OTLP 追踪或作为接入自建/第三方后端前的参考。

## 目录结构

```
fastapi_otel/
├── README.md         # 本文件
├── requirements.txt # Python 依赖
└── main.py          # 追踪初始化 + FastAPI 应用 + instrument_app()
```

## 安装依赖

```bash
cd experimental/fastapi_otel
pip install -r requirements.txt
```

## 运行

```bash
cd experimental/fastapi_otel
uvicorn main:app --reload
```

服务默认在 `http://127.0.0.1:8000` 启动。

## 验证

- 访问 `http://127.0.0.1:8000/` 或 `http://127.0.0.1:8000/items/42`，终端会打印对应请求的 span（方法、路径、状态码等）。
- 访问 `http://127.0.0.1:8000/error` 会触发异常，span 中可看到错误信息。

## 可选：OTLP 导出

若需将 trace 导出到 OTLP 后端（如 Jaeger、Sentry OTLP、自建 collector），可设置环境变量后再启动：

```bash
export OTEL_SERVICE_NAME=fastapi-otel-demo
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4318/v1/traces
uvicorn main:app --reload
```

HTTP 协议默认 endpoint 为 `http://localhost:4318/v1/traces`；gRPC 常用 `http://localhost:4317`，需使用对应 exporter 包。

---

## 在 Uptrace 上查看 trace

本 demo 使用标准 OTLP HTTP 导出；[Uptrace](https://uptrace.dev) 支持 OTLP 并提供 Web UI 查看 trace。**请使用环境变量 `UPTRACE_DSN`**（不要用 `OTEL_EXPORTER_OTLP_HEADERS`）：DSN 内含 `=`（如 `?grpc=4317`），放在 header 环境变量里会被解析错误，本 demo 在代码里读取 `UPTRACE_DSN` 并传给 exporter，与 [Uptrace Direct OTLP (Python)](https://uptrace.dev/get/opentelemetry-python/otlp) 一致。

### 1. 创建 Uptrace 项目并获取 DSN

1. 打开 [Uptrace Get started](https://uptrace.dev/get)，创建免费云账号或自建实例。
2. 在 **Project Settings** 中复制 **DSN**（Data Source Name）。格式示例：`https://<secret>@api.uptrace.dev?grpc=4317`。无需在 Uptrace 网站做额外配置，OTLP 默认启用。

### 2. 配置环境变量

只需设置 **`UPTRACE_DSN`**（将 `<YOUR_DSN>` 替换为 Project Settings 中的完整 DSN）：

```bash
export UPTRACE_DSN="<YOUR_DSN>"
```

例如 DSN 为 `https://abc123@api.uptrace.dev?grpc=4317` 时：

```bash
export UPTRACE_DSN="https://abc123@api.uptrace.dev?grpc=4317"
```

可选：覆盖服务名或 endpoint（默认已指向 Uptrace Cloud）：

```bash
export OTEL_SERVICE_NAME=fastapi-otel-demo
# 仅自建 Uptrace 时需要改 endpoint：
# export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="https://your-uptrace.example/v1/traces"
```

### 3. 启动应用并产生流量

```bash
cd experimental/fastapi_otel
uvicorn main:app --reload
```

在浏览器或命令行访问若干次：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/items/42`
- `http://127.0.0.1:8000/error`（会报错，trace 中可见异常）

### 4. 在 Uptrace Web UI 中查看

1. 登录 [Uptrace](https://app.uptrace.dev)（或你的自建地址）。
2. 打开 **Traces**（或 **Explore**），按服务名 `fastapi-otel-demo` 或时间范围筛选。
3. 点击某条 trace 可查看 span 列表、请求方法、路径、状态码、耗时等。

更多说明见 Uptrace 官方文档：

- [OpenTelemetry Python — Uptrace](https://uptrace.dev/get/opentelemetry-python)
- [Direct OTLP Configuration (Python)](https://uptrace.dev/get/opentelemetry-python/otlp)（endpoint、headers、推荐设置）

---

## 方案摘要（用于接入 app/ 等 FastAPI 应用）

- **原理**：用 OpenTelemetry 的 `TracerProvider` + `BatchSpanProcessor` 做 trace 采集；用 `FastAPIInstrumentor.instrument_app(app)` 对 FastAPI 做一次封装，即可为每个 HTTP 请求自动生成 span（方法、路径、状态码、耗时等）。Trace 可同时打控制台（`ConsoleSpanExporter`）和 OTLP 后端（如 Uptrace）。
- **Uptrace 要点**：认证必须用 **`UPTRACE_DSN`** 环境变量，在代码里传给 `OTLPSpanExporter(..., headers={"uptrace-dsn": os.environ["UPTRACE_DSN"]})`。不要用 `OTEL_EXPORTER_OTLP_HEADERS` 传 DSN，DSN 里的 `=`（如 `?grpc=4317`）会导致解析错误。
- **接入步骤**：  
  1. 依赖：`opentelemetry-instrumentation-fastapi`、`opentelemetry-exporter-otlp-proto-http`（及 `opentelemetry-api` / `opentelemetry-sdk` 若未已有）。  
  2. 在创建 FastAPI 应用**之前**：设置 `Resource(service.name=...)`、`TracerProvider`、按需加 Console 与/或 Uptrace 的 `BatchSpanProcessor(OTLPSpanExporter(...))`，再 `trace.set_tracer_provider(provider)`。  
  3. 创建 app 并注册路由后调用 **`FastAPIInstrumentor.instrument_app(app)`**。  
  4. 运行时设置 `UPTRACE_DSN`（及可选 `OTEL_SERVICE_NAME`）。
- **Uptrace 中可见**：按 endpoint 分组的 span、count/min、p50/p90/p99 耗时、错误率；按 `service_name` 过滤可区分不同应用（如 demo 与 app/）。

## 参考

- [OpenTelemetry FastAPI Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [OpenTelemetry Python OTLP Exporters](https://opentelemetry-python.readthedocs.io/en/stable/exporter/otlp/otlp.html)
- [Uptrace — OpenTelemetry Python](https://uptrace.dev/get/opentelemetry-python)
- [Uptrace — Direct OTLP (Python)](https://uptrace.dev/get/opentelemetry-python/otlp)
