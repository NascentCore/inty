# Android App 聊天 UI 实现架构文档

## 概述

Android app 的聊天 UI 采用 Jetpack Compose 构建，遵循 MVVM 架构模式，使用 Clean Architecture 分层设计。支持多 Agent 横向滑动、分页加载历史消息、语音播放、实时消息同步等功能。

## 架构层次

```
┌─────────────────────────────────────────────────────────┐
│                    UI Layer (Compose)                    │
│  ChatPageContainer → ChatPage → ChatItem/ChatInput     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   ViewModel Layer                       │
│  ChatTabViewModel → ChatViewModel (StateFlow)          │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   Domain Layer                          │
│  UseCases (SendMessage, LoadChatHistory, SyncData)     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                            │
│  ChatRepository → ChatLocalDataSource + RemoteDataSource│
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. ChatPageContainer（容器层）

**文件**: `app/src/main/kotlin/com/ai/intellimate/chat/ChatPageContainer.kt`

**职责**:
- 管理多个 Agent 的横向滑动（使用 `HorizontalPager`）
- 为每个 Agent 创建独立的 `ChatViewModel` 实例
- 处理页面切换时的状态管理
- 实现新用户引导功能

**关键特性**:
```kotlin
// 使用 HorizontalPager 支持多 Agent 横向滑动
HorizontalPager(
    state = pageState,
    beyondViewportPageCount = 3, // 预加载左右各3个页面
) { currentPage ->
    val chatViewModel: ChatViewModel = viewModel(key = agent.id, factory = viewModelFactory)
    ChatPage(chatViewModel = chatViewModel, ...)
}
```

**特点**:
- ✅ **按需创建 ViewModel**: 使用 `viewModel(key = agent.id)` 为每个 Agent 创建独立实例
- ✅ **预加载优化**: `beyondViewportPageCount = 3` 预加载相邻页面
- ✅ **静默预取**: 滑到倒数第5个时自动加载下一页数据
- ✅ **状态隔离**: 每个 Agent 的聊天状态完全独立

### 2. ChatPage（主页面）

**文件**: `app/src/main/kotlin/com/ai/intellimate/chat/ChatPage.kt`

**职责**:
- 渲染聊天界面布局
- 管理消息列表显示
- 处理用户交互（输入、发送、设置等）
- 协调各个子组件

**布局结构**:
```
ChatPage
├── AgentBackground (背景图片)
├── Scaffold
│   ├── ChatTopBar (顶部栏)
│   ├── PremiumModelTag (Premium标签)
│   ├── LazyColumn (消息列表 - 反向布局)
│   │   ├── 加载更多指示器（顶部）
│   │   ├── Agent Intro + Opening（顶部）
│   │   └── 消息列表（ChatItem）
│   └── ChatInput (输入框)
├── ChatMorePanel (更多面板)
├── ChatSettingsDrawer (设置抽屉)
└── ShowLimitDialog (限制弹窗)
```

**关键实现**:

#### 反向布局（Reverse Layout）
```kotlin
LazyColumn(
    state = listState,
    reverseLayout = true, // ⚠️ 关键：列表是反向的
) {
    // 最新消息在底部，但列表顶部显示
    // 滚动到顶部 = 加载更早的消息
}
```

**为什么使用反向布局？**
- 新消息自动显示在底部（用户可见区域）
- 符合用户习惯：最新消息在底部
- 滚动到顶部加载历史消息更自然

#### 智能加载更多
```kotlin
// 监听滚动状态，智能触发加载更多
LaunchedEffect(hasMoreMessages, isLoadingMore, chatMessages.size) {
    snapshotFlow {
        listState.firstVisibleItemIndex to listState.firstVisibleItemScrollOffset
    }.collect { (firstVisibleIndex, scrollOffset) ->
        // 在反向布局中，接近顶部时触发加载
        val isNearTop = lastVisibleIndex >= (totalItemsCount - LOAD_MORE_NEAR_TOP_THRESHOLD)
        if (shouldLoadMore && hasMoreMessages && !isLoadingMore) {
            chatViewModel.loadMoreMessages()
        }
    }
}
```

#### 动态底部间距
```kotlin
val bottomPadding = when {
    showBackButton -> ChatInputBottomSpacerHeight // 独立页面
    isKeyboardVisible -> ChatInputBottomSpacerHeight // 键盘弹出
    else -> BottomNavigationBarHeight + ChatInputBottomSpacerHeight // 首页无键盘
}
```

### 3. ChatItem（消息项）

**文件**: `app/src/main/kotlin/com/ai/intellimate/chat/ChatItem.kt`

**职责**:
- 渲染单条消息内容
- 区分用户消息和 AI 消息
- 处理语音播放
- 支持文本格式化（动作描写、旁白等）

**消息类型**:

#### 用户消息（ChatItemUser）
```kotlin
Row {
    Spacer(modifier = Modifier.widthIn(80.dp).weight(1f)) // 左侧留白
    Box(
        modifier = Modifier
            .background(Color.White.copy(alpha = 0.6f), RoundedCornerShape(12.dp))
            .padding(12.dp, 13.dp)
            .widthIn(1.dp, 300.dp)
    ) {
        StyledMessageText(...) // 格式化文本
    }
}
```

#### AI 消息（ChatItemAI）
```kotlin
Column {
    // 语音播放按钮
    VoicePlayer(
        audioInfo = audioInfo,
        autoPlay = shouldAutoPlay, // 开场白自动播放
        onTtsGenerated = { audioUrl ->
            viewModel.updateMessageAudioUrl(item.localMsgId, audioUrl)
        }
    )
    
    // 消息内容
    Row {
        Box(
            modifier = Modifier
                .background(Color.Black.copy(alpha = 0.5f), msgShape)
                .padding(12.dp, 13.dp)
                .widthIn(1.dp, 300.dp)
        ) {
            StyledMessageText(...) // 格式化文本
        }
        Spacer(modifier = Modifier.widthIn(80.dp).weight(1f)) // 右侧留白
    }
}
```

**文本格式化**:
- 使用 `ChatTextFormatter.formatChatMessage()` 处理文本样式
- 区分普通文本和动作描写（斜体、不同颜色）
- 支持旁白括号 `()` 的特殊显示

**开场白自动播放逻辑**:
```kotlin
val shouldAutoPlay =
    item.isOpening() &&
    isOnlyOpeningMessage &&
    !hasPlayedOpening &&
    isCurrentPage &&
    isQueryMsgsCompleted &&
    safeAgentId.isNotEmpty() &&
    audioInfo.url.isNotEmpty()
```

### 4. ChatInput（输入框）

**文件**: `app/src/main/kotlin/com/ai/intellimate/chat/ui/ChatInput.kt`

**职责**:
- 处理用户输入
- 提供发送按钮
- 支持旁白输入（括号按钮）
- 显示更多面板切换

**关键功能**:

#### 旁白输入
```kotlin
// 在光标位置插入括号
insertParenthesesAtCursor(
    currentText = inputData.value,
    currentSelection = chatViewModel.inputSelection.value,
    onTextUpdate = { newText -> chatViewModel.inputData.value = newText }
)
```

#### 多功能按钮
```kotlin
// 有输入时显示发送按钮，无输入时显示更多按钮
if (hasInput) {
    AsyncImage(/* 发送按钮 */)
} else {
    AsyncImage(/* 更多按钮 */)
}
```

#### 键盘处理
```kotlin
val imeHeight = WindowInsets.ime.getBottom(density)
val isKeyboardVisible = imeHeight > 0
// 动态调整底部间距
```

### 5. ChatViewModel（状态管理）

**文件**: `app/src/main/kotlin/com/ai/intellimate/chat/viewmodel/ChatViewModel.kt`

**职责**:
- 管理聊天状态（消息列表、Agent 信息、输入状态）
- 处理业务逻辑（发送消息、加载历史、同步数据）
- 协调 Repository 层数据操作

**状态管理**:
```kotlin
// 使用 StateFlow 替代 mutableStateListOf，解决并发问题
private val _msgs = MutableStateFlow<List<MsgInfo>>(emptyList())
val msgs = _msgs.asStateFlow()

private val _agentInfo = MutableStateFlow<AgentInfo?>(null)
val agentInfo = _agentInfo.asStateFlow()

val inputData = MutableStateFlow<String>("")
val inputSelection = MutableStateFlow<Int>(0)
```

**数据流绑定**:
```kotlin
private fun bindToAgentSession(agentId: String) {
    // 绑定到 ChatSessionManager，监听数据变化
    messagesJob = viewModelScope.launch(Dispatchers.IO) {
        chatRepository.getMessagesFlow(agentId).collect { list ->
            _msgs.value = list // 自动更新 UI
        }
    }
}
```

**关键方法**:
- `setAgentInfo()`: 设置 Agent，触发数据加载
- `sendMsg()`: 发送消息（含防抖机制）
- `loadMoreMessages()`: 加载更多历史消息
- `syncLatestMessages()`: 同步最新消息

### 6. ChatRepository（数据层）

**文件**: `core/data/src/main/kotlin/ai/sxwl/android/data/chat/repository/ChatRepositoryImpl.kt`

**职责**:
- 统一数据访问接口
- 协调本地和远程数据源
- 实现增量同步策略

**数据流程**:
```
ensureInitialHistory()
├── 检查本地缓存
│   ├── 有缓存 → 立即显示 → 后台同步服务器数据
│   └── 无缓存 → 从服务器加载 → 保存到本地
└── 返回结果

loadMoreMessages()
├── 检查是否有更多数据
├── 从服务器加载（分页）
├── 追加到本地数据源
└── 更新状态

sendMessage()
├── 插入用户消息（本地）
├── 插入 loading 占位符（本地）
├── 发送到服务器
├── 更新 loading 占位符为真实回复
└── 保存到本地
```

## 数据流

### 消息加载流程

```
用户打开聊天
    ↓
ChatViewModel.setAgentInfo()
    ↓
bindToAgentSession() → 绑定 Repository Flow
    ↓
ensureInitialHistory()
    ├── 检查本地缓存
    │   ├── 有缓存 → 立即显示 → 后台同步
    │   └── 无缓存 → 从服务器加载
    └── 更新 StateFlow
    ↓
UI 自动更新（通过 collectAsState）
```

### 发送消息流程

```
用户点击发送
    ↓
ChatViewModel.sendMsg()
    ├── 防抖检查
    ├── 插入用户消息（本地）
    ├── 插入 loading 占位符（本地）
    ├── 发送到服务器
    ├── 接收 AI 回复
    ├── 更新 loading 占位符
    └── 保存到本地
    ↓
UI 自动更新
```

### 分页加载流程

```
用户滚动到顶部
    ↓
LazyColumn 监听滚动状态
    ↓
检测到接近顶部
    ↓
ChatViewModel.loadMoreMessages()
    ↓
ChatRepository.loadMoreMessages()
    ├── 获取当前 offset
    ├── 从服务器加载（分页）
    ├── 追加到本地数据源
    └── 更新 hasMore 状态
    ↓
UI 自动更新
```

## 关键设计决策

### 1. 反向布局（Reverse Layout）

**原因**:
- 符合用户习惯：最新消息在底部
- 自动滚动到最新消息
- 加载历史消息更自然

**实现**:
```kotlin
LazyColumn(reverseLayout = true) {
    // 列表顶部 = 最新消息
    // 滚动到顶部 = 加载更早的消息
}
```

### 2. 状态隔离（Per-Agent ViewModel）

**原因**:
- 每个 Agent 的聊天状态独立
- 避免状态混乱
- 支持多 Agent 切换

**实现**:
```kotlin
// 使用 agent.id 作为 ViewModel key
val chatViewModel: ChatViewModel = viewModel(key = agent.id, factory = viewModelFactory)
```

### 3. 增量同步策略

**原因**:
- 优先显示本地缓存，提升体验
- 后台同步最新数据
- 减少等待时间

**实现**:
```kotlin
if (hasLocalData) {
    _isQueryMsgsCompleted.value = true // 立即显示
    // 后台同步
    viewModelScope.launch(Dispatchers.IO) {
        syncChatDataUseCase(agentInfo.id)
    }
} else {
    loadChatHistory(agentInfo.id) // 首次加载
}
```

### 4. 防抖机制

**原因**:
- 避免快速点击发送按钮
- 防止重复请求

**实现**:
```kotlin
private val SEND_DEBOUNCE_TIME = 1000L // 1秒防抖
val currentTime = System.currentTimeMillis()
if (currentTime - lastSendTime < SEND_DEBOUNCE_TIME) {
    return // 忽略快速点击
}
```

### 5. 智能加载更多

**原因**:
- 只在真正需要时加载
- 避免误触发
- 提升性能

**实现**:
```kotlin
val shouldLoadMore =
    hasEnoughData && // 数据量足够
    isNearTop && // 接近顶部
    hasScrolled && // 已滚动过
    hasMoreMessages && // 还有更多数据
    !isLoadingMore // 未在加载中
```

## 性能优化

### 1. 预加载策略

- **HorizontalPager**: `beyondViewportPageCount = 3` 预加载相邻页面
- **静默预取**: 滑到倒数第5个时自动加载下一页

### 2. 本地缓存优先

- 优先显示本地缓存
- 后台同步最新数据
- 减少等待时间

### 3. 分页加载

- 每次加载 20 条消息
- 按需加载历史消息
- 避免一次性加载过多数据

### 4. 状态管理优化

- 使用 `StateFlow` 替代 `mutableStateListOf`
- 按 Agent ID 隔离状态
- 避免不必要的重组

### 5. 语音播放优化

- 按消息 ID 管理播放状态
- 切换 Agent 时自动停止播放
- 支持自动播放（仅开场白）

## 生命周期管理

### 页面生命周期

```kotlin
// 页面进入 onPause 时停止音频
LifecycleResumeEffect(isCurrentPage) {
    chatViewModel.syncLatestMessages() // 恢复时同步
    onPauseOrDispose { 
        chatViewModel.pauseVoicePlayback() // 暂停时停止
    }
}

// 离开页面时重置播放状态
DisposableEffect(chatViewModel, isCurrentPage) {
    onDispose {
        if (!isCurrentPage) {
            chatViewModel.resetVoicePlayback()
        }
    }
}
```

### Agent 切换管理

```kotlin
// 监听 Agent 变化，停止非当前 Agent 的播放
LaunchedEffect(agentInfo?.id) {
    val currentAgentId = agentInfo?.id
    if (currentAgentId != null) {
        chatViewModel.stopNonCurrentAgentPlayback()
    }
}
```

## 错误处理

### 消息渲染错误

```kotlin
runCatching {
    ChatItem(item, ...)
}.onFailure { e ->
    // 渲染失败时显示错误占位符
    Box(/* 错误提示 */)
}
```

### 数据加载错误

```kotlin
try {
    val result = remoteDataSource.getMessages(...)
    when (result) {
        is HttpResult.Success -> { /* 成功处理 */ }
        is HttpResult.Failure -> { /* 错误处理 */ }
    }
} catch (e: Exception) {
    LogUtils.e("Error: ${e.message}")
    // 使用本地缓存
}
```

## 测试考虑

### 单元测试

- `ChatViewModel` 的状态管理
- `ChatRepository` 的数据操作
- 消息格式化逻辑

### UI 测试

- 消息列表显示
- 输入框交互
- 发送消息流程

### 集成测试

- 完整的数据流
- 多 Agent 切换
- 语音播放

## 相关文件

### UI 组件
- `ChatPage.kt` - 主页面
- `ChatItem.kt` - 消息项
- `ChatInput.kt` - 输入框
- `ChatTopBar.kt` - 顶部栏
- `ChatPageContainer.kt` - 容器层

### ViewModel
- `ChatViewModel.kt` - 聊天状态管理
- `ChatTabViewModel.kt` - Tab 状态管理

### 数据层
- `ChatRepositoryImpl.kt` - Repository 实现
- `ChatLocalDataSource.kt` - 本地数据源
- `ChatRemoteDataSource.kt` - 远程数据源

### 工具类
- `ChatTextFormatter.kt` - 文本格式化
- `VoicePlayer.kt` - 语音播放

## 未来改进方向

1. **消息编辑**: 支持消息编辑和删除
2. **消息搜索**: 在聊天历史中搜索消息
3. **消息引用**: 支持引用回复
4. **多媒体消息**: 支持图片、文件等
5. **实时同步**: WebSocket 实时消息推送
6. **离线支持**: 更好的离线消息处理
