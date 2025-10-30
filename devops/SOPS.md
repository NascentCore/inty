# DevOps 日常操作

## 迁移已有后端数据库到一个新的服务器

大体流程：
1. 初始化数据库 schema
2. 转移数据

### 初始化数据库 schema

1. 准备一个新的 config.yaml.new 文件，修改其 数据库 指向新的数据库实例
2. 使用最新的后端容器镜像，启动 bash
   ```
   docker run -it -v $(pwd)/config.yaml.new:/config.yaml ghcr.io/nascentcore/inty-backend/inty-server:main-dev
   ```
   这个命令会启动后端服务，后端服务启动初期会初始化数据库 schema

### 拷贝数据

```bash
docker run --rm -e PGPASSWORD=<password> --network host postgres:16 pg_dump -h localhost -p 5432 -U postgres -d devdb -Fc >devdb.dump
docker run --rm -e PGPASSWORD=<password> --network host -v $(pwd)/devdb.dump:/devdb.dump postgres:16 pg_restore -h <host> -p 5432 -U postgres -d inty-dev /devdb.dump
```
