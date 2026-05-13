# 同步角色 Dev 与 Prod

在 dev 与 prod 环境之间同步角色数据，支持两个方向。

## 功能特性

- **dev-to-prod**：从 dev 同步指定运营用户创建的角色到 prod
- **prod-to-dev**：从 prod 按名称同步指定角色到 dev
- 支持创建和更新操作
- 自动检查并创建目标环境的运营用户
- 智能处理 readable_id 冲突，自动生成新的自增 ID
- Dry-run 模式预览更改
- 详细的日志记录

## 同步逻辑

同步操作按以下顺序执行：

1. **更新**：源和目标都存在且字段不同的角色会被更新
2. **创建**：源存在但目标不存在的角色会被创建

操作顺序说明：先更新后创建。如果创建时 readable_id 冲突，会自动生成新的自增 ID

补充说明：当目标库存在同 `id` 的软删除角色时，会按“更新”处理并自动恢复（`deleted_at` 置空），不会重复插入。

## 配置

复制配置文件示例并修改数据库连接信息：

```bash
cp config.yaml.example config.yaml
```

编辑 config.yaml 文件，配置：

- dev 和 prod 数据库连接信息
- 运营用户 ID 和基本信息
- 日志级别

## 使用方法

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库连接

编辑 config.yaml 文件，确保数据库连接信息正确。

### 3. 预览同步操作

先运行预览模式，查看将要执行的操作。

**dev-to-prod（默认）**：

```bash
python sync_agents.py --dry-run
```

**prod-to-dev（按名称同步单个角色）**：

```bash
python sync_agents.py --direction prod-to-dev --agent-name IntelliMate --dry-run
```

预览输出示例：

```
========================================================
开始同步角色数据
方向: Dev → Prod
模式: 预览模式 (dry-run)
========================================================
Dev环境找到 15 个角色
Prod环境找到 12 个角色

同步计划:
  需要创建: 5 个角色
  需要更新: 2 个角色
  无需变更: 10 个角色

【预览模式】以下是详细操作列表:

创建角色列表:
  ✨ 创建: Amber (ID: agent-xxx)
  ✨ 创建: Lily (ID: agent-yyy)
  ...

更新角色列表:
  🔄 更新: Sophie (ID: agent-zzz)
  ...
```

### 4. 执行同步

确认预览结果无误后，执行实际同步。

**dev-to-prod**：

```bash
python sync_agents.py
```

**prod-to-dev**：

```bash
python sync_agents.py --direction prod-to-dev --agent-name IntelliMate
```

执行输出示例：

```
数据库连接成功
Dev环境运营用户: admin (user-01JWZ34Y4D1C92GD86A5R6EWYJ)
运营用户已存在: user-01JWZ34Y4D1C92GD86A5R6EWYJ

开始执行同步操作...
操作顺序：1) 更新 → 2) 创建

第 1 步：执行更新操作...
🔄 更新成功: Sophie (ID: agent-zzz)

第 2 步：执行创建操作...
⚠️  readable_id 冲突: 10000002 已存在，使用新 ID: 10000015
✨ 创建成功: Amber (ID: agent-xxx)
✨ 创建成功: Lily (ID: agent-yyy)

========================================================
同步完成！
  创建: 5 个
  更新: 2 个
========================================================
```

## 命令行参数

- `--config <path>`: 指定配置文件路径（默认: config.yaml）
- `--direction`: 同步方向，`dev-to-prod` 或 `prod-to-dev`（默认: dev-to-prod）
- `--agent-name <name>`: 按名称筛选角色；prod-to-dev 时必填
- `--dry-run`: 预览模式，不实际执行操作

## 注意事项

1. **运营用户**: 如果目标环境不存在运营用户，脚本会自动创建
2. **prod-to-dev**: 必须指定 `--agent-name`；若 prod 中不存在该名称的角色，脚本会报错退出
3. **readable_id 冲突**: 如果创建角色时 readable_id 已存在，会自动生成新的自增 ID 并记录警告
4. **事务安全**: 所有操作在一个事务中执行，如有错误会自动回滚
5. **字段同步**: 同步所有角色相关字段，但不包括 created_at, updated_at, deleted_at
6. **建议流程**: 先运行 dry-run 预览，确认无误后再执行实际同步

## 故障排除

### 数据库连接失败

检查配置文件中的数据库连接信息是否正确，确认数据库服务正在运行。

### 运营用户不存在

脚本会自动在目标环境创建运营用户。dev-to-prod 时需确保 dev 环境中该用户存在；prod-to-dev 时需确保 prod 中角色的 creator 在 dev 中存在（或为运营用户）。

### prod-to-dev 时提示「不存在名为 X 的未删除角色」

确认 prod 数据库中确实存在该名称的角色，且未被软删除（deleted_at 为空）。

### 同步失败

查看详细日志输出，检查具体错误信息。所有失败的操作会自动回滚，不会影响数据一致性。
