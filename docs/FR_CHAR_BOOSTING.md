<!-- CREATED_BY_AGENT -->
# Boost AI Characters 功能设计与实现计划

## 目标与背景
- 通过「角色打榜」玩法，将每日签到等轻任务与真实聊天行为绑定，提升留存与会话深度。
- 纯前端实现 MVP，不新增或修改后端接口；所有数据均以本地/缓存方式模拟。
- 为后续后端支持预留清晰的数据契约，便于逐步切换到真实排行榜。

## 核心概念
- **Token Energy**：用户每日通过签到、活动奖励等方式领取的额度，直接与聊天 token 消耗挂钩。
- **Points**：基于 Token Energy 或聊天 token 消耗实时折算的积分，兑换比例在客户端常量中配置（默认 1 Point = 1 Token Energy）。积分只在本地存储，刷新即重置。
- **Boost**：一次打榜行为，消耗 100 Points（可配置），为当前 AI 角色累积人气。
- **Top Boosted Characters**：按 Boost 次数排序的排行榜，默认展示前 100 个角色，可作为 Explore 页签的子 Tab。

## 用户旅程
1. **签到/活动**：用户触发签到即获得 Token Energy，提示当前可用积分。
2. **聊天转化**：聊天时根据 token 消耗实时折算并累积 Points。
3. **Explore 子 Tab**：用户进入 Explore → Boost 子 Tab，浏览 Top 100 AI 角色，点击即可跳转聊天。
4. **角色主页 Boost**：在角色主页显示积分面板，点击可打开 Boost 弹窗进行 boost 操作。

## UI/UX 要点
- **签到反馈**：Toast + 积分条动画，突出「今日剩余 X Points」。
- **Explore 子 Tab**：
  - 排行列表：角色头像、名称、Boost 计数、涨幅趋势箭头。
  - 按钮：`Boost`（直接打开对应聊天并聚焦 Boost 面板）与 `Chat`。
  - 空状态：若无数据，展示「暂无打榜数据，去聊天赚积分」。
- **角色主页**：
  - 显示 `BoostStatusChip`（积分面板），展示可用积分
  - 点击后弹出半屏面板：角色简介、当前 Boost 总数、输入消耗 Points 的滑条或步进器（每步 100）。
  - 成功后在对话流插入系统消息提示。

## 当前实现状态（本地 MVP）

### 核心组件

1. **BoostManager** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostManager.kt`)
   - Boost 功能的统一入口
   - 提供 `boostState` 和 `leaderboard` 的 StateFlow
   - 协调仓库与业务逻辑

2. **BoostRepository** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt`)
   - 管理本地持久化状态（DataStore）
   - 构建排行榜数据
   - 处理每日重置逻辑

3. **BoostConfig** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostConfig.kt`)
   - 集中管理所有配置常量
   - 避免魔法数字/字符串

4. **BoostCalculator** (`android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostCalculator.kt`)
   - Token ↔ Point 的估算与转换
   - 积分校验与规范化

### 数据来源

#### 1. 真实数据（主要来源）

**存储位置**：本地 DataStore
- 文件：`boost_state.json`（通过 `BoostStateSerializer` 序列化）
- 数据结构：`BoostStateSnapshot`
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

```
用户操作（聊天/图片/语音）
    ↓
BoostManager.record*() 
    ↓
BoostRepository.addPoints() → 更新 DataStore
    ↓
DataStore.data.collectLatest → 触发 buildLeaderboard()
    ↓
BoostManager.leaderboard (StateFlow) → UI 展示
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

1. **Chat 页面** (`ChatPage.kt`)
   - 已移除 Boost Points 面板（迁移到角色主页）
   - 保留 `BoostSheet` 支持（用于从 Explore 跳转时自动打开）

2. **角色主页** (`AgentInfoScreen.kt`)
   - 显示 `BoostStatusChip`（积分面板）
   - 支持打开 `BoostSheet` 进行 boost 操作

3. **Explore 页面** (`ExplorePage.kt`)
   - Boost Tab 展示排行榜（`BoostLeaderboardTab`）
   - 支持点击 Chat/Boost 按钮跳转到聊天页面
   - Seed 数据点击时显示提示，无法打开聊天

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

## 实现分层
1. **Domain 层**
   - `BoostRepository`: 管理积分余额、Boost 记录、排行榜。
   - `BoostCalculator`: 负责 Token → Points 折算策略。
   - `BoostManager`: 统一入口，协调业务逻辑。
2. **ViewModel 层**
   - `ChatViewModel`：集成 Boost 记录逻辑（聊天、图片、语音）。
   - `ExploreViewModel`：新增 `Boost` Tab 状态，支持切换过滤条件（热门、推荐、Boost）。
3. **UI 层**
   - Compose 组件：`BoostStatusChip`, `BoostSheet`, `BoostLeaderboardTab`。
   - 动画与可访问性：按钮禁用、积分变化过渡、TalkBack 描述。

## 与推荐系统的集成计划
- 在现有「推荐角色」请求参数中加入 `variant = BOOSTED_TOP`.
- 未有后端时，`variant = BOOSTED_TOP` 走客户端排行榜。
- 当后端接口上线时，仅需在 Repository 内切换数据源即可。

## 事件与埋点
- `boost_token_earned`：来源（签到/聊天/图片/语音）、数量。
- `boost_invested`：角色 ID、投入 Points、剩余余额、总 Boost 次数。
- `boost_daily_reward_claimed`：领取的积分数量。
- `boost_leaderboard_viewed`：序号区间（待实现）。
- `boost_shortage_prompted`：触发缺口弹窗（待实现）。

> 当前已接入 Firebase Analytics，事件通过 `BoostManager` 记录。

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

### 核心代码
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostManager.kt` - Boost 功能统一入口
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt` - 数据仓库
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostCalculator.kt` - 积分计算
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostConfig.kt` - 配置常量
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostModels.kt` - 数据模型
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostStateSerializer.kt` - 序列化
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostSeedProvider.kt` - Seed 数据

### UI 组件
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/ui/BoostUiComponents.kt` - UI 组件
- `android_app/app/src/main/kotlin/com/ai/intellimate/boost/ui/BoostLeaderboardTab.kt` - 排行榜 Tab
- `android_app/app/src/main/kotlin/com/ai/intellimate/agent/info/AgentInfoScreen.kt` - 角色主页（集成 Boost）
- `android_app/app/src/main/kotlin/com/ai/intellimate/explore/ExplorePage.kt` - Explore 页面（Boost Tab）

### 资源文件
- `android_app/app/src/main/res/values/strings.xml` - Boost 相关文案
- `android_app/app/src/main/res/drawable/ic_boost_fire.xml` - Boost 图标

### 文档
- `android_app/AGENTS.md` - Boost 功能简要说明
- `android_app/doc/CHAR_BOOSTING_PLAN.md` - 详细实现计划（已合并到本文档）

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
