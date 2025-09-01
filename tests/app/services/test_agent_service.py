import io
from PIL import Image
from google.cloud import storage
from loguru import logger
from app.core.config import global_config_loaded_from_config_yaml
from app.services.agent_service import _crop_avatar_from_background
from app.utils.gcs import download_from_gcs, get_bucket_and_path_from_gcs_url


async def test_crop_avatar_from_background():
    bucket_name, path = get_bucket_and_path_from_gcs_url(
        "https://storage.googleapis.com/yx-test/Screenshot_20250815_213911-cropped-avatar.png")
    bucket = storage.Client.from_service_account_json(
        global_config_loaded_from_config_yaml.gcs.credentials
    ).bucket(bucket_name)
    try:
        bucket.blob(path).delete()
    except Exception:
        pass

    assert not bucket.blob(path).exists()

    cropped_avatar_url = await _crop_avatar_from_background(
        "https://storage.cloud.google.com/yx-test/Screenshot_20250815_213911.png",
    )
    assert cropped_avatar_url == "https://storage.googleapis.com/yx-test/Screenshot_20250815_213911-cropped-avatar.png"
    logger.info(f"Cropped avatar URL: {cropped_avatar_url}")
    jpe_data = download_from_gcs(cropped_avatar_url)
    image = Image.open(io.BytesIO(jpe_data))
    image.show()