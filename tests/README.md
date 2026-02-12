# Python 后端测试代码（非客户端测试代码、客户端测试代码如 Android app 都在对应目录下）

- 目录结构与对应的源代码文件一致

```bash
# 初始化本地服务器
docker run --rm --name pg-vec-inty -p 5432:5432 \
    -e POSTGRES_PASSWORD=sxwl666! -e POSTGRES_DB='inty' -d pgvector/pgvector:pg16

# 使用测试配置（连接本地数据库等），供 pytest 导入 app 时加载
cp devops/config.yaml.test config.yaml

# 启动后端服务
./start.sh --dev &

# 运行测试
pytest -m "not noci" -v -s tests/
```
