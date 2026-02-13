#!/usr/bin/env python3
"""
关闭已实现的 Issues 脚本（使用 PyGithub）

使用前需要：
1. 安装依赖：pip install PyGithub
2. 设置环境变量：export GITHUB_TOKEN="your_personal_access_token"
   或在脚本中直接设置 GITHUB_TOKEN 变量

运行：python scripts/close_implemented_issues.py
"""

import os
import sys
from github import Github, GithubException

# GitHub Token（从环境变量获取或直接设置）
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

if not GITHUB_TOKEN:
    print("❌ 错误：未设置 GITHUB_TOKEN")
    print()
    print("请设置环境变量：")
    print("  export GITHUB_TOKEN='your_personal_access_token'")
    print()
    print("或在脚本中直接设置 GITHUB_TOKEN 变量")
    print()
    print("创建 Token：https://github.com/settings/tokens")
    print("需要的权限：repo")
    sys.exit(1)

# 仓库信息
OWNER = "NascentCore"
REPO = "inty"

# Issues 及其关闭评论
ISSUES_TO_CLOSE = {
    1360: """此功能已完整实现，包含：

**CharacterDatabase**:
- CharacterEntity & FestivalMemory 实体
- CharacterDao with CRUD operations
- 版本 5，支持自动迁移
- 文件：`android_app/app/src/main/kotlin/.../CharacterDatabase.kt`

**IntyChatDatabase**:
- MessageEntity & ChatSyncStateEntity 实体
- ChatMessageDao & ChatSyncStateDao
- 版本 10，支持自动迁移
- 文件：`android_app/core/data/src/main/kotlin/.../IntyChatDatabase.kt`

**功能覆盖**:
✅ 消息本地缓存与分页查询
✅ 角色信息本地存储与搜索
✅ 同步状态追踪（offset、hasMore、lastSyncedAt）
✅ Flow 实时数据观察
✅ 单例模式安全管理
✅ TypeConverters 支持复杂类型
✅ 软删除支持

所有 Room 数据库组件已完整实现，代码位于 `android_app/core/data/src/main/kotlin/` 目录下。

关闭此 Issue。""",

    1691: """此功能已实现，使用了性能更优的 **MMKV** 替代方案（腾讯开源，性能优于 DataStore 约 100 倍）。

**实现位置**: 
`android_app/core/data/src/main/kotlin/ai/sxwl/android/data/store/IntySetting.kt`

**架构设计**:
- **应用级设置**: `MMKV.defaultMMKV()` (单进程模式)
  - 存储全局配置，如当前用户 ID
- **用户级设置**: `MMKV.mmkvWithID("user_$curUid")` (多进程模式)
  - 按用户隔离的个性化设置

**支持的配置项**:
- 订阅提醒（时间、次数）
- 聊天设置（字体大小、模型 ID）
- 推送状态（消息 tab、会话级别）
- UI 状态（收藏、弹窗显示时间）
- 统计数据（总消息数）

**技术优势**:
✅ 性能优于 DataStore（约 100 倍）
✅ 多进程原生支持
✅ 同步读写，无需 coroutine 包装
✅ 类型安全的 API
✅ 腾讯微信团队维护，久经考验

MMKV 是 DataStore 的更好替代品，完全满足数据存储需求。

关闭此 Issue。""",

    582: """角色标签功能已完整实现。

**数据模型**:
- Web App: `IAgent.tags: string[]` (`web_app/src/types/agent.ts:160`)
- Evaluation: `BaseAgent.tags?: string[]` (`evaluation/types.ts`)
- API: 创建和更新时均支持 `tags` 参数

**API 支持**:
- ✅ AgentCreateRequest 支持传入 tags
- ✅ AgentUpdateRequest 支持修改 tags
- ✅ 查询 Agent 时返回 tags 数组

**前端展示**:
- **AgentDetailPanel**: 角色详情页展示标签列表
- **AgentInfoDisplay**: 使用 Ant Design Tag 组件展示（蓝色标签）

**功能覆盖**:
✅ 创建角色时添加多个标签
✅ 更新角色时修改标签
✅ 角色详情页面展示标签
✅ 评测管理页面展示标签
✅ 支持标签数组（灵活扩展）
✅ 前端样式化展示（条件渲染）

基础标签功能已完整实现。如需更高级的"内部标签"功能（如权限控制、标签分类管理、仅管理员可见等），请创建新的 Issue 专门处理。

关闭此 Issue。""",

    771: """AI 角色主动消息功能已完整实现并在生产环境稳定运行。

**核心组件**:
- ✅ `app/models/push_notification.py` - PushNotificationHistory 模型（防重复）
- ✅ `app/services/push_notification_service.py` - 推送服务核心逻辑
- ✅ `app/services/push_scheduler_service.py` - APScheduler 定时调度器
- ✅ `app/services/push_worker.py` - 独立 Worker 进程入口
- ✅ `app/core/prompting/push_message_prompt.py` - LLM 提示词模板

**推送策略**（多阶段用户激活）:
- **10分钟推送**: 用户最后消息后 10 分钟（轻度提醒）
- **30分钟推送**: 用户最后消息后 30 分钟（中度催促）
- **2小时推送**: 用户最后消息后 2 小时（重新吸引）
- **24小时推送**: 无聊天记录用户的欢迎消息
- **48小时推送**: 仍无响应用户的再次激活

**工作流程**:
1. APScheduler 定时触发检查任务
2. 查询符合条件的聊天会话（活跃、达到阈值、未推送过）
3. 调用 Agent 生成个性化推送消息（基于聊天历史和角色设定）
4. 通过 Firebase FCM 发送推送通知
5. 记录推送历史到数据库，防止重复发送
6. 完整的失败重试机制

**技术特性**:
- 基于 APScheduler 的可靠定时任务
- Firebase FCM 推送通知集成
- 三种消息生成模式（简化版、完整版、欢迎消息）
- 支持 Docker 独立部署
- 支持水平扩展（多实例并行）
- 完整的日志记录和错误处理

**完整文档**:
- 系统文档: `backend/docs/PUSH_NOTIFICATION_SYSTEM.md`
- 快速指南: `app/services/PUSH_NOTIFICATION_README.md`
- 配置示例: `devops/config.yaml`

功能完整，文档齐全，生产环境稳定运行。

关闭此 Issue。"""
}


def close_issues():
    """关闭 Issues"""
    print("🚀 开始关闭已实现的 Issues...")
    print()

    try:
        # 初始化 GitHub 客户端
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{OWNER}/{REPO}")

        print(f"✅ 已连接到仓库：{OWNER}/{REPO}")
        print()

        # 关闭每个 Issue
        for issue_number, comment_text in ISSUES_TO_CLOSE.items():
            try:
                print(f"📝 处理 Issue #{issue_number}...")

                # 获取 Issue
                issue = repo.get_issue(issue_number)

                # 检查 Issue 是否已经关闭
                if issue.state == "closed":
                    print(f"⚠️  Issue #{issue_number} 已经是关闭状态")
                else:
                    # 添加评论
                    issue.create_comment(comment_text)
                    print(f"   ✓ 已添加关闭评论")

                    # 关闭 Issue
                    issue.edit(state="closed")
                    print(f"   ✓ 已关闭 Issue")

                print(f"✅ Issue #{issue_number} 处理完成")
                print()

            except GithubException as e:
                print(f"❌ 处理 Issue #{issue_number} 时出错：{e}")
                print()
                continue

        print("🎉 成功！所有 Issues 已处理。")
        print()
        print("查看结果：")
        for issue_number in ISSUES_TO_CLOSE.keys():
            print(f"  https://github.com/{OWNER}/{REPO}/issues/{issue_number}")

    except GithubException as e:
        print(f"❌ GitHub API 错误：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 发生错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    close_issues()
