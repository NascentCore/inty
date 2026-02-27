# 直接调用 localhost:8000 API Endpoints 的端到端功能测试

专门存放端到端功能测试，这些测试直接访问本地运行的后端实例；
使用 tests/app/api/test_client.py 来访问 API Endpoints；完整模拟一个功能端到端的使用流程，来完成测试。

- Always calls the backend runs at localhost:8000
