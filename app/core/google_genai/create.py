from __future__ import annotations

from google import genai
from google.oauth2 import service_account
from app.core.config import global_config_loaded_from_config_yaml

_VERTEX_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)


def create_genai_client():
    credentials_path = global_config_loaded_from_config_yaml.app.gcp_service_account_key
    location = global_config_loaded_from_config_yaml.agent.vertex_ai_location
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=_VERTEX_SCOPES
    )
    return genai.Client(
        vertexai=True,
        credentials=creds,
        location=location,
    )
