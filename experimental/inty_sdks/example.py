import os
from inty import Inty
from dotenv import load_dotenv

load_dotenv()

client = Inty(
    base_url="http://localhost:8000",
    api_key=os.environ.get("INTY_API_KEY"),  # This is the default and can be omitted
)

response = client.api.v1.ai.agents.list()
print("Agents list response:", response)
#创建注册用户并获取token
guest_response = client.api.v1.auth.create_guest()
print("Guest response:", guest_response)
# 从请求中提取令牌并创建具有身份验证的新客户端
token = guest_response.data.token
authenticated_client = Inty(
    base_url="http://localhost:8000",
    api_key=token,
)
# 现在将通过身份验证的客户端用于 protected 端点
response = authenticated_client.api.v1.ai.agents.list()
print("Agents response:", response)
