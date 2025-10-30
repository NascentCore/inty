# 数据库迁移文档索引

## 📚 文档结构

本目录包含完整的数据库迁移指南和工具，帮助你安全、高效地将数据从一个 PostgreSQL 数据库服务器迁移到另一个。

### 1️⃣ [完整迁移指南](./DATABASE_MIGRATION_GUIDE.md)
**适合**: 第一次迁移，需要了解完整流程和原理

**内容**:
- 三种迁移方案详解（pg_dump、逻辑复制、表级 COPY）
- 完整的步骤说明（准备、导出、导入、验证、优化）
- 故障排除和常见问题
- 回滚计划
- 性能参考

**推荐阅读顺序**: 从头到尾完整阅读一遍

---

### 2️⃣ [快速参考卡](./DATABASE_MIGRATION_QUICK_REFERENCE.md)
**适合**: 已经熟悉流程，需要快速查找命令

**内容**:
- 快速开始命令
- 常用 PostgreSQL 命令
- 故障排除快速解决方案
- 性能优化技巧
- 验证检查清单

**使用方式**: 作为速查手册，需要时查找特定命令

---

### 3️⃣ [实战示例](./DATABASE_MIGRATION_EXAMPLE.md)
**适合**: 通过真实场景学习迁移流程

**内容**:
- 完整的生产环境迁移案例
- 使用自动化脚本的详细步骤
- 手动执行的完整流程
- 实际问题解决案例
- 监控和验证方法

**使用方式**: 参考示例，根据实际情况调整

---

### 4️⃣ [自动化迁移脚本](./scripts/migrate_database.sh)
**适合**: 需要自动化执行迁移流程

**功能**:
- 自动化完整迁移流程
- 内置检查和验证
- 支持 Dry Run 模式
- 生成详细迁移报告
- 错误处理和日志记录

**使用方式**:
```bash
# 查看帮助
./scripts/migrate_database.sh --help

# Dry Run 测试
./scripts/migrate_database.sh --dry-run \
    --source-host SOURCE_HOST --source-db SOURCE_DB \
    --sink-host SINK_HOST --sink-db SINK_DB

# 正式执行
./scripts/migrate_database.sh \
    --source-host SOURCE_HOST --source-db SOURCE_DB \
    --sink-host SINK_HOST --sink-db SINK_DB \
    --parallel-jobs 8
```

---

## 🚀 快速开始（5 分钟）

### 场景：你需要从 db1.example.com 迁移到 db2.example.com

```bash
# 1. 测试连接
psql -h db1.example.com -U postgres -d mydb -c "SELECT 1"
psql -h db2.example.com -U postgres -d mydb -c "SELECT 1"

# 2. Dry Run 测试（推荐）
./scripts/migrate_database.sh --dry-run \
    --source-host db1.example.com --source-db mydb \
    --sink-host db2.example.com --sink-db mydb

# 3. 正式迁移
./scripts/migrate_database.sh \
    --source-host db1.example.com --source-db mydb \
    --sink-host db2.example.com --sink-db mydb \
    --parallel-jobs 4

# 4. 查看报告
# 脚本执行完成后会显示备份目录路径
cd /tmp/db_migration_XXXXXX
cat migration_report.txt
cat row_count_comparison.txt

# 5. 测试应用连接
# 更新应用配置指向 db2.example.com
# 测试应用功能是否正常
```

---

## 📋 选择合适的方案

### 方案对比

| 方案 | 数据量 | 停机时间 | 复杂度 | 推荐度 |
|------|--------|----------|--------|--------|
| **自动化脚本（pg_dump）** | < 100GB | 短（几小时） | ⭐ 简单 | ⭐⭐⭐⭐⭐ |
| 手动 pg_dump | < 100GB | 短（几小时） | ⭐⭐ 中等 | ⭐⭐⭐ |
| 逻辑复制 | > 100GB | 极短（分钟） | ⭐⭐⭐⭐ 复杂 | ⭐⭐⭐⭐ |
| 表级 COPY | 任意 | 中等 | ⭐⭐⭐ 中等 | ⭐⭐ |

### 决策树

```
数据量 < 100GB?
├─ 是 → 可以接受几小时停机?
│   ├─ 是 → ✅ 使用自动化脚本（推荐）
│   └─ 否 → 考虑逻辑复制
└─ 否 → 数据量 > 500GB?
    ├─ 是 → ✅ 使用逻辑复制
    └─ 否 → ✅ 使用自动化脚本（可行）
```

---

## ⚠️ 迁移前必读

### 关键前置条件
- [ ] SOURCE 和 SINK schema 完全一致
- [ ] SINK 数据库为空（或准备清空）
- [ ] 有足够的磁盘空间（至少 2 倍数据量）
- [ ] 测试数据库连接正常
- [ ] 准备好回滚方案
- [ ] 通知相关人员（如需停机）

### 风险提示
- ⚠️ 迁移过程中可能需要停止应用写入
- ⚠️ 大数据量迁移可能需要几小时
- ⚠️ 必须有回滚方案
- ⚠️ 建议先在测试环境完整演练

---

## 📞 获取帮助

### 文档导航
1. **不知道从哪开始？** → 阅读 [完整迁移指南](./DATABASE_MIGRATION_GUIDE.md)
2. **需要快速命令？** → 查看 [快速参考卡](./DATABASE_MIGRATION_QUICK_REFERENCE.md)
3. **想看实际例子？** → 参考 [实战示例](./DATABASE_MIGRATION_EXAMPLE.md)
4. **需要自动化？** → 使用 [迁移脚本](./scripts/migrate_database.sh)

### 常见问题快速链接
- [外键约束违反](./DATABASE_MIGRATION_QUICK_REFERENCE.md#问题-1外键约束违反)
- [序列值不正确](./DATABASE_MIGRATION_QUICK_REFERENCE.md#问题-2序列值不正确)
- [磁盘空间不足](./DATABASE_MIGRATION_QUICK_REFERENCE.md#问题-3磁盘空间不足)
- [大表导入缓慢](./DATABASE_MIGRATION_QUICK_REFERENCE.md#问题-4大表导入缓慢)

### 脚本选项
```bash
./scripts/migrate_database.sh --help
```

---

## 🎯 最佳实践

1. **充分准备**
   - 先在测试环境完整演练
   - 准备详细的迁移计划
   - 确保有足够的时间窗口

2. **使用工具**
   - 优先使用自动化脚本
   - 利用 Dry Run 模式测试
   - 保存所有日志和报告

3. **验证验证再验证**
   - 比对表行数
   - 验证外键完整性
   - 测试应用功能
   - 监控性能指标

4. **安全第一**
   - 始终准备回滚方案
   - 保留 SOURCE 作为备份
   - 分阶段上线（先测试一台）
   - 密切监控迁移后的系统

---

## 📈 迁移流程图

```
┌─────────────────┐
│  1. 准备阶段    │  检查环境、测试连接、确认前置条件
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. 导出阶段    │  从 SOURCE 导出数据和序列
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. 导入阶段    │  导入数据到 SINK，重置序列
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. 验证阶段    │  比对数据，验证完整性
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. 优化阶段    │  更新统计信息，VACUUM
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. 测试阶段    │  测试应用，验证功能
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  7. 上线阶段    │  切换配置，全量上线
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  8. 监控阶段    │  持续监控，确保稳定
└─────────────────┘
```

---

## 🔄 版本历史

- **v1.0** (2025-10-30)
  - 初始版本
  - 包含完整指南、快速参考、实战示例
  - 自动化迁移脚本

---

## 📝 反馈和改进

如果你在使用过程中遇到问题或有改进建议：
1. 查看相关文档的故障排除部分
2. 联系 DevOps 团队
3. 更新文档记录新的问题和解决方案

---

**最后更新**: 2025-10-30  
**维护者**: DevOps Team  
**项目**: Inty Backend
