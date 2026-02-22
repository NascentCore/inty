<!-- CREATED_BY_AGENT -->
# Hype an iMate 功能设计与实现计划

## 目标与背景
- 通过「Hype iMate 打榜」玩法，将每日签到等轻任务与真实聊天行为绑定，提升留存与会话深度。
- 纯前端实现 MVP，不新增或修改后端接口；所有数据均以本地/缓存方式模拟。
- 为后续后端支持预留清晰的数据契约，便于逐步切换到真实排行榜。

## 核心概念
- **Token Energy**：用户每日通过签到、活动奖励等方式领取的额度，直接与聊天 token 消耗挂钩。
- **Hype Credits（账号可支配积分，代码实现中沿用 Boost Points 命名）**：用户通过聊天/图片/语音/签到获得的可支配积分，用于后续选择要 Hype 的 iMate。客户端常量控制兑换比例与获取规则。
- **iMate Hype Score（iMate 榜单积分）**：iMate 在榜单中的总分（后端字段 `energy_points` / `agents.points`），用于 Top10/排行榜排序。Hype 行为会把用户投入的 Hype Credits 以增量形式累加到 iMate 的 Hype Score 上。
- **Hype**：一次直接支持/打榜行为，消耗一定数量的 Hype Credits（默认 100，步长可配置），为当前 iMate 累积 Hype Score。
- **Top iMates（Leaderboard）**：按 iMate Hype Score 排序的排行榜（例如 Top 10），用于展示“全站热度”。

## 用户旅程
1. **签到/活动**：用户触发签到即获得 Token Energy，提示当前可用积分。
2. **聊天转化**：聊天时根据 token 消耗实时折算并累积 Points。
3. **Explore 子 Tab**：用户进入 Explore → Hype 子 Tab，浏览 Top 100 iMates，点击即可跳转聊天。
4. **iMate 主页 Hype**：在 iMate 主页显示积分面板，点击可打开 Hype 弹窗进行 hype 操作。

## UI/UX 要点
- **签到反馈**：Toast + 积分条动画，突出「今日剩余 X Points」。
- **Explore 子 Tab**：
  - 排行列表：iMate 头像、名称、Hype 计数、涨幅趋势箭头。
  - 按钮：`Hype`（直接打开对应聊天并聚焦 Hype 面板）与 `Chat`。
  - 空状态：若无数据，展示「暂无打榜数据，去聊天赚积分」。
- **iMate 主页**：
  - 显示 `BoostStatusChip`（积分面板，组件命名暂不改），展示可用积分
  - 点击后弹出半屏面板：iMate 简介、当前 Hype 总数、输入消耗 Points 的滑条或步进器（每步 100）。
  - 成功后在对话流插入系统消息提示。

## 当前实现状态（本地 MVP）

### 初始化与生命周期

**初始化位置**：`IntelliMateApp.onCreate()`

**初始化顺序**（重要）：
1. **MMKV 初始化**（第一优先级）：
   - 在 `IntelliMateApp.onCreate()` 的最开始调用 `MMKV.initialize(this)`
   - 必须在所有使用 MMKV 的代码之前初始化（包括 `IntySetting` 和 `BoostStorage`）
   - 这是全局单次初始化，确保所有 MMKV 实例都能正常工作

2. **BoostManager 初始化**（仅在 debug 模式）：
   - 通过 `HeartAppUtils.isAppDebugMode()` 判断是否启用
   - 调用 `BoostManager.initialize(context)` 创建 `BoostRepository` 实例
   - 初始化时机：在 MMKV 初始化之后，其他服务初始化之后

**生命周期管理**：
- `BoostManager` 为单例对象，生命周期与 Application 一致
- `BoostRepository` 在 `BoostManager.initialize()` 时创建，持有 Application Context
- 使用独立的 `CoroutineScope(SupervisorJob() + Dispatchers.IO)` 处理异步操作
- MMKV 自动处理数据持久化，无需手动管理生命周期
- `BoostStorage` 使用 `by lazy` 延迟初始化 MMKV 实例，确保在 MMKV 全局初始化之后才创建

### 核心组件架构

#### 1. **BoostManager** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostManager.kt`)

**设计模式**：单例对象（Singleton Object）

**核心职责**：
- Boost 功能的统一入口，负责协调仓库与业务方
- 提供 `boostState` 和 `leaderboard` 的 StateFlow
- 管理事件流（`BoostEvent`）和 Firebase 埋点
- 封装积分记录方法（`recordChatTokens`, `recordImageGeneration`, `recordAudioPlayback`）

**关键特性**：
- **延迟初始化**：`repository` 为可空类型，未初始化时返回默认空状态
- **默认状态流**：未初始化时提供 `defaultState` 和 `defaultLeaderboard`，避免空指针
- **事件系统**：使用 `SharedFlow<BoostEvent>` 发布内部事件（`PointsEarned`, `BoostSuccess`, `Error`）
- **协程作用域**：使用 `SupervisorJob` 确保子协程异常不影响其他操作

**MMKV 使用说明**：
- **间接使用**：`BoostManager` 不直接使用 MMKV，而是通过以下调用链间接使用：
  ```
  BoostManager
      ↓ (creates & uses)
  BoostRepository
      ↓ (calls)
  BoostStorage
      ↓ (directly uses)
  MMKV
  ```
- **初始化要求**：MMKV 必须在 `BoostManager.initialize()` 之前初始化，这已在 `IntelliMateApp.onCreate()` 中通过 `MMKV.initialize(this)` 完成
- **数据隔离**：Boost 功能使用独立的 MMKV 实例（`"boost_state"`），与 `IntySetting` 使用的 MMKV 实例完全隔离
- **设计优势**：这种分层设计实现了关注点分离：
  - `BoostManager`：业务逻辑和事件管理
  - `BoostRepository`：数据管理和状态同步
  - `BoostStorage`：持久化抽象（MMKV 的具体实现）

**公共 API**：
```kotlin
// 初始化（仅需调用一次）
fun initialize(context: Context)

// 积分记录方法
fun recordChatTokens(agentInfo: AgentInfo?, message: String)
fun recordImageGeneration(agentInfo: AgentInfo?)
fun recordAudioPlayback(agentId: String, agentName: String?)

// Boost 操作
suspend fun boostAgent(agentInfo: AgentInfo, requestedPoints: Int): BoostResult
suspend fun claimDailyReward(): Int

// 状态流
val boostState: StateFlow<BoostState>
val leaderboard: StateFlow<List<BoostLeaderboardEntry>>
val events: SharedFlow<BoostEvent>
```

#### 2. **BoostRepository** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt`)

**设计模式**：仓库模式（Repository Pattern）

**核心职责**：
- 管理本地持久化状态（DataStore）
- 构建排行榜数据（合并真实数据与 Seed 数据）
- 处理每日重置逻辑（`runDailyResetIfNeeded()`）
- 提供数据操作的原子性保证

**关键特性**：
- **MMKV 集成**：使用 `BoostStorage` 对象进行持久化（独立的 MMKV 实例）
- **手动状态更新**：每次写入后手动更新 StateFlow，确保 UI 及时响应
- **自动每日重置**：在 `init` 中启动协程检查并执行每日重置
- **依赖注入**：`seedProvider` 可通过构造函数注入，便于测试
- **线程安全**：MMKV 支持多进程模式，保证并发安全

**数据流**：
```
MMKV 写入操作
    ↓
BoostStorage.saveBoostState()
    ↓
MMKV 持久化
    ↓
BoostStorage.getBoostState() → 读取最新状态
    ↓
snapshot.toDomain() → 更新 _state
    ↓
buildLeaderboard(snapshot) → 更新 _leaderboard
    ↓
StateFlow 通知 UI
```

**公共 API**：
```kotlin
// 状态流
val stateFlow: StateFlow<BoostState>
val leaderboardFlow: StateFlow<List<BoostLeaderboardEntry>>

// 数据操作
suspend fun addPoints(points: Int, source: PointSource)
suspend fun claimDailyReward(): Int
suspend fun boostAgent(agentInfo: AgentInfo, points: Int): AgentBoostInfo
suspend fun runDailyResetIfNeeded()
```

#### 3. **BoostConfig** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostConfig.kt`)

**设计模式**：配置对象（Configuration Object）

**核心职责**：
- 集中管理所有配置常量
- 避免魔法数字/字符串散布在代码中
- 便于后续通过远程配置动态调整

**配置项**：
- `BOOST_STEP_POINTS = 100`：每次 Boost 的最小积分步长
- `DAILY_SIGN_IN_REWARD = 200`：每日签到奖励
- `AVG_CHARS_PER_TOKEN = 4.0`：字符到 Token 的估算比例
- `TOKEN_TO_POINT_RATIO = 1.0`：Token 到 Points 的转换比例
- `IMAGE_TOKEN_COST = 600`：图片生成的 Token 成本
- `AUDIO_TOKEN_COST = 120`：语音播放的 Token 成本
- `MAX_POINTS_PER_DAY = 10_000`：每日积分上限
- `LEADERBOARD_LIMIT = 100`：排行榜展示上限

#### 4. **BoostCalculator** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostCalculator.kt`)

**设计模式**：工具对象（Utility Object）

**核心职责**：
- Token ↔ Point 的估算与转换
- 积分校验与规范化
- 每日积分上限校验

**关键方法**：
- `estimateTokensFromMessage(message: String): Int`：估算消息的 Token 数量
- `tokensToPoints(tokens: Int): Int`：将 Token 转换为 Points
- `imageGenerationPoints(): Int`：图片生成的固定积分
- `audioPlaybackPoints(): Int`：语音播放的固定积分
- `clampDailyGain(current: Int, delta: Int): Int`：限制每日积分增长
- `normalizeBoostAmount(requested: Int, available: Int): Int`：规范化 Boost 投入金额（确保是步长的整数倍）

#### 5. **事件系统**

**BoostEvent** (`BoostManager.kt`)：
```kotlin
sealed class BoostEvent {
    data class PointsEarned(val source: PointSource, val points: Int)
    data class BoostSuccess(
        val agentId: String,
        val agentName: String,
        val pointsSpent: Int,
        val totalBoosts: Int,
    )
    data class Error(val error: BoostError)
}
```

**错误类型** (`BoostModels.kt`)：
```kotlin
sealed class BoostError {
    data object NotEnoughPoints
    data object DailyRewardAlreadyClaimed
    data object InvalidAmount
    data object NotInitialized
}
```

**事件发布**：
- `BoostManager` 通过 `_events.emit()` 发布事件
- UI 层可通过 `BoostManager.events.collectAsState()` 监听事件
- Firebase 埋点与事件系统并行，互不干扰

### 数据来源

#### 1. 真实数据（主要来源）

**存储位置**：本地 MMKV

**MMKV 实例配置**：
- **实例 ID**：`"boost_state"`（独立的 MMKV 实例，与 `IntySetting` 隔离）
- **模式**：`MMKV.MULTI_PROCESS_MODE`（支持多进程访问）
- **管理类**：`BoostStorage`（内部对象，封装 MMKV 操作）
- **存储键**：`"boost_state_snapshot"`（单个键存储完整状态快照）

**MMKV 使用链**：
```
BoostManager (业务逻辑层)
    ↓ 调用
BoostRepository (数据管理层)
    ↓ 调用
BoostStorage (持久化抽象层)
    ↓ 直接使用
MMKV.mmkvWithID("boost_state", MMKV.MULTI_PROCESS_MODE)
```

**数据结构**：`BoostStateSnapshot`
  ```kotlin
  data class BoostStateSnapshot(
      val availablePoints: Int = 0,              // 可用积分
      val dailyEnergyEarned: Int = 0,            // 今日已获得积分
      val hasClaimedDailyReward: Boolean = false, // 是否已领取每日奖励
      val lastResetDate: String = "",            // 最后重置日期
      val boostsByAgent: Map<String, AgentBoostInfoSnapshot> = emptyMap(), // 角色 Boost 信息
  )
  ```

**数据内容**：用户实际 boost 过的角色信息
- `agentId`、`agentName`、`avatarUrl`
- `boostCount`（boost 次数）
- `pointsInvested`（投入的积分）
- `lastBoostedAt`（最后 boost 时间）

**数据更新时机**：
- 用户执行 boost 操作时（`BoostManager.boostAgent()`）
- 用户获得积分时（聊天、图片生成、语音播放等）

**存储实现**：
- **存储抽象**：使用 `BoostStorage` 内部对象封装 MMKV 操作，`BoostManager` 不直接访问 MMKV
- **序列化**：通过 Moshi 进行 JSON 序列化/反序列化（`MoshiUtils.toJson()` / `MoshiUtils.fromJson()`）
- **多进程支持**：使用 `MMKV.MULTI_PROCESS_MODE` 确保多进程环境下的数据一致性
- **延迟初始化**：`BoostStorage` 中的 MMKV 实例使用 `by lazy` 延迟初始化，确保在全局 `MMKV.initialize()` 之后才创建
- **错误处理**：包含完整的异常捕获和损坏数据清理机制
- **数据隔离**：使用独立的 MMKV 实例（`"boost_state"`），与应用的其它存储（如 `IntySetting`）完全隔离

#### 2. 假数据（Seed，占位展示）

**来源**：`BoostSeedProvider` (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostSeedProvider.kt`)

**用途**：当真实数据不足时，用于填充排行榜展示

**特点**：
- 包含 8 个预设角色（Aurora Starfall、Midnight Rain 等）
- 每个角色有预设的 boostCount 和 trend
- 标记为 `isSeed = true`，点击时会显示提示无法打开聊天

### 排行榜构建逻辑

在 `BoostRepository.buildLeaderboard()` 中实现：

```kotlin
private fun buildLeaderboard(snapshot: BoostStateSnapshot): List<BoostLeaderboardEntry> {
    // 1. 从 DataStore 提取真实数据
    val actual = snapshot.boostsByAgent.values
        .filter { it.boostCount > 0 }
        .sortedByDescending { it.boostCount }
        .map { /* 转换为 BoostLeaderboardEntry */ }

    // 2. 从 SeedProvider 获取假数据（排除已存在的 agentId）
    val seeds = seedProvider.seeds(snapshot.boostsByAgent.keys)

    // 3. 合并并重新排序
    return (actual + seeds)
        .sortedWith(
            compareByDescending<BoostLeaderboardEntry> { it.boostCount }
                .thenBy { it.agentName }
        )
        .take(BoostConfig.LEADERBOARD_LIMIT)  // 限制 100 条
        .mapIndexed { index, entry -> entry.copy(rank = index + 1) }
}
```

**排序规则**：
1. 按 `boostCount` 降序
2. 相同 `boostCount` 时按 `agentName` 字母序

### 数据流

**完整数据流图**：

```
用户操作（聊天/图片/语音/签到）
    ↓
业务层调用 BoostManager.record*()
    ↓
BoostManager 计算积分（BoostCalculator）
    ↓
BoostRepository.addPoints() → BoostStorage.saveBoostState()
    ↓
MMKV 持久化到磁盘（boost_state MMKV 实例）
    ↓
手动调用 updateStateFlows()
    ↓
snapshot.toDomain() → 更新 _state (StateFlow)
    ↓
buildLeaderboard(snapshot) → 更新 _leaderboard (StateFlow)
    ↓
BoostManager.boostState / leaderboard (StateFlow)
    ↓
UI 层 collectAsState() → Compose 重组
```

**Boost 操作数据流**：

```
用户点击 Boost 按钮
    ↓
BoostManager.boostAgent(agentInfo, points)
    ↓
BoostCalculator.normalizeBoostAmount() 规范化金额
    ↓
BoostRepository.boostAgent() → BoostStorage.saveBoostState()
    ↓
扣除积分 + 更新角色 Boost 信息
    ↓
MMKV 持久化
    ↓
手动触发状态流更新（updateStateFlows()）
    ↓
发布 BoostEvent.BoostSuccess
    ↓
UI 显示成功提示 + 插入系统消息（ChatViewModel.appendBoostSystemMessage）
```

**每日重置流程**：

```
应用启动 / 每日首次访问
    ↓
BoostRepository.init → runDailyResetIfNeeded()
    ↓
检查 lastResetDate != 今天
    ↓
BoostStorage.saveBoostState() 重置：
  - dailyEnergyEarned = 0
  - hasClaimedDailyReward = false
  - lastResetDate = 今天
    ↓
手动触发状态流更新（updateStateFlows()）
```

### 积分获取规则

根据 `BoostConfig` 配置：

| 行为 | Token 估算 | Points 转换 |
|------|-----------|------------|
| 聊天消息 | 字符数 / 4.0 | Token × 1.0 |
| 图片生成 | 600 tokens | 600 points |
| 语音播放 | 120 tokens | 120 points |
| 每日签到 | - | 200 points |

**每日限制**：通过行为最多可获得 10,000 points/天（`MAX_POINTS_PER_DAY`）

### UI 集成点

#### 1. **Chat 页面** (`ChatPage.kt`)

**集成方式**：
- 已移除 Boost Points 面板（迁移到角色主页）
- 保留 `BoostSheet` 支持，用于从 Explore 跳转时自动打开

**关键实现**：
- **参数**：`shouldShowBoostSheetOnOpen: Boolean` - 控制是否在打开时显示 BoostSheet
- **状态管理**：使用 `pendingBoostSheet` 状态，在 `LaunchedEffect` 中延迟显示（确保 agentInfo 已加载）
- **Boost 操作**：调用 `BoostManager.boostAgent()` 后，通过 `ChatViewModel.appendBoostSystemMessage()` 插入系统消息
- **事件处理**：监听 `BoostManager.events`，处理成功/失败事件并显示 Toast

**代码片段**：
```kotlin
LaunchedEffect(agentInfo?.id, pendingBoostSheet, isDebugMode) {
    if (isDebugMode && agentInfo != null && pendingBoostSheet) {
        showBoostSheet = true
        pendingBoostSheet = false
    }
}

// BoostSheet 显示逻辑
if (isDebugMode && showBoostSheet) {
    BoostSheet(
        agentInfo = info,
        availablePoints = boostState.availablePoints,
        hasDailyReward = boostState.hasClaimedDailyReward,
        onBoostConfirmed = { points ->
            scope.launch {
                val result = BoostManager.boostAgent(info, points)
                chatViewModel.appendBoostSystemMessage(
                    agent = info,
                    points = result.pointsSpent,
                    totalBoosts = result.info.boostCount,
                )
            }
        },
        // ...
    )
}
```

#### 2. **角色主页** (`AgentInfoScreen.kt`)

**集成方式**：
- 显示 `BoostStatusChip`（积分面板），展示可用积分
- 点击后打开 `BoostSheet` 进行 boost 操作

**关键实现**：
- **条件显示**：仅在 `isDebugMode` 下显示 Boost 相关 UI
- **状态订阅**：通过 `BoostManager.boostState.collectAsState()` 获取实时积分状态
- **Boost 操作**：与 Chat 页面类似，成功后显示 Toast 提示
- **错误处理**：统一的错误处理函数 `showBoostError`，根据错误类型显示对应提示

**代码片段**：
```kotlin
val boostState by if (isDebugMode) 
    BoostManager.boostState.collectAsState() 
else 
    remember { mutableStateOf(BoostState()) }

if (isDebugMode) {
    BoostStatusChip(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        availablePoints = boostState.availablePoints,
        onClick = {
            if (boostState.availablePoints < BoostConfig.BOOST_STEP_POINTS) {
                ToastUtils.showShort(R.string.boost_toast_not_enough_points)
            } else {
                showBoostSheet = true
            }
        },
    )
}
```

#### 3. **Explore 页面** (`ExplorePage.kt`)

**集成方式**：
- Boost Tab 展示排行榜（`BoostLeaderboardTab`）
- 支持点击 Chat/Boost 按钮跳转到聊天页面
- Seed 数据点击时显示提示，无法打开聊天

**关键实现**：
- **Tab 切换**：使用 `ExploreSubTab` 枚举（`Recommended`, `Boost`）控制显示内容
- **排行榜数据**：通过 `BoostManager.leaderboard.collectAsState()` 获取
- **跳转逻辑**：`handleLeaderboardAction` 函数处理点击事件，通过 `ChatActivity.launch()` 跳转并传递 `showBoostSheet` 参数
- **Seed 数据处理**：检查 `entry.isSeed`，显示提示 Toast 而不跳转

**代码片段**：
```kotlin
val leaderboard by if (isDebugMode) 
    BoostManager.leaderboard.collectAsState() 
else 
    remember { mutableStateOf(emptyList<BoostLeaderboardEntry>()) }

val handleLeaderboardAction: (BoostLeaderboardEntry, Boolean) -> Unit =
    { entry, showSheet ->
        if (entry.isSeed || entry.agentId.isBlank()) {
            ToastUtils.showShort(R.string.boost_seed_placeholder_toast)
        } else {
            ChatActivity.launch(
                context,
                agentInfo = null,
                agentId = entry.agentId,
                pageSource = ChatActivity.EXPLORE_TAB,
                showBoostSheet = showSheet,
            )
        }
    }
```

#### 4. **ChatViewModel 集成** (`ChatViewModel.kt`)

**积分记录点**：
- **发送消息**：`sendMessage()` 方法中，记录用户输入和助手回复的 Token
- **Keep Talking**：`keepTalking()` 方法中，记录用户输入和助手回复的 Token
- **图片生成**：`generateImage()` 方法中，记录图片生成的固定积分（600 points）

**关键实现**：
```kotlin
// 发送消息时记录
if (HeartAppUtils.isAppDebugMode(Utils.getApp())) {
    BoostManager.recordChatTokens(agent, inputMsg)
    assistantContent?.let { BoostManager.recordChatTokens(agent, it) }
}

// 图片生成时记录
if (HeartAppUtils.isAppDebugMode(Utils.getApp())) {
    agent?.let { BoostManager.recordImageGeneration(it) }
}
```

**系统消息插入**：
- `appendBoostSystemMessage()` 方法：在 Boost 成功后，向聊天记录插入系统提示消息
- 消息格式：`"You hyped %2$s with %1$d credits. Total hypes: %3$d."`

#### 5. **AudioManager 集成** (`AudioManager.kt`)

**积分记录点**：
- **语音播放**：在 `playAudio()` 方法中，当音频开始播放时记录积分（120 points）

**关键实现**：
```kotlin
if (HeartAppUtils.isAppDebugMode(context)) {
    BoostManager.recordAudioPlayback(agentId, agentName ?: "")
}
```

**注意事项**：
- 仅在 debug 模式下记录，避免影响生产环境性能
- 每次播放都会记录，不区分自动播放或手动播放

## 客户端数据模型（本地）

```kotlin
data class BoostState(
    val availablePoints: Int,
    val boostsByAgent: Map<String, AgentBoostInfo>,
    val dailyEnergyEarned: Int,
    val hasClaimedDailyReward: Boolean,
    val lastResetDate: String
)
```

- **AgentBoostInfo**：包含 `agentId`, `agentName`, `avatarUrl`, `boostCount`, `pointsInvested`, `lastBoostedAt`。
- 数据持久化于 DataStore（`boost_state.json`），并提供 `resetIfNewDay()`。

## 业务逻辑
- **积分来源**：
  - 签到：固定奖励（200 Points）。
  - 聊天：按 token 使用量实时增加，基于消息估算字数（字符数 / 4.0）。
  - 图片生成：固定 600 points。
  - 语音播放：固定 120 points。
  - 其他活动：预留枚举类型，便于未来扩展。
- **Boost 约束**：
  - 每次至少 100 Points，可配置 `BOOST_STEP_POINTS`。
  - 若不足显示入口灰态，点击弹出缺口提示。
  - 同一角色不限 Boost 次数；排行榜以本地累积排序。
- **排行榜**：
  - 客户端根据 `boostCount` 排序，截取前 100。
  - 真实数据与 Seed 数据合并展示。

## 架构分层

### 1. **Domain 层**（数据与业务逻辑）

**组件**：
- `BoostRepository`: 管理积分余额、Boost 记录、排行榜，负责数据持久化
- `BoostCalculator`: 负责 Token → Points 折算策略，提供工具方法
- `BoostManager`: 统一入口，协调业务逻辑，管理事件流
- `BoostConfig`: 配置常量集中管理
- `BoostModels`: 数据模型定义（`BoostState`, `BoostLeaderboardEntry`, `BoostError` 等）
- `BoostStorage`: MMKV 存储管理类，负责序列化/反序列化
- `BoostSeedProvider`: Seed 数据提供者

**职责**：
- 数据持久化（DataStore）
- 业务逻辑封装
- 数据转换与校验
- 排行榜构建

### 2. **ViewModel 层**（状态管理）

**组件**：
- `ChatViewModel`：集成 Boost 记录逻辑
  - `sendMessage()` → `BoostManager.recordChatTokens()`
  - `keepTalking()` → `BoostManager.recordChatTokens()`
  - `generateImage()` → `BoostManager.recordImageGeneration()`
  - `appendBoostSystemMessage()` → 插入系统消息

**职责**：
- 在业务操作中调用 Boost 记录方法
- 不直接管理 Boost 状态（通过 `BoostManager` 的状态流获取）

### 3. **UI 层**（界面展示）

**组件**：
- `BoostStatusChip` (`BoostUiComponents.kt`): 积分状态展示芯片
- `BoostSheet` (`BoostUiComponents.kt`): Boost 操作弹窗
- `BoostLeaderboardTab` (`BoostLeaderboardTab.kt`): 排行榜 Tab 页面
- `BoostLeaderboardRow` (`BoostLeaderboardTab.kt`): 排行榜条目行
- `TrendPill` (`BoostLeaderboardTab.kt`): 趋势标签

**集成页面**：
- `ChatPage.kt`: 支持从外部跳转时自动打开 BoostSheet
- `AgentInfoScreen.kt`: 显示 BoostStatusChip 和 BoostSheet
- `ExplorePage.kt`: 显示 Boost Tab 和排行榜

**职责**：
- 展示 Boost 相关 UI
- 处理用户交互
- 订阅状态流并响应变化
- 错误提示和成功反馈

## 与推荐系统的集成计划
- 在现有「推荐角色」请求参数中加入 `variant = BOOSTED_TOP`.
- 未有后端时，`variant = BOOSTED_TOP` 走客户端排行榜。
- 当后端接口上线时，仅需在 Repository 内切换数据源即可。

## 事件与埋点

### Firebase Analytics 事件

**已实现事件**：

1. **`boost_token_earned`** - 积分获得事件
   - **触发时机**：用户通过聊天、图片生成、语音播放获得积分时
   - **参数**：
     - `source`: 积分来源（`"chat"`, `"image"`, `"audio"`, `"sign_in"`, `"manual"`）
     - `points`: 获得的积分数量
     - `agent_name`: 关联的角色名称（可选）
   - **实现位置**：`BoostManager.logPointsEvent()`

2. **`boost_invested`** - Boost 投入事件
   - **触发时机**：用户成功执行 Boost 操作时
   - **参数**：
     - `agent_id`: 角色 ID
     - `agent_name`: 角色名称
     - `points`: 投入的积分数量
     - `total_boosts`: 该角色的总 Boost 次数
   - **实现位置**：`BoostManager.boostAgent()`

3. **`boost_daily_reward_claimed`** - 每日奖励领取事件
   - **触发时机**：用户领取每日签到奖励时
   - **参数**：
     - `points`: 领取的积分数量（固定 200）
   - **实现位置**：`BoostManager.claimDailyReward()`

**待实现事件**：

4. **`boost_leaderboard_viewed`** - 排行榜查看事件
   - **计划参数**：
     - `viewed_count`: 查看的条目数量
     - `time_spent`: 停留时间（秒）

5. **`boost_shortage_prompted`** - 积分不足提示事件
   - **计划参数**：
     - `required_points`: 需要的积分数量
     - `available_points`: 当前可用积分

### 内部事件系统

**BoostEvent** (`BoostManager.kt`)：
- `PointsEarned(source: PointSource, points: Int)` - 积分获得事件
- `BoostSuccess(agentId, agentName, pointsSpent, totalBoosts)` - Boost 成功事件
- `Error(error: BoostError)` - 错误事件

**使用方式**：
```kotlin
// UI 层可以监听事件
LaunchedEffect(Unit) {
    BoostManager.events.collect { event ->
        when (event) {
            is BoostEvent.PointsEarned -> {
                // 处理积分获得
            }
            is BoostEvent.BoostSuccess -> {
                // 处理 Boost 成功
            }
            is BoostEvent.Error -> {
                // 处理错误
            }
        }
    }
}
```

> **注意**：当前 UI 层主要通过状态流（`boostState`, `leaderboard`）响应变化，事件系统主要用于内部协调和未来扩展。

## 风险与对策
- **本地排行榜与真实数据不一致**：在文案中标注「本地体验版」，Seed 数据点击时显示提示。
- **数据丢失**：使用 DataStore 持久化，未来支持同步到服务器。
- **Token 估算误差**：允许运维通过远程配置调整折算比例（待实现）。
- **用户频繁点击 Boost**：100 Points 阈值 + 提示冷却动画（待实现）。

## 推出策略
1. **Phase 0**：隐藏开关 + 内测，验证 UI/UX。
2. **Phase 1**：灰度 10% 用户，观察 Boost 行为、Crash、性能。
3. **Phase 2**：全量发布，同时准备后端排行榜需求文档。

## 开发任务拆解（已完成 ✅）
- **数据与逻辑**
  1. ✅ 新建 `BoostRepository`, `BoostCalculator`, `BoostManager`。
  2. ✅ 在聊天、图片生成、语音播放模块内触发 `record*()`。
- **UI 入口**
  3. ✅ Explore 页面新增 `Boost` 子 Tab 与列表组件。
  4. ✅ 角色主页新增 Boost 积分面板与弹窗。
  5. ✅ Chat 页面保留 BoostSheet 支持（用于跳转时自动打开）。

## 待完成工作清单

### 🔴 高优先级（核心功能）

#### 1. 后端 API 支持

**状态**：未开始

**工作项**：
- [ ] 设计并实现后端 API 接口
  - `GET /api/v1/boost/leaderboard` - 获取全局排行榜
  - `POST /api/v1/boost/sync` - 同步本地数据到服务器
  - `GET /api/v1/boost/user/stats` - 获取用户统计信息
- [ ] 在 Android 客户端集成 API 调用
  - 在 `BoostRepository` 中新增 `fetchRemoteLeaderboard()` 方法
  - 实现数据同步逻辑（`syncToServer()`）
  - 添加网络错误处理和重试机制
- [ ] 实现混合模式（本地 + 远程数据合并）
  - 修改 `buildLeaderboard()` 支持混合数据源
  - 处理数据冲突和去重逻辑

**依赖**：需要后端团队配合

#### 2. 趋势计算真实实现

**状态**：部分实现（当前所有真实数据标记为 `UP`）

**工作项**：
- [ ] 扩展数据模型，增加历史数据字段
  ```kotlin
  data class AgentBoostInfoSnapshot(
      // ... 现有字段
      val boostHistory: Map<String, Int> = emptyMap(), // 按日期记录 boost 数量
  )
  ```
- [ ] 实现趋势计算逻辑
  - 对比最近 7 天 vs 前 7 天的 boost 数量
  - 计算变化百分比，判断趋势（UP/DOWN/FLAT）
- [ ] 在 `buildLeaderboard()` 中应用趋势计算
- [ ] 添加数据迁移逻辑（为现有数据初始化历史记录）

**文件**：
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostModels.kt`
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt`

#### 3. 数据同步机制

**状态**：未开始

**工作项**：
- [ ] 实现离线队列机制
  - 使用本地队列存储待同步的 boost 操作
  - 应用启动时检查并同步待处理数据
- [ ] 实现增量同步
  - 只同步变更的数据，避免全量同步
  - 添加同步状态标记（已同步/待同步/同步失败）
- [ ] 处理同步冲突
  - 当本地和服务器数据不一致时的合并策略
  - 实现冲突解决机制（以服务器为准或用户选择）

**文件**：
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt`
- 新增：`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostSyncManager.kt`

### 🟡 中优先级（功能完善）

#### 4. 测试覆盖

**状态**：未开始

**工作项**：
- [ ] 单元测试
  - `BoostCalculator` 的 token 转换测试
  - `BoostRepository` 的数据持久化测试
  - `BoostManager` 的业务逻辑测试
- [ ] 集成测试
  - DataStore 读写测试
  - 排行榜构建逻辑测试
  - 每日重置逻辑测试
- [ ] UI 测试
  - `BoostSheet` 交互测试
  - `BoostLeaderboardTab` 展示测试
  - 错误场景测试

**文件**：
- 新增：`android_app/app/src/test/kotlin/com/ai/intellimate/boost/`
- 新增：`android_app/app/src/androidTest/kotlin/com/ai/intellimate/boost/`

#### 5. 错误处理完善

**状态**：部分实现

**工作项**：
- [ ] 网络错误处理
  - 请求失败时的降级策略（使用本地数据）
  - 超时重试机制
  - 网络不可用时的用户提示
- [ ] 数据一致性检查
  - 启动时验证数据完整性
  - 数据损坏时的修复机制
  - 异常数据的清理逻辑
- [ ] 用户友好的错误提示
  - 细化错误类型和提示文案
  - 添加错误恢复建议

**文件**：
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostError.kt`
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostManager.kt`

#### 6. 性能优化

**状态**：未开始

**工作项**：
- [ ] 排行榜分页加载
  - 当数据量大时，实现分页加载
  - 使用 `LazyColumn` 的 `items()` 优化
- [ ] 图片加载优化
  - 使用 Coil 的缓存策略
  - 实现头像占位符和错误处理
- [ ] 数据更新优化
  - 避免不必要的排行榜重建
  - 使用 `derivedStateOf` 优化状态计算

**文件**：
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/ui/BoostLeaderboardTab.kt`
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt`

### 🟢 低优先级（体验优化）

#### 7. Seed 数据管理优化

**状态**：当前硬编码

**工作项**：
- [ ] 迁移到配置文件
  - 将 Seed 数据移到 `assets/` 或远程配置
  - 支持动态更新 Seed 数据
- [ ] 或移除 Seed 数据
  - 当有真实数据时，不再显示 Seed 数据
  - 改进空状态展示

**文件**：
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostSeedProvider.kt`

#### 8. 排行榜分类功能

**状态**：未开始

**工作项**：
- [ ] 按时间维度分类
  - 今日/本周/本月/全部排行榜
  - 添加时间筛选 UI
- [ ] 按角色分类
  - 按 category 分组展示
  - 添加分类筛选器
- [ ] 个人排行榜
  - 显示用户自己的 boost 历史
  - 个人统计信息展示

**文件**：
- 新增：`android_app/app/src/main/kotlin/com/ai/intellimate/boost/ui/BoostLeaderboardFilter.kt`
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt`

#### 9. 实时更新支持

**状态**：未开始

**工作项**：
- [ ] 实现 WebSocket/SSE 连接
  - 连接到服务器实时更新流
  - 处理连接断开和重连
- [ ] 实时数据更新
  - 当其他用户 boost 时，实时更新排行榜
  - 优化更新频率，避免过于频繁

**依赖**：需要后端支持 WebSocket/SSE

#### 10. 数据迁移策略

**状态**：未开始

**工作项**：
- [ ] 版本化数据模型
  - 为 `BoostStateSnapshot` 添加版本号
  - 实现版本升级逻辑
- [ ] 数据迁移工具
  - 处理旧版本数据格式
  - 平滑升级到新版本

**文件**：
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostStateSerializer.kt`
- 新增：`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostDataMigrator.kt`

#### 11. 用户体验优化

**状态**：部分实现

**工作项**：
- [ ] 添加加载状态
  - 排行榜加载时的 skeleton UI
  - 数据同步时的进度提示
- [ ] 动画效果
  - Boost 操作成功时的动画反馈
  - 排行榜更新时的过渡动画
- [ ] 引导和帮助
  - 首次使用时的功能引导
  - 帮助文档或 FAQ

**文件**：
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/ui/BoostLeaderboardTab.kt`
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/ui/BoostSheet.kt`

#### 12. 分析和监控

**状态**：部分实现（已有 Firebase 事件）

**工作项**：
- [ ] 完善 Firebase 事件
  - 添加更多用户行为追踪（如 `boost_leaderboard_viewed`）
  - 性能指标监控
- [ ] 错误监控
  - 使用 Crashlytics 记录异常
  - 数据一致性问题的监控

**文件**：
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostManager.kt`

## 未来扩展方向

### 1. 远程排行榜 API

**目标**：从服务器获取全局排行榜数据

**实现方案**：
- 新增 API 接口：`GET /api/v1/boost/leaderboard`
- 返回格式：
  ```json
  {
    "entries": [
      {
        "rank": 1,
        "agentId": "...",
        "agentName": "...",
        "avatarUrl": "...",
        "boostCount": 1000,
        "pointsInvested": 100000,
        "trend": "UP"
      }
    ],
    "total": 1000,
    "page": 1,
    "pageSize": 100
  }
  ```

**集成方式**：
- 在 `BoostRepository` 中新增 `fetchRemoteLeaderboard()` 方法
- 修改 `buildLeaderboard()` 支持混合模式（本地 + 远程）
- 添加缓存机制，避免频繁请求

### 2. 数据同步

**目标**：将本地 boost 数据同步到服务器

**实现方案**：
- 新增 API 接口：`POST /api/v1/boost/sync`
- 在 `BoostManager.boostAgent()` 成功后，异步同步到服务器
- 使用队列机制，确保离线时也能记录，上线后批量同步

### 3. 实时更新

**目标**：排行榜数据实时更新

**实现方案**：
- 使用 WebSocket 或 Server-Sent Events (SSE)
- 当其他用户 boost 角色时，实时推送更新
- 在 `BoostRepository` 中订阅实时更新流

### 4. 趋势计算优化

**当前实现**：所有真实数据标记为 `BoostTrend.UP`

**改进方案**：
- 记录历史 boost 数据（按时间窗口）
- 计算趋势：对比最近 7 天 vs 前 7 天的 boost 数量
- 在 `AgentBoostInfoSnapshot` 中增加历史数据字段

### 5. 排行榜分类

**扩展方向**：
- 按时间维度：今日/本周/本月/全部
- 按角色分类：按 category 分组
- 个人排行榜：显示用户自己的 boost 历史

## 技术债务

1. **Seed 数据管理**
   - 当前硬编码在 `BoostSeedProvider` 中
   - 建议：迁移到配置文件或远程配置

2. **趋势计算**
   - 当前所有真实数据都标记为 `UP`
   - 需要实现真实的历史数据对比逻辑

3. **错误处理**
   - 网络请求失败时的降级策略
   - 数据不一致时的修复机制

4. **性能优化**
   - 排行榜数据量大时的分页加载
   - 图片加载优化（avatarUrl）

## 实现优先级建议

### Phase 1: 核心功能完善（1-2 周）
1. 趋势计算真实实现
2. 错误处理完善
3. 基础测试覆盖

### Phase 2: 后端集成（2-3 周）
1. 后端 API 支持
2. 数据同步机制
3. 混合模式实现

### Phase 3: 体验优化（1-2 周）
1. 性能优化
2. 用户体验优化
3. 实时更新支持（可选）

### Phase 4: 高级功能（按需）
1. 排行榜分类
2. Seed 数据管理优化
3. 数据迁移策略

## 相关文件

### 核心代码（Domain 层）
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostManager.kt` - Boost 功能统一入口，单例对象
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt` - 数据仓库，管理持久化和排行榜
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostCalculator.kt` - 积分计算工具类
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostConfig.kt` - 配置常量集中管理
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostModels.kt` - 数据模型定义（State, Entry, Error 等）
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostStorage.kt` - MMKV 存储管理类
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostSeedProvider.kt` - Seed 数据提供者

### UI 组件（UI 层）
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/ui/BoostUiComponents.kt` - UI 组件（BoostStatusChip, BoostSheet）
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/ui/BoostLeaderboardTab.kt` - 排行榜 Tab 页面

### 集成点（ViewModel/UI 层）
- `android_app/app/src/main/kotlin/com/ai/intellimate/chat/ChatPage.kt` - Chat 页面，支持 BoostSheet 自动打开
- `android_app/app/src/main/kotlin/com/ai/intellimate/chat/ChatPageContainer.kt` - Chat 页面容器
- `android_app/app/src/main/kotlin/com/ai/intellimate/chat/ChatActivity.kt` - Chat Activity，支持跳转参数
- `android_app/app/src/main/kotlin/com/ai/intellimate/chat/viewmodel/ChatViewModel.kt` - Chat ViewModel，集成积分记录
- `android_app/app/src/main/kotlin/com/ai/intellimate/agent/info/AgentInfoScreen.kt` - iMate 主页，显示 BoostStatusChip
- `android_app/app/src/main/kotlin/com/ai/intellimate/explore/ExplorePage.kt` - Explore 页面，Hype 入口展示
- `android_app/app/src/main/kotlin/com/ai/intellimate/audio/AudioManager.kt` - 音频管理器，集成语音播放积分记录

### 初始化
- `android_app/app/src/main/kotlin/com/ai/intellimate/IntelliMateApp.kt` - Application 类，初始化 BoostManager

### 资源文件
- `android_app/app/src/main/res/values/strings.xml` - Hype 相关文案（所有用户可见文本）
- `android_app/app/src/main/res/drawable/ic_boost_fire.xml` - Boost 火焰图标

### 文档
- `android_app/AGENTS.md` - Hype 功能简要说明（在相关本地 MVP 章节）
- `docs/FR_CHAR_BOOSTING.md` - 本文档，完整的功能设计与实现文档

## 后续待办
- 拟定后端接口：`GET /agents/boosted`, `POST /agents/{id}/boost`。
- 设计跨设备同步策略，避免多端积分差异。
- 与产品确认积分兑换是否可逆、是否允许赠送给好友。
- 实现趋势计算真实逻辑。
- 添加测试覆盖。

## 更新记录

- 2025-01-XX: 创建本地 MVP 实现
- 2025-01-XX: 将 Boost Points 面板从 Chat 页面迁移到角色主页
- 2025-01-XX: 合并详细实现计划文档
