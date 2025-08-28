#!/usr/bin/env python3
"""
快速集成测试脚本
验证评测系统调用现有API的正确性
"""

import asyncio
from typing import Any, Dict

import aiohttp
import pytest

# 测试配置
BASE_URL = "http://localhost:8000/api/v1"
TEST_USER_ID = "test_user_123"


class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """GET请求"""
        url = f"{self.base_url}{endpoint}"
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"GET {endpoint} failed: {response.status}")
                return {}

    async def post(self, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """POST请求"""
        url = f"{self.base_url}{endpoint}"
        async with self.session.post(url, json=data) as response:
            if response.status in [200, 201]:
                result = await response.json()
                # 仅对聊天接口处理 APIResponse 格式
                if "chat/completions" in endpoint and isinstance(result, dict) and "data" in result and result.get("code") == 200:
                    return result["data"]
                return result
            else:
                print(f"POST {endpoint} failed: {response.status}")
                text = await response.text()
                print(f"Error response: {text}")
                return {}


@pytest.mark.asyncio
async def test_existing_apis():
    """测试现有的API端点"""
    print("🔍 测试现有API端点...")

    async with APITester(BASE_URL) as tester:

        # 1. 测试智能体API
        print("\n📋 测试智能体API:")
        agents = await tester.get("/agents/me")
        print(
            f"  ✓ 获取智能体列表: {len(agents) if isinstance(agents, list) else 'Error'}"
        )

        if agents and isinstance(agents, list) and len(agents) > 0:
            agent_id = agents[0].get("id")
            if agent_id:
                # 测试获取智能体详情
                agent_detail = await tester.get(f"/agents/{agent_id}")
                print(f"  ✓ 获取智能体详情: {agent_detail.get('name', 'Error')}")

        # 2. 测试聊天API
        print("\n💬 测试聊天API:")
        chats = await tester.get("/chats/")
        print(f"  ✓ 获取聊天列表: {len(chats) if isinstance(chats, list) else 'Error'}")

        if agents and isinstance(agents, list) and len(agents) > 0:
            agent_id = agents[0].get("id")
            if agent_id:
                # 测试获取聊天详情
                chat_detail = await tester.get(f"/chats/agents/{agent_id}/detail")
                print(f"  ✓ 获取聊天详情: {'Success' if chat_detail else 'Error'}")

                # 测试发送消息 (OpenAI格式)
                message_data = {
                    "messages": [{"role": "user", "content": "你好，这是一个测试消息"}],
                    "max_tokens": 100,
                    "temperature": 0.7,
                    "stream": False,
                }

                try:
                    chat_response = await tester.post(
                        f"/chats/agents/{agent_id}/chat/completions", message_data
                    )
                    if chat_response and "choices" in chat_response:
                        response_content = chat_response["choices"][0]["message"][
                            "content"
                        ]
                        print(f"  ✓ 发送消息成功: {response_content[:50]}...")
                    else:
                        print("  ❌ 发送消息失败")
                except Exception as e:
                    print(f"  ❌ 发送消息异常: {str(e)}")


async def test_evaluation_apis():
    """测试评测系统API"""
    print("\n🧪 测试评测系统API:")

    async with APITester(BASE_URL) as tester:

        # 测试创建评测会话
        session_data = {
            "name": "API集成测试",
            "questions": ["你好", "你是谁？"],
            "selected_agents": [],  # 需要实际的agent ID
            "scoring_model": "openrouter/anthropic/claude-3-haiku",
            "scoring_criteria": "测试评分标准",
            "use_new_user_identity": True,
            "config": {},
        }

        # 先获取一些智能体ID
        agents = await tester.get("/agents/me")
        if agents and isinstance(agents, list) and len(agents) > 0:
            session_data["selected_agents"] = [agents[0]["id"]]

            # 创建评测会话
            session = await tester.post("/evaluation/sessions", session_data)
            if session and session.get("id"):
                session_id = session["id"]
                print(f"  ✓ 创建评测会话: {session_id}")

                # 获取会话详情
                session_detail = await tester.get(f"/evaluation/sessions/{session_id}")
                print(f"  ✓ 获取会话详情: {session_detail.get('name', 'Error')}")

                # 启动评测
                start_result = await tester.post(
                    f"/evaluation/sessions/{session_id}/start"
                )
                print(f"  ✓ 启动评测: {start_result.get('success', False)}")

            else:
                print("  ❌ 创建评测会话失败")
        else:
            print("  ❌ 无可用智能体，跳过评测测试")


async def main():
    """主测试函数"""
    print("🚀 InTy 评测系统集成测试")
    print("=" * 50)

    try:
        await test_existing_apis()
        await test_evaluation_apis()

        print("\n" + "=" * 50)
        print("✅ 集成测试完成")

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("注意：请确保 InTy 后端服务正在运行 (http://localhost:8000)")
    print("如果需要修改地址，请编辑脚本中的 BASE_URL")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n💥 测试启动失败: {str(e)}")
