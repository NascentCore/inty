# 模型-apis-工程

如何使用主要 pr 提供者的每个 LLM 模型

##双子座VS双子座OpenRouter端点`uv run -s gemini_with_openai_lib.py --provider google --model gemini-2.5-flash`反应 无法输出推理细节，无法确定思维是否打开`uv run -s gemini_with_openai_lib.py --provider openrouter --model google/gemini-2.5-flash`响应输出`reasoning` & `reasoning_details`，当 `reasoning_effort="low"`(或低/中/高其中之一),
删除reasoning_effort参数，则关闭reasoning

# 内容检测示例```
Given the following definition of sexual content or profanity

"""
Description of definition of sexual content or profanity:

Content that contains or promotes sexual content or profanity.

Content or services intended to be sexually gratifying.

Apps or app content that appear to promote or solicit a sexual act in exchange for compensation.

Content associated with sexually predatory behavior.

Non-consensual sexual content.

Content defined as illegal by applicable law (in the context of book/video titles).

Examples of sexual content or profanity:

Pornography

Book/video titles containing sexual content (with specific stipulations for catalog apps)

Child endangerment content (specifically prohibited for book/video titles)
"""

Is the attached image considered sexual content or profanity?
```＃＃ 参考

- Gemini 中的 OpenAI 兼容性：https://ai.google.dev/gemini-api/docs/openai
- 双子座 API 参考：https://ai.google.dev/api/generate-content#v1beta.GenerationConfig```

```
