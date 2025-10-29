# Agent Tags Migration - 标签迁移

这个工具用于从智能体的 `personality` 字段中提取标签信息，并将其迁移到 `tags` 字段中。

## 功能特性

- **智能解析**: 自动识别和解析 personality 字段中的 Character info 结构
- **多格式支持**: 支持多种 JSON 格式和引号形式
- **安全迁移**: 提供分析模式和备份机制
- **批量处理**: 支持大规模数据的分批处理
- **标签标准化**: 自动清理和标准化提取的标签
- **详细日志**: 完整的操作日志和统计信息

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置文件

复制配置文件示例并修改数据库连接信息：

```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml 文件，设置正确的数据库连接信息
```

## 使用方法

### 1. 分析模式（推荐先运行）

分析现有数据，查看可以提取多少标签，不会修改数据库：

```bash
python extract_tags_from_personality.py --analyze
```

### 2. 执行迁移

确认分析结果后，执行实际的迁移操作：

```bash
python extract_tags_from_personality.py --update
```

### 3. 高级选项

```bash
# 指定配置文件
python extract_tags_from_personality.py --config /path/to/config.yaml --analyze

# 设置批处理大小
python extract_tags_from_personality.py --batch-size 50 --update

# 设置日志级别
python extract_tags_from_personality.py --log-level DEBUG --analyze

# 指定日志文件
python extract_tags_from_personality.py --log-file migration.log --update

# 不跳过已有标签的智能体
python extract_tags_from_personality.py --update --no-skip-existing

# 不标准化标签
python extract_tags_from_personality.py --update --no-normalize
```

## 支持的数据格式

工具可以解析以下格式的 Character info：

### 格式1：标准JSON格式

```
##Charactor info:
{'name': 'Layla', 'age': 26, 'gender': 'FEMALE', 'tags': 'Dancer, Sexy, Exotic, Singer'}
```

### 格式2：双引号JSON格式

```
##Character info:
{"name": "Layla", "age": 26, "gender": "FEMALE", "tags": "Dancer, Sexy, Exotic, Singer"}
```

### 格式3：混合引号格式

```
##角色信息:
{'name': "Layla", 'tags': "Dancer, Sexy, Exotic, Singer"}
```

## 输出信息

### 分析模式输出

```
=== 分析模式 ===
2024-01-15 10:30:00 | INFO     | 开始分析智能体数据...
2024-01-15 10:30:01 | INFO     | 找到 150 个包含personality字段的智能体
2024-01-15 10:30:05 | INFO     | [100/150] (66.7%) 已分析 50 个智能体
...

迁移完成！统计信息:
  总智能体数: 150
  成功提取: 120
  提取失败: 30
  执行时间: 4.52 秒

最常见的标签:
  Sexy: 45
  Beautiful: 38
  Intelligent: 32
  Dancer: 28
  Singer: 25
```

### 更新模式输出

```
=== 迁移模式 ===
2024-01-15 10:35:00 | INFO     | 开始执行标签迁移...
2024-01-15 10:35:01 | INFO     | 准备迁移 150 个智能体的标签
2024-01-15 10:35:05 | INFO     | ✓ 更新成功: Layla - 标签: Dancer, Sexy, Exotic, Singer
...

迁移完成！统计信息:
  总智能体数: 150
  成功提取: 120
  提取失败: 30
  更新成功: 115
  跳过处理: 5
  执行时间: 6.78 秒
```

## 安全特性

### 1. 分析模式

- 先运行分析模式查看结果，确认无误后再执行迁移

### 2. 自动备份

- 更新前自动备份相关数据
- 备份文件保存为 `backup_batch_N_timestamp.json`

### 3. 事务控制

- 批量更新使用数据库事务，确保数据一致性

### 4. 跳过已有标签

- 默认跳过已有标签的智能体，避免覆盖现有数据

## 故障排除

### 1. 数据库连接失败

```
错误: 无法连接到数据库: connection refused
```

- 检查 config.yaml 中的数据库配置
- 确认数据库服务正在运行
- 检查网络连接和防火墙设置

### 2. 没有找到可提取的标签

```
统计信息显示成功提取为0
```

- 检查 personality 字段中是否包含 Character info 结构
- 确认 tags 字段格式是否正确
- 可以设置 `--log-level DEBUG` 查看详细解析过程

### 3. 权限错误

```
错误: permission denied
```

- 确认数据库用户有相应的读写权限
- 检查表结构是否正确

## 目录结构

```
agent_tags_migration/
├── README.md                           # 项目说明文档
├── requirements.txt                    # Python依赖
├── config.yaml.example                # 配置文件示例
├── extract_tags_from_personality.py   # 主要迁移脚本
├── models.py                          # 数据模型定义
├── database.py                        # 数据库操作封装
├── tag_parser.py                      # 标签解析逻辑
├── logger.py                          # 日志配置
└── tests/                             # 测试文件
    ├── test_tag_parser.py             # 标签解析测试
    ├── test_database.py               # 数据库操作测试
    └── sample_data.py                 # 测试数据样本
```

## 贡献

如果发现问题或有改进建议，请创建 Issue 或提交 Pull Request。

## 许可证

本项目使用 MIT 许可证。
