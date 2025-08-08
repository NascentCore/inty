#!/usr/bin/env python3
"""
测试并发聊天请求脚本
验证重复聊天记录问题是否已解决
"""

import asyncio
import json
import time

import aiohttp

# 配置
BASE_URL = "http://localhost:8000"
AGENT_ID = "d8b01c9e-c692-49db-a43a-16b39d9fc7ee"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTUxOTU4MjUsInN1YiI6InVzZXItMDFLMjNRVkY5S1g2NVI5WlkwVlQ5MjROUjYifQ.ix5giiYwcdfmj-UIMqZhvHCk0_Yz9MzDisFbvWy6Src"
MESSAGE = "hello"
CONCURRENCY = 2


async def check_service(session):
    """检查服务状态"""
    try:
        async with session.get(f"{BASE_URL}/docs") as response:
            if response.status == 200:
                print("✅ FastAPI服务运行正常")
                return True
            else:
                print(f"⚠️ FastAPI服务响应异常: {response.status}")
                return False
    except Exception as e:
        print(f"❌ 无法连接到FastAPI服务: {e}")
        return False


async def send_chat_request(session, request_id):
    """发送聊天请求"""
    # 尝试不同的API路径
    possible_urls = [
        f"{BASE_URL}/api/v1/chats/agents/{AGENT_ID}/chat/completions",
        f"{BASE_URL}/api/v1/chats/agents/{AGENT_ID}/chat/fast",
        f"{BASE_URL}/api/v1/chats/{AGENT_ID}/messages",
        f"{BASE_URL}/api/v1/agents/{AGENT_ID}/chat",
    ]

    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    data = {
        "messages": [
            {
                "role": "user",
                "content": MESSAGE
            }
        ],
        "stream": False,
        "model": "chatbot",
        "language": "zh"
    }

    # 如果是第一个请求，先测试所有可能的URL
    if request_id == 1:
        print("🔍 测试可能的API路径...")
        for i, test_url in enumerate(possible_urls):
            try:
                async with session.post(
                    test_url, headers=headers, json=data
                ) as response:
                    print(f"  {i+1}. {test_url} -> {response.status}")
                    if response.status != 404:
                        print(f"     找到有效路径: {test_url}")
                        break
            except Exception as e:
                print(f"  {i+1}. {test_url} -> 错误: {e}")

    url = possible_urls[0]  # 使用第一个URL

    print(f"请求 {request_id}: 开始发送...")
    start_time = time.time()

    try:
        async with session.post(url, headers=headers, json=data) as response:
            end_time = time.time()
            status = response.status
            text = await response.text()

            print(
                f"请求 {request_id}: 状态码 {status}, 耗时 {end_time - start_time:.2f}s"
            )

            if status == 200:
                try:
                    result = json.loads(text)
                    chat_id = result.get("chat_id", "N/A")
                    print(f"请求 {request_id}: ✅ 成功, chat_id = {chat_id}")
                    return {
                        "request_id": request_id,
                        "status": "success",
                        "chat_id": chat_id,
                        "response": result,
                    }
                except json.JSONDecodeError:
                    print(f"请求 {request_id}: ⚠️ 响应不是有效JSON")
                    return {
                        "request_id": request_id,
                        "status": "json_error",
                        "response": text,
                    }
            else:
                print(f"请求 {request_id}: ❌ 失败, 响应: {text}")
                return {"request_id": request_id, "status": "error", "response": text}

    except Exception as e:
        end_time = time.time()
        print(
            f"请求 {request_id}: ❌ 异常, 耗时 {end_time - start_time:.2f}s, 错误: {e}"
        )
        return {"request_id": request_id, "status": "exception", "error": str(e)}


async def main():
    """主函数"""
    print(f"=== 并发聊天测试 ===")
    print(f"目标: {BASE_URL}/api/v1/chats/agents/{AGENT_ID}/chat/completions")
    print(f"并发数: {CONCURRENCY}")
    print(f"消息内容: {MESSAGE}")
    print(f"Token: {TOKEN[:20]}...")
    print()

    async with aiohttp.ClientSession() as session:
        # 创建并发任务
        tasks = []
        for i in range(CONCURRENCY):
            task = send_chat_request(session, i + 1)
            tasks.append(task)

        # 并发执行所有请求
        print("🚀 开始并发执行...")
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        print(f"\n📊 总耗时: {end_time - start_time:.2f}s")
        print("\n=== 结果分析 ===")

        # 分析结果
        success_count = 0
        chat_ids = []

        for result in results:
            if isinstance(result, dict):
                if result.get("status") == "success":
                    success_count += 1
                    chat_id = result.get("chat_id")
                    if chat_id:
                        chat_ids.append(chat_id)

        print(f"成功请求数: {success_count}/{CONCURRENCY}")
        print(f"获得的 chat_id: {chat_ids}")

        # 检查是否有重复的 chat_id
        unique_chat_ids = set(chat_ids)
        if len(chat_ids) == len(unique_chat_ids):
            if len(unique_chat_ids) == 1:
                print("✅ 测试通过: 所有请求使用了相同的 chat_id，没有创建重复聊天")
            else:
                print("⚠️ 注意: 多个不同的 chat_id，可能存在问题")
        else:
            print("❌ 测试失败: 发现重复的 chat_id")

        # 详细输出
        print(f"\n=== 详细结果 ===")
        for i, result in enumerate(results):
            if isinstance(result, dict):
                print(f"请求 {result.get('request_id', i+1)}: {result}")
            else:
                print(f"请求 {i+1}: 异常 - {result}")


if __name__ == "__main__":
    asyncio.run(main())
