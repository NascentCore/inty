"""
模型目录

对各类模型进行管理和综合分析；任何新进模型都需要在这里定义。
这些模型与常见的 Model Cards 对应。
"""


from enum import StrEnum

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
    inputs: set[DataModality] = Field(description="""
        模型输入的模态，比如文本、图像、音频、视频等。
        不是互斥的，仅仅用于常见的分类说明。""")
    outputs: set[DataModality] = Field(description="""
        模型输出的模态，比如文本、图像、音频、视频等。
        不是互斥的，仅仅用于常见的分类说明。""")


class ModelBuilder(StrEnum):
    """
    模型构建者，目前只提供 Google 一个选项，因为只使用 Google 家的模型。
    """
    GOOGLE = "google"


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


class GenAIModel(BaseModel):
    """
    用于准确指代一个 AI 模型，包括模型构建者、模型名称。
    在 Inty 代码中，本对象实例唯一确定了一个模型，背后采用哪个 API 提供者，
    是由底层代码决定的。
    为了方便和简化命名规则，我们这里只考虑模型构建者、模型名称，不考虑 API 提供者。
    """
    nickname: str = Field(description="""
        用于给非后端团队提供的名称，方便沟通和理解。

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

    provider_pricing: str = Field(description="""
        模型 API 提供者的价格，用于在代码中唯一标识一个模型。拷贝自供应商的文档，方便查看和理解。""")

    playground_url: str = Field(description="""
        模型 API 提供者的 playground 地址，用于在代码中唯一标识一个模型。
        这个地址需要与第三方平台上的模型名称一致。比如 Google 的模型名称是 gemini-2.5-flash，
        那么在该平台上名字是 google/gemini-2.5-flash。""")


GEMINI_2_5_FLASH_LITE = GenAIModel(
    nickname="Gemini 2.5 Flash Lite",
    modalities=ModelModalities(inputs={DataModality.TEXT}, outputs={DataModality.TEXT}),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="google/gemini-2.5-flash-lite",
    provider_pricing="""
        https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5
    """,
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-2.5-flash-image&project=alien-paratext-461204-i9",
)


GEMINI_2_5_FLASH = GenAIModel(
    nickname="Gemini 2.5 Flash",
    modalities=ModelModalities(inputs={DataModality.TEXT}, outputs={DataModality.TEXT}),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.OPENROUTER,
    id_on_provider="google/gemini-2.5-flash",
    provider_pricing="""
        https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5
    """,
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-2.5-flash-image&project=alien-paratext-461204-i9",
)


NANO_BANANA = GenAIModel(
    nickname="Nano Banana",
    modalities=ModelModalities(inputs={DataModality.TEXT, DataModality.IMAGE}, outputs={DataModality.IMAGE}),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-2.5-flash-image",
    provider_pricing="https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-2.5",
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-2.5-flash-image&project=alien-paratext-461204-i9",
)


NANO_BANANA_PRO = GenAIModel(
    nickname="Nano Banana Pro",
    modalities=ModelModalities(inputs={DataModality.TEXT, DataModality.IMAGE}, outputs={DataModality.IMAGE}),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="gemini-3-pro-image-preview",
    provider_pricing="""
        https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models-3
    """,
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=gemini-2.5-flash-image&project=alien-paratext-461204-i9",
)


IMAGEN_4_FAST = GenAIModel(
    nickname="Imagen 4.0 Fast",
    modalities=ModelModalities(inputs={DataModality.TEXT, DataModality.IMAGE}, outputs={DataModality.IMAGE}),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="imagen-4.0-fast-generate-001",
    provider_pricing="https://cloud.google.com/vertex-ai/generative-ai/pricing#imagen-models",
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=imagen-4.0-fast-generate-001&project=alien-paratext-461204-i9",
)


IMAGEN_4 = GenAIModel(
    nickname="Imagen 4.0",
    modalities=ModelModalities(inputs={DataModality.TEXT, DataModality.IMAGE}, outputs={DataModality.IMAGE}),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="imagen-4.0-generate-001",
    provider_pricing="https://cloud.google.com/vertex-ai/generative-ai/pricing#imagen-models",
    playground_url="https://console.cloud.google.com/vertex-ai/studio/multimodal?model=imagen-4.0-generate-001&project=alien-paratext-461204-i9",
)


VEO_3_1_FAST = GenAIModel(
    nickname="Veo3.1 Fast",
    modalities=ModelModalities(inputs={DataModality.TEXT, DataModality.IMAGE}, outputs={DataModality.VIDEO}),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="veo-3.1-fast-generate-001",
    provider_pricing="https://cloud.google.com/vertex-ai/generative-ai/pricing#veo",
    playground_url="https://console.cloud.google.com/vertex-ai/studio/media/video?project=alien-paratext-461204-i9",
)

VEO_3_1 = GenAIModel(
    nickname="Veo3.1",
    modalities=ModelModalities(inputs={DataModality.TEXT, DataModality.IMAGE}, outputs={DataModality.VIDEO}),
    builder=ModelBuilder.GOOGLE,
    provider=ModelAPIProvider.GOOGLE_VERTEX_AI,
    id_on_provider="veo-3.1-generate-001",
    provider_pricing="https://cloud.google.com/vertex-ai/generative-ai/pricing#veo",
    playground_url="https://console.cloud.google.com/vertex-ai/studio/media/video?project=alien-paratext-461204-i9",
)
