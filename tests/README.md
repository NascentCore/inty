# Python 后端测试代码（非客户端测试代码、客户端测试代码如 Android app 都在对应目录下）

- 目录结构与对应的源代码文件一致
- 不要 patch 数据库 sqlalchemy 函数，读写都直接进入真实数据库 

## 运行`tests/app/features`下的端到端功能测试

```bash
# 初始化本地服务器
docker run --rm --name pg-inty -p 5432:5432 \
    -e POSTGRES_PASSWORD=sxwl666! -e POSTGRES_DB='inty' -d \
    postgres:16

# 使用测试配置（连接本地数据库等），供 pytest 导入 app 时加载
cp devops/config.yaml.test config.yaml

# 启动后端服务
./backend/inty/start.sh --test

# 运行测试
pytest -m "not noci" -v -s tests/
pytest -m "not noci" -v -s tests/features/
```

依赖本地后端与 `config.yaml` 的 E2E（如节日记忆 Chat History 投递）需先启动服务（如 `./backend/inty/start.sh --dev`）后再运行；单独运行该 E2E：`pytest tests/app/api/v1/endpoints/test_festival_memory_chat_history_e2e.py -v -s`。节日记忆投递还由集成测试覆盖：`deliver_festival_memories_for_user_agent` 会写入 chat_history 并更新 memory.delivery_at（见 `tests/app/services/test_memory_service_deliver_festival_integration.py`）。
