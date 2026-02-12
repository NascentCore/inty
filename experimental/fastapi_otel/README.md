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

## 参考

- [OpenTelemetry FastAPI Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [OpenTelemetry Python OTLP Exporters](https://opentelemetry-python.readthedocs.io/en/stable/exporter/otlp/otlp.html)
