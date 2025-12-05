# FCM 消息推送流程梳理

## 1. 消息推送如何通过字段标记打开聊天界面

### 关键字段

FCM 消息通过以下字段来区分消息类型和跳转目标：

```kotlin
// FCMConstants.kt
object FCMConstants {
    /** 数据键名：消息类型 */
    const val DATA_KEY_TYPE = "type"
    
    /** 数据键名：Agent ID（用于跳转到聊天页面） */
    const val DATA_KEY_AGENT_ID = "agent_id"
    
    /** 消息类型：聊天消息 */
    const val TYPE_AGENT_MESSAGE = "agent_message"
}
```

### 消息流程

#### 场景 1：App 在前台时收到消息

1. **FCMService.onMessageReceived()** 接收消息
   - 解析 `data` 字段中的 `type` 和 `agent_id`
   - 调用 `handler.handleMessage()` 发布 `PushNotificationEvent.MessageReceived` 事件

2. **MainViewModel.handlePushMessageEvent()** 处理消息
   - 检查 `event.type == FCMConstants.TYPE_AGENT_MESSAGE`
   - 更新 `messagesTabHasPush` 状态，显示消息 Tab 红点

3. **FCMService** 显示通知（如果有 notification 字段）
   - 调用 `handler.showNotification()` 发布 `PushNotificationEvent.ShowNotification` 事件

4. **PushNotificationManager.subscribeToPushNotificationEvents()** 接收通知事件
   - 调用 `showNotification()` 显示系统通知

5. **PushNotificationManager.createNotificationIntent()** 创建点击 Intent
   ```kotlin
   when (messageType) {
       FCMConstants.TYPE_AGENT_MESSAGE -> {
           if (!agentId.isNullOrEmpty()) {
               ChatActivity.notifyIntent(application, agentId)  // 跳转到聊天页面
           }
       }
   }
   ```

6. 用户点击通知 → 打开 ChatActivity，显示对应 agent 的聊天界面

#### 场景 2：App 在后台时收到消息

1. **系统自动显示通知**（如果消息包含 `notification` 字段）
   - Firebase 系统会自动显示通知，不会触发 `onMessageReceived()`

2. **用户点击通知**
   - 系统启动 MainActivity，并将 `data` 字段作为 Intent extras 传递

3. **MainActivity.handleNotificationIntent()** 处理 Intent
   ```kotlin
   val messageType = intent.getStringExtra(FCMConstants.DATA_KEY_TYPE)
   val agentId = intent.getStringExtra(FCMConstants.DATA_KEY_AGENT_ID)
   
   if (messageType == FCMConstants.TYPE_AGENT_MESSAGE && !agentId.isNullOrEmpty()) {
       ChatActivity.launch(context = this, agentId = agentId, ...)
   }
   ```

### 关键代码位置

1. **PushNotificationManager.createNotificationIntent()** (行 208-234)
   - 根据 `type` 和 `agent_id` 创建跳转 Intent
   - `TYPE_AGENT_MESSAGE` + `agent_id` → `ChatActivity.notifyIntent()`

2. **MainActivity.handleNotificationIntent()** (行 238-272)
   - 处理从通知点击启动的情况
   - 检查 `TYPE_AGENT_MESSAGE` 和 `agent_id`，跳转到 ChatActivity

3. **ChatActivity.notifyIntent()** (行 65-71)
   - 创建跳转到聊天页面的 Intent
   - 设置 `FLAG_ACTIVITY_NEW_TASK | FLAG_ACTIVITY_CLEAR_TOP`
   - 传递 `agent_id` 和 `PUSH_NOTIFICATION` 作为 pageSource

---

## 2. PushNotificationManager 的主要作用价值

### 核心职责

`PushNotificationManager` 是一个单例管理器，负责统一处理所有推送通知相关的业务逻辑：

1. **统一的通知显示管理**
   - 创建和管理通知渠道（Android 8.0+）
   - 统一的通知样式和配置
   - 处理通知权限检查

2. **通知点击后的导航逻辑**
   - 根据消息类型（`type`）和附加数据（`agent_id`）决定跳转目标
   - 支持多种消息类型的跳转逻辑

3. **Direct Boot 模式支持**
   - 处理设备重启后、用户解锁前的消息
   - 保存消息元数据，待用户解锁后处理

4. **解耦和可维护性**
   - 将通知逻辑从 FCMService 中分离
   - 通过 EventBus 实现松耦合的事件驱动架构

### 架构设计

```
FCMService (接收消息)
    ↓
FCMessageHandlerImpl (转换事件)
    ↓
EventBus (事件总线)
    ↓
PushNotificationManager (处理通知显示和点击)
    ↓
系统通知栏 / Activity 跳转
```

### 为什么要在 PushNotificationManager 中过滤 feedback_request？

#### 原因 1：统一入口控制

`PushNotificationManager.subscribeToPushNotificationEvents()` 是所有通知显示的统一入口。所有需要显示系统通知的消息都会经过这里：

```kotlin
EventBus.subscribe(PushNotificationEvent.ShowNotification::class) { event ->
    // 所有通知都会经过这里
    showNotification(event.title, event.body, event.data)
}
```

在这里过滤 `feedback_request` 可以确保：
- **一致性**：所有通知类型的处理逻辑集中管理
- **可维护性**：新增消息类型时，只需在一个地方添加过滤逻辑
- **清晰性**：明确哪些消息类型需要显示通知，哪些不需要

#### 原因 2：业务逻辑分离

`feedback_request` 类型的消息有特殊的业务需求：
- **不需要系统通知**：只在 App 前台时显示弹窗
- **不需要后台处理**：App 不在前台时直接忽略

在 `PushNotificationManager` 中过滤，可以：
- 避免在通知栏显示 `feedback_request` 通知
- 让 `MainActivity` 专注于处理弹窗逻辑
- 保持通知管理器的职责单一

#### 原因 3：双重保障

实际上，我们在两个地方都做了过滤：

1. **FCMService.handleMessageInNormalMode()** (行 170-194)
   ```kotlin
   if (messageType == FCMConstants.TYPE_FEEDBACK_REQUEST) {
       // 不调用 showNotification()
   }
   ```

2. **PushNotificationManager.subscribeToPushNotificationEvents()** (行 70-78)
   ```kotlin
   if (messageType == FCMConstants.TYPE_FEEDBACK_REQUEST) {
       return  // 不显示通知
   }
   ```

这样做的好处：
- **防御性编程**：即使 FCMService 的过滤失效，PushNotificationManager 也能兜底
- **代码清晰**：明确表达"feedback_request 不应该显示通知"的意图
- **未来扩展**：如果未来有其他地方可能触发通知显示，这里也能拦截

### 对比：为什么不在 MainActivity 中过滤？

如果只在 `MainActivity` 中处理 `feedback_request`，会有以下问题：

1. **通知仍会显示**：FCMService 已经通过 EventBus 发送了 `ShowNotification` 事件
2. **职责混乱**：MainActivity 不应该负责通知显示逻辑
3. **难以维护**：通知相关的逻辑分散在多个地方

### 总结

在 `PushNotificationManager` 中过滤 `feedback_request` 是合理的架构设计：
- ✅ 统一管理所有通知显示逻辑
- ✅ 保持职责分离和代码清晰
- ✅ 提供双重保障，确保不会误显示通知
- ✅ 便于未来扩展和维护
