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

## Security gate verification for /metrics

Verify `/metrics` is blocked when not in debug/test:

```bash
cp devops/config.yaml.test /tmp/config.metrics.prod.yaml
sed -i 's/debug: true/debug: false/' /tmp/config.metrics.prod.yaml
sed -i 's/environment: "test"/environment: "prod"/' /tmp/config.metrics.prod.yaml
```

Prepare temporary local service-account files for startup in prod-like mode:

```bash
openssl genrsa -out /tmp/fake_service_account_key.pem 2048
awk 'NF {sub(/\r/, ""); printf "%s\\n", $0;}' /tmp/fake_service_account_key.pem > /tmp/fake_service_account_key_escaped.txt
printf '{"type":"service_account","project_id":"fake-project","private_key_id":"fake-key-id","private_key":"%s","client_email":"fake@fake-project.iam.gserviceaccount.com","client_id":"1234567890","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/fake%%40fake-project.iam.gserviceaccount.com"}\n' "$(cat /tmp/fake_service_account_key_escaped.txt)" > /tmp/fake-gcp-service-account.json
cp /tmp/fake-gcp-service-account.json .secrets/inty-backend-key.json
cp /tmp/fake-gcp-service-account.json .secrets/firebase-service-account.json
```

Start a secondary backend instance on port 8002 with prod-like config:

```bash
cp config.yaml /tmp/config.yaml.backup
cp /tmp/config.metrics.prod.yaml config.yaml
source .venv/bin/activate
python -m uvicorn backend.inty.main:app --host 127.0.0.1 --port 8002 --log-level warning
```

In another terminal:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8002/metrics
```

Expected:

- Status code is `404`.

Cleanup:

```bash
cp /tmp/config.yaml.backup config.yaml
rm -f .secrets/inty-backend-key.json .secrets/firebase-service-account.json
rm -f /tmp/fake-gcp-service-account.json /tmp/fake_service_account_key.pem /tmp/fake_service_account_key_escaped.txt
```

