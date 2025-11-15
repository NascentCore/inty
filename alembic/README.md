# Alembic - 数据库迁移

## Generate version

- `alembic upgrade head`: run this to make sure the local database is in sync with the newest version
- `alembic revision --autogenerate --message "<write your message for this version>": this will write the new version script for you
- `alembic upgrade head`: run this again to apply your new version file
- If the above failed, you'll need to debug with @yaxiong on why this failed
- If you want to redo the newest version, first rollback the local changes with `alembic downgrade -1` and then delete the new version
  file you generated with `alembic revision --autogenerate --message "<...>"`, and then recreate the version file, by rerunning
  `alembic revision --autogenerate --message "<...>"`.

## 自定义 config.yaml 路径

环境脚本会读取 Alembic 的 `-x` 自定义参数，并优先使用 `config=<path>` 的值覆盖默认的 `config.yaml`：

```bash
alembic upgrade head -x config=devops/config.yaml.local
alembic upgrade head -x config=.secrets/prod-config.yaml
```

Alembic 环境脚本会直接调用 `app.core.config.load_config()` 加载对应文件，适合 CI 里按需切换配置；同一次命令中仍可附带其它 `-x key=value` 以便迁移脚本读取自定义参数。

## SOPs

### Manually set alembic_version when

- `alembic_version` table has a single row, writes the newest version applied to the database.
- You can update its value to the newest version number: `insert into alembic_version (version_num) values ('75796d073cb2');`
- Afterwards the revisions will be applied after the recorded version
