"""
Inty Backend Chat API 负载测试脚本

使用Locust框架对Inty Backend的chat接口进行并发测试
主要测试场景：
1. 游客注册
2. 与Nora Agent (e27c11d0-7a23-4c54-a109-66623af62d63) 聊天对话
3. 混合场景测试

作者: Claude
创建时间: 2025-08-14
更新时间: 2025-08-14 (专用于Nora测试)
"""

import json
import random
import time
import uuid
from typing import Dict, List, Optional

from locust import HttpUser, TaskSet, between, task
from locust.env import Environment


class ChatAPIUser(HttpUser):
    """
    模拟用户的聊天行为
    """
    wait_time = between(2, 8)  # 用户操作间隔2-8秒
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.agent_ids: List[str] = [
            # Nora Agent ID (第197行数据)
            "e27c11d0-7a23-4c54-a109-66623af62d63"
        ]
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
            "夏天的农场一定很美吧？"
        ]
        
    def on_start(self):
        """用户开始测试时的初始化操作"""
        self.register_guest()
        
    def register_guest(self) -> bool:
        """
        注册游客用户
        """
        device_id = f"test_device_{uuid.uuid4().hex[:8]}"
        nickname = f"TestUser_{random.randint(1000, 9999)}"
        
        payload = {
            "device_id": device_id,
            "nickname": nickname
        }
        
        with self.client.post(
            "/api/v1/auth/guest",
            json=payload,
            name="auth_guest_register",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("code") == 200 and "data" in data:
                        self.auth_token = data["data"]["token"]
                        self.user_id = data["data"]["user"]["id"]
                        response.success()
                        return True
                    else:
                        response.failure(f"注册失败: {data}")
                        return False
                except Exception as e:
                    response.failure(f"解析响应失败: {e}")
                    return False
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
                return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    @task(3)
    def chat_with_agent(self):
        """
        与Agent进行聊天对话 (权重3，相对高频)
        """
        if not self.auth_token:
            # 如果没有token，先注册
            if not self.register_guest():
                return
        
        agent_id = random.choice(self.agent_ids)
        message_content = random.choice(self.chat_messages)
        
        payload = {
            "messages": [
                {"role": "user", "content": message_content}
            ],
            "stream": False,
            "model": "chatbot", 
            "language": "zh"
        }
        
        with self.client.post(
            f"/api/v1/chats/agents/{agent_id}/chat/completions",
            json=payload,
            headers=self.get_auth_headers(),
            name="chat_completions",
            catch_response=True,
            timeout=30  # 聊天可能需要更长时间
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("code") == 200:
                        # 记录响应长度用于分析
                        if "data" in data and "choices" in data["data"]:
                            content_length = len(data["data"]["choices"][0]["message"]["content"])
                            response.success()
                        else:
                            response.failure("响应格式错误")
                    else:
                        response.failure(f"业务错误: {data.get('message', 'Unknown')}")
                except Exception as e:
                    response.failure(f"解析响应失败: {e}")
            elif response.status_code == 401:
                # token过期，重新注册
                self.register_guest()
                response.failure("认证失败，已重新注册")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(1) 
    def get_agent_messages(self):
        """
        获取与Agent的聊天历史 (权重1，低频)
        """
        if not self.auth_token:
            return
            
        agent_id = random.choice(self.agent_ids)
        
        params = {
            "limit": 20,
            "offset": 0,
            "order": "desc"
        }
        
        with self.client.get(
            f"/api/v1/chats/agents/{agent_id}/messages",
            params=params,
            headers=self.get_auth_headers(),
            name="get_agent_messages",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                self.register_guest()
                response.failure("认证失败")
            else:
                response.failure(f"HTTP {response.status_code}")


class HealthCheckUser(HttpUser):
    """
    系统健康检查用户，用于监控系统基础状态
    """
    wait_time = between(10, 30)  # 健康检查频率较低
    weight = 1  # 相对较少的健康检查用户
    
    @task
    def health_check(self):
        """健康检查"""
        with self.client.get("/health", name="health_check", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")


class StressTestTaskSet(TaskSet):
    """
    压力测试任务集，用于更激进的测试场景
    """
    
    def on_start(self):
        """初始化"""
        self.auth_token = None
        self.register_guest()
    
    def register_guest(self):
        """快速注册"""
        device_id = f"stress_device_{uuid.uuid4().hex[:8]}"
        nickname = f"StressUser_{random.randint(10000, 99999)}"
        
        response = self.client.post("/api/v1/auth/guest", json={
            "device_id": device_id,
            "nickname": nickname
        })
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                self.auth_token = data["data"]["token"]
    
    @task
    def rapid_chat(self):
        """快速连续聊天"""
        if not self.auth_token:
            self.register_guest()
            
        # 发送多条消息模拟快速对话
        messages = ["你好Nora", "农场忙吗", "谢谢你"]
        for msg in messages:
            payload = {
                "messages": [{"role": "user", "content": msg}],
                "stream": False,
                "model": "chatbot",
                "language": "zh"
            }
            
            self.client.post(
                "/api/v1/chats/agents/e27c11d0-7a23-4c54-a109-66623af62d63/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {},
                name="rapid_chat"
            )
            time.sleep(0.5)  # 短暂间隔


class StressTestUser(HttpUser):
    """
    压力测试用户，使用更激进的任务集
    """
    tasks = [StressTestTaskSet]
    wait_time = between(1, 3)  # 更短的等待时间
    weight = 1  # 少量压力测试用户


# 自定义事件处理
def on_test_start(environment: Environment, **kwargs):
    """测试开始时的初始化"""
    print("=" * 50)
    print("Inty Backend Chat API 负载测试开始")
    print(f"测试目标: {environment.host}")
    print(f"用户数配置: {environment.runner.user_count if hasattr(environment.runner, 'user_count') else 'Unknown'}")
    print("=" * 50)


def on_test_stop(environment: Environment, **kwargs):
    """测试结束时的清理"""
    print("=" * 50)
    print("Inty Backend Chat API 负载测试结束")
    print("正在生成测试报告...")
    print("=" * 50)


# 注册事件监听器
from locust import events
events.test_start.add_listener(on_test_start)
events.test_stop.add_listener(on_test_stop)


# 测试场景配置示例
class LightLoadUser(HttpUser):
    """轻负载测试用户"""
    tasks = [ChatAPIUser]
    wait_time = between(5, 15)
    weight = 8


class MediumLoadUser(HttpUser): 
    """中负载测试用户"""
    tasks = [ChatAPIUser]
    wait_time = between(2, 8)
    weight = 3


class HeavyLoadUser(HttpUser):
    """重负载测试用户"""
    tasks = [ChatAPIUser]
    wait_time = between(1, 3)
    weight = 1


if __name__ == "__main__":
    """
    直接运行脚本时的配置示例
    """
    import os
    import sys
    
    # 设置默认测试参数
    if len(sys.argv) == 1:
        # 基础负载测试
        os.system("locust -f locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=5m --html=report.html")
    else:
        # 使用命令行参数
        pass