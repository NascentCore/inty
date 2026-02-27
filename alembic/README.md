# Alembic - 数据库迁移

配置文件位于 `alembic/alembic.ini`。从仓库根目录执行 alembic 时需指定配置：先 `export ALEMBIC_CONFIG=alembic/alembic.ini`，或使用 `alembic -c alembic/alembic.ini ...`。

## 增加新的 Alembic version 文件的步骤

```bash
# 删除现有的 postgres 实例及其存储卷，从而彻底清空；然后启动并确保数据库为空
docker rm -f -v pg-inty
docker run --rm --name pg-inty -p 5432:5432 \
    -e POSTGRES_PASSWORD=sxwl666! -e POSTGRES_DB='inty' -d \
    postgres:16
# 运行 alembic 将数据库升级到最新状态，此时必须确保没有新增的 alembic version 文件！！！
cp devops/config.yaml.test config.yaml
export PYTHONPATH=.
export ALEMBIC_CONFIG=alembic/alembic.ini
alembic upgrade head
alembic revision --autogenerate -m "<revision description>"
```

## SOPs

### 手动设置 alembic_version

- `alembic_version` 表只有一行，记录已应用到数据库的最新版本。
- 可以更新其值为最新版本号：`insert into alembic_version (version_num) values ('75796d073cb2');`
- 之后，迁移将在记录的版本之后应用
