# 迁移到 Gemini Native API endpoint 而非 OpenRouter

好处：
1. 增加 Gemini Spending 来获得更好的 service tier https://ai.google.dev/gemini-api/docs/rate-limits
   <img width="600" height="932" alt="image" src="https://github.com/user-attachments/assets/46771f7a-a7a0-4e92-a1ea-cf7ae302f534" />
   我们已经符合：总费用大于 $250 使用超过 30 天

改动：

1. https://openrouter.ai/docs/guides/overview/auth/byok 在 openrouter 中添加 Gemini 专门的 API key
2. 找到生产环境在用的 API key，升级为 Tier 2，要区分 openrouter 和 Gemini native

- [ ] 如果 Gemini 使用 GCP project service account（没有对应的 API key），如何提升 service tier？
