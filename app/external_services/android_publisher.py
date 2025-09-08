"""
Android publisher service to access Google Play Developer API.
https://developers.google.com/android-publisher/api-ref/rest
"""

import os
from typing import Union
import json
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import Resource, build

from loguru import logger


ANDROID_PUBLISHER_SCOPE = "https://www.googleapis.com/auth/androidpublisher"
ANDROID_PUBLISHER_SERVICE_NAME = "androidpublisher"
ANDROID_PUBLISHER_SERVICE_VERSION = "v3"


def create_android_publisher_service(service_account_key: Union[str, os.PathLike]) -> Resource:
    """
    Return an Android publisher service.
    """
    if service_account_key.endswith(".json"):
        key_path = Path(service_account_key)
        if not key_path.exists():
            logger.error("Android publisher service account key file not found")
            raise FileNotFoundError(
                f"Android publisher service account key file not found: {service_account_key}"
            )

        with open(key_path, "r") as f:
            service_account_info = json.load(f)
    else:
        service_account_info = json.loads(service_account_key)

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=[ANDROID_PUBLISHER_SCOPE],
    )

    return build(ANDROID_PUBLISHER_SERVICE_NAME, ANDROID_PUBLISHER_SERVICE_VERSION, credentials=credentials)