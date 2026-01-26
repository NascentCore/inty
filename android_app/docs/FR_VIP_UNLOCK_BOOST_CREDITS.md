# VIP 角色解锁、Boost/Credits 获取与消耗及获取提醒 — 技术方案

<!-- CREATED_BY_AGENT -->

本文档说明 IntelliMate Android 端「VIP 角色解锁」「Boost / Credits（积分）的获取与消耗」以及「积分获取时显示提醒」的实现技术方案，便于后续维护与扩展。

---

## 查看相关功能的用户操作说明

以下为用户在 App 内查看、获取、消耗积分以及解锁 VIP 角色、投入 Boost 时的主要入口与操作步骤，便于产品、测试或客服对照技术实现。

### 查看积分余额与 Boost 排行榜

| 入口 | 路径与说明 |
|------|-------------|
| **签到页** | **Me（我的）** → 顶部日历图标 **或** 「Daily Check-in」每日奖励横幅 → **签到页**；页内顶部展示「我的积分」余额。 |

### 获取积分（用户可执行或自动触发的行为）

| 方式 | 用户操作 | 积分（参考） |
|------|----------|--------------|
| **每日签到** | **Me** → 每日奖励 / 签到入口 → **签到页** → 点击当日 **「签到」** 按钮 | 200，每日限一次 |
| **每日登录** | 用户登录成功后自动发放，无需操作 | 免费 10 / 订阅 20，每日一次 |
| **月度会员** | 订阅用户登录后自动发放，无需操作 | 500/月 |

### 积分增加时的提醒

| 场景 | 用户可见效果 |
|------|--------------|
| **任意积分增加** | 屏幕顶部弹出 **Banner**：「Added X Boost Points! Total Y Boost Points!」，数秒后自动消失。 |

### VIP 角色解锁

| 步骤 | 用户操作 |
|------|----------|
| 1. 进入 VIP 角色聊天 | 从探索、角色主页等进入带 **VIP** 标签的角色聊天页（未订阅且当日未用积分解锁时）。 |
| 2. 看到锁态 | **无历史且查询完成**：弹出 **解锁弹窗**（角色图、订阅按钮、积分解锁按钮）；**有历史或查询中**：底部输入区为 **「Unlock by credits」** 按钮。 |
| 3. 积分解锁 | 点击弹窗内 **「Unlock with Credits」** 或底部 **「Unlock by credits」**；扣 10 积分，成功则当日可聊；不足时 Toast「Credits not enough!」。 |
| 4. 订阅解锁 | 弹窗内点击 **「订阅」** → 进入会员中心完成订阅，订阅成功后自动解锁。 |


---

## 一、概念与术语

| 术语 | 含义 |
|------|------|
| **Credits / 积分** | 与 **Boost 积分（points）** 同义，即 `BoostState.availablePoints`，用于解锁 VIP 角色、投入角色 Boost 等。 |
| **Boost** | 用户将积分投入到某角色，提升该角色在排行榜的「能量」与排名；每次投入以 `BoostConfig.BOOST_STEP_POINTS`（100）为步长。 |
| **VIP 角色** | 带有 `tags` 中含 `"vip"`（不区分大小写）的角色；未订阅用户需满足一定条件才能聊天。 |
| **解锁 VIP 角色** | 通过**积分解锁**或**订阅会员**获得当日与该 VIP 角色聊天的权限。 |

---

## 二、VIP 角色解锁

### 2.1 判定逻辑

由 `ChatViewModel.checkVipAgentUnlock()` 通过 `combine` 合并以下流：

- `VipStatusHelper.vipStatus`：是否已订阅
- `isQueryMsgsCompleted`：是否完成历史消息查询
- `chatRepository.getMessagesFlow(agentId).map { it.isNotEmpty() }`：是否有聊天记录
- `agentFlow`：来自 `characterRepository.getCharacterFlow(agentId)` 的 `CharacterEntity?`（`lastUnlockByCredits`、`tags` 等用于判定）

判定结果 `VipAgentLockType`：

| 条件 | 结果 |
|------|------|
| 角色无 `vip` 标签 **或** 用户已订阅 **或** 今日已用积分解锁（`agent.lastUnlockByCredits == LocalDate.now().toString()`） | `NONE`：不展示锁，正常聊天 |
| 有聊天记录 **或** 尚未完成历史查询 | `INPUT`：底部输入区替换为「Unlock by credits」按钮 |
| 以上都不满足 | `DIALOG`：弹出 `VipAgentUnlockDialog`，阻塞输入 |

`lastUnlockByCredits` 存于 `CharacterEntity.lastUnlockByCredits`，格式 `yyyy-MM-dd`，由 `CharacterDao.unlockAgentByCredits` 在积分解锁成功时更新。（存储技术实现见 **7.2 VIP 积分解锁存储**。）

### 2.2 解锁方式

- **积分解锁**：`ChatViewModel.chatUnlockByCredits()`  
  - 调用 `BoostManager.unlockVipAgent()` 扣减 `BoostConfig.UNLOCK_VIP_AGENT_COST`（10）积分；不足则 Toast「Credits not enough!」  
  - 成功则 `characterRepository.unlockAgentByCredits(agentId)`，将 `last_unlock_by_credits` 设为当日。  
- **订阅解锁**：弹窗内「订阅」按钮执行 `navController.navigate(Routes.Me.VipCenter)`，用户完成订阅后 `VipStatusHelper.isUserVip()` 为 true，`VipAgentLockType` 会变为 `NONE`。

### 2.3 相关实现位置

| 模块 | 路径 |
|------|------|
| 判定与状态 | `ChatViewModel.checkVipAgentUnlock()`、`ChatUIState.VipAgentLockType` |
| 积分解锁 | `ChatViewModel.chatUnlockByCredits()`、`BoostManager.unlockVipAgent()`、`CharacterRepository.unlockAgentByCredits()`、`CharacterDao.unlockAgentByCredits()` |
| 弹窗 UI | `VipAgentUnlockDialog`（`chat/ui/VipAgentUnlockDialog.kt`） |
| 输入区按钮 | `ChatPage` 中 `vipAgentLockType == INPUT` 时的 `Button`，`onClick = chatViewModel::chatUnlockByCredits` |
| VIP 状态 | `VipStatusHelper`、`BillingRepository.vipStatusFlow` |

---

## 三、Boost / Credits 获取与消耗

### 3.1 架构概览

- **BoostManager**：统一入口，协调 `BoostRepository` 与业务；持有 `BoostEvent` 的 `SharedFlow`、对外暴露 `boostState`、`leaderboard`、`pointChanged` 等。
- **BoostRepository**：基于 `BoostStorage` 的读写与 `BoostCalculator` 的规则，维护 `BoostStateSnapshot`、排行榜、每日重置等。
- **BoostStorage**：DataStore + JSON 持久化 `BoostStateSnapshot`；在 `saveBoostState` / `update` 时向 `pointChanged` 发送 `(delta, newTotal)`。
- **BoostConfig**：积分与步长等常量。

### 3.2 积分获取（来源与规则）

所有「增加积分」最终经 `BoostRepository.addPoints(points, source)`，其中 `PointSource` 与单次上限如下：

| PointSource | 触发入口 | 规则 / 常量 |
|-------------|----------|-------------|
| `Chat(agentId)` | `BoostManager.recordChatTokens(agentInfo, message)` | `BoostCalculator.tokensToPoints(estimateTokensFromMessage(message))`；`recordAssistantMessage` 固定 +`CHAT_MESSAGE_POINT_REWARD`（1） |
| `Image(agentId)` | `BoostManager.recordImageGeneration(agentInfo)` | `BoostCalculator.imageGenerationPoints()`，按 `IMAGE_TOKEN_COST`（600）折算 |
| `Audio(agentId)` | `BoostManager.recordAudioPlayback(agentId, agentName)` | `BoostCalculator.audioPlaybackPoints()`，按 `AUDIO_TOKEN_COST`（120）折算 |
| `SignIn` | `BoostManager.claimDailyReward()` | 固定 `DAILY_SIGN_IN_REWARD`（200），每日仅可领一次 |
| `DailyLogin` | `BoostManager.checkClaimReward()` → `claimDailyLoginReward(isVip)` | 免费 10 / VIP 20，每日一次，自动发放在 `checkClaimReward` 时 |
| `MonthlyVip` | `BoostManager.checkClaimReward()` → `claimMonthReward()` | 仅 `VipStatusHelper.isUserVip()` 时为 500/月 |
| `Manual` | `BoostManager.requestManualPoints(points)` | 节日/运营等手动发放，无步长限制 |

除 `SignIn`、`Manual` 外，当日行为积分受 `BoostCalculator.clampDailyGain(dailyEnergyEarned, points)` 限制，上限 `MAX_POINTS_PER_DAY`（10_000）。

`checkClaimReward` 在用户登录成功后由 `MainViewModel.updateLoginState()` 内 `isLoggedIn.collect` 时调用，先 `claimDailyRewardLogin`，约 5 秒后 `claimMonthReward`。

### 3.3 积分消耗

| 场景 | 入口 | 规则 |
|------|------|------|
| 解锁 VIP 角色 | `BoostManager.unlockVipAgent()` | 扣减 `UNLOCK_VIP_AGENT_COST`（10），不足返回 false |
| 投入角色 Boost | `BoostManager.boostAgent(agentInfo, requestedPoints)` | 以 `BOOST_STEP_POINTS`（100）为步长，从 `availablePoints` 扣减；扣减后异步 `AgentService.updateAgentEnergyPoints` 同步服务端，并 emit `BoostEvent.BoostSuccess` |

### 3.4 配置与存储

- **BoostConfig**：`BOOST_STEP_POINTS=100`、`UNLOCK_VIP_AGENT_COST=10`、`DAILY_SIGN_IN_REWARD=200`、`DAILY_LOGIN_REWARD_FREE/VIP=10/20`、`MONTHLY_VIP_REWARD=500`、`MAX_POINTS_PER_DAY=10_000` 等。
- **BoostStorage**：`BoostStateSnapshot` 含 `availablePoints`、`dailyEnergyEarned`、`hasClaimedDailyReward`、`lastResetDate`、`lastClaimedDailyLoginReward`、`lastClaimedMonthReward`、`boostsByAgent` 等；`pointChanged` 为 `Flow<Pair<Int,Int>>`，发出 `(本次变化 delta, 更新后总积分)`。（技术实现见 **7.1 积分状态存储**。）

### 3.5 相关实现位置

| 模块 | 路径 |
|------|------|
| 入口与事件 | `BoostManager`、`BoostEvent`（含 `PointsEarned`、`BoostSuccess`、`Error`） |
| 仓库与规则 | `BoostRepository`、`BoostCalculator`、`BoostConfig` |
| 持久化 | `BoostStorage`、`BoostStateSnapshot` |
| 数据模型 | `BoostModels.kt`（`PointSource`、`BoostState`、`BoostError` 等） |

---

## 四、积分获取时显示提醒

### 4.1 两套「获取提醒」机制

1. **全应用级：任意积分增加时的 Banner（`pointChanged`）**  
   - 数据：`BoostStorage.pointChanged` → `BoostManager.pointChanged`，`Flow<Pair<Int,Int>>`，即 `(delta, newTotal)`。  
   - 消费：`MainActivity` 内 `LaunchedEffect` 收集 `BoostManager.pointChanged`，写入 `creditsPointChanged`。  
   - 展示：当 `creditsPointChanged.first > 0`（仅**增加**）时，弹出 `EnergyCelebrationBanner(onDismissRequest, content = Text(stringResource(R.string.energy_points_add_title, delta, total)))`。  
   - 文案：`energy_points_add_title` 形如「Added %1$d Boost Points! Total %2$d Boost Points!」。

2. **聊天页级：按 `chatMessagePoints` 里程碑的庆祝卡**  
   - 数据：`BoostManager.boostState` 的 `chatMessagePoints`（仅来自 `PointSource.Chat` 的累计）。  
   - 消费：`ChatPage` 在 `shouldShowBoostUi` 为 true 时，将 `boostState.chatMessagePoints` 与 `isCurrentPage` 传入 `EnergyCelebrationBanner(totalPoints, enabled)`。  
   - 展示：该重载根据 `resolveCelebrationLevel(totalPoints)` 在**首次 1、10 的倍数、100 的倍数、1000 的倍数**触发不同层级的 `EnergyCelebrationCard`（First / Tens / Hundreds / Thousands），`enabled` 且为当前页时显示，约 2800ms 后收起。

### 4.2 `BoostEvent.PointsEarned` 的用途

`BoostManager` 在每日登录、月度 VIP、签到、以及各 `record*` / `logPointsEvent` 中会 `_events.emit(BoostEvent.PointsEarned(source, points))`。  
**当前 UI 未消费 `BoostManager.events`**；提醒完全由 `pointChanged`（Banner）和 `chatMessagePoints`（聊天页里程碑）承担。`PointsEarned` 可用于埋点、调试或日后扩展（例如按来源差异化提示）。

### 4.3 相关实现位置

| 模块 | 路径 |
|------|------|
| `pointChanged` 与 Banner | `BoostStorage.pointChanged`、`MainActivity` 中 `BoostManager.pointChanged` + `EnergyCelebrationBanner` |
| 聊天页里程碑 | `ChatPage` 中 `EnergyCelebrationBanner(totalPoints=boostState.chatMessagePoints, enabled=isCurrentPage)` |
| 文案与组件 | `strings.xml`（`energy_points_add_title`、`energy_points_first_title` 等）、`EnergyCelebrationBanner.kt`、`resolveCelebrationLevel` |

---

## 五、简要数据流示意

```
积分增加（任意来源）
  → BoostRepository.addPoints / 其他写操作
  → BoostStorage.saveBoostState 或 update
  → pointChanged.emit(delta, newTotal)
  → MainActivity：delta>0 时 EnergyCelebrationBanner（Added %d / Total %d）

聊天行为产生 Chat 积分
  → BoostRepository.addPoints(..., PointSource.Chat)
  → chatMessagePoints 增加
  → ChatPage：boostState.chatMessagePoints 达 1/10/100/1000 倍数
  → EnergyCelebrationBanner(totalPoints, enabled) 展示对应里程碑卡

VIP 积分解锁
  → BoostManager.unlockVipAgent() 扣 10
  → CharacterRepository.unlockAgentByCredits(agentId)
  → CharacterDao 更新 last_unlock_by_credits = 今日
  → checkVipAgentUnlock 中 agent.lastUnlockByCredits == 今日 → NONE
```

---

## 六、扩展与注意事项

- **VIP 判定**：依赖 `CharacterEntity.tags` 含 `"vip"` 及 `VipStatusHelper`，若 `AgentInfo` 与 `CharacterEntity` 映射变更，需保证 `lastUnlockByCredits` 与 `tags` 正确同步。  
- **积分与 Boost**：Credits 与 Boost 使用同一 `availablePoints` 池；解锁 VIP 与 Boost 的扣减都经 `BoostRepository.deductPoints` / `boostAgent`，由 `BoostStorage` 持久化。  
- **提醒**：仅「积分增加」会触发 `pointChanged` 的正 `delta` 和聊天页 `chatMessagePoints` 上升；解锁、Boost 等消耗不会触发「获得积分」类提醒。  
- **`BoostEvent`**：若需按 `PointSource` 做差异化提醒或埋点，可直接 collect `BoostManager.events` 处理 `PointsEarned`。

---

## 七、积分状态存储与 VIP 积分解锁存储的技术实现

### 7.1 积分状态存储

**介质与 API**  
- 使用 **Jetpack DataStore（typed API）** + **Kotlin Serialization JSON**，通过 `core/data` 的 `jsonDataStore` 扩展创建。  
- 委托：`private val Context.boostState by jsonDataStore("boost_state", BoostStateSnapshot())`，`BoostStorage` 经 `Utils.getApp().boostState` 访问。  
- 文件：`fileName = "boost_state"`，落在应用私有目录下 DataStore 的默认路径（`dataStore` 的 `fileName` 即存储键/文件名）。

**序列化与结构**  
- 整体为 `BoostStateSnapshot`（`@Serializable`），Kotlin Serialization 的 `Json` 编码/解码。  
- `BoostStateSnapshot` 字段：

  | 字段 | 类型 | 含义 |
  |------|------|------|
  | `availablePoints` | Int | 可用积分余额 |
  | `chatMessagePoints` | Int | 来自 Chat 的累计积分（仅 `PointSource.Chat`） |
  | `dailyEnergyEarned` | Int | 当日通过行为已获得的积分，用于 `clampDailyGain` 与每日重置 |
  | `hasClaimedDailyReward` | Boolean | 当日是否已领取签到奖励 |
  | `lastResetDate` | String | 上次执行每日重置的日期 `yyyy-MM-dd` |
  | `boostsByAgent` | Map<String, AgentBoostInfoSnapshot> | key=agentId，value 为单角色 Boost 快照 |
  | `lastClaimedDailyLoginReward` | String | 上次领取每日登录奖励的日期 `yyyy-MM-dd` |
  | `lastClaimedMonthReward` | String | 上次领取月度奖励的月份 `yyyy-MM` |

- `AgentBoostInfoSnapshot`（`@Serializable`，作为 Map 的 value）：`agentId`、`agentName`、`avatarUrl`、`pointsInvested`、`boostCount`、`lastBoostedAt`。

**读写与变更通知**  
- **读**：`BoostStorage.getBoostState()` 使用 `boostState.first()` 取当前快照（`boostState` = `Utils.getApp().boostState.data`，即 DataStore 的 `Flow<BoostStateSnapshot>`）；`BoostStorage.boostState` 为该 Flow，供需流式订阅处使用。  
- **写**：  
  - `saveBoostState(snapshot)`：`Utils.getApp().boostState.updateData { snapshot.also { ... } }`，在回调内 `_pointChanged.trySend(updated.availablePoints - last.availablePoints to updated.availablePoints)`。  
  - `update(transform)`：`updateData { transform(last).also { ... } }`，同样在写入后 `trySend(delta, newTotal)`。  
- **pointChanged**：`Channel<Pair<Int,Int>>`，`receiveAsFlow()` 暴露为 `BoostStorage.pointChanged`，再由 `BoostManager.pointChanged` 转曝；每笔 `saveBoostState` / `update` 成功写入后发送 `(本次变化 delta, 更新后 availablePoints)`。

**调用链**  
- `BoostRepository.addPoints`、`deductPoints`、`boostAgent`、`claimDailyReward`、`claimDailyLoginReward`、`claimMonthReward` 及 `runDailyResetIfNeeded` 等，最终都经 `BoostStorage.saveBoostState` 或 `update` 落盘；`BoostRepository` 在 `init` 中 `getBoostState()` 加载初值并 `runDailyResetIfNeeded`。

**实现位置**  
- `BoostStorage.kt`、`jsonDataStore`（`JsonDattaStoreExt.kt`）、`BoostStateSnapshot` / `AgentBoostInfoSnapshot`（`BoostModels.kt`）。

---

### 7.2 VIP 积分解锁存储

**介质与库**  
- 使用 **Room** 数据库 `CharacterDatabase`，库名 `character.db`，版本 4，`fallbackToDestructiveMigration`。  
- 表：`characters`，主键 `agent_id`（TEXT）；角色元数据与「当日是否已用积分解锁」同表存储。

**字段与含义**  
- 列 `last_unlock_by_credits`（TEXT，可空），对应 `CharacterEntity.lastUnlockByCredits`。  
- 含义：最近一次**用积分解锁该 VIP 角色**的日期，格式 `yyyy-MM-dd`。  
- 判定：`agent.lastUnlockByCredits == LocalDate.now().toString()` 表示当日已用积分解锁，无需再锁或再扣积分。

**写入**  
- **DAO**：`CharacterDao.unlockAgentByCredits(agentId: String, date: String)`。  
- **SQL**：`UPDATE characters SET last_unlock_by_credits = :date WHERE agent_id = :agentId`，**仅更新该列**，不触碰 `energy_points`、`tags` 等。  
- **调用**：`CharacterRepository.unlockAgentByCredits(agentId)` 在 IO 中调用 `dao.unlockAgentByCredits(agentId, LocalDate.now().toString())`；该调用发生于 `BoostManager.unlockVipAgent()` 扣减成功之后、由 `ChatViewModel.chatUnlockByCredits` 驱动。

**读取**  
- `CharacterDao.observeCharacter(agentId)`、`getCharacter(agentId)` 的 `SELECT *` 均包含 `last_unlock_by_credits`。  
- `ChatViewModel.checkVipAgentUnlock` 的 `agentFlow` 来自 `characterRepository.getCharacterFlow(agentId)`，即 `dao.observeCharacter(agentId).filterNotNull()`，拿到的 `CharacterEntity` 含 `lastUnlockByCredits`，直接用于 `agent.lastUnlockByCredits == LocalDate.now().toString()` 判断。

**迁移与 schema**  
- `last_unlock_by_credits` 在 Room 的 `character.db` schema 4 中已存在；`CharacterDatabase` 使用 `fallbackToDestructiveMigration()`，未配置显式 Migration 时，版本升级会清库重建（若需保留旧数据，须自增 version 并添加 Migration）。  
- Schema 导出见 `core/data/schemas/.../CharacterDatabase/4.json`，其中 `characters` 的 `createSql` 含 `last_unlock_by_credits` 列。

**实现位置**  
- `CharacterEntity.kt`（`lastUnlockByCredits` 列）、`CharacterDao.kt`（`unlockAgentByCredits`）、`CharacterRepository.kt`（`unlockAgentByCredits`）、`CharacterDatabase.kt`。
