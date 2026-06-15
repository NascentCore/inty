"""
模型目录

对各类模型进行管理和综合分析；任何新进模型都需要在这里定义。
这些模型与常见的 Model Cards 对应。

OpenRouter 模型排行榜（roleplay / agentic benchmark）：
https://openrouter.ai/rankings?category=roleplay&benchmark=agentic#categories
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DataModality(StrEnum):
    """
    模型模态，比如文本、图像、音频、视频等。
    """

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class ModelModalities(BaseModel):
    """
    模型输入输出的模态组合，用于描述模型支持的输入和输出模态。
    """

    inputs: list[DataModality] = Field(description="""
        模型输入的模态列表，比如文本、图像、音频、视频等。
        列表中的模态可以互斥，也可以不互斥，比如文本和图像可以同时输入。""")
    outputs: list[DataModality] = Field(description="""
        模型输出的模态列表，比如文本、图像、音频、视频等。
        列表中的模态可以互斥，也可以不互斥，比如文本和图像可以同时输出。""")

    notes: str = Field(description="模型价格的一些备注信息", default="")


class ModelBuilder(StrEnum):
    """
    模型构建者，目前只提供 Google 一个选项，因为只使用 Google 家的模型。
    """

    GOOGLE = "google"
    BYTE_DANCE = "bytedance"
    OPENAI = "openai"
    ELEVENLABS = "11labs"
    ALIBABA_TONGYI = "alibaba_tongyi"
    DEEPSEEK = "deepseek"
    XIAOMI = "xiaomi"


class PricingModel(StrEnum):
    """
    模型价格类型，比如按 token 计费、按图片计费、按视频计费等。
    """

    # 1M token 的价格，1M token 是个流行选项
    BY_1M_TOKEN = "by_1m_token"

    # 按使用次数计费，比如图片生成次数、视频生成次数等
    BY_USE = "by_use"


class PriceInfo(BaseModel):
    """
    模型价格，用于计算用量和成本。
    """

    price: float = Field(description="模型价格，都是美元计价。")
    model: PricingModel = Field(
        description="模型价格类型，比如按 token 计费、按使用次数计费等。"
    )
    modality: DataModality = Field(
        description="本价格使用的模态，比如文本、图像、音频、视频等。有时候同一个模型，不同的模态价格不同。"
    )


class Pricing(BaseModel):
    """
    模型价格，用于计算用量和成本。
    """

    inputs: list[PriceInfo] = Field(
        description="模型输入价格信息列表，用于计算用量和成本。"
    )
    outputs: list[PriceInfo] = Field(
        description="模型输出价格信息列表，用于计算用量和成本。"
    )
    official_url: str = Field(
        default="",
        description="""
        模型 API 提供者的官方定价页面 URL，比如 fal.ai 的定价页面。
        """,
    )
    notes: str = Field(description="模型价格的一些备注信息", default="")


class ModelAPIProvider(StrEnum):
    """
    模型 API 提供者。
    氛围官方 API 提供者和第三方 API 聚合器，聚合器都以 _AGGREGATOR 结尾。
    """

    # OpenRouter 是模型 API 聚合器，以文本模型为主，并不运行模型。
    # API 聚合服务商，不运行模型，只是将多个 API 聚合在一起，提供一个统一的 API 接口。
    OPENROUTER = "openrouter"
    # fal.ai 专注多模态模型推理服务，运行模型，推理服务。
    # 曾经测试 fal.ai 的推理服务，发现审核比官方更严格，比如 z-image，因此没有继续使用。
    FALAI = "falai"
    # Google 还有其他的 API 服务比如 AI Studio，所以明确指出。
    GOOGLE_VERTEX_AI = "google"
    # NewAPI 等网关上的 Gemini Developer API（/v1beta/models/...），非 Vertex 路径。
    NEWAPI_GEMINI = "newapi_gemini"

    # 本地部署的 litellm 端点；这是用于对接第三方代金券提供者的本地部署大模型网关。
    # 部署于与后端服务器同一台虚机上，可以对接第三方代金券所有者提供的 service account
    # 或其他的 API 凭证。可以访问各类模型，实际支付成本远低于官方报价。
    #
    # 这里使用的 API input & output schema 仍然是兼容 openai（还包括兼容 Claude 等等）
    # 但是其 API base URL 需要修改。
    LOCAL_LITELLM = "local_litellm"


class ModelAPIBaseURL(StrEnum):
    """
    模型 API base URL。
    """

    OPENROUTER = "https://openrouter.ai/api/v1"
    LOCAL_LITELLM = "http://10.128.0.5:4000/v1"


# OpenRouter public rankings: roleplay category, agentic benchmark (same host as ModelAPIBaseURL.OPENROUTER).
OPENROUTER_RANKINGS_AGENTIC_ROLEPLAY_URL = "https://openrouter.ai/rankings?category=roleplay&benchmark=agentic#categories"


class ResponseFormatWithToolsCompatibility(StrEnum):
    """
    OpenAI 兼容 chat.completions 单次请求中：结构化响应格式（response_format json_schema 等）
    与 tools 列表并存时的兼容性登记（与「函数 strict」单独开启不同）。
    """

    UNSPECIFIED = "unspecified"
    INCOMPATIBLE = "incompatible"


class GenAIModel(BaseModel):
    """
    用于准确指代一个 AI 模型，包括模型构建者、模型名称。
    在 Inty 代码中，本对象实例唯一确定了一个模型，背后采用哪个 API 提供者，
    是由底层代码决定的。
    为了方便和简化命名规则，我们这里只考虑模型构建者、模型名称，不考虑 API 提供者。
    """

    nickname: str = Field(description="""
        用于给非后端团队提供的名称，方便沟通和理解。
        计划在 app/utils/config.py 中使用这些名字来指代模型。

        这个名字可以包含空格，比如 "Nano Banana"。

        模型简称，用于全团队沟通的一般性名字；有多种情况，比如业界的统称：Nano Banana。
        指的是 Gemini 2.5 Flash Image。
        而有些模型没有业界统称，像 Imagen 4.0 Ultra 等等。
        但最终在使用时的名字要根据后台实际使用的 API 提供者来确定，比如 openrouter 上需要增加
        模型构建者名字；而 Google 内部对 geminie imagen 模型的称呼则各有不同""")

    modalities: ModelModalities = Field(description="""
        模型输入输出的模态组合，用于描述模型支持的输入和输出模态。""")

    builder: ModelBuilder = Field(description="""
        模型构建者，比如 Google，这个用于在代码中确定某个模型在第三方平台上的使用时的名字。
        这个名称需要与第三方平台上的模型名称一致。比如 Google 的模型名称是 gemini-2.5-flash，
        那么在该平台上名字是 google/gemini-2.5-flash。""")

    provider: ModelAPIProvider = Field(description="""
        模型 API 提供者，比如 OpenRouter，这个用于在代码中确定某个模型在第三方平台上的使用时的名字。
        这个名称需要与第三方平台上的模型名称一致。比如 Google 的模型名称是 gemini-2.5-flash，
        那么在该平台上名字是 google/gemini-2.5-flash。""")

    id_on_provider: str = Field(description="""
        模型 ID，用于在代码中唯一标识一个模型。
        这个 ID 需要与第三方平台上的模型名称一致。比如 Google 的模型名称是 gemini-2.5-flash，
        那么在该平台上名字是 google/gemini-2.5-flash。

        现阶段，不区分 Provider，只隐含在代码中的对应 API 上使用合适的名字。
        这个 ID 只用于后端代码使用""")

    pricing: Pricing = Field(description="模型价格，用于计算用量和成本。")

    official_url: str = Field(
        default="",
        description="""
        模型 API 提供者的官方 URL，多为 Hugging Face 或 GitHub 地址。
        """,
    )

    notes: str = Field(
        description="""
        模型的一些备注信息，比如模型的使用技巧和功能限制、注意事项等。""",
        default="",
    )

    response_format_with_tools_compatibility: (
        ResponseFormatWithToolsCompatibility
    ) = Field(
        default=ResponseFormatWithToolsCompatibility.UNSPECIFIED,
        description="""
        同一请求内同时使用 response_format（如 json_schema）与 tools 时是否可行；
        UNSPECIFIED 表示未核实；INCOMPATIBLE 表示已知供应商或网关互斥或会导致无法 tool call。""",
    )

    context_window_tokens: int = Field(
        default=0,
        description="""
        供应商标称的上下文窗口上限（tokens），用于与 API usage 中的 prompt_tokens 等对比。
        口径以对该条目负责的 provider 官方文档为准（通常为总上下文或文档声明的 max context）。
        0 表示无适用的 token 级窗口（例如仅按次计费且无统一 context 的生图/视频管线），不计算利用率。
        对未编入本目录、仅通过 OpenRouter 等裸 id 接入的模型，默认亦为 0，直至在目录中写明官方窗口。
        """,
    )


DEEPSEEK_V3_2 = GenAIModel(
    nickname="DeepSeek V3.2",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.DEEPSEEK,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="deepseek/deepseek-v3.2",
    context_window_tokens=163_840,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.25,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.40,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://openrouter.ai/deepseek/deepseek-v3.2",
    ),
    official_url="https://huggingface.co/deepseek-ai/DeepSeek-V3.2",
    notes="163,840 context window. Supports reasoning via `reasoning.enabled` parameter.",
    response_format_with_tools_compatibility=(
        ResponseFormatWithToolsCompatibility.INCOMPATIBLE
    ),
)


DEEPSEEK_V4_PRO = GenAIModel(
    nickname="DeepSeek V4 Pro",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.DEEPSEEK,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="deepseek/deepseek-v4-pro",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.435,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.87,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://openrouter.ai/deepseek/deepseek-v4-pro",
    ),
    official_url="https://openrouter.ai/deepseek/deepseek-v4-pro",
    notes="1,048,576 context window. Supports reasoning via `reasoning` parameter.",
    response_format_with_tools_compatibility=(
        ResponseFormatWithToolsCompatibility.INCOMPATIBLE
    ),
)


DEEPSEEK_V4_FLASH = GenAIModel(
    nickname="DeepSeek V4 Flash",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.DEEPSEEK,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="deepseek/deepseek-v4-flash",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.14,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.28,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://openrouter.ai/deepseek/deepseek-v4-flash",
    ),
    official_url="https://openrouter.ai/deepseek/deepseek-v4-flash",
    notes="1,048,576 context window. Supports reasoning via `reasoning` parameter.",
    response_format_with_tools_compatibility=(
        ResponseFormatWithToolsCompatibility.INCOMPATIBLE
    ),
)


MIMO_V2_5 = GenAIModel(
    nickname="MiMo V2.5",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.XIAOMI,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="xiaomi/mimo-v2.5",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.14,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.28,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://openrouter.ai/xiaomi/mimo-v2.5",
    ),
    official_url="https://openrouter.ai/xiaomi/mimo-v2.5",
    notes="1,048,576 context window. Omnimodal model; agentic / tool-use oriented.",
)


GEMINI_2_5_FLASH_LITE = GenAIModel(
    nickname="Gemini 2.5 Flash Lite",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="google/gemini-2.5-flash-lite",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.1,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
            PriceInfo(
                price=0.3,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.AUDIO,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.4,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            )
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-2.5-flash-image&project=alien-paratext-461204-i9",
)


GEMINI_2_5_FLASH = GenAIModel(
    nickname="Gemini 2.5 Flash",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="google/gemini-2.5-flash",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.30,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
            PriceInfo(
                price=1.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.AUDIO,
            ),
        ],
        outputs=[
            PriceInfo(
                price=2.50,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
            PriceInfo(
                price=30.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.IMAGE,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-2.5-flash-image&project=alien-paratext-461204-i9",
)


GEMINI_3_5_FLASH = GenAIModel(
    nickname="Gemini 3.5 Flash",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="google/gemini-3.5-flash",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=1.50,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=9.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-3",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-3.5-flash&project=alien-paratext-461204-i9",
    notes="GA Flash model (2026-05); supports thinking, tools, structured outputs, 1M context.",
)


NANO_BANANA = GenAIModel(
    nickname="Nano Banana",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.IMAGE],
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-2.5-flash-image",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.30,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            )
        ],
        outputs=[
            PriceInfo(
                price=30.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.IMAGE,
            )
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-2.5-flash-image&project=alien-paratext-461204-i9",
)


NANO_BANANA_PRO = GenAIModel(
    nickname="Nano Banana Pro",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.IMAGE],
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-3-pro-image-preview",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=2.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            )
        ],
        outputs=[
            PriceInfo(
                price=12.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
            PriceInfo(
                price=120.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.IMAGE,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-3",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-2.5-flash-image&project=alien-paratext-461204-i9",
    notes="最多支持 14 张参考图片。",
)


NANO_BANANA_2 = GenAIModel(
    nickname="Nano Banana 2",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.TEXT, DataModality.IMAGE],
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-3.1-flash-image-preview",
    context_window_tokens=200_000,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.5,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
            PriceInfo(
                price=0.5,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.IMAGE,
            ),
        ],
        outputs=[
            PriceInfo(
                price=3.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
            PriceInfo(
                price=60.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.IMAGE,
            ),
        ],
        official_url="https://blog.google/innovation-and-ai/technology/ai/nano-banana-2/",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal;mode=prompt?model=gemini-3.1-flash-image-preview&project=alien-paratext-461204-i9",
    notes="<= 200k input tokens, <= 14 reference images.",
)


NEWAPI_NANO_BANANA_2 = GenAIModel(
    nickname="NewAPI Nano Banana 2",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.IMAGE],
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.NEWAPI_GEMINI,
    id_on_provider="google/gemini-3-pro-image-preview",
    context_window_tokens=1_048_576,
    pricing=NANO_BANANA_PRO.pricing,
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-2.5-flash-image&project=alien-paratext-461204-i9",
    notes="经 NewAPI Gemini 端点；需配置 agent.newapi_gemini_base_url 与 Bearer。",
)

# Vertex AI–only Gemini text/multimodal models (used by tools/verify_gcp_service_account_json_on_genai.py).
VERTEX_GEMINI_2_5_FLASH_LITE = GenAIModel(
    nickname="Gemini 2.5 Flash Lite (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-2.5-flash-lite",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.1,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.4,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            )
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-lite",
)

VERTEX_GEMINI_2_5_FLASH = GenAIModel(
    nickname="Gemini 2.5 Flash (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-2.5-flash",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.30,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=2.50,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash",
)

VERTEX_GEMINI_2_5_PRO = GenAIModel(
    nickname="Gemini 2.5 Pro (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-2.5-pro",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=1.25,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=10.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-pro",
)

VERTEX_GEMINI_2_0_FLASH = GenAIModel(
    nickname="Gemini 2.0 Flash (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-2.0-flash-001",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.10,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.40,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-0-flash",
)

VERTEX_GEMINI_2_0_FLASH_LITE = GenAIModel(
    nickname="Gemini 2.0 Flash Lite (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-2.0-flash-lite-001",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.075,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.30,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-0-flash-lite",
)

VERTEX_GEMINI_3_1_FLASH_LITE_PREVIEW = GenAIModel(
    nickname="Gemini 3.1 Flash Lite Preview (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-3.1-flash-lite-preview",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.15,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.60,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-1-flash-lite",
)

VERTEX_GEMINI_3_1_PRO_PREVIEW = GenAIModel(
    nickname="Gemini 3.1 Pro Preview (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-3.1-pro-preview",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=1.25,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=10.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-1-pro",
)

VERTEX_GEMINI_3_FLASH_PREVIEW = GenAIModel(
    nickname="Gemini 3 Flash Preview (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-3-flash-preview",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.35,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=1.05,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash",
)

VERTEX_GEMINI_3_PRO_PREVIEW = GenAIModel(
    nickname="Gemini 3 Pro Preview (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-3-pro-preview",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=1.25,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=10.0,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro",
)

VERTEX_GEMINI_2_5_FLASH_LITE_PREVIEW_09_2025 = GenAIModel(
    nickname="Gemini 2.5 Flash Lite Preview 09-2025 (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-2.5-flash-lite-preview-09-2025",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[
            PriceInfo(
                price=0.1,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            ),
        ],
        outputs=[
            PriceInfo(
                price=0.4,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.TEXT,
            )
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-lite",
)

VERTEX_GEMINI_LIVE_2_5_FLASH_NATIVE_AUDIO = GenAIModel(
    nickname="Gemini Live 2.5 Flash Native Audio (Vertex)",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.AUDIO],
        outputs=[DataModality.TEXT, DataModality.AUDIO],
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-live-2.5-flash-native-audio",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[],
        outputs=[],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing",
    ),
    official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-live-api",
    notes="Live API only; generate_content not supported. Skipped in verify script.",
)

# All Gemini models in this catalog (id_on_provider contains "gemini"). Used by tools/verify_gcp_service_account_json_on_genai.py.
ALL_GEMINI_MODELS = (
    GEMINI_2_5_FLASH_LITE,
    GEMINI_2_5_FLASH,
    GEMINI_3_5_FLASH,
    NANO_BANANA,
    NANO_BANANA_PRO,
    NANO_BANANA_2,
    VERTEX_GEMINI_2_5_FLASH_LITE,
    VERTEX_GEMINI_2_5_FLASH,
    VERTEX_GEMINI_2_5_PRO,
    VERTEX_GEMINI_2_0_FLASH,
    VERTEX_GEMINI_2_0_FLASH_LITE,
    VERTEX_GEMINI_3_1_FLASH_LITE_PREVIEW,
    VERTEX_GEMINI_3_1_PRO_PREVIEW,
    VERTEX_GEMINI_3_FLASH_PREVIEW,
    VERTEX_GEMINI_3_PRO_PREVIEW,
    VERTEX_GEMINI_2_5_FLASH_LITE_PREVIEW_09_2025,
    VERTEX_GEMINI_LIVE_2_5_FLASH_NATIVE_AUDIO,
)


IMAGEN_4_FAST = GenAIModel(
    nickname="Imagen 4.0 Fast",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.IMAGE],
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="imagen-4.0-fast-generate-001",
    context_window_tokens=0,
    pricing=Pricing(
        inputs=[],
        outputs=[
            PriceInfo(
                price=0.02,
                model=PricingModel.BY_USE,
                modality=DataModality.IMAGE,
            )
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#imagen-models",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=imagen-4.0-fast-generate-001&project=alien-paratext-461204-i9",
)


IMAGEN_4 = GenAIModel(
    nickname="Imagen 4.0",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.IMAGE],
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="imagen-4.0-generate-001",
    context_window_tokens=0,
    pricing=Pricing(
        inputs=[],
        outputs=[
            PriceInfo(
                price=0.04,
                model=PricingModel.BY_USE,
                modality=DataModality.IMAGE,
            )
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#imagen-models",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=imagen-4.0-generate-001&project=alien-paratext-461204-i9",
)


VEO_3_1_FAST = GenAIModel(
    nickname="Veo3.1 Fast",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.VIDEO],
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="veo-3.1-fast-generate-001",
    context_window_tokens=0,
    pricing=Pricing(
        inputs=[],
        outputs=[
            PriceInfo(
                price=0.15,
                model=PricingModel.BY_USE,
                modality=DataModality.VIDEO,
            )
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#veo",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/media/video?project=alien-paratext-461204-i9",
)

VEO_3_1 = GenAIModel(
    nickname="Veo3.1",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.VIDEO],
    ),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="veo-3.1-generate-001",
    context_window_tokens=0,
    pricing=Pricing(
        inputs=[],
        outputs=[
            PriceInfo(
                price=0.40,
                model=PricingModel.BY_USE,
                modality=DataModality.VIDEO,
            )
        ],
        official_url="https://cloud.google.com/vertex-ai/generative-ai/pricing#veo",
    ),
    playground_url="https://console.cloud.google.com/vertex-ai/studio/media/video?project=alien-paratext-461204-i9",
)

SEEDREAM_V4_5_EDIT = GenAIModel(
    nickname="Seedream V4.5 Edit",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.IMAGE],
    ),
    builder=ModelBuilder.BYTE_DANCE,
    # TODO：Openrouter 没有 edit 版本似乎，需要调研
    # Ref: https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit/api?platform=python
    provider=ModelAPIProvider.FALAI,
    id_on_provider="fal-ai/bytedance/seedream/v4.5/edit",
    context_window_tokens=0,
    pricing=Pricing(
        inputs=[],
        outputs=[
            PriceInfo(
                price=0.04,
                model=PricingModel.BY_USE,
                modality=DataModality.IMAGE,
            )
        ],
        notes="没有专门针对模型的价格列表，通过 playground 测试后观察实际 cost",
    ),
    playground_url="https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit",
)

GPT_IMAGE_1_5 = GenAIModel(
    nickname="GPT Image 1.5",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.TEXT, DataModality.IMAGE],
    ),
    builder=ModelBuilder.OPENAI,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="openai/gpt-image-1.5/edit",
    context_window_tokens=1_048_576,
    pricing=Pricing(
        inputs=[],
        outputs=[
            PriceInfo(
                price=0.01,
                model=PricingModel.BY_1M_TOKEN,
                modality=DataModality.IMAGE,
            )
        ],
        notes="""测试中，fal.ai 4k 输出，80 张话费 $6.59，合 $0.082375/图片
        原生 openai api platform 0.04/图片
        """,
    ),
    notes="价格列表：https://fal.ai/models/fal-ai/gpt-image-1.5/edit",
    playground_url="https://platform.openai.com/playground/images",
)

Z_IMAGE_TURBO = GenAIModel(
    nickname="Z Image Turbo",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT], outputs=[DataModality.IMAGE]
    ),
    builder=ModelBuilder.ALIBABA_TONGYI,
    provider=ModelAPIProvider.FALAI,
    id_on_provider="fal-ai/z-image/turbo",
    context_window_tokens=0,
    official_url="https://github.com/Tongyi-MAI/Z-Image",
    pricing=Pricing(
        inputs=[],
        outputs=[
            PriceInfo(
                price=0.005,
                model=PricingModel.BY_USE,
                modality=DataModality.IMAGE,
            )
        ],
        notes="没有专门给模型的定价页面，playground 测试后观察实际 cost",
    ),
    playground_url="https://fal.ai/models/fal-ai/z-image/turbo",
)

Z_IMAGE_TURBO_IMAGE_TO_IMAGE = GenAIModel(
    nickname="Z Image Turbo Image to Image",
    modalities=ModelModalities(
        inputs=[DataModality.TEXT, DataModality.IMAGE],
        outputs=[DataModality.IMAGE],
    ),
    builder=ModelBuilder.ALIBABA_TONGYI,
    provider=ModelAPIProvider.FALAI,
    id_on_provider="fal-ai/z-image/turbo/image-to-image",
    context_window_tokens=0,
    official_url="https://github.com/Tongyi-MAI/Z-Image",
    pricing=Pricing(
        inputs=[],
        outputs=[
            PriceInfo(
                price=0.01,
                model=PricingModel.BY_USE,
                modality=DataModality.IMAGE,
            )
        ],
        notes="没有专门给模型的定价页面，playground 测试后观察实际 cost",
    ),
    playground_url="https://fal.ai/models/fal-ai/z-image/turbo/image-to-image/playground",
)

# Follow-up (context utilization): ``GenAIModel.context_window_tokens`` is not wired here.
# Intentionally leave ``chat_completions.py`` / ``runtime_inspect_context.py`` unchanged in this PR
# (see PR review); future work: merge ``response.usage`` + catalog window in those harness paths.
# Other anchors: ``app/core/agent/agent.py`` (LangSmith usage), ``tests/app/utils/test_models_catalog.py``.

# Chat image (message-to-image): only these models are allowed; config uses nickname.
CHAT_IMAGE_GEN_MODELS = [
    NANO_BANANA,
    NANO_BANANA_2,
    NANO_BANANA_PRO,
    NEWAPI_NANO_BANANA_2,
    SEEDREAM_V4_5_EDIT,
    Z_IMAGE_TURBO_IMAGE_TO_IMAGE,
]

NANO_BANANA_MODELS = [
    NANO_BANANA,
    NANO_BANANA_2,
    NANO_BANANA_PRO,
    NEWAPI_NANO_BANANA_2,
]
Z_IMAGE_TURBO_MODELS = [Z_IMAGE_TURBO, Z_IMAGE_TURBO_IMAGE_TO_IMAGE]

# Subset of CHAT_IMAGE_GEN_MODELS that use fal (app/core/images/fal.py). Used by unified chat image routing.
CHAT_IMAGE_FAL_MODELS = [SEEDREAM_V4_5_EDIT, Z_IMAGE_TURBO_IMAGE_TO_IMAGE]
CHAT_IMAGE_FAL_IDS = tuple(m.id_on_provider for m in CHAT_IMAGE_FAL_MODELS)

# TODO(companion-multimodal-user-turn): Phase 1a — add ``chat_model_accepts_image_input(model)``
# https://github.com/NascentCore/inty/issues/3293
# (``DataModality.IMAGE in model.modalities.inputs``); fix vision-capable ``CHAT_TEXT_MODELS``
# entries (e.g. GEMINI_2_5_FLASH*) to declare IMAGE input. Gate multimodal user turns on
# ``select_chat_model()`` result, not a separate vision/caption model.
# Chat text (LLM) models: config may use nickname or id_on_provider; resolve to id before API call.
CHAT_TEXT_MODELS = [
    DEEPSEEK_V3_2,
    DEEPSEEK_V4_PRO,
    DEEPSEEK_V4_FLASH,
    MIMO_V2_5,
    GEMINI_2_5_FLASH_LITE,
    GEMINI_2_5_FLASH,
    GEMINI_3_5_FLASH,
]


def openrouter_chat_model_from_id_uncatalogued(
    id_on_provider: str,
) -> GenAIModel:
    """
    Build a minimal catalog entry for OpenRouter chat model IDs not listed in ``CHAT_TEXT_MODELS``.

    ``id_on_provider`` is used verbatim (after strip) for API calls. Pricing is a placeholder and
    must not be used for billing without extending the catalog.
    """

    trimmed = id_on_provider.strip()
    return GenAIModel(
        nickname=trimmed,
        modalities=ModelModalities(
            inputs=[DataModality.TEXT], outputs=[DataModality.TEXT]
        ),
        builder=ModelBuilder.OPENAI,
        provider=ModelAPIProvider.OPENROUTER,
        id_on_provider=trimmed,
        pricing=Pricing(
            inputs=[
                PriceInfo(
                    price=0.0,
                    model=PricingModel.BY_1M_TOKEN,
                    modality=DataModality.TEXT,
                )
            ],
            outputs=[
                PriceInfo(
                    price=0.0,
                    model=PricingModel.BY_1M_TOKEN,
                    modality=DataModality.TEXT,
                )
            ],
            official_url="",
            notes="Placeholder; uncatalogued OpenRouter chat model.",
        ),
        notes="uncatalogued OpenRouter chat model; extend CHAT_TEXT_MODELS for full metadata.",
        response_format_with_tools_compatibility=(
            ResponseFormatWithToolsCompatibility.UNSPECIFIED
        ),
    )


def resolve_chat_text_model(value: str) -> GenAIModel:
    """
    Resolve YAML/config chat model string (nickname or ``id_on_provider``) to ``GenAIModel``.

    Matches ``CHAT_TEXT_MODELS`` first; otherwise wraps the trimmed string as an uncatalogued
    OpenRouter model (same API id as the config value). Empty/whitespace input yields
    ``DEEPSEEK_V3_2`` (harness default chat model).
    """

    normalized = (value or "").strip()
    if not normalized:
        return DEEPSEEK_V3_2
    for model in CHAT_TEXT_MODELS:
        if model.nickname == normalized or model.id_on_provider == normalized:
            return model
    return openrouter_chat_model_from_id_uncatalogued(normalized)


def resolve_chat_model_to_id(value: str) -> str:
    """
    Resolve chat model config (nickname or id_on_provider) to provider model ID.
    If value matches a CHAT_TEXT_MODELS nickname or id_on_provider, returns that model's id_on_provider.
    Otherwise returns value unchanged (e.g. custom OpenRouter IDs like z-ai/glm-4.5-air:free).
    """
    normalized = value.strip() if value else ""
    if not normalized:
        return value
    return resolve_chat_text_model(value).id_on_provider


def genai_model_langsmith_meta_subset(model: GenAIModel) -> dict[str, Any]:
    """JSON-safe catalog subset for LangSmith / inspect (excludes pricing trees)."""

    return {
        "nickname": model.nickname,
        "id_on_provider": model.id_on_provider,
        "builder": model.builder.value,
        "provider": model.provider.value,
        "response_format_with_tools_compatibility": (
            model.response_format_with_tools_compatibility.value
        ),
    }


class ModelNameFamily(StrEnum):
    """
    模型名字族，用于做路由判断。
    这里只区分 fal、gemini 与其他模型。
    """

    FAL = "fal"
    GEMINI = "gemini"
    OTHER = "other"


def resolve_nickname(nickname: str) -> GenAIModel | None:
    """
    Resolve GenAIModel by exact nickname match among CHAT_IMAGE_GEN_MODELS.
    Callers use model.id_on_provider when they need the provider ID.
    """
    for model in CHAT_IMAGE_GEN_MODELS:
        if model.nickname == nickname:
            return model
    return None


def must_resolve_nickname(nickname: str) -> GenAIModel:
    """
    Resolve GenAIModel by exact nickname match among CHAT_IMAGE_GEN_MODELS.
    Callers use model.id_on_provider when they need the provider ID.
    """
    model = resolve_nickname(nickname)
    if not model:
        allowed_nicknames = [m.nickname for m in CHAT_IMAGE_GEN_MODELS]
        raise ValueError(
            f"Chat image model nickname {nickname!r} not allowed; allowed: {allowed_nicknames}"
        )
    return model


def resolve_id_on_provider(id_on_provider: str) -> GenAIModel | None:
    """
    Resolve GenAIModel by exact id_on_provider match among CHAT_IMAGE_GEN_MODELS.
    Callers use model.id_on_provider when they need the provider ID.
    """
    for model in CHAT_IMAGE_GEN_MODELS:
        if model.id_on_provider == id_on_provider:
            return model
    return None


def normalize_model_name(model: str) -> str:
    """
    规范化模型名用于检测：
    - trim + lower
    - fal/<id> 归一化为 fal-ai/<id>
    """
    if not model:
        return ""
    normalized = model.strip().lower()
    if normalized.startswith("fal/"):
        suffix = normalized.removeprefix("fal/").strip()
        return f"fal-ai/{suffix}" if suffix else "fal-ai/"
    return normalized


def detect_model_name_family(model: str) -> ModelNameFamily:
    """
    将模型名识别为 fal / gemini / other。
    支持 provider id、chat image nickname，以及常见前缀规则。
    """
    normalized = normalize_model_name(model)
    if not normalized:
        return ModelNameFamily.OTHER

    # 先尝试从 chat image catalog 精确识别（id / nickname）
    catalog_model = resolve_id_on_provider(normalized)
    if not catalog_model:
        catalog_model = resolve_nickname(model.strip())
    if catalog_model:
        if catalog_model.provider == ModelAPIProvider.FALAI:
            return ModelNameFamily.FAL
        if (
            catalog_model.builder == ModelBuilder.GOOGLE
            and "gemini" in catalog_model.id_on_provider.lower()
        ):
            return ModelNameFamily.GEMINI

    # 兜底规则：catalog 外模型也能识别
    if normalized.startswith("fal-ai/"):
        return ModelNameFamily.FAL
    if normalized.startswith("gemini-") or normalized.startswith(
        "google/gemini-"
    ):
        return ModelNameFamily.GEMINI
    return ModelNameFamily.OTHER


def is_fal_model(model: str) -> bool:
    """
    Check if a model is a fal model.
    """
    return detect_model_name_family(model) == ModelNameFamily.FAL


def is_gemini_model(model: str | GenAIModel) -> bool:
    """
    Check if a model is a gemini model.
    """
    sid = model.id_on_provider if isinstance(model, GenAIModel) else model
    return detect_model_name_family(sid) == ModelNameFamily.GEMINI


def is_deepseek_on_openrouter(model: str | GenAIModel) -> bool:
    """
    Check if a model is a DeepSeek model on OpenRouter (id starts with "deepseek/").
    """
    sid = model.id_on_provider if isinstance(model, GenAIModel) else model
    return normalize_model_name(sid).startswith("deepseek/")
