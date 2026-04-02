# API Error Response Contract

## Scope

- Applies to global exception responses from `backend/inty`.
- Business errors returned by `APIResponse` are unchanged in this phase.

## Unified error envelope

All handled exceptions now return the same body shape:

- `code`: string error code
- `message`: user-facing summary
- `details`: structured details for debugging/client branching
- `request_id`: request correlation id

Example:

{
  "code": "NOT_FOUND",
  "message": "Agent not found",
  "details": {
    "detail": "Agent not found"
  },
  "request_id": "ab12cd34"
}

Response header:

- `x-request-id: <same as body.request_id>`

## HTTP status to code mapping

| HTTP status | code |
| --- | --- |
| 400 | `BAD_REQUEST` |
| 401 | `UNAUTHORIZED` |
| 403 | `FORBIDDEN` |
| 404 | `NOT_FOUND` |
| 405 | `METHOD_NOT_ALLOWED` |
| 409 | `CONFLICT` |
| 422 | `UNPROCESSABLE_ENTITY` |
| 429 | `TOO_MANY_REQUESTS` |
| 500 | `INTERNAL_SERVER_ERROR` |
| 503 | `SERVICE_UNAVAILABLE` |
| others | `HTTP_ERROR` |

## Handler coverage

- `RequestValidationError` -> 422 + unified envelope
- `JWTError` -> 401 + unified envelope
- `SQLAlchemyError` -> 500 + unified envelope
- `ValidationError` -> 422 + unified envelope
- `HTTPException` / `StarletteHTTPException` -> pass-through status + mapped `code`
- fallback `Exception` -> 500 + unified envelope

## Verification

- `tests/app/api/test_error_handler_contract.py`
- `.venv/bin/pytest tests/app/api/test_error_handler_contract.py -q`
