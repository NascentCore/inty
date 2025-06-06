from google.cloud import storage
from app.core.config import settings  # 假设你的配置是settings对象

def upload_to_gcs(file_data, content_type, bucket_name, path):
    client = storage.Client.from_service_account_json(settings.gcs.credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    blob.upload_from_string(file_data, content_type=content_type)
    return blob.public_url

# 新增删除方法
def delete_from_gcs(bucket_name, path):
    client = storage.Client.from_service_account_json(settings.gcs.credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    blob.delete() 