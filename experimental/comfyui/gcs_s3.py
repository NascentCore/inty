import boto3
from botocore.client import Config
import os

# Your HMAC keys for Google Cloud Storage
# It's a best practice to use environment variables or a secure vault
# to store your credentials, rather than hardcoding them.
GOOGLE_ACCESS_KEY_ID = "YOUR_GOOGLE_ACCESS_KEY_ID"
GOOGLE_SECRET_ACCESS_KEY = "YOUR_GOOGLE_SECRET_ACCESS_KEY"

# The name of your Google Cloud Storage bucket
BUCKET_NAME = "yx-test"

# The endpoint URL for Google Cloud Storage's S3-compatible API
GCS_ENDPOINT_URL = "https://storage.googleapis.com"

# --- Set up the boto3 client ---

# Note: Google Cloud Storage's S3 compatibility layer has some nuances.
# The 's3v4' signature version is required.
# 'endpoint_url' is critical to point boto3 to GCS instead of AWS S3.
s3_client = boto3.client(
    "s3",
    aws_access_key_id=GOOGLE_ACCESS_KEY_ID,
    aws_secret_access_key=GOOGLE_SECRET_ACCESS_KEY,
    endpoint_url=GCS_ENDPOINT_URL,
    config=Config(signature_version="s3v4"),
)

# --- Define a local file and its destination in the bucket ---
local_file_path = "req.json"
object_key = "req.json"
downloaded_file_path = "downloaded_req.json"

# Create a dummy file to upload
with open(local_file_path, "w") as f:
    f.write("This is a test file for Google Cloud Storage using boto3!")

try:
    # --- Upload a file to the bucket ---
    print(f"Uploading {local_file_path} to {BUCKET_NAME}/{object_key}...")
    s3_client.upload_file(local_file_path, BUCKET_NAME, object_key)
    print("Upload successful!")

    # --- List objects in the bucket ---
    print("\nListing objects in the bucket:")
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
    for obj in response.get("Contents", []):
        print(f" - {obj['Key']}")

    # --- Download the file from the bucket ---
    print(f"\nDownloading {object_key} from {BUCKET_NAME}...")
    s3_client.download_file(BUCKET_NAME, object_key, downloaded_file_path)
    print("Download successful!")

    # Verify the downloaded file content
    with open(downloaded_file_path, "r") as f:
        print(f"Content of downloaded file: '{f.read()}'")

finally:
    # --- Clean up the local files ---
    os.remove(local_file_path)
    if os.path.exists(downloaded_file_path):
        os.remove(downloaded_file_path)

    # Note: You can also delete the object from the bucket if you want.
    # s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_key)
