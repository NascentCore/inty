# Alembic - 数据库迁移

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
