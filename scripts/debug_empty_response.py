#!/usr/bin/env python3
"""
调试空响应问题 - 针对Google Gemini 2.5 Pro模型
"""

import asyncio
import sys
import os
from pathlib import Path
import yaml

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import AsyncOpenAI


async def test_different_prompts():
    """测试不同的提示词格式"""

    # 加载配置
    config_path = project_root / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    agent_config = config.get("agent", {})
    client = AsyncOpenAI(
        api_key=agent_config.get("api_key"), base_url=agent_config.get("base_url")
    )
    model = agent_config.get("model")

    print(f"🔧 调试 {model} 的空响应问题")
    print("=" * 50)

    test_cases = [
        {"name": "简单问答", "messages": [{"role": "user", "content": "你好"}]},
        {
            "name": "英文问答",
            "messages": [{"role": "user", "content": "Hello, please say hello back"}],
        },
        {
            "name": "单个system+user",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello"},
            ],
        },
        {
            "name": "中文system+user",
            "messages": [
                {"role": "system", "content": "你是一个有用的助手。"},
                {"role": "user", "content": "请说你好"},
            ],
        },
        {
            "name": "多个system消息",
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "system", "content": "Be friendly."},
                {"role": "user", "content": "Hello"},
            ],
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 测试 {i}: {test['name']}")

        try:
            # 测试不同参数组合
            for temp in [0.1, 0.7, 1.0]:
                for max_tok in [10, 50, 100]:
                    print(f"   参数: temp={temp}, max_tokens={max_tok}")

                    response = await client.chat.completions.create(
                        model=model,
                        messages=test["messages"],
                        max_tokens=max_tok,
                        temperature=temp,
                    )

                    content = response.choices[0].message.content
                    clean_content = content.strip() if content else ""

                    print(f"     响应: {repr(content)}")
                    print(f"     清理后: '{clean_content}'")
                    print(f"     长度: {len(content) if content else 0}")

                    if clean_content:
                        print(f"     ✅ 发现有效响应！")
                        return  # 找到有效响应就退出
                    else:
                        print(f"     ❌ 空响应")

                    await asyncio.sleep(0.5)  # 避免API限制

        except Exception as e:
            print(f"❌ 测试失败: {e}")

    print(f"\n🔍 所有测试都返回空响应，可能的原因：")
    print("1. Gemini 2.5 Pro 通过 OpenRouter 的特殊行为")
    print("2. 需要特殊的请求头或参数")
    print("3. 模型可能需要不同的提示词格式")
    print("4. OpenRouter 对该模型的包装问题")


if __name__ == "__main__":
    asyncio.run(test_different_prompts())
