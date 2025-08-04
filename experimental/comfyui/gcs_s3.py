import boto3
from botocore.client import Config
import os
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

load_dotenv()

# Use environment variables for credentials - much more secure
ACCESS_KEY_ID = os.getenv("GCP_YX_TEST_ACCESS_KEY")
ACCESS_SECRET = os.getenv("GCP_YX_TEST_SECRET")

# Validate that credentials are provided
if not ACCESS_KEY_ID or not ACCESS_SECRET:
    raise ValueError(
        "Missing credentials. Please set GOOGLE_ACCESS_KEY_ID and "
        "GOOGLE_SECRET_ACCESS_KEY environment variables."
    )

# The name of your Google Cloud Storage bucket
BUCKET_NAME = "yx-test-2"

# The endpoint URL for Google Cloud Storage's S3-compatible API
GCS_ENDPOINT_URL = "https://storage.googleapis.com"

# --- Set up the boto3 client ---

# Note: Google Cloud Storage's S3 compatibility layer has some nuances.
# The 's3v4' signature version is required.
# 'endpoint_url' is critical to point boto3 to GCS instead of AWS S3.
s3_client = boto3.client(
    "s3",
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=ACCESS_SECRET,
    endpoint_url=GCS_ENDPOINT_URL,
    config=Config(signature_version="s3v4"),
)

# --- Define a local file and its destination in the bucket ---
local_file_path = "req.json"
object_key = "req.json"
downloaded_file_path = "downloaded_req.json"


def upload_file():
    """Upload a file to GCS bucket with error handling"""
    try:
        # Create a dummy file to upload
        with open(local_file_path, "w") as f:
            f.write("This is a test file for Google Cloud Storage using boto3!")

        print(f"Uploading {local_file_path} to {BUCKET_NAME}/{object_key}...")
        s3_client.upload_file(local_file_path, BUCKET_NAME, object_key)
        print("Upload successful!")
        return True
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NoSuchBucket":
            print(f"Error: Bucket '{BUCKET_NAME}' does not exist")
        elif error_code == "AccessDenied":
            print("Error: Access denied. Check your credentials and permissions")
        else:
            print(f"Error uploading file: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during upload: {e}")
        return False


# Main execution
if __name__ == "__main__":
    upload_file()
