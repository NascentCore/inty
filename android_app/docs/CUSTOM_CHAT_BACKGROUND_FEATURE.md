# 自定义聊天背景功能文档

## 功能概述

允许用户从 AI 生成的图片中选择任意一张作为该角色的聊天背景。这是一个纯本地功能，所有设置存储在设备本地，无需与后端交互。

## 功能入口

### 1. 角色主页（AgentInfoScreen）

在角色主页的 "AI-Generated Images" 画廊中：

- **设置背景**：点击任意图片打开全屏预览，在预览界面右下角点击 "Set as Chat Background" 按钮
- **查看当前背景**：如果某张图片已被设置为背景，会在图片右上角显示一个绿色圆点指示器
- **重置背景**：长按已设置为背景的图片，会弹出确认对话框，点击 "Reset" 可恢复为默认背景

### 2. 聊天页面（ChatPage）

在聊天消息中显示的 AI 生成图片：

- **设置背景**：点击消息中的生成图片打开全屏预览，在预览界面右下角点击 "Set as Chat Background" 按钮
- 设置成功后会自动关闭预览并显示成功提示

## 技术实现

### 数据存储

使用 `IntySetting` 存储每个角色的自定义背景图片 URL：

- **存储键格式**：`"chat_background_$agentId"`
- **存储方法**：`IntySetting.setChatBackgroundImage(agentId, imageUrl)`
- **读取方法**：`IntySetting.getChatBackgroundImage(agentId)`
- **清除方法**：`IntySetting.clearChatBackgroundImage(agentId)`

### 背景显示优先级

在 `AgentBackground` 组件中，背景图片的显示优先级为：

1. **自定义背景**（如果已设置）
2. **动画背景**（`backgroundAnimatedUrl`，如果存在）
3. **默认静态背景**（`agentInfo.getOriginShowImage()`）
4. **IntelliMate 官方背景**（如果是官方角色）

**注意**：自定义背景仅适用于静态背景，不会覆盖动画背景。如果角色有动画背景，自定义背景将被忽略。

### 实时更新机制

由于 `IntySetting` 不是响应式的，`AgentBackground` 组件使用以下机制确保背景能及时更新：

1. 使用 `mutableStateOf` 存储 `customBackgroundUrl`
2. 使用 `LaunchedEffect` 定期检查（每 500ms）背景设置是否变化
3. 只在当前页面（`isCurrentPage == true`）时检查，减少资源消耗
4. 使用 `key(staticImageUrl)` 确保背景 URL 改变时强制重新组合图片组件

### UI 组件

#### FullScreenImageViewer

全屏图片查看器支持可选的操作按钮：

- `onAction: (() -> Unit)?` - 操作按钮的回调
- `actionLabel: String?` - 操作按钮的文本标签

当提供这两个参数时，会在预览界面右下角显示操作按钮。

#### AgentGalleryImageCard

画廊图片卡片支持：

- 点击打开全屏预览
- 长按已设置为背景的图片显示重置对话框
- 显示绿色圆点指示器标识当前背景

## 字符串资源

所有用户可见的文本都定义在 `strings.xml` 中：

- `agent_gallery_set_as_background` - "Set as Chat Background"
- `agent_gallery_background_set_success` - "Background updated"
- `agent_gallery_reset_background` - "Reset to Default Background"
- `agent_gallery_background_reset_success` - "Background reset to default"

## 使用限制

1. **仅限静态背景**：自定义背景不会覆盖动画背景
2. **本地存储**：所有设置仅存储在本地，不会同步到服务器
3. **按角色存储**：每个角色的背景设置是独立的
4. **更新延迟**：设置背景后，最多需要 500ms 才能看到更新（由于定期检查机制）

## 代码文件

### 核心实现

- `core/data/src/main/kotlin/ai/sxwl/android/data/store/IntySetting.kt` - 存储方法
- `app/src/main/kotlin/com/ai/intellimate/ui/components/AgentBackground.kt` - 背景显示逻辑
- `app/src/main/kotlin/com/ai/intellimate/chat/ui/FullScreenImageViewer.kt` - 全屏预览组件

### UI 集成

- `app/src/main/kotlin/com/ai/intellimate/agent/info/AgentInfoScreen.kt` - 角色主页集成
- `app/src/main/kotlin/com/ai/intellimate/chat/ChatItem.kt` - 聊天页面集成

### 资源文件

- `app/src/main/res/values/strings.xml` - 字符串资源

## 未来改进建议

1. **响应式存储**：考虑将 `IntySetting` 改为使用 `StateFlow` 或类似机制，实现真正的响应式更新
2. **即时更新**：在设置背景后立即触发更新，而不是等待定期检查
3. **背景预览**：在设置前提供背景预览功能
4. **多背景管理**：支持为同一角色设置多个背景并切换
5. **云端同步**：如果需要，可以将背景设置同步到服务器

