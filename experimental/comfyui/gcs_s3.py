import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()
#您的 Google Cloud Storage 存储桶的名称
BUCKET_NAME = "yx-test-3"
# Google Cloud Storage 的 S3 兼容端点 URL API
GCS_ENDPOINT_URL = "https://yx-test-3.storage.googleapis.com"
# --- 设置 boto3 客户端 ---
#注意：Google Cloud Storage 的 S3 兼容层存在一些较小的差异。
# 需要's3v4'签名版本。
# 'endpoint_url' 用于将 boto3 指向 GCS 而不是 AWS S3 密钥。
s3_client = boto3.client(
    "s3",
# aws_access_key_id=ACCESS_KEY_ID,
# aws_secret_access_key=ACCESS_SECRET,
    endpoint_url=GCS_ENDPOINT_URL,
    config=Config(signature_version="s3v4"),
)
# --- 定义本地文件及其在存储桶中的路径 ---
local_file_path = "req.json"
object_key = "req.json"
downloaded_file_path = "downloaded_req.json"

s3_client.upload_file(local_file_path, BUCKET_NAME, object_key)
