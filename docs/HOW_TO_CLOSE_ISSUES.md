# 如何关闭已实现的 Issues - 快速指南

## 三种方法，任选其一

### 方法 1️⃣: 手动关闭（最简单，推荐）⭐

**时间**: 约 4 分钟  
**难度**: ⭐☆☆☆☆

1. 打开文档：[`docs/QUICK_CLOSE_ISSUES_COMMENTS.md`](./QUICK_CLOSE_ISSUES_COMMENTS.md)
2. 逐个复制关闭评论
3. 访问对应的 Issue 页面并粘贴评论
4. 点击 "Close with comment" 按钮

**Issues 链接**：
- [Issue #1360](https://github.com/NascentCore/inty/issues/1360) - Room 数据库集成
- [Issue #1691](https://github.com/NascentCore/inty/issues/1691) - inty setting 数据存储
- [Issue #582](https://github.com/NascentCore/inty/issues/582) - 角色标签功能
- [Issue #771](https://github.com/NascentCore/inty/issues/771) - AI 主动消息

---

### 方法 2️⃣: 使用 GitHub CLI（可批量）

**时间**: 首次设置 5 分钟 + 运行 1 分钟  
**难度**: ⭐⭐⭐☆☆

#### 安装 GitHub CLI（首次）

```bash
# macOS
brew install gh

# Linux (Ubuntu/Debian)
sudo apt install gh

# Windows
winget install --id GitHub.cli
```

#### 认证（首次）

```bash
gh auth login
# 选择: GitHub.com → HTTPS → Yes (browser)
```

#### 运行脚本

```bash
cd /home/runner/work/inty/inty
chmod +x scripts/close_implemented_issues.sh
./scripts/close_implemented_issues.sh
```

脚本会自动关闭所有 4 个 Issues 并添加详细的关闭评论。

---

### 方法 3️⃣: 使用 Python 脚本

**时间**: 首次设置 10 分钟 + 运行 1 分钟  
**难度**: ⭐⭐⭐⭐☆

#### 创建 GitHub Token（首次）

1. 访问：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选权限：`repo`
4. 生成并复制 Token

#### 安装依赖（首次）

```bash
pip install PyGithub
```

#### 运行脚本

```bash
export GITHUB_TOKEN="your_token_here"
cd /home/runner/work/inty/inty
python scripts/close_implemented_issues.py
```

---

## 详细说明

如需了解更多细节，请查看：
- **权限说明**：[`docs/GITHUB_API_PERMISSIONS_AND_CLOSING_OPTIONS.md`](./GITHUB_API_PERMISSIONS_AND_CLOSING_OPTIONS.md)
- **关闭原因**：[`docs/ISSUES_TO_CLOSE_WITH_REASONS.md`](./ISSUES_TO_CLOSE_WITH_REASONS.md)
- **完整审查**：[`docs/OPEN_ISSUES_REVIEW_2026_02.md`](./OPEN_ISSUES_REVIEW_2026_02.md)

---

## 为什么 AI 不能直接关闭？

简短回答：**环境设计限制，无法扩展权限**。

AI 运行在预配置的沙箱环境中，GitHub 凭证由系统管理且不暴露。这是安全设计，确保重要操作需要人工审核。

详细解释见：[`docs/GITHUB_API_PERMISSIONS_AND_CLOSING_OPTIONS.md`](./GITHUB_API_PERMISSIONS_AND_CLOSING_OPTIONS.md)

---

**推荐使用方法 1**（手动关闭），最快最简单！
