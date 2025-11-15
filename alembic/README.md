# Alembic - 数据库迁移

## Generate version

- `alembic upgrade head`: run this to make sure the local database is in sync with the newest version
- `alembic revision --autogenerate --message "<write your message for this version>": this will write the new version script for you
- `alembic upgrade head`: run this again to apply your new version file
- If the above failed, you'll need to debug with @yaxiong on why this failed
- If you want to redo the newest version, first rollback the local changes with `alembic downgrade -1` and then delete the new version
  file you generated with `alembic revision --autogenerate --message "<...>"`, and then recreate the version file, by rerunning
  `alembic revision --autogenerate --message "<...>"`.

## 指定配置文件

迁移脚本默认读取项目根目录下的 `config.yaml`。如果需要使用不同的配置文件（例如 `devops/config.yaml.dev`），可通过 Alembic 的 `-x` 自定义参数或环境变量覆盖：

- `alembic upgrade head -x config=devops/config.yaml.dev`
- `alembic revision --autogenerate -x app_config=/abs/path/config.yaml --message "add_new_table"`
- 或者在命令前设置环境变量 `INTY_CONFIG_PATH=/abs/path/config.yaml alembic upgrade head`

支持的 `-x` 键包含：`config`、`config_file`、`config-file`、`config_path`、`config-path`、`app_config`、`app-config`。以上方式会在运行时通过环境变量 `INTY_CONFIG_PATH` 覆盖默认的配置文件路径。

## SOPs

### Manually set alembic_version when

- `alembic_version` table has a single row, writes the newest version applied to the database.
- You can update its value to the newest version number: `insert into alembic_version (version_num) values ('75796d073cb2');`
- Afterwards the revisions will be applied after the recorded version
