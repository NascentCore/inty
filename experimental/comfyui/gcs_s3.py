import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

# The name of your Google Cloud Storage bucket
BUCKET_NAME = "yx-test-3"

# The endpoint URL for Google Cloud Storage's S3-compatible API
GCS_ENDPOINT_URL = "https://yx-test-3.storage.googleapis.com"

# --- Set up the boto3 client ---

# Note: Google Cloud Storage's S3 compatibility layer has some nuances.
# The 's3v4' signature version is required.
# 'endpoint_url' is critical to point boto3 to GCS instead of AWS S3.
s3_client = boto3.client(
    "s3",
    # aws_access_key_id=ACCESS_KEY_ID,
    # aws_secret_access_key=ACCESS_SECRET,
    endpoint_url=GCS_ENDPOINT_URL,
    config=Config(signature_version="s3v4"),
)

# --- Define a local file and its destination in the bucket ---
local_file_path = "req.json"
object_key = "req.json"
downloaded_file_path = "downloaded_req.json"

s3_client.upload_file(local_file_path, BUCKET_NAME, object_key)
