from __future__ import annotations

import json
from pathlib import Path

import yaml


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config.yaml"
SECRETS_DIR = BASE_DIR / ".secrets"
FIREBASE_CRED_PATH = SECRETS_DIR / "firebase-service-account.json"


def _ensure_minimal_config() -> None:
    if CONFIG_PATH.exists():
        return

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    if not FIREBASE_CRED_PATH.exists():
        FIREBASE_CRED_PATH.write_text(
            json.dumps(
                {
                    "type": "service_account",
                    "project_id": "inty-test",
                    "private_key_id": "test",
                    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIB...test...\n-----END PRIVATE KEY-----\n",
                    "client_email": "inty-test@inty.iam.gserviceaccount.com",
                    "client_id": "1234567890",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/inty-test",
                }
            ),
            encoding="utf-8",
        )

    minimal_cfg = {
        "app": {"debug": True, "backend_cors_origins": [], "environment": "local"},
        "logging": {"level": "DEBUG"},
        "database": {"host": "localhost"},
        "agent": {"api_key": "test", "langchain_api_key": "test"},
        "gcs": {"bucket": "inty-test"},
        "firebase": {"service_account_path": str(FIREBASE_CRED_PATH)},
        "elevenlabs": {"api_key": "test"},
    }
    CONFIG_PATH.write_text(
        yaml.safe_dump(minimal_cfg, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


# Ensure config before any test collection that imports app.*
_ensure_minimal_config()
