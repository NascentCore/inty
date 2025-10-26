import pytest
from loguru import logger
# 可选依赖项：如果Python SDK不可用，则跳过测试
inty_module = pytest.importorskip("inty")
Inty = getattr(inty_module, "Inty")


@pytest.mark.noci
def test_get_subscription_usage():
    """Test getting subscription usage statistics"""
# 使用虚拟 API 密钥创建客户端来创建来宾用户
    client = Inty(base_url="http://localhost:8000", api_key="dummy-api-key")
# 创建注册用户
    guest_response = client.api.v1.auth.create_guest(
        device_id="test-device-usage-123",
        system_language="en",
        age_group="adult",
    )

    logger.debug(f"Guest registration response: {guest_response}")
# 提取令牌并更新客户端
    token = guest_response.data.token
    client = Inty(base_url="http://localhost:8000", api_key=token)
#调用订阅使用端点
    usage_response = client.api.v1.subscription.get_usage()

    logger.debug(f"Usage response: {usage_response}")
# 验证响应结构
    assert usage_response.data is not None, "Usage data should not be None"
