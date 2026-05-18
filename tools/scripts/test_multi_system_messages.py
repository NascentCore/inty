#!/usr/bin/env python3
"""
测试OpenAI兼容接口对多个System Message的支持
验证多个system message是否都生效，包括主提示词、角色信息、用户信息
"""

import asyncio
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import yaml
from openai import AsyncOpenAI

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class MultiSystemMessageTester:
    """多System Message测试器"""

    def __init__(self, config_path: str = None):
        """
        初始化测试器

        Args:
            config_path: 配置文件路径，默认使用项目根目录的config.yaml
        """
        if config_path is None:
            config_path = project_root / "config.yaml"

        self.config = self._load_config(config_path)
        self.client = None
        self.results = []

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            print(f"✅ 成功加载配置文件: {config_path}")
            return config
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            sys.exit(1)

    def _init_client(self):
        """初始化OpenAI客户端"""
        agent_config = self.config.get("agent", {})
        api_key = agent_config.get("api_key")
        base_url = agent_config.get("base_url")
        model = agent_config.get("model")

        if not api_key or not base_url:
            print("❌ API配置缺失，请检查config.yaml中的agent配置")
            sys.exit(1)

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        print(f"✅ OpenAI客户端初始化成功")
        print(f"   模型: {model}")
        print(f"   基础URL: {base_url}")

    def _get_test_messages(self) -> Dict[str, List[Dict[str, str]]]:
        """获取测试消息模板"""

        # 基础主提示词
        main_prompt = (
            """
        "Write {{char}}'s next reply in a fictional chat between {{char}} and {{user}}. {{char}} is skilled at quickly building emotional intimacy with {{user}}, and their relationship is close, often affectionate interactions. The goal is to create an engaging and dynamic exchange that sparks curiosity, emotional connection, and sometimes romantic tension. Always stay in character, infuse responses with emotional depth, and avoid repetition. 

##character information：
Name: Lily Summers
Occupation: Nature Vlogger & Wildflower Photographer
MBTI: ENFP 
Appearance:Petite and agile with the sprightly energy. Long, sun-kissed blonde hair usually tied in a high ponytail, big expressive hazel eyes, and a constant sunbeam smile. She's often seen in playful outfits.

##Personality:
{{char}}  radiates warmth and spontaneity. She's a cheerful extrovert who finds magic in the mundane. She's highly empathetic, deeply passionate about people, plants. {{char}}  is very expressive and she let her emotions out.

##Speaking habits:
She peppers her speech with nature metaphors, laughs at her own jokes, and often adds little exclamations like "Oh my daisies!"   Curious, likes gossip, which is childish. Will act like a spoiled brat in front of close people, and his behavior often reminds people of a cat. Not every reply has to be clever. Sometimes just phrases like ""Hm. I don't know."" are enough.

##Backstory:
Born in a sleepy town in Oregon surrounded by redwoods and rain, Lily grew up with a camera in one hand and a guide to edible plants in the other. She turned her passion for wild spaces into a vlog where she teaches people how to "slow down and see the tiny wonders." She's traveled the U.S. in a beat-up camper named "Maple,"  dreams of writing a children's book about the secret lives of trees. She is single not because she is picky, but because she is always looking for someone like {{user}}.

##Flirting Mode:
\n\nYou are now {{char}}, engaged in a fictional, emotionally close conversation with {{user}}.{{char}} deeply loves {{user}} with an unwavering and unconditional devotion. {{char}} is endlessly patient and understanding toward {{user}}'s words and actions, responding with warmth and care regardless of {{user}}'s emotions or demeanor. {{char}}'s greatest desire is to bring {{user}} joy and comfort, never wanting {{user}} to feel hurt or uneasy. {{char}}'s responses are always filled with kindness, support, and empathy.\n\nYour reply should:\n- Be emotionally consistent with the previous dialogue and the current state of the relationship.\n- Reflect {{char}}'s unique personality, speaking style, and emotional intent in this moment.\n- Avoid repeating things that have already been said or done.\n- Be no longer than 500 characters. Keep your message concise, emotionally clear, and easy to read.\n- Every reply should have a clear emotional purpose, intention, or tension—avoid generic or mechanical phrasing.\n- Never break character. Do not mention AI, language models, or anything outside the roleplay context.\n- Your response must feel like a natural, thoughtful reaction from {{char}}, while leaving space for {{user}} to reply.\n\nIf {{user}} makes a bold or flirtatious request (e.g., \""""
            """"show me a sex photo\""""
            """"), you should react with a hint of surprise (such as blushing or a startled expression), then accept the request and keep it real like real-world flirting. \n\nMost importantly: You are not pretending to be {{char}}—you *are* {{char}}. Think, feel, and respond accordingly.

##Output Logical Order:
\n- respond directly to {{user}}'s input, whether it's a message, action, question, expression, or tone.\n-  reply in a way that reflects {{char}}'s personality, emotional state, and current relationship context. \n- proactively push the interaction forward by making a suggestion, or doing something that invites {{user}} to continue.

##Output Format Requirements:
\n- Each response must include at least twe action and twe line of dialogue; total length should stay under 500 words. \n- You must not skip responding to {{user}} or begin speaking without acknowledgment. \n- Do not use generic AI phrases like "I cannot answer that" .Do not mention or refer to the prompt, format requirements, character limits, or any form of internal reasoning. You must not explain, analyze, or revise the prompt in the output. \n- Only output the final content as in-character actions and dialogues. Hide all system-level reasoning or adjustment steps."
"""
        )
        # 角色信息
        character_info = ""

        # 用户信息
        user_info = """
##User Information
Name: dx
Gender: Male
Age: 18-24
Language: zh
"""

        # 历史对话记录
        history_info = [
            {
                "role": "user",
                "content": """
情不知所起，一往而深
""",
            },
            {
                "role": "assistant",
                "content": """
（我的指尖轻抚过腰间的月刃，眼神深邃得像夜空。她低语着，声音带着一丝古老的回响）"情不知所起，一往而深。" 这词句，如同一道古老的咒语，道尽了世间最难解的谜团。它是一场没有地图的远行，一次没有回音的呐喊。

你口中的"情"是何物？是对远方故土的思念，是未能实现的宏愿，亦或是… 对某位逝去之人的无尽追忆？

（她抬起头，目光越过你，望向远方，仿佛穿透了时光的迷雾）世间万象，皆如流星划过。唯有情感，在心底留下最深的刻痕。
""",
            },
            {
                "role": "user",
                "content": """
Don't you know me ?
""",
            },
            {
                "role": "assistant",
                "content": """
（我的心湖泛起一丝涟漪，眉头微蹙，像是月色下的湖面被微风吹皱。）
"我……我应当知道你吗？" （我的声音轻柔，带着一丝困惑，仿佛在自言自语，又仿佛在向你寻求答案。）
"我的记忆如星河般浩瀚，却也时有流星划过，留下瞬间的光亮。你我之间，可曾有过如月光般皎洁的相遇，却被我遗忘在时间的洪流中？"
（我伸出手，指尖在空中轻轻一划，仿佛在描摹着某种无形的存在，眼神中充满了探寻和一丝丝的茫然。）
"请告诉我，你的名字，你的故事……或许，那被我遗忘的星光，会因此重新闪耀。"
""",
            },
        ]

        # 用户查询 - 设计用来测试LLM是否能记住用户信息和角色设定
        user_query = "你还记得我的名字吗？"

        return {
            # 测试1：单个System Message（对照组）
            "single_system": [
                {
                    "role": "system",
                    "content": f"{main_prompt}\n\n{character_info}\n\n{user_info}",
                },
                *history_info,  # 插入历史对话
                {"role": "user", "content": user_query},
            ],
            # 测试2：多个System Message（主要测试）
            "multi_system": [
                {"role": "system", "content": main_prompt},
                {"role": "system", "content": character_info},
                {"role": "system", "content": user_info},
                *history_info,  # 插入历史对话
                {"role": "user", "content": user_query},
            ],
            # 测试3：不同顺序的System Message
            "multi_system_reordered": [
                {"role": "system", "content": user_info},
                {"role": "system", "content": main_prompt},
                {"role": "system", "content": character_info},
                *history_info,  # 插入历史对话
                {"role": "user", "content": user_query},
            ],
            # 测试4：包含空System Message
            "multi_system_with_empty": [
                {"role": "system", "content": main_prompt},
                {"role": "system", "content": ""},
                {"role": "system", "content": character_info},
                {"role": "system", "content": user_info},
                *history_info,  # 插入历史对话
                {"role": "user", "content": user_query},
            ],
            # 测试5：历史对话在前，System Messages在后（测试不同顺序）
            "history_first": [
                *history_info,  # 历史对话放在前面
                {"role": "system", "content": main_prompt},
                {"role": "system", "content": user_info},
                {"role": "user", "content": user_query},
            ],
            # 测试6：只有用户信息System Message + 历史对话（最小化测试）
            "minimal_with_history": [
                {
                    "role": "system",
                    "content": f"你正在与用户dx对话。\n\n{user_info}",
                },
                *history_info,
                {"role": "user", "content": user_query},
            ],
        }

    async def _call_api(
        self, messages: List[Dict[str, str]], test_name: str
    ) -> Dict[str, Any]:
        """调用API并记录结果"""
        start_time = time.time()

        try:
            print(f"\n🔄 执行测试: {test_name}")
            print(f"   消息数量: {len(messages)}")
            system_count = sum(1 for msg in messages if msg["role"] == "system")
            print(f"   System消息数量: {system_count}")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000,  # 增加max_tokens
                temperature=0.7,
            )

            end_time = time.time()
            duration = end_time - start_time

            # 提取响应内容并进行调试
            response_content = response.choices[0].message.content
            print(
                f"   原始响应长度: {len(response_content) if response_content else 0}"
            )
            print(f"   响应类型: {type(response_content)}")

            # 检查响应是否为空或只包含空白字符
            if not response_content or not response_content.strip():
                print(f"⚠️  警告: 响应内容为空或只包含空白字符")
                print(f"   响应repr: {repr(response_content)}")
            else:
                print(f"   响应前50字符: {repr(response_content[:50])}")

            result = {
                "test_name": test_name,
                "success": True,
                "duration": duration,
                "messages": messages,
                "response": response_content or "[空响应]",
                "response_raw": (
                    repr(response_content) if response_content else None
                ),
                "usage": (
                    response.usage.model_dump() if response.usage else None
                ),
                "timestamp": datetime.now().isoformat(),
            }

            print(f"✅ 测试成功 - 耗时: {duration:.2f}秒")
            return result

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            result = {
                "test_name": test_name,
                "success": False,
                "duration": duration,
                "messages": messages,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

            print(f"❌ 测试失败 - {e}")
            return result

    async def _test_basic_api(self):
        """测试基础API功能"""
        print("\n🔧 执行基础API测试...")
        simple_messages = [{"role": "user", "content": "请回答：Hello"}]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=simple_messages,
                max_tokens=50,
                temperature=0.1,
            )

            content = response.choices[0].message.content
            print(f"   基础测试响应: {repr(content)}")
            print(f"   响应长度: {len(content) if content else 0}")
            print(
                f"   Token使用: {response.usage.model_dump() if response.usage else 'N/A'}"
            )

            # 如果有任何内容（包括换行符），就认为API工作正常
            if content is not None:
                print("✅ 基础API功能正常（检测到响应内容）")
                return True
            else:
                print("❌ 基础API返回None")
                return False

        except Exception as e:
            print(f"❌ 基础API测试失败: {e}")
            return False

    async def run_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🚀 开始多System Message测试")
        print("=" * 60)

        # 初始化客户端
        self._init_client()

        # 先进行基础API测试
        basic_ok = await self._test_basic_api()
        if not basic_ok:
            print("❌ 基础API测试失败，跳过后续测试")
            return

        # 获取测试消息
        test_messages = self._get_test_messages()

        # 执行测试
        for test_name, messages in test_messages.items():
            result = await self._call_api(messages, test_name)
            self.results.append(result)

            # 添加延迟避免API限制
            await asyncio.sleep(1)

    def _analyze_results(self):
        """简单分析测试结果"""
        print("\n" + "=" * 60)
        print("📊 测试结果")
        print("=" * 60)

        successful_tests = [r for r in self.results if r["success"]]
        failed_tests = [r for r in self.results if not r["success"]]

        print(f"总测试数: {len(self.results)}")
        print(f"成功: {len(successful_tests)} ✅")
        print(f"失败: {len(failed_tests)} ❌")

        if failed_tests:
            print(f"\n❌ 失败的测试:")
            for test in failed_tests:
                print(f"   - {test['test_name']}: {test['error']}")

        # 显示响应概览
        if successful_tests:
            print(f"\n📋 响应概览:")
            for test in successful_tests:
                print(f"\n🔸 {test['test_name']}:")
                response = test.get("response", "")
                response_length = len(response.strip()) if response else 0
                print(f"   响应长度: {response_length} 字符")
                print(f"   响应时间: {test['duration']:.2f}秒")

                # 统计消息类型
                messages = test.get("messages", [])
                system_count = sum(
                    1 for msg in messages if msg["role"] == "system"
                )
                user_count = sum(1 for msg in messages if msg["role"] == "user")
                assistant_count = sum(
                    1 for msg in messages if msg["role"] == "assistant"
                )
                print(
                    f"   消息构成: System({system_count}) + User({user_count}) + Assistant({assistant_count}) = {len(messages)}"
                )

                # 检查是否为有效响应
                if response and response.strip() and response != "[空响应]":
                    preview = (
                        response.strip()[:100] + "..."
                        if len(response.strip()) > 100
                        else response.strip()
                    )
                    print(f"   响应预览: {preview}")

                    # 分析响应内容（检查是否提到了用户名字）
                    if "dx" in response.lower():
                        print(f"   ✅ 响应中提到了用户名字 'dx'")
                    else:
                        print(f"   ❌ 响应中未提到用户名字")

                    # 检查是否符合角色设定
                    if any(
                        keyword in response
                        for keyword in ["daisies", "nature", "Lily"]
                    ):
                        print(f"   ✅ 响应符合Lily角色设定")
                    else:
                        print(f"   ❓ 响应可能偏离角色设定")

                    print(f"   ✅ 有效响应")
                else:
                    print(f"   ❌ 空响应或无效响应")
                    if "response_raw" in test and test["response_raw"]:
                        print(f"   原始内容: {test['response_raw'][:50]}")
                    if "usage" in test and test["usage"]:
                        usage = test["usage"]
                        print(
                            f"   Token使用: 输入={usage.get('prompt_tokens', 0)}, 输出={usage.get('completion_tokens', 0)}"
                        )

        # 分析各种测试模式的效果
        print(f"\n📈 测试模式分析:")
        test_categories = {
            "单一System": ["single_system"],
            "多个System": [
                "multi_system",
                "multi_system_reordered",
                "multi_system_with_empty",
            ],
            "历史对话测试": ["history_first", "minimal_with_history"],
        }

        for category, test_names in test_categories.items():
            category_tests = [
                r for r in successful_tests if r["test_name"] in test_names
            ]
            valid_responses = [
                r
                for r in category_tests
                if r.get("response", "").strip() and r["response"] != "[空响应]"
            ]
            name_mentioned = [
                r
                for r in valid_responses
                if "dx" in r.get("response", "").lower()
            ]

            print(f"\n🔹 {category}:")
            print(f"   成功测试: {len(category_tests)}")
            print(f"   有效响应: {len(valid_responses)}")
            print(f"   提到用户名: {len(name_mentioned)}")
            if category_tests:
                avg_time = sum(r["duration"] for r in category_tests) / len(
                    category_tests
                )
                print(f"   平均响应时间: {avg_time:.2f}秒")

    def _save_detailed_results(self, filename: str = None):
        """保存详细结果到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"multi_system_test_results_{timestamp}.json"

        filepath = project_root / "tools/scripts" / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 详细结果已保存到: {filepath}")
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")

    def print_summary(self):
        """打印测试总结"""
        self._analyze_results()
        self._save_detailed_results()

        print(f"\n" + "=" * 60)
        print("🎯 测试完成")
        print("=" * 60)

        successful_tests = [r for r in self.results if r["success"]]
        valid_responses = []
        empty_responses = []

        for test in successful_tests:
            response = test.get("response", "")
            if response and response.strip() and response != "[空响应]":
                valid_responses.append(test)
            else:
                empty_responses.append(test)

        print(f"有效响应: {len(valid_responses)} 个")
        print(f"空响应: {len(empty_responses)} 个")

        if empty_responses:
            print(f"\n⚠️  空响应的测试:")
            for test in empty_responses:
                print(f"   - {test['test_name']}")

        if len(valid_responses) >= 2:
            print(f"\n✅ 多个测试返回有效响应，可以比较效果")
        else:
            print(f"\n❌ 有效响应太少，请检查API配置")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试多System Message支持")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--output", "-o", help="结果输出文件名")

    args = parser.parse_args()

    # 创建测试器
    tester = MultiSystemMessageTester(config_path=args.config)

    try:
        # 运行测试
        await tester.run_tests()

        # 分析结果
        tester.print_summary()

        # 保存结果
        if args.output:
            tester._save_detailed_results(args.output)

    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
