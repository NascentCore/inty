# AI角色迁移脚本使用说明 - 角色迁移

这个脚本用于在测试环境和生产环境之间迁移AI角色数据，完全独立于项目代码运行。

## 文件清单

- `agent_migration.py` - 主脚本文件
- `agent_migration_config.yaml` - 配置文件
- `requirements.txt` - Python依赖
- `MIGRATION_README.md` - 使用说明

## 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置文件说明

编辑 `agent_migration_config.yaml` 文件，配置你的测试和生产环境信息：

```yaml
environments:
  test:
    name: "测试环境"
    database:
      host: "localhost"
      port: 15432
      user: "postgres"
      password: "postgres"
      db: "devdb"

  production:
    name: "生产环境"
    database:
      host: "your-prod-host.com"
      port: 5432
      user: "prod_user"
      password: "prod_password"
      db: "prod_db"
```

### 迁移选项配置

```yaml
migration:
  export:
    include_deleted: false # 是否包含已删除的角色
    status_filter: "APPROVED" # 状态过滤(PENDING/APPROVED/REJECTED)
    visibility_filter: null # 可见性过滤(PUBLIC/PRIVATE)
    include_creator_info: true # 是否导出创建者信息
    output_file: "agents_export.json"

  import:
    update_existing: false # 如果角色已存在是否更新
    keep_original_ids: false # 是否保持原始ID
    default_creator_id: null # 默认创建者ID
    force_status: null # 强制设置状态
    skip_validation: false # 是否跳过验证
```

## 使用方法

### 导出AI角色

从测试环境导出AI角色：

```bash
python agent_migration.py export --from test --config agent_migration_config.yaml
```

指定导出文件路径：

```bash
python agent_migration.py export --from test --file my_agents.json
```

### 导入AI角色

向生产环境导入AI角色：

```bash
python agent_migration.py import --to production --file agents_export.json --config agent_migration_config.yaml
```

## 注意事项

1. **数据库权限**: 确保配置的数据库用户有足够权限读写agents和users表
2. **备份数据**: 在导入生产环境前，建议先备份数据库
3. **测试验证**: 先在测试环境之间互相迁移测试脚本功能
4. **创建者处理**: 如果生产环境不存在对应的创建者用户，需要配置`default_creator_id`
5. **ID冲突**: 默认会生成新的UUID，如需保持原ID需设置`keep_original_ids: true`

## 日志文件

脚本运行时会生成 `migration.log` 日志文件，记录详细的操作过程和错误信息。

- log 示例

```bash
2025-08-01 14:59:59,491 - INFO - 开始从 test 环境导出AI角色
2025-08-01 15:00:00,183 - INFO - 成功连接到 test 环境数据库
2025-08-01 15:00:01,566 - INFO - 查询到 11 个AI角色
2025-08-01 15:00:01,569 - INFO - 成功导出 11 个AI角色到文件: agents_export.json

2025-08-01 16:18:22,474 - INFO - 开始向 production 环境导入AI角色
2025-08-01 16:18:22,475 - INFO - 读取到 11 个AI角色待导入
2025-08-01 16:18:22,954 - INFO - 成功连接到 production 环境数据库
2025-08-01 16:18:23,386 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:24,357 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:24,891 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:25,325 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:25,695 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:26,006 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:26,374 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:26,744 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:27,057 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:27,501 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:27,869 - WARNING - 使用默认创建者 user-01K0V3RK5H4BCFHGS1H6BBTZ4R 替代不存在的创建者 user-01JWZ34Y4D1C92GD86A5R6EWYJ
2025-08-01 16:18:27,949 - INFO - 导入完成: 成功 11, 跳过 0, 错误 0
```

## 故障排除

### 连接数据库失败

- 检查数据库主机、端口、用户名、密码是否正确
- 确认数据库服务是否运行
- 检查网络连接和防火墙设置

### 导入失败

- 检查导入文件格式是否正确
- 查看日志文件中的具体错误信息
- 确认目标数据库表结构是否匹配

### 权限错误

- 确保数据库用户有agents表和users表的读写权限
- 检查是否有外键约束限制

## 示例工作流

1. 导出测试环境数据：

```bash
python agent_migration.py export --from test
```

2. 检查导出文件：

```bash
# 查看导出的角色数量和基本信息
head -20 agents_export.json
```

3. 导入到生产环境：

```bash
python agent_migration.py import --to production --file agents_export.json
```

4. 验证导入结果：

```bash
# 检查日志
tail -50 migration.log
```
