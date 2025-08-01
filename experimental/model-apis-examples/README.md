# model-apis-engineering

How to work with each and every LLM models from major providers

## Gemini vs. OpenRounter endpoints

`uv run -s gemini_with_openai_lib.py --provider google --model gemini-2.5-flash`
Response 无法输出 reasoning details，无法确定 thinking 是否打开

`uv run -s gemini_with_openai_lib.py --provider openrouter --model google/gemini-2.5-flash`
Response 输出 `reasoning` & `reasoning_details`，当 `reasoning_effort="low"` (或 low/medium/high 其中之一),
删除 reasoning_effort 参数，则关闭 reasoning

# Content detection example

```
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
```

## References

- OpenAI compatibility in Gemini: https://ai.google.dev/gemini-api/docs/openai
- Gemini API reference: https://ai.google.dev/api/generate-content#v1beta.GenerationConfig

```

```
