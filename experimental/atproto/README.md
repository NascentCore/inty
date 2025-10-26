# ATProto（账户可携性Protocol）演示

**这是实验性的，详情请向亚雄询问**

## AT Protocol 示例

请参阅 https://stackoverflow.com/a/77633012, AT Protocol 的 SDK 使用 pydantic 模型
那是未版本化的？所以需要安装最新版本，否则导入
在 protocol 的 pydantic 模型失败。```bash
# Put your https://bsky.app/ username and password as env vars to .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bluesky_example.py
```## AT Protocol 是什么？

AT Protocol (Authenticated Transfer Protocol) 是 Bluesky 开发的开放社交网络 protocol。它旨在创建一个去中心化的社交网络，用户可以控制自己的数据，并可以在不同的服务之间移动，同时保持社交联系。

###主要特点

1. 账户可移植性

- 用户可以在不同的服务之间移动帐户
- 跨平台维护您的身份和社交图谱
- 无供应商锁定

2.算法选择

- 用户可以选择自己的内容发现算法
- 不同的服务可以实现不同的推荐系统- 在不同的算法之间自由切换

3.可互操作的数据

- 社交内容的标准化数据格式
- 不同服务之间轻松共享和互动
- 社交功能通用 protocol

###核心概念

1. **DID**：您在网络中的唯一标识符
2. **句柄**：您的人类用户名
3. **存储库**：您的个人数据存储
4. **记录**：个别内容

＃＃资源- [AT Protocol 文档](https://atproto.com/docs)- [Bluesky GitHub](https://github.com/bluesky-social)- [Protocol 规范](https://atproto.com/specs)