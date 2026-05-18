"""
Minimal FastAPI + OpenTelemetry request/response tracing demo.
Every HTTP request is automatically traced; spans go to console and optionally OTLP.
"""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

# Tracing setup: must run before creating the FastAPI app
_service_name = os.environ.get("OTEL_SERVICE_NAME", "fastapi-otel-demo")
_resource = Resource(attributes={"service.name": _service_name})
_provider = TracerProvider(resource=_resource)
_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

# OTLP export: Uptrace (recommended) or generic env-based
_uptrace_dsn = os.environ.get("UPTRACE_DSN")
if _uptrace_dsn:
    # Pass endpoint and DSN in code so the DSN (e.g. ...?grpc=4317) is not
    # mangled by OTEL_EXPORTER_OTLP_HEADERS comma/equals parsing. See:
    # https://uptrace.dev/get/opentelemetry-python/otlp
    _provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=os.environ.get(
                    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
                    "https://api.uptrace.dev/v1/traces",
                ),
                headers={"uptrace-dsn": _uptrace_dsn},
            )
        )
    )
elif os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"):
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(_provider)

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI(title="FastAPI OpenTelemetry Demo")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}


@app.get("/error")
async def trigger_error():
    raise ValueError("Demo error for span visibility")


FastAPIInstrumentor.instrument_app(app)
