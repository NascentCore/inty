# 🚀 快速开始指南

## 一键运行

```bash
cd experimental/user_analytics
python analyze_user_activity.py --last-days 3
```

## 查看报告

运行完成后，打开以下文件：

### 1. 📊 数据分析（图表）

```bash
open reports/user_analytics_report.html
```

**内容**：5 个交互式图表

- 每日新用户趋势
- 用户活跃度分布
- 热门角色排行
- 对话轮数分布
- 用户会话详情表

---

### 2. 💬 对话详情（强烈推荐！）⭐⭐⭐

```bash
open reports/conversations_detailed.html
```

**内容**：完整的用户对话查看器

- ✅ **按消息数降序排列**（最活跃用户在最前面）
- ✅ **认证类型筛选**（全部/游客/Google）
- ✅ **会话类型筛选**（全部/有用户消息/仅浏览开场白）⭐ 新增
- ✅ 点击用户卡片查看所有会话
- ✅ 聊天气泡样式展示对话内容
- ✅ 搜索用户 ID、昵称、邮箱、角色名称
- ✅ 显示用户昵称和邮箱（Google 用户）
- ✅ 统计信息：总浏览数 vs 总会话数（区分仅浏览和真实会话）⭐ 新增

**这是最有价值的报告！** 可以看到：

- 每个新用户说了什么
- AI 如何回复
- 哪些话题最受欢迎
- 对话质量如何

---

### 3. 📄 CSV 数据文件

可用 Excel 打开查看原始数据：

```bash
open reports/daily_new_users.csv
open reports/user_sessions_detail.csv
open reports/popular_agents.csv
```

---

## 常用命令

### 分析最近 7 天

```bash
python analyze_user_activity.py --last-days 7
```

### 指定日期范围

```bash
python analyze_user_activity.py \
  --start-date 2025-10-26 \
  --end-date 2025-10-28
```

### 仅查看统计（不生成文件）

```bash
python analyze_user_activity.py --last-days 3 --dry-run
```

### 自定义输出目录

```bash
python analyze_user_activity.py --last-days 7 --output-dir ./weekly_reports
```

---

## 💡 使用技巧

### 1. 快速查看新用户对话

1. 运行脚本（分析最近 1 天数据最快）

   ```bash
   python analyze_user_activity.py --last-days 1
   ```

2. 打开 `conversations_detailed.html`

3. 点击第一个用户卡片展开

4. 查看完整对话内容

### 2. 按认证类型筛选用户

1. 打开 `conversations_detailed.html`

2. 点击顶部的筛选按钮：

   - **全部**：显示所有用户
   - **🏷️ 游客**：只显示游客用户
   - **🔐 Google**：只显示 Google 认证用户

3. 查看对应类型的用户对话

### 3. 按会话类型筛选

1. 打开 `conversations_detailed.html`

2. 点击会话类型筛选按钮：

   - **全部**：显示所有用户
   - **✅ 有用户消息**：只显示真实聊天的用户
   - **👁️ 仅浏览开场白**：只显示看了开场白但没聊天的用户

3. 分析转化率：
   - 总浏览数 = 所有打开会话的用户
   - 总会话数 = 实际发送消息的用户
   - 转化率 = 总会话数 / 总浏览数

### 4. 搜索特定用户或角色

1. 打开 `conversations_detailed.html`

2. 在搜索框输入：

   - 用户 ID
   - 用户昵称
   - 邮箱地址
   - 角色名称（如 "Alice"）

3. 查看匹配的结果（可与认证类型和会话类型组合使用）

### 5. 分析活跃用户

1. 打开 `user_sessions_detail.csv`

2. 按 `message_count` 列排序

3. 查看消息数最多的用户

4. 在 `conversations_detailed.html` 中搜索该用户 ID

5. 查看具体对话内容

### 6. 发现热门话题

1. 打开 `conversations_detailed.html`

2. 浏览前 10 个用户的对话

3. 记录用户最常问的问题

4. 分析 AI 回复的质量

---

## 🐛 常见问题

### Q: 没有生成对话详情 HTML？

**A**: 检查日志，如果显示"未找到任何对话消息"，说明该时间范围内没有对话数据。尝试：

- 增加时间范围：`--last-days 7`
- 检查数据库连接
- 使用 `--dry-run` 查看统计信息

### Q: HTML 文件很大？

**A**: 正常现象，对话内容多时文件会较大。可以：

- 减少时间范围
- 对话内容已自动截断（超过 500 字符）

### Q: 搜索功能不工作？

**A**: 确保在浏览器中打开 HTML 文件，不要用文本编辑器打开。

### Q: 数据库连接失败？

**A**: 检查配置：

```bash
# 方法1：使用环境变量
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=yourpassword
export DB_NAME=inty

# 方法2：使用命令行参数
python analyze_user_activity.py --last-days 3 \
  --db-host localhost \
  --db-port 5432 \
  --db-user postgres \
  --db-password yourpassword \
  --db-name inty
```

---

## 📚 更多信息

- 完整文档：`README.md`
- 测试指南：`TEST_GUIDE.md`
- 技术细节：查看脚本注释

---

## 🎯 推荐工作流

1. **快速概览**：先用 `--dry-run` 查看数据量
2. **生成报告**：运行完整分析
3. **查看图表**：打开 `user_analytics_report.html` 了解趋势
4. **深入分析**：打开 `conversations_detailed.html` 查看对话细节
5. **数据导出**：需要时打开 CSV 文件进行进一步分析

---

Happy Analyzing! 📊💬✨
