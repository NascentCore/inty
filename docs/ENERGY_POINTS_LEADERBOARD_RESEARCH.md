<!-- CREATED_BY_AGENT -->
# iMate 能量值排名功能实现现状调研

## 一、功能需求概述

完整功能包括：

1. **用户获得 energy points**
   - 从签到获得 energy points
   - 从跟 iMate 聊天获得 energy points

2. **用户 Hype iMate**
   - 用户可以选择一定数量自己从聊天、每日签到获得的 energy points
   - 将选定的 energy points 加到用户自己选择的某个 iMate 上

3. **Explore 页面 Top 10 排行榜**
   - Explore 页面有 "Top 10" 按钮
   - 点击后进入页面，显示按照 energy points 排名的 iMate 列表

## 二、后端实现现状

### 2.1 数据库模型

**Agent 模型** (`app/models/agent.py`):
```python
points = Column(
    Integer,
    default=0,
    server_default=sa.text("0"),
    comment="iMate 积分，用于 iMate 热度排名（hype an iMate feature）",
)
```

- 数据库字段：`points` (Integer)
- 默认值：0
- 用途：存储 iMate 的 energy points，用于排行榜排序

### 2.2 API 接口

#### 2.2.1 `/api/v1/ai/agents/recommend` - 推荐 iMate 列表

**位置**: `app/api/v1/endpoints/agents.py:117`

**支持的排序参数**:
- `sort=energy_points`: 按 energy points 降序排列

**实现逻辑** (`app/services/agent_service.py:648`):
```python
elif sort_by == AgentSortOption.ENERGY_POINTS:
    sort_order = desc(models.Agent.points)
```

**状态**: ✅ **已实现**
- 可以返回按 energy points 降序排列的 iMate 列表
- 支持分页（`page`, `page_size`）

#### 2.2.2 `/api/v1/ai/agents/{agent_id}` - 更新角色

**位置**: `app/api/v1/endpoints/agents.py` (通过 `update_agent` 服务方法)

**支持的更新字段**:
- `energy_points`: 需要新增的能量点数，会累加到 agent 的积分列中

**实现逻辑** (`app/services/agent_service.py:1016-1029`):
```python
energy_points_delta = update_data.pop("energy_points", None)
if energy_points_delta is not None and energy_points_delta <= 0:
    raise HTTPException(
        status_code=400, detail="energy_points must be a positive integer"
    )

if energy_points_delta:
    current_points = db_agent.points or 0
    db_agent.points = current_points + energy_points_delta
```

**Schema 定义** (`app/schemas/agent.py:257`):
```python
energy_points: Optional[int] = Field(
    None,
    gt=0,
    description="需要新增的能量点数，会累加到 agent 的积分列中",
)
```

**状态**: ✅ **已实现**
- 支持通过 `energy_points` 字段增量更新角色的 points
- 验证：必须为正整数

#### 2.2.3 Agent 信息返回

**Agent 响应 Schema** (`app/schemas/agent.py:284`):
```python
energy_points: int = Field(
    default=0,
    ge=0,
    description="Agent 当前能量点数，对应数据库 points 列",
    validation_alias=AliasChoices("energy_points", "points"),
)
```

**状态**: ✅ **已实现**
- Agent 信息中已包含 `energy_points` 字段
- 客户端可以从 agent info 中获取 energy points

### 2.3 后端实现总结

| 功能 | 状态 | 说明 |
|------|------|------|
| 数据库字段 | ✅ | `agents.points` 字段已存在 |
| 推荐接口排序 | ✅ | 支持 `sort=energy_points` |
| 更新角色积分 | ✅ | 支持通过 `energy_points` 增量更新 |
| Agent 信息返回 | ✅ | 返回 `energy_points` 字段 |

## 三、前端（Android）实现现状

### 3.1 Energy Points 显示

**聊天页面顶部栏** (`android_app/app/src/main/kotlin/com/ai/intellimate/chat/ui/ChatTopBar.kt`):
- 显示位置：角色头像右侧，角色名称上方
- 显示格式：⚡图标 + 数字 + "pts"（例如：⚡ 15 pts）
- 数据来源：从本地数据库 `characters` 表的 `energy_points` 字段读取

**数据同步逻辑** (`android_app/app/src/main/kotlin/com/ai/intellimate/chat/viewmodel/ChatViewModel.kt:320-332`):
```kotlin
private fun syncCharacterEnergyFromMessages(agent: AgentInfo, messages: List<MsgInfo>) {
    val energyPoints = messages.count { msg ->
        msg.role == "assistant" &&
        !msg.isOpening() &&
        msg.content != LOADING_PLACEHOLDER_CONTENT
    }
    if (energyPoints <= lastSyncedEnergyPoints) return
    lastSyncedEnergyPoints = energyPoints
    viewModelScope.launch(Dispatchers.IO) {
        characterRepository.syncCharacterSnapshot(agent, energyPoints)
    }
}
```

**状态**: ✅ **已实现**
- 从 agent info 中获取 `energyPoints` 并显示
- 本地计算并存储 energy points（基于消息数量）

### 3.2 Boost 功能（本地实现）

#### 3.2.1 Boost 系统架构

**核心组件**:
- `BoostManager`: 统一入口，协调仓库与业务方
- `BoostRepository`: 数据仓库，管理本地状态
- `BoostStorage`: MMKV 存储，持久化数据
- `BoostCalculator`: 积分计算工具

**数据存储**: MMKV（本地存储，不涉及后端）

#### 3.2.2 用户获得 Points

**签到获得 Points** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt:81-96`):
```kotlin
suspend fun claimDailyReward(): Int {
    val current = BoostStorage.getBoostState()
    if (current.hasClaimedDailyReward) {
        throw BoostException(BoostError.DailyRewardAlreadyClaimed)
    }
    val claimed = BoostConfig.DAILY_SIGN_IN_REWARD  // 200 points
    val updated = current.copy(
        availablePoints = current.availablePoints + BoostConfig.DAILY_SIGN_IN_REWARD,
        hasClaimedDailyReward = true,
    )
    BoostStorage.saveBoostState(updated)
    updateStateFlows()
    return claimed
}
```

**聊天获得 Points** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostManager.kt:54-65`):
```kotlin
fun recordAssistantMessage(agentInfo: AgentInfo?) {
    if (agentInfo == null) return
    val repo = repository ?: return
    scope.launch {
        repo.addPoints(BoostConfig.CHAT_MESSAGE_POINT_REWARD, PointSource.Chat(agentInfo.id))
        // CHAT_MESSAGE_POINT_REWARD = 1 point per message
    }
}
```

**积分规则** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostConfig.kt`):
- 每日签到：200 points
- 聊天消息：1 point/条
- 图片生成：600 points
- 语音播放：120 points
- 每日上限：10,000 points

**状态**: ✅ **已实现（仅本地）**
- 用户可以通过签到、聊天获得 points
- 数据存储在本地 MMKV，**未同步到后端**

#### 3.2.3 Hype iMate

**Boost 操作** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt:99-130`):
```kotlin
suspend fun boostAgent(agentInfo: AgentInfo, points: Int): AgentBoostInfo {
    // 验证 points 有效性
    // 扣除用户可用积分
    // 更新 iMate 的 boost 信息（本地）
    // 保存到 MMKV
}
```

**状态**: ⚠️ **部分实现（仅本地）**
- 用户可以 hype iMate，消耗本地 points
- **未调用后端 API 更新 iMate 的 energy points**
- Boost 数据仅存储在本地，不与其他用户共享

#### 3.2.4 排行榜

**本地排行榜** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt:151-178`):
```kotlin
private fun buildLeaderboard(snapshot: BoostStateSnapshot): List<BoostLeaderboardEntry> {
    // 从本地 MMKV 提取真实数据
    val actual = snapshot.boostsByAgent.values
        .filter { it.boostCount > 0 }
        .sortedByDescending { it.boostCount }
        .map { /* 转换为 BoostLeaderboardEntry */ }
    
    // 从 SeedProvider 获取假数据（用于填充）
    val seeds = seedProvider.seeds(snapshot.boostsByAgent.keys)
    
    // 合并并重新排序
    return (actual + seeds)
        .sortedWith(compareByDescending<BoostLeaderboardEntry> { it.boostCount })
        .take(BoostConfig.LEADERBOARD_LIMIT)  // 限制 100 条
}
```

**排行榜页面** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostLeaderboardActivity.kt`):
- 显示本地排行榜（基于本地 boost 数据）
- 支持点击 iMate 跳转到聊天页面

**状态**: ⚠️ **部分实现（仅本地）**
- 排行榜数据来自本地 MMKV，**不是从后端获取的真实排行榜**
- 只显示用户自己 boost 过的 iMate

### 3.3 Explore 页面 Top 10 按钮

**按钮位置** (`android_app/app/src/main/kotlin/com/ai/intellimate/explore/ExplorePage.kt:110-116`):
```kotlin
actions = {
    if (isDebugMode) {
        Box(modifier = Modifier.padding(end = UiConfigs.Padding.ScreenHorizontal)) {
            BoostShortcutButton(
                onClick = { BoostLeaderboardActivity.launch(context) }
            )
        }
    }
}
```

**按钮文本**: "Top 10" (`android_app/app/src/main/res/values/strings.xml:463`)

**状态**: ⚠️ **部分实现**
- 按钮仅在 debug 模式下显示
- 点击后打开本地排行榜页面，**不是从后端获取的真实排行榜**

### 3.4 前端实现总结

| 功能 | 状态 | 说明 |
|------|------|------|
| Energy Points 显示 | ✅ | 聊天页面顶部栏显示 |
| 签到获得 Points | ✅ | 本地实现，未同步后端 |
| 聊天获得 Points | ✅ | 本地实现，未同步后端 |
| Hype iMate | ⚠️ | 本地实现，未调用后端 API |
| 本地排行榜 | ⚠️ | 仅显示本地数据 |
| Top 10 按钮 | ⚠️ | 仅 debug 模式，显示本地排行榜 |

## 四、与完整功能的差距分析

### 4.1 用户获得 Energy Points

**现状**:
- ✅ 前端已实现签到、聊天获得 points 的逻辑
- ❌ **未同步到后端**：用户获得的 points 仅存储在本地 MMKV

**差距**:
- 需要后端 API 记录用户的 energy points 余额
- 需要后端 API 记录用户从签到、聊天获得的 points 历史

### 4.2 用户 Hype iMate

**现状**:
- ✅ 前端已实现 boost 操作的 UI 和本地逻辑
- ❌ **未调用后端 API**：boost 操作未更新 iMate 的 `points` 字段

**差距**:
- 需要在 `BoostManager.boostAgent()` 中调用后端 API
- 需要调用 `/api/v1/ai/agents/{agent_id}` 的 `update` 接口，传递 `energy_points` 增量
- 需要处理网络错误、重试等场景

**后端 API 调用示例**:
```kotlin
// 在 BoostManager.boostAgent() 中
val result = AgentService.updateAgent(
    agentId = agentInfo.id,
    agentInfo = AgentInfo(
        // ... 其他字段
        energyPoints = points  // 需要新增的 points
    )
)
```

**注意**: 后端 `AgentUpdate` schema 中的 `energy_points` 是增量值，不是绝对值。

### 4.3 Explore 页面 Top 10 排行榜

**现状**:
- ✅ Explore 页面有 "Top 10" 按钮（仅 debug 模式）
- ❌ **显示的是本地排行榜**，不是从后端获取的真实排行榜

**差距**:
- 需要调用 `/api/v1/ai/agents/recommend?sort=energy_points&page_size=10` 获取 Top 10
- 需要创建新的排行榜页面，显示从后端获取的数据
- 需要将按钮从 debug 模式改为正式功能

**实现方案**:
1. 创建新的 `EnergyPointsLeaderboardActivity` 或修改现有的 `BoostLeaderboardActivity`
2. 调用 `AgentService.getRecommendAgents(sort="energy_points", pageSize=10)`
3. 显示从后端获取的 iMate 列表，按 energy points 降序排列

## 五、实现完整功能的计划

### 5.1 后端（基本已完成）

**需要确认**:
- [ ] 是否需要新增用户 energy points 余额的数据库表？
- [ ] 是否需要记录用户获得 points 的历史记录？
- [ ] 是否需要记录用户 boost 操作的历史记录？

**当前后端已支持**:
- ✅ 更新 iMate energy points（增量）
- ✅ 按 energy points 排序获取 iMate 列表
- ✅ 返回 iMate 的 energy points

### 5.2 前端（需要实现）

#### 5.2.1 Boost 操作同步到后端

**任务**:
1. 修改 `BoostManager.boostAgent()` 方法
2. 在本地 boost 成功后，调用后端 API 更新 iMate 的 energy points
3. 处理网络错误、重试逻辑

**代码位置**:
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostManager.kt:94-119`
- `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/services/AgentService.kt:136-189`

**实现步骤**:
```kotlin
suspend fun boostAgent(agentInfo: AgentInfo, requestedPoints: Int): BoostResult {
    // 1. 本地 boost 操作（现有逻辑）
    val info = repo.boostAgent(agentInfo, normalized)
    
    // 2. 调用后端 API 更新 iMate 的 energy points
    try {
        val updateResult = AgentService.updateAgent(
            agentId = agentInfo.id,
            agentInfo = AgentInfo(
                // 只传递 energy_points 增量
                energyPoints = normalized
            )
        )
        when (updateResult) {
            is ApiResult.Success -> {
                // 更新成功
            }
            is ApiResult.Error -> {
                // 处理错误：可能需要回滚本地操作
            }
        }
    } catch (e: Exception) {
        // 处理异常
    }
    
    return result
}
```

**注意**: 后端 `AgentUpdate` 需要确认是否支持只传递 `energy_points` 字段。

#### 5.2.2 Top 10 排行榜页面

**任务**:
1. 修改 Explore 页面的 "Top 10" 按钮（移除 debug 模式限制）
2. 创建或修改排行榜页面，从后端获取数据
3. 调用 `/api/v1/ai/agents/recommend?sort=energy_points&page_size=10`

**代码位置**:
- `android_app/app/src/main/kotlin/com/ai/intellimate/explore/ExplorePage.kt:110-116`
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostLeaderboardActivity.kt`

**实现步骤**:
1. 修改 `ExplorePage.kt`，移除 `isDebugMode` 条件
2. 创建新的 `EnergyPointsLeaderboardActivity` 或修改 `BoostLeaderboardActivity`
3. 在 Activity 中调用 `AgentService.getRecommendAgents(sort="energy_points", pageSize=10)`
4. 显示从后端获取的 iMate 列表

**AgentService 需要支持**:
```kotlin
suspend fun getRecommendAgents(
    page: Int = 1,
    pageSize: Int = 10,
    sort: String = "random",  // 需要支持 "energy_points"
    sortSeed: String = "default",
): ApiResult<List<AgentInfo>>
```

**当前实现**: `AgentService.getRecommendAgents()` 只支持 `"random"`, `"created_asc"`, `"created_desc"`，需要添加 `"energy_points"` 支持。

#### 5.2.3 用户 Energy Points 同步（可选）

**任务**:
- 如果需要跨设备同步用户的 energy points 余额，需要后端支持
- 当前可以保持本地实现，仅同步 boost 操作到后端

## 六、关键代码位置总结

### 6.1 后端

| 功能 | 文件路径 | 关键代码 |
|------|---------|---------|
| 数据库模型 | `app/models/agent.py` | `points` 字段定义 |
| 推荐接口 | `app/api/v1/endpoints/agents.py:117` | `recommend_agents()` |
| 排序逻辑 | `app/services/agent_service.py:648` | `sort_by == AgentSortOption.ENERGY_POINTS` |
| 更新逻辑 | `app/services/agent_service.py:1016-1029` | `energy_points_delta` 处理 |
| Schema | `app/schemas/agent.py:257,284` | `energy_points` 字段定义 |

### 6.2 前端

| 功能 | 文件路径 | 关键代码 |
|------|---------|---------|
| Boost Manager | `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostManager.kt` | `boostAgent()` |
| Boost Repository | `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt` | `boostAgent()`, `buildLeaderboard()` |
| 排行榜页面 | `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostLeaderboardActivity.kt` | 本地排行榜显示 |
| Explore 页面 | `android_app/app/src/main/kotlin/com/ai/intellimate/explore/ExplorePage.kt` | Top 10 按钮 |
| Agent Service | `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/services/AgentService.kt` | `getRecommendAgents()`, `updateAgent()` |
| Energy Points 显示 | `android_app/app/src/main/kotlin/com/ai/intellimate/chat/ui/ChatTopBar.kt` | 顶部栏显示 |

## 七、下一步行动建议

### 优先级 1：Hype 操作同步到后端
- 修改 `BoostManager.boostAgent()` 调用后端 API
- 确保 boost 操作能正确更新 iMate 的 energy points

### 优先级 2：Top 10 排行榜
- 修改 `AgentService.getRecommendAgents()` 支持 `sort="energy_points"`
- 创建或修改排行榜页面，从后端获取数据
- 移除 Explore 页面 Top 10 按钮的 debug 模式限制

### 优先级 3：用户 Energy Points 同步（可选）
- 如果需要跨设备同步，需要后端支持用户 energy points 余额管理

## 八、注意事项

1. **后端 API 调用**: `AgentUpdate` 的 `energy_points` 是增量值，不是绝对值
2. **错误处理**: Boost 操作需要处理网络错误，可能需要回滚本地操作
3. **数据一致性**: 本地 boost 数据和后端 energy points 需要保持一致
4. **性能**: 排行榜页面需要考虑缓存、分页等优化
5. **用户体验**: 网络请求失败时的降级方案（显示本地数据或错误提示）

