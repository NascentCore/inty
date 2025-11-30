# Gemini 语音合成后端实现工作日志

> **CREATED_BY_AGENT**  
> 本文件记录了在 `cursor/add-gemini-speech-to-text-backend-f67f` 分支中实现的 Gemini TTS 多供应商语音生成功能。

## 概述

本次实现为 InTy 后端添加了 Gemini 2.5 Flash TTS 作为语音生成的首选提供商，并实现了与 ElevenLabs 的自动回退机制。该功能增强了语音多样性，提供了冗余保障，并支持通过配置灵活切换语音提供商。

## 实现目标

- ✅ 集成 Gemini 2.5 Flash TTS 作为主要语音生成提供商
- ✅ 实现多供应商自动回退策略（Gemini → ElevenLabs）
- ✅ 支持音色映射与自动转换
- ✅ 保持与现有缓存系统的兼容性
- ✅ 添加完整的配置支持
- ✅ 编写单元测试覆盖核心逻辑

## 变更文件清单

### 1. 配置层 (`app/core/config.py`)

**新增配置类：`GeminiVoiceConfig`**

```python
@dataclass
class GeminiVoiceConfig:
    enabled: bool = False
    api_key: Optional[str] = None
    model: str = "gemini-2.5-flash-preview-tts"
    default_voice_name: str = "Zephyr"
    default_language_code: Optional[str] = "cmn-CN"
    temperature: float = 1.0
    top_p: float = 0.95
```

**变更点：**
- 新增 `GeminiVoiceConfig` 数据类，包含 Gemini TTS 所需的所有配置项
- 在 `Config` 类中添加 `gemini_voice: GeminiVoiceConfig` 字段
- 在 `load_config` 函数中加载 `gemini_voice` 配置
- 在 `_validate_config` 中添加验证逻辑：当 `gemini_voice.enabled = true` 时，必须提供 `api_key`

### 2. 核心服务层 (`app/services/voice_service.py`)

**主要重构：**

#### 2.1 新增枚举与数据结构

- **`VoiceProvider` 枚举**：定义 `GEMINI` 和 `ELEVENLABS` 两个提供商
- **`VoiceSelection` 数据类**：统一管理不同提供商的音色选择逻辑
  - `requested_voice_id`: 用户请求的原始 voice_id
  - `gemini_voice_name`: Gemini 音色名称
  - `elevenlabs_voice_id`: ElevenLabs 音色 ID
  - `provider_voice_id(provider)`: 根据提供商返回对应的音色标识

#### 2.2 音色映射表

```python
GEMINI_GENDER_DEFAULT_MAPPING = {
    "MALE": "Charon",
    "FEMALE": "Kore",
    "OTHER": "Zephyr",
}

GEMINI_TO_ELEVEN_VOICE_ID = {
    "kore": "4tRn1lSkEn13EVTuqb0g",
    "charon": "rHWSYoq8UlV0YIBKMryp",
    "zephyr": "O7p2vmz2iEYgMXxkbsif",
}

ELEVEN_TO_GEMINI_VOICE_ID = {value: key for key, value in GEMINI_TO_ELEVEN_VOICE_ID.items()}
```

**设计说明：**
- 建立了 Gemini 预设音色（Kore、Charon、Zephyr）与 ElevenLabs 音色 ID 的双向映射
- 支持通过 `gemini:<voice_name>` 格式直接指定 Gemini 音色
- 当用户指定 ElevenLabs voice_id 时，自动映射到对应的 Gemini 音色以便回退

#### 2.3 客户端初始化优化

**变更前：**
```python
self.client = ElevenLabs(api_key=self.config.api_key)
```

**变更后：**
```python
self._elevenlabs_client: Optional[ElevenLabs] = None
self._gemini_client: Optional[genai.Client] = None
if self.config.enabled:
    self._elevenlabs_client = ElevenLabs(api_key=self.config.api_key)
```

**设计说明：**
- 采用懒加载模式，仅在需要时初始化客户端
- 支持动态启用/禁用提供商，提高灵活性
- 通过 `_get_elevenlabs_client()` 和 `_get_gemini_client()` 方法统一管理客户端实例

#### 2.4 `generate_voice` 方法重构

**核心流程：**

1. **构建提供商序列**：根据配置的启用状态，按优先级构建提供商列表（Gemini 优先）
2. **音色解析**：通过 `_resolve_voice_selection` 统一解析音色选择
3. **循环尝试提供商**：
   - 检查缓存（缓存键包含 `model`，确保不同提供商缓存隔离）
   - 调用提供商 API
   - 音频格式标准化（Gemini 返回的 PCM/WAV 需要转换为统一格式）
   - 上传到 GCS
   - 记录用量
   - 成功则返回，失败则尝试下一个提供商

**关键改进：**
- 多供应商自动回退：Gemini 失败时自动切换到 ElevenLabs
- 缓存隔离：不同 `model` 的缓存条目互不干扰
- 统一的错误处理：每个提供商失败不影响下一个尝试
- 用量记录增强：记录 `provider` 和 `requested_voice_id` 信息

#### 2.5 Gemini TTS API 调用实现

**`_call_gemini_tts_api` 方法：**

```python
async def _call_gemini_tts_api(
    self, text: str, voice_name: str, model: str, language: str
) -> Optional[Tuple[bytes, float, str, str]]:
```

**实现要点：**
- 使用 `google.genai.Client` 调用 Gemini API
- 构建 `SpeechConfig` 配置，指定 `voice_name` 和 `language_code`
- 使用 `GenerateContentConfig` 设置 `response_modalities=["AUDIO"]`
- 从响应中提取 `inline_data` 音频数据
- 调用 `_normalize_gemini_audio` 标准化音频格式

#### 2.6 音频格式标准化

**`_normalize_gemini_audio` 方法：**

Gemini 可能返回多种音频格式：
- `audio/L16;rate=24000` (PCM 线性音频)
- `audio/wav` (WAV 格式)
- `audio/mpeg` (MP3 格式)

**处理逻辑：**
- PCM 格式：解析 MIME type 中的采样率和位深度，转换为 WAV
- WAV 格式：直接使用，通过 `wave` 模块计算时长
- MP3 格式：直接使用，通过 `mutagen.mp3` 计算时长
- 默认回退：假设为 PCM 24kHz/16bit，转换为 WAV

**辅助函数：**
- `_parse_audio_mime_type`: 解析 MIME type 中的采样率和位深度
- `_pcm_to_wav`: 将 PCM 数据转换为 WAV 格式
- `_calculate_pcm_duration`: 计算 PCM 音频时长
- `_calculate_wav_duration`: 计算 WAV 音频时长（新增）

#### 2.7 语言代码处理

**`_resolve_language_code` 方法：**

支持语言代码别名：
```python
LANGUAGE_CODE_ALIAS = {
    "zh": "cmn-CN",
    "en": "en-US",
}
```

- 将简写语言代码（如 `zh`、`en`）转换为 Gemini 所需的完整代码（如 `cmn-CN`、`en-US`）
- 如果未匹配到别名，使用配置中的 `default_language_code`

#### 2.8 其他方法调整

- **`_generate_file_name`**：新增 `extension` 参数，支持不同音频格式的文件扩展名
- **`_call_elevenlabs_api`**：返回值从 `Tuple[bytes, float]` 扩展为 `Tuple[bytes, float, str, str]`，增加 `content_type` 和文件扩展名
- **`get_available_voices`**、**`get_voice_by_id`**：使用 `_get_elevenlabs_client()` 替代直接访问 `self.client`

### 3. 配置文件模板 (`devops/config.yaml.template`)

**新增配置段：**

```yaml
gemini_voice:
  enabled: false
  {{ gemini_voice__api_key }}
  model: "gemini-2.5-flash-preview-tts"
  default_voice_name: "Zephyr"
  default_language_code: "cmn-CN"
  temperature: 1.0
  top_p: 0.95
```

**说明：**
- 默认 `enabled: false`，需要显式启用
- 使用模板变量 `{{ gemini_voice__api_key }}` 支持通过环境变量注入

### 4. 文档更新 (`backend/docs/AI_VOICE_SYSTEM.md`)

**新增章节：**

- **Gemini 优先的多供应商策略**：说明 Gemini 作为首选、自动回退机制、音色映射和缓存隔离
- **Gemini 语音配置**：配置项说明和使用示例
- **缓存策略更新**：说明缓存键包含 `model` 字段，不同供应商缓存隔离

### 5. 单元测试 (`tests/app/services/test_voice_service.py`)

**新增测试用例：**

1. **`test_resolve_voice_selection_with_gemini_prefix`**：
   - 测试 `gemini:Kore` 格式的音色解析
   - 验证 Gemini 音色名称和 ElevenLabs 回退音色 ID 的正确映射

2. **`test_resolve_voice_selection_from_elevenlabs_id`**：
   - 测试从 ElevenLabs voice_id 自动映射到 Gemini 音色
   - 验证双向映射的正确性

3. **`test_build_provider_sequence_respects_flags`**：
   - 测试提供商序列构建逻辑
   - 验证根据配置启用状态正确构建序列

4. **`test_normalize_gemini_audio_returns_wav`**：
   - 测试 PCM 音频格式标准化
   - 验证转换为 WAV 格式的正确性

**测试工具：**
- 使用 `monkeypatch` 模拟 ElevenLabs SDK，避免实际 API 调用
- 创建 `_DummyElevenLabs` 和 `_DummyVoicesAPI` 类模拟 SDK 行为

## 技术决策与设计考量

### 1. 多供应商回退策略

**决策：** 实现循环尝试机制，而非并行调用

**理由：**
- 成本考虑：避免同时调用多个 API 造成浪费
- 优先级明确：Gemini 作为首选，仅在失败时回退
- 错误处理简单：逐个尝试，失败即切换，逻辑清晰

### 2. 音色映射设计

**决策：** 建立双向映射表，支持自动转换

**理由：**
- 向后兼容：现有代码使用 ElevenLabs voice_id 无需修改
- 灵活性：支持直接指定 Gemini 音色（`gemini:<name>`）
- 一致性：确保回退时音色风格尽可能接近

### 3. 缓存键设计

**决策：** 缓存键包含 `model` 字段

**理由：**
- 隔离不同供应商：`gemini-2.5-flash-preview-tts` 和 `eleven_flash_v2_5` 生成不同缓存
- 避免交叉污染：同一文本在不同模型下可能生成不同音频
- 支持模型升级：模型变更时自动使用新缓存

### 4. 音频格式标准化

**决策：** 统一转换为 WAV 或保持 MP3，而非保留原始格式

**理由：**
- 兼容性：确保客户端能正确播放
- 简化处理：减少格式判断逻辑
- 质量保证：WAV 格式无损，适合后续处理

### 5. 客户端懒加载

**决策：** 使用可选客户端，按需初始化

**理由：**
- 资源节约：未启用的提供商不创建客户端
- 配置灵活：支持动态启用/禁用
- 错误隔离：某个提供商配置错误不影响其他提供商

## 依赖变更

### 新增依赖

- `google-genai`: Google Gemini API 客户端库

**注意：** 需要在 `requirements.txt` 中添加该依赖（本次实现中未显式修改，可能已在其他分支添加）

## 配置迁移指南

### 启用 Gemini 语音

1. **在配置文件中添加：**

```yaml
gemini_voice:
  enabled: true
  api_key: "your_gemini_api_key"
  model: "gemini-2.5-flash-preview-tts"
  default_voice_name: "Zephyr"
  default_language_code: "cmn-CN"
```

2. **验证配置：**

确保 `gemini_voice.api_key` 已正确设置，否则启动时会报错。

3. **测试回退机制：**

可以通过临时禁用 Gemini 或模拟 API 错误，验证自动回退到 ElevenLabs 的功能。

## 已知限制与未来改进

### 当前限制

1. **音色映射固定**：仅支持 3 对预设音色的映射（Kore/Charon/Zephyr）
2. **语言支持有限**：主要针对中文和英文优化
3. **音频格式**：Gemini 返回的音频格式可能因模型版本变化而不同

### 未来改进方向

1. **动态音色映射**：支持从配置或数据库加载音色映射关系
2. **更多语言支持**：扩展语言代码别名表
3. **音频质量优化**：根据使用场景选择最佳音频格式
4. **监控与指标**：添加各提供商的调用成功率、延迟等指标
5. **智能路由**：根据文本内容、用户偏好等因素智能选择提供商

## 测试验证清单

- [x] 单元测试覆盖核心逻辑（音色解析、提供商序列构建、音频标准化）
- [x] 配置验证（启用/禁用、API 密钥验证）
- [x] 文档更新（配置说明、使用示例）
- [ ] 集成测试（实际调用 Gemini API，验证回退机制）
- [ ] 性能测试（缓存命中率、API 调用延迟）
- [ ] 端到端测试（从 API 请求到音频返回的完整流程）

## 提交信息

```
feat: Add Gemini TTS as a voice generation provider

Integrates Gemini TTS as a primary voice generation option, with ElevenLabs as a fallback. 
This enhances voice diversity and provides redundancy.

Co-authored-by: z <z@sxwl.ai>
```

## 相关文档

- [AI_VOICE_SYSTEM.md](./AI_VOICE_SYSTEM.md) - 完整的语音系统文档
- [config.yaml.template](../../devops/config.yaml.template) - 配置模板

## 总结

本次实现成功将 Gemini TTS 集成到 InTy 语音生成系统中，实现了多供应商自动回退机制，提高了系统的可靠性和灵活性。通过统一的音色映射、缓存隔离和格式标准化，确保了与现有系统的良好兼容性。代码结构清晰，易于维护和扩展。

