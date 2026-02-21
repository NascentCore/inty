from __future__ import annotations

import os
from google import genai
from app.core.config import global_config_loaded_from_config_yaml

def create_genai_client():
    credentials_path = (
        global_config_loaded_from_config_yaml.app.gcp_service_account_key
    )
    # 这是必须的，否则 genai.Client() 会报错
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    location = global_config_loaded_from_config_yaml.agent.vertex_ai_location

    return genai.Client(
        vertexai=True,
        # 密钥 json 文件已经包含了 project_id，所以这里不需要再传入
        # project=,
        location=location,
    )
