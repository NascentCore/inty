# TEST_STEPS_BACKEND_OBSERVABILITY_REQUEST_ID_METRICS

## Goal

- Verify backend observability baseline:
  - `x-request-id` is always returned and propagated.
  - `/metrics` exposes request count and latency metrics.

## Preconditions

- Backend is running at `http://localhost:8000`.
- PostgreSQL is reachable by backend.

## Steps

1. Health check and capture generated request id:

```bash
curl -si http://localhost:8000/ | rg "HTTP/|x-request-id"
```

Expected:

- Status line is `HTTP/1.1 200 OK`.
- Response contains `x-request-id` header.

2. Verify request id propagation (client provided id should be echoed):

```bash
curl -si -H "x-request-id: req-e2e-observe-001" http://localhost:8000/ | rg "HTTP/|x-request-id"
```

Expected:

- Status line is `HTTP/1.1 200 OK`.
- Response contains `x-request-id: req-e2e-observe-001`.

3. Trigger at least one API request for metrics sampling:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/version/check
```

Expected:

- Returns a valid HTTP status code (typically 405 for GET on POST endpoint).

4. Verify metrics endpoint and key series:

```bash
curl -s http://localhost:8000/metrics | rg "http_requests_total|http_request_duration_seconds"
```

Expected:

- Contains `http_requests_total`.
- Contains `http_request_duration_seconds`.

## Automated test command

```bash
.venv/bin/pytest tests/app/features/test_observability.py -q
```

