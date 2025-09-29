#!/usr/bin/env python3
"""
演示脚本：展示API endpoint环境控制机制

这个脚本演示了如何在不同环境中控制API endpoints的可见性。
"""

import os
import sys
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api.middleware.endpoint_filter import create_endpoint_filter_middleware
from app.core.endpoint_config import is_endpoint_hidden_in_production


def create_demo_app(environment: str = "dev"):
    """创建演示应用"""
    app = FastAPI(title=f"Endpoint Filtering Demo - {environment}")
    
    # 添加一些测试endpoints
    @app.get("/api/v1/auth/login")
    async def login():
        return {"message": "Login endpoint - available in all environments"}
    
    @app.get("/api/v1/users/profile")
    async def user_profile():
        return {"message": "User profile - available in all environments"}
    
    @app.get("/api/v1/evaluation/sessions")
    async def evaluation_sessions():
        return {"message": "Evaluation sessions - hidden in production"}
    
    @app.get("/api/v1/admin/system-settings")
    async def admin_settings():
        return {"message": "Admin settings - hidden in production"}
    
    @app.get("/api/v1/report/")
    async def list_reports():
        return {"message": "List reports (GET) - hidden in production"}
    
    @app.post("/api/v1/report/")
    async def create_report():
        return {"message": "Create report (POST) - available in all environments"}
    
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
    
    # 添加endpoint过滤中间件
    app.add_middleware(create_endpoint_filter_middleware)
    
    return app


def test_endpoint_visibility(environment: str):
    """测试endpoint在不同环境中的可见性"""
    print(f"\n{'='*60}")
    print(f"测试环境: {environment.upper()}")
    print(f"{'='*60}")
    
    # 模拟环境配置
    with patch('app.core.config.global_config_loaded_from_config_yaml.app.environment', environment):
        app = create_demo_app(environment)
        client = TestClient(app)
        
        # 测试endpoints
        test_endpoints = [
            ("/api/v1/auth/login", "GET", "认证登录"),
            ("/api/v1/users/profile", "GET", "用户资料"),
            ("/api/v1/evaluation/sessions", "GET", "评测会话"),
            ("/api/v1/admin/system-settings", "GET", "管理员设置"),
            ("/api/v1/report/", "GET", "举报列表"),
            ("/api/v1/report/", "POST", "创建举报"),
            ("/health", "GET", "健康检查"),
        ]
        
        for path, method, description in test_endpoints:
            response = client.request(method, path)
            status = "✅ 可用" if response.status_code == 200 else "❌ 被屏蔽"
            print(f"{method:4} {path:30} - {description:15} - {status}")
            
            if response.status_code == 404:
                try:
                    error_msg = response.json().get("message", "Not Found")
                    print(f"     错误信息: {error_msg}")
                except:
                    pass


def test_configuration_functions():
    """测试配置函数"""
    print(f"\n{'='*60}")
    print("测试配置函数")
    print(f"{'='*60}")
    
    test_cases = [
        ("/api/v1/evaluation/sessions", "GET", True, "评测API应该被屏蔽"),
        ("/api/v1/admin/settings", "GET", True, "管理员API应该被屏蔽"),
        ("/api/v1/report/", "GET", True, "GET举报列表应该被屏蔽"),
        ("/api/v1/report/", "POST", False, "POST创建举报应该允许"),
        ("/api/v1/auth/login", "GET", False, "认证API应该允许"),
        ("/api/v1/users/profile", "GET", False, "用户API应该允许"),
    ]
    
    for path, method, expected, description in test_cases:
        result = is_endpoint_hidden_in_production(path, method)
        status = "✅ 正确" if result == expected else "❌ 错误"
        print(f"{method:4} {path:30} - {description:20} - {status} (结果: {result})")


def main():
    """主函数"""
    print("API Endpoint 环境控制机制演示")
    print("=" * 60)
    
    # 测试配置函数
    test_configuration_functions()
    
    # 测试不同环境
    for environment in ["dev", "staging", "prod"]:
        test_endpoint_visibility(environment)
    
    print(f"\n{'='*60}")
    print("演示完成！")
    print("=" * 60)
    print("\n总结:")
    print("1. 开发环境 (dev): 所有endpoints都可用")
    print("2. 生产环境 (prod): 敏感endpoints被屏蔽")
    print("3. 中间件自动根据环境配置过滤请求")
    print("4. 支持HTTP方法特定的路由控制")
    print("5. 配置集中管理，易于维护")


if __name__ == "__main__":
    main()
