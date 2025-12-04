# RoomDataSource 在 Chat Page 中的使用方式

## 架构概览

Chat Page 使用 **Offline-First（离线优先）** 架构，遵循以下原则：

1. **单一可信数据源**：Room 数据库作为唯一的数据源
2. **UI 读取本地化**：所有 UI 通过 StateFlow 从本地数据库读取
3. **网络同步后台化**：网络请求只负责刷新数据库，不直接更新 UI
4. **状态持久化**：分页状态（hasMore/offset）持久化到数据库

## 数据流架构

```
ChatViewModel (UI层)
    ↓
ChatRepository (Domain层)
    ↓
RoomDataSource (Data层 - 本地) + ChatRemoteDataSource (Data层 - 远程)
    ↓
Room Database (IntyChatDatabase)
```

## RoomDataSource 在 Chat Page 中的使用

### 1. 初始化绑定（bindToAgentSession）

当 ChatViewModel 绑定到特定 agent 时，会订阅 RoomDataSource 提供的 StateFlow：

```kotlin
// ChatViewModel.kt:205-243
private fun bindToAgentSession(agentId: String) {
    // 1. 立即获取当前值（同步）
    _msgs.value = chatRepository.getMessagesFlow(agentId).value
    _isLoadingMore.value = chatRepository.getLoadingMoreFlow(agentId).value
    _hasMoreMessages.value = chatRepository.getHasMoreFlow(agentId).value

    // 2. 订阅消息流（异步更新）
    messagesJob = viewModelScope.launch {
        chatRepository.getMessagesFlow(agentId).collect { list ->
            _msgs.value = list  // UI 自动更新
        }
    }
    
    // 3. 订阅加载状态流
    loadingMoreJob = viewModelScope.launch {
        chatRepository.getLoadingMoreFlow(agentId).collect { loading ->
            _isLoadingMore.value = loading
        }
    }
    
    // 4. 订阅是否有更多消息流
    hasMoreJob = viewModelScope.launch {
        chatRepository.getHasMoreFlow(agentId).collect { more ->
            _hasMoreMessages.value = more
        }
    }
}
```

### 2. RoomDataSource 的 StateFlow 实现

RoomDataSource 通过 Room 的 Flow 自动将数据库变化转换为 StateFlow：

```kotlin
// RoomDataSource.kt:55-68
fun getMessagesFlow(agentId: String): StateFlow<List<MsgInfo>> =
    messageFlows.getOrPut(agentId) {
        messageDao
            .streamMessages(agentId)  // Room Flow，自动监听数据库变化
            .map { list ->
                list.map(ChatMessageEntity::toModel)  // Entity → Model
            }
            .stateIn(scope, SharingStarted.Eagerly, emptyList())
    }
```

**关键点**：
- `messageDao.streamMessages(agentId)` 返回 Room Flow，自动监听数据库变化
- 当数据库中的数据发生变化时，Flow 会自动发出新值
- StateFlow 缓存最新值，新订阅者立即获得当前状态

## 消息同步流程

### 场景 1：初始加载（ensureInitialHistory）

**触发时机**：首次打开聊天页面或切换 agent

```kotlin
// ChatRepositoryImpl.kt:57-124
override suspend fun ensureInitialHistory(agentId: String, pageSize: Int) {
    // 1. 检查是否已加载
    if (localDataSource.isInitialLoaded(agentId)) return

    // 2. 检查本地缓存
    val localMessages = localDataSource.getMessagesFlow(agentId).value
    if (localMessages.isNotEmpty()) {
        // 有本地数据：立即显示，后台同步
        localDataSource.setInitialLoaded(agentId, true)
        // 后台同步最新数据
        val result = remoteDataSource.getMessages(agentId, pageSize, 0)
        if (result is HttpResult.Success) {
            localDataSource.updateMessages(agentId, serverMessages)
        }
        return
    }

    // 3. 无本地数据：从服务器加载
    val result = remoteDataSource.getMessages(agentId, pageSize, 0)
    if (result is HttpResult.Success) {
        localDataSource.updateMessages(agentId, messages)
        localDataSource.setInitialLoaded(agentId, true)
    }
}
```

**流程**：
1. 检查本地是否有缓存 → 有则立即显示
2. 后台请求服务器最新数据
3. 更新 Room 数据库 → StateFlow 自动通知 UI 更新

### 场景 2：同步最新消息（syncLatestMessages）

**触发时机**：应用恢复、页面切换、手动刷新

```kotlin
// ChatRepositoryImpl.kt:215-283
override suspend fun syncLatestMessages(agentId: String, pageSize: Int) {
    // 1. 检查是否需要初始化
    if (!localDataSource.isInitialLoaded(agentId) || 
        localDataSource.getMessagesFlow(agentId).value.isEmpty()) {
        ensureInitialHistory(agentId, pageSize)
        return
    }

    // 2. 获取服务器最新消息
    val result = remoteDataSource.getMessages(agentId, pageSize, 0)
    if (result is HttpResult.Success) {
        val serverMessages = result.data.messages
        val localMessages = localDataSource.getMessagesFlow(agentId).value

        // 3. 检查是否有新消息或状态变化
        val hasNewMessages = serverMessages.any { serverMsg ->
            localMessages.none { localMsg ->
                localMsg.id == serverMsg.id || 
                (localMsg.content == serverMsg.content && localMsg.role == serverMsg.role)
            }
        }

        val hasStatusChanges = serverMessages.any { serverMsg ->
            localMessages.any { localMsg ->
                localMsg.id == serverMsg.id && 
                localMsg.user_vote != serverMsg.user_vote
            }
        }

        // 4. 如果有变化，更新本地数据库
        if (hasNewMessages || hasStatusChanges) {
            localDataSource.updateMessages(agentId, serverMessages)
            // StateFlow 自动通知 UI 更新
        }
    }
}
```

**流程**：
1. 从服务器获取最新消息（offset=0，即最新一页）
2. 与本地消息对比，检测新消息或状态变化
3. 有变化则更新 Room 数据库 → StateFlow 自动通知 UI

### 场景 3：发送消息（sendMessage）

**触发时机**：用户发送消息

```kotlin
// ChatRepositoryImpl.kt:165-213
override suspend fun sendMessage(agentId: String, content: String) {
    // 1. 立即插入用户消息和 loading 占位（乐观更新）
    val userMsg = MsgInfo(content = content, role = "user")
    val loadingMsg = MsgInfo(content = "loading_animation", role = "assistant")
    localDataSource.appendMessages(agentId, listOf(userMsg, loadingMsg))
    // → StateFlow 立即更新，UI 立即显示

    // 2. 发送到服务器
    val result = remoteDataSource.sendMessage(agentId, listOf(userMsg))

    // 3. 移除 loading 占位
    val currentMessages = localDataSource.getMessagesFlow(agentId).value
    val filteredMessages = currentMessages.filterNot { 
        it.content == "loading_animation" && it.role == "assistant" 
    }
    localDataSource.updateMessages(agentId, filteredMessages)

    // 4. 追加 AI 回复
    if (result is HttpResult.Success) {
        val assistantMsgs = result.data.data?.choices?.map { it.message } ?: emptyList()
        localDataSource.appendMessages(agentId, assistantMsgs)
        // → StateFlow 自动更新，UI 显示 AI 回复
    }
}
```

**流程**：
1. **乐观更新**：立即写入本地数据库，UI 立即显示
2. 发送到服务器
3. 收到回复后更新数据库 → StateFlow 自动通知 UI

### 场景 4：加载更多消息（loadMoreMessages）

**触发时机**：用户滚动到顶部，加载历史消息

```kotlin
// ChatRepositoryImpl.kt:126-163
override suspend fun loadMoreMessages(agentId: String, pageSize: Int) {
    // 1. 检查状态
    if (localDataSource.getLoadingMoreFlow(agentId).value) return
    if (!localDataSource.getHasMoreFlow(agentId).value) return

    // 2. 设置加载状态
    localDataSource.setLoadingMore(agentId, true)

    // 3. 获取当前 offset
    val offset = localDataSource.getOffset(agentId)
    
    // 4. 从服务器加载更多消息
    val result = remoteDataSource.getMessages(agentId, pageSize, offset)
    if (result is HttpResult.Success) {
        val moreMessages = result.data.messages
        // 5. 前置插入（历史消息在列表顶部）
        localDataSource.prependMessages(agentId, moreMessages)
        localDataSource.incrementOffset(agentId, pageSize)
        localDataSource.setHasMore(agentId, result.data.hasMore)
    }
    
    // 6. 清除加载状态
    localDataSource.setLoadingMore(agentId, false)
}
```

**流程**：
1. 使用当前 offset 从服务器加载历史消息
2. 使用 `prependMessages` 插入到列表开头（较小的 sortKey）
3. 更新 offset 和 hasMore 状态
4. StateFlow 自动通知 UI 更新

## 关键设计点

### 1. Offline-First 设计

- **UI 始终从本地读取**：通过 StateFlow 订阅 Room 数据库
- **网络失败不影响 UI**：即使网络请求失败，UI 仍显示本地数据
- **后台同步**：网络请求只更新数据库，不直接操作 UI

### 2. 自动 UI 更新

- Room Flow → StateFlow → UI 自动更新
- 数据库变化 → Flow 发出新值 → StateFlow 更新 → UI 重组

### 3. 状态管理

- **分页状态**：`offset`、`hasMore` 持久化到 `ChatSyncStateEntity`
- **加载状态**：`isLoadingMore` 使用内存中的 `MutableStateFlow`
- **初始化状态**：`isInitialLoaded` 持久化到数据库

### 4. 消息排序

- 使用 `sortKey`（Long 类型，基于 `System.nanoTime()`）确保消息顺序
- `sortKey DESC` 排序，新消息在列表底部
- `prependMessages` 用于加载历史消息（插入到顶部）

## 数据同步时机

1. **初始加载**：`ensureInitialHistory()` - 首次打开或切换 agent
2. **手动刷新**：`syncLatestMessages()` - 应用恢复、页面切换
3. **发送消息**：`sendMessage()` - 用户发送消息
4. **加载更多**：`loadMoreMessages()` - 滚动加载历史消息

## 总结

RoomDataSource 在 Chat Page 中的使用遵循 **Offline-First** 原则：

1. **UI 层**：通过 StateFlow 订阅 Room 数据库变化
2. **Repository 层**：协调本地和远程数据源
3. **Data 层**：
   - RoomDataSource：管理本地数据库（Room）
   - ChatRemoteDataSource：处理网络请求
4. **自动同步**：数据库变化 → Flow → StateFlow → UI 自动更新

这种设计确保了：
- ✅ 快速响应（本地数据立即显示）
- ✅ 离线可用（网络失败不影响 UI）
- ✅ 数据一致性（单一可信数据源）
- ✅ 自动 UI 更新（响应式数据流）

