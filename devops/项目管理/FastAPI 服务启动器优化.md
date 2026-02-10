# 优化启动选项

> https://gemini.google.com/app/fd8071bae33e3c47

To run a FastAPI application in production, you need to transition from the "development" mindset (using `uvicorn main:app --reload`) to a "robustness" mindset. This involves process management, concurrency handling, and security.

The industry standard is to use **Gunicorn** as a process manager to handle multiple **Uvicorn** workers.

---

## 1. The Production Stack

In a production environment, you typically layer your application like this:

1. **Nginx/Caddy:** Acts as a Reverse Proxy (handles SSL, buffering, and static files).
2. **Gunicorn:** Acts as the Process Manager (restarts dead workers, manages signals).
3. **Uvicorn Workers:** The actual ASGI server that runs your FastAPI code.

---

## 2. The Deployment Command

You can launch your app using the following command. Make sure you have both `gunicorn` and `uvicorn` installed.

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000

```

### Breakdown of the flags:

* **`-w 4`**: Tells Gunicorn to start 4 worker processes. A common rule of thumb is .
* **`-k uvicorn.workers.UvicornWorker`**: Tells Gunicorn to use the Uvicorn worker class so it can handle asynchronous FastAPI code.
* **`main:app`**: Points to your Python file (`main.py`) and the FastAPI instance variable (`app`).

---

## 3. Critical Production Settings

When moving to production, don't forget these "safety" configurations:

* **Disable Swagger UI (Optional):** If your API is private, you might want to hide the docs in production to prevent leaking your endpoint structure.
```python
app = FastAPI(docs_url=None, redoc_url=None)

```


* **Timeouts:** If your app performs long-running tasks, increase the timeout so Gunicorn doesn't kill the worker prematurely: `--timeout 120`.
* **Graceful Shutdown:** Use the `--graceful-timeout` flag to give your app time to finish current requests before the process is killed during a restart.

---

## 4. Using Docker (Recommended)

The most reliable way to run FastAPI is inside a container. This ensures your environment is identical from staging to production.

```dockerfile
FROM python:3.11-slim

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

# Run Gunicorn with Uvicorn workers
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:80"]

```

---

## 5. Summary Checklist

| Feature | Production Setting |
| --- | --- |
| **Worker Count** | Multiple (based on CPU) |
| **Logging** | Set level to `INFO` or `WARNING` |
| **Security** | Run behind a Reverse Proxy (Nginx/Cloudflare) |
| **Scaling** | Use Docker and an Orchestrator (Kubernetes/ECS) |

**Would you like me to help you write a basic Nginx configuration file to sit in front of your FastAPI app?**
