import json
import os
from typing import Dict, Optional

import firebase_admin
from firebase_admin import credentials, exceptions, initialize_app, messaging

from loguru import logger

_ENV_CRED_JSON = "FIREBASE_CREDENTIALS_JSON"
_ENV_CRED_FILE = "GOOGLE_APPLICATION_CREDENTIALS"

_app_initialized = False


def _initialize_from_env() -> Optional[firebase_admin.App]:
    """Initialize Firebase Admin using env credentials.

    Priority:
    1) FIREBASE_CREDENTIALS_JSON (inline JSON)
    2) GOOGLE_APPLICATION_CREDENTIALS (file path)
    3) Default application credentials
    """
    if firebase_admin._apps:  # type: ignore[attr-defined]
        return firebase_admin.get_app()

    inline_json = os.getenv(_ENV_CRED_JSON)
    if inline_json:
        try:
            data = json.loads(inline_json)
            cred = credentials.Certificate(data)
            return initialize_app(cred)
        except json.JSONDecodeError:
            logger.debug("Invalid JSON in FIREBASE_CREDENTIALS_JSON")
        except exceptions.FirebaseError as err:  # type: ignore[attr-defined]
            logger.debug("Firebase init failed from inline JSON: %s", err)

    file_path = os.getenv(_ENV_CRED_FILE)
    if file_path and os.path.exists(file_path):
        try:
            cred = credentials.Certificate(file_path)
            return initialize_app(cred)
        except Exception as err:
            logger.debug("Firebase init failed from file: %s", err)

    try:
        # Fall back to default app credentials
        return initialize_app()
    except Exception as err:
        logger.debug("Firebase init failed using default credentials: %s", err)
        return None


def ensure_firebase_app() -> firebase_admin.App:
    global _app_initialized
    if firebase_admin._apps:  # type: ignore[attr-defined]
        _app_initialized = True
        return firebase_admin.get_app()

    app = _initialize_from_env()
    if app is None:
        raise RuntimeError(
            "Failed to initialize Firebase Admin. Set FIREBASE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS."
        )
    _app_initialized = True
    return app


def send_message_to_token(
    *,
    device_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> str:
    """Send a notification+data FCM message to a device token."""
    ensure_firebase_app()

    notification = messaging.Notification(title=title, body=body)
    message = messaging.Message(
        token=device_token,
        notification=notification,
        data=data or {},
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="server_task_updates"
            ),
        ),
    )
    try:
        message_id = messaging.send(message, dry_run=False)
        logger.debug("FCM send ok: %s", message_id)
        return message_id
    except exceptions.FirebaseError as err:  # type: ignore[attr-defined]
        logger.debug("FCM send failed: %s", err)
        raise


def send_data_only_to_token(*, device_token: str, data: Dict[str, str]) -> str:
    ensure_firebase_app()

    message = messaging.Message(
        token=device_token,
        data=data,
        android=messaging.AndroidConfig(priority="high"),
    )
    try:
        return messaging.send(message, dry_run=False)
    except exceptions.FirebaseError as err:  # type: ignore[attr-defined]
        logger.debug("FCM data-only send failed: %s", err)
        raise
