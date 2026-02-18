To run a Python script regularly on Google Cloud Platform (GCP) that interacts with **Cloud SQL** and **Gemini (Vertex AI)**, the most robust "cloud-native" architecture is using **Cloud Run Jobs** triggered by **Cloud Scheduler**.

### 1. Recommended Architecture

* **Cloud Run Job**: Best for scripts that "run to completion" (like a cron job). Unlike a standard Cloud Run Service, it doesn't need to listen for HTTP requests; it just executes your code and exits.
* **Cloud Scheduler**: A managed cron service that triggers your Cloud Run Job on a set interval (e.g., every hour, daily).
* **Cloud SQL Python Connector**: A library that manages the connection to your database securely without needing to manage IP whitelists.
* **Vertex AI SDK**: The enterprise-grade way to access Gemini models within GCP.

---

### 2. IAM & Permissions

You should create a dedicated **Service Account** for your script. Do not use the default "Compute Engine" service account. Grant it these roles:

* `roles/cloudsql.client`: Allows connecting to Cloud SQL.
* `roles/aiplatform.user`: Allows calling the Gemini API via Vertex AI.
* `roles/secretmanager.secretAccessor`: (Highly recommended) To fetch DB passwords from Secret Manager instead of hardcoding them.

---

### 3. The Python Script Template

You will need to install `google-cloud-aiplatform`, `google-cloud-sql-connector`, and `sqlalchemy`.

```python
import os
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import vertexai
from vertexai.generative_models import GenerativeModel

# 1. Setup Gemini (Vertex AI)
def call_gemini(prompt):
    vertexai.init(project="your-project-id", location="us-central1")
    model = GenerativeModel("gemini-2.0-flash") # Or latest version
    response = model.generate_content(prompt)
    return response.text

# 2. Setup Cloud SQL Connection
def get_db_connection():
    connector = Connector()
    def getconn():
        conn = connector.connect(
            "project-id:region:instance-name",
            "pymysql", # or "psycopg2" for Postgres
            user="your-db-user",
            password="your-db-password", # Best fetched from Secret Manager
            db="your-database-name",
            ip_type=IPTypes.PUBLIC  # Or PRIVATE if using VPC
        )
        return conn

    engine = sqlalchemy.create_engine("mysql+pymysql://", creator=getconn)
    return engine

def main():
    # Example logic
    prompt = "Summarize the latest database entries."
    summary = call_gemini(prompt)
    
    engine = get_db_connection()
    with engine.connect() as db_conn:
        db_conn.execute(sqlalchemy.text("INSERT INTO logs (content) VALUES (:val)"), {"val": summary})
        db_conn.commit()
    print("Job completed successfully.")

if __name__ == "__main__":
    main()

```

---

### 4. Deployment Steps

#### Step A: Containerize your code

Create a `Dockerfile` in your script directory:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]

```

#### Step B: Build and Deploy the Job

Run these commands in your terminal (or Cloud Shell):

1. **Build the image**:
`gcloud builds submit --tag gcr.io/PROJECT_ID/my-python-job`
2. **Create the Cloud Run Job**:
```bash
gcloud run jobs create my-scheduled-job \
  --image gcr.io/PROJECT_ID/my-python-job \
  --region us-central1 \
  --service-account=YOUR_SERVICE_ACCOUNT_EMAIL \
  --set-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_NAME

```



#### Step C: Schedule it

Use **Cloud Scheduler** to trigger this job every day at midnight:

```bash
gcloud scheduler jobs create http my-job-trigger \
  --location us-central1 \
  --schedule="0 0 * * *" \
  --uri="https://us-central1-run.googleapis.com/v1/projects/PROJECT_ID/locations/us-central1/jobs/my-scheduled-job:run" \
  --http-method=POST \
  --oauth-service-account-email=YOUR_SERVICE_ACCOUNT_EMAIL

```

---

### Summary Checklist

| Feature | Service/Library |
| --- | --- |
| **Scheduling** | Cloud Scheduler |
| **Compute** | Cloud Run Jobs |
| **Database** | Cloud SQL Python Connector + SQLAlchemy |
| **AI/Gemini** | Vertex AI SDK (`google-cloud-aiplatform`) |
| **Security** | IAM Service Account + Secret Manager |
