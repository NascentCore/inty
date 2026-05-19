"""
Inty Backend Chat API 负载测试脚本 (简化版)

专注于测试与Nora Agent的聊天接口性能
核心功能：
1. 游客注册
2. 持续与Nora Agent聊天对话

作者: Claude
创建时间: 2025-08-14
更新时间: 2025-08-14 (简化版，专注聊天测试)
"""

import random
import uuid
from typing import Dict, Optional

from locust import HttpUser, between, task


class ChatAPIUser(HttpUser):
    """
    专注于聊天的用户 - 收到回复后立即发送下一条消息
    """

    wait_time = between(0.1, 0.5)  # 极短间隔，快速连续聊天

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.agent_id: str = (
            "e27c11d0-7a23-4c54-a109-66623af62d63"  # Nora Agent ID
        )
        self.chat_messages = [
            "你好Nora，今天过得怎么样？",
            "农场里最近有什么新鲜事吗？",
            "你最喜欢农场的哪个季节？",
            "能聊聊你的拖拉机吗？",
            "农场生活是什么样的？",
            "你觉得城市和乡村哪个更好？",
            "可以教我一些农活吗？",
            "农场里都有什么动物？",
            "你小时候就在农场长大吗？",
            "夏天的农场一定很美吧？",
        ]

    def on_start(self):
        """用户开始测试时的初始化操作"""
        self.register_guest()

    def register_guest(self) -> bool:
        """
        注册游客用户
        """
        device_id = f"test_device_{uuid.uuid4().hex[:8]}"

        # 根据 GuestRequest schema 构建正确的请求负载
        payload = {
            "device_id": device_id,
            "system_language": "zh",
            "age_group": "adult",
        }

        with self.client.post(
            "/api/v1/auth/guest",
            json=payload,
            name=None,  # 不在统计报告中显示此请求
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("code") == 200 and "data" in data:
                        # 根据实际API响应结构解析字段
                        response_data = data["data"]
                        self.auth_token = response_data.get("token")
                        self.user_id = response_data.get(
                            "guest_id"
                        )  # 修正字段名

                        if self.auth_token and self.user_id:
                            response.success()
                            return True
                        else:
                            response.failure(
                                f"缺失必要字段: token={self.auth_token}, guest_id={self.user_id}"
                            )
                            return False
                    else:
                        response.failure(f"注册失败: {data}")
                        return False
                except Exception as e:
                    # 增加更详细的错误信息用于调试
                    response.failure(
                        f"解析响应失败: {e}, 响应内容: {response.text[:200]}"
                    )
                    return False
            else:
                response.failure(
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False

    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}

    @task
    def chat_with_agent(self):
        """
        与Nora Agent进行持续聊天对话
        """
        if not self.auth_token:
            # 如果没有token，先注册
            if not self.register_guest():
                return

        message_content = random.choice(self.chat_messages)

        payload = {
            "messages": [{"role": "user", "content": message_content}],
            "stream": False,
            "model": "chatbot",
            "language": "zh",
        }

        with self.client.post(
            f"/api/v1/chats/agents/{self.agent_id}/chat/completions",
            json=payload,
            headers=self.get_auth_headers(),
            name="chat_completions",
            catch_response=True,
            timeout=30,  # 聊天可能需要更长时间
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("code") == 200:
                        # 成功收到回复
                        response.success()
                    else:
                        response.failure(
                            f"业务错误: {data.get('message', 'Unknown')}"
                        )
                except Exception as e:
                    response.failure(f"解析响应失败: {e}")
            elif response.status_code == 401:
                # token过期，重新注册
                self.register_guest()
                response.failure("认证失败，已重新注册")
            else:
                response.failure(
                    f"HTTP {response.status_code}: {response.text}"
                )


if __name__ == "__main__":
    """
    直接运行脚本时的配置示例
    """
    import os
    import sys

    # 设置默认测试参数
    if len(sys.argv) == 1:
        # 基础聊天测试
        os.system(
            "locust -f locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=5m --html=report.html"
        )
    else:
        # 使用命令行参数
        pass
