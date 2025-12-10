# Alembic - 数据库迁移

## 增加新的 Alembic version 文件的步骤

```
# 删除现有的 postgres 实例及其存储卷，从而彻底清空；然后启动并确保数据库为空
docker compose down pgvector -v
docker compose up pgvector -d
psql -h localhost -U postgres -d inty
# 输入密码进入 psql
inty=# \d+;
Did not find any relations.

# 运行 alembic 将数据库升级到最新状态，此时必须确保没有新增的 alembic verison 文件！！！
cp devops/config.yaml.local config.yaml
export PYTHONPATH=.
alembic -x config=devops/config.yaml.local upgrade head
psql -h localhost -U postgres -d inty
# 输入密码进入 psql
inty=# \d
Schema |             Name              |   Type   |  Owner   
--------+-------------------------------+----------+----------
 public | agent_followers               | table    | postgres
 public | agents                        | table    | postgres

# 运行 alembic 生成新的 revision 文件；并验证其效果符合预期
alembic -x config=devops/config.yaml.local revision --autogenerate -m "Users 表中增加 password 字段"
alembic -x config=devops/config.yaml.local upgrade head
```

## Generate version

- `alembic upgrade head`: run this to make sure the local database is in sync with the newest version
- `alembic revision --autogenerate --message "description for thsi revision"`: this will write the new version script for you

## 自定义 config.yaml 路径

环境脚本会读取 Alembic 的 `-x` 自定义参数，并优先使用 `config=<path>` 的值覆盖默认的来自
`app/core/config.py` 的全局配置：

```bash
alembic -x config=devops/config.yaml.local upgrade head
```

## SOPs

### 手动设置 alembic_version

- `alembic_version` 表只有一行，记录已应用到数据库的最新版本。
- 可以更新其值为最新版本号：`insert into alembic_version (version_num) values ('75796d073cb2');`
- 之后，迁移将在记录的版本之后应用
