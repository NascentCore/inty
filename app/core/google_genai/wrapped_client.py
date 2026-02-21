"""
Limitations of the official LangSmith tracing wrapper for the Google GenAI SDK.

Ref: https://docs.langchain.com/langsmith/trace-with-google-gemini#configure-tracing
Implementation: app.utils.google_genai_client.wrap_google_genai_client_with_langsmith
"""

# -----------------------------------------------------------------------------
# Official wrapper: langsmith.wrappers.wrap_gemini
# -----------------------------------------------------------------------------
#
# 1. Only generate_content and generate_content_stream are traced
#    - client.models.generate_images (Imagen) is NOT wrapped.
#    - Imagen calls produce no LangSmith run; "full model request" is unavailable
#      unless you add your own @traceable or span around generate_images.
#
# 2. "Model requests" (complete prompts) depend on contents being dict-like
#    - wrap_gemini uses process_inputs=_process_gemini_inputs, which builds
#      "messages" only when each item in contents is a dict (isinstance(content, dict)).
#    - When you pass google.genai.types.Content (Pydantic), the branch that builds
#      messages is skipped; the trace gets raw kwargs and the prompt text may not
#      appear in the UI.
#
# 3. Our mitigation (in google_genai_client)
#    - After wrap_gemini(client), we patch client.models.generate_content and
#      generate_content_stream so that contents are normalized to list-of-dict
#      (via model_dump()) before the LangSmith traceable runs. That way
#      _process_gemini_inputs sees dicts and records full prompts.
#
# 4. Config / multimodal
#    - Config is converted with vars(config) for tracing; "complete prompts" in
#      the docs refer mainly to contents/messages, not necessarily full config.
#    - Multimodal contents (e.g. inline_data images) are only normalized when
#      parts are dict-like; Pydantic Part objects may not serialize fully.
#
# See: app/core/google_genai/todos/LangSmith_full_model_requests_investigation.md
#


import types
from google import genai

from app.core.google_genai.predefined_configs import GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR


class AsyncClient:
    def __init__(self, client: genai.aio.Client):
        self.client = client

    def generate_image(self, model: str, reference_jpeg_urls: list[str], prompt: str):
        """
        使用指定的模型生成图片。
        这个符合消息生图的设计。
        """
        parts = []
        for reference_jpeg_url in reference_jpeg_urls:
            reference_image = types.Part.from_uri(
                file_uri=reference_jpeg_url,
                mime_type="image/jpeg",
            )
            parts.append(reference_image)

        parts.append(types.Part.from_text(text=prompt))
        return self.client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=parts,
                )
            ],
            config=GEN_CONTENT_CONFIG_IMAGE_9_16_1K_R_RATED_ROMANCE_DIRECTOR,
        )
