<!-- CREATED_BY_AGENT -->

# Android App 功能与 FEATURE_IDEAS 对照分析

本文档基于对 [android_app/](../android_app/) 代码与 [FEATURE_IDEAS.md](FEATURE_IDEAS.md) 的阅读，整理 IntelliMate Android 端已实现/部分实现的功能与文档中功能创意的对应关系，便于后续产品与开发对齐。

## 一、Android App 当前能力概览

Android 端（Kotlin/Compose）已具备的核心能力包括：

- **聊天**：Room 离线优先、消息流、历史同步、VIP 角色积分解锁
- **语音**：实时语音通话（WebSocket `live-chat`）、TTS 消息语音播放、语音消息组展示
- **角色与探索**：推荐列表、主题专区（CharacterTheme）、角色主页、AI 生成图画廊
- **积分与榜单**：Credits/Boost 体系、签到/每日登录/月度奖励、角色能量榜（BoostLeaderboard）
- **订阅与计费**：Google Play Billing、VipStatusHelper、订阅中心
- **推送**：FCM、agent_message 跳转聊天、反馈请求等
- **版本**：VersionService.checkAppUpgrade、changelog、强制更新/弹窗/设置角标

下文按 FEATURE_IDEAS 中的功能逐项对照「部分实现」情况。

---

## 二、已部分实现的功能（与 FEATURE_IDEAS 对应）

### 1. 功能 1：实时恋爱电话（Live RP）

| 文档能力 | 当前实现情况 |
| --- | --- |
| Live Voice Chat / WebRTC 实时语音 | **已实现**：WebSocket `api/v1/live-chat/{agentId}`，[AICallRepository](../android_app/app/src/main/kotlin/com/ai/intellimate/call/data/AICallRepository.kt)、[AICallDataSource](../android_app/app/src/main/kotlin/com/ai/intellimate/call/data/AICallDataSource.kt)、[VoiceCallScreen](../android_app/app/src/main/kotlin/com/ai/intellimate/call/VoiceCallScreen.kt)，发送/接收音频包（Base64），AudioRecordManager + AudioStreamPlayer |
| TTS / 语音消息 | **已实现**：TtsManager、fetchMsgVoice、语音消息类型（isVoiceMessage）、VoiceMessageGroup 折叠/展开、自动播放设置 |
| Text-to-Image 动态背景/氛围图 | **部分实现**：聊天内「消息生图」 [ChatService.messageGenerateImage](../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/services/ChatService.kt)，角色主页「AI-Generated Images」画廊；无通话中动态背景随情绪变换 |
| Live2D Avatar | **未实现**：代码库中无 Live2D/Cubism 相关依赖或渲染 |
| Text-to-Video / 心动瞬间插片 | **未实现** |
| 通话后摘要、心动瞬间回顾 | **未实现** |

结论：**实时语音 + 消息生图 + TTS 已具备**；Live2D、文生视频、动态背景、通话后复盘均未实现。

---

### 2. 功能 9：Leaderboard 榜单中心

| 文档能力 | 当前实现情况 |
| --- | --- |
| 角色榜（最受欢迎/最会聊） | **部分实现**： [BoostLeaderboardScreen](../android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostLeaderboardScreen.kt) 按 `energy_points` 排序，通过 `AgentService.getRecommendAgents(sort=energy_points)` 拉取； [BoostLeaderboardTrendCalculator](../android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostLeaderboardTrendCalculator.kt) 做排名趋势（升/降/持平） |
| 统一榜单容器（Tabs/时间范围/我的名次） | **部分实现**：有排行榜 Tab 与列表，无「今日/本周/本月」切换，无「我的名次」吸底条 |
| 用户榜（聊得最凶） | **未实现**：仅有角色能量榜，无用户维度榜单 |
| 分享排名卡片、徽章、防刷与隐私 | **未实现** |

结论：**角色能量榜 + 趋势**已部分实现；统一框架、用户榜、时间范围、分享与激励未做。

---

### 3. 功能 3：每日亲密仪式（Morning/Lunch/Bedtime）

| 文档能力 | 当前实现情况 |
| --- | --- |
| 推送与跳转 | **已实现**：FCM、 [FCMConstants](../android_app/core/firebase/src/main/kotlin/ai/sxwl/android/firebase/FCMConstants.kt)（如 agent_message、agent_id），点击通知跳转聊天 |
| 签到与每日奖励 | **已实现**： [CheckIn](../android_app/app/src/main/kotlin/com/ai/intellimate/settings/check/) 签到页、 [BoostRepository](../android_app/app/src/main/kotlin/com/ai/intellimate/boost/BoostRepository.kt) 每日签到/每日登录/月度会员积分 |
| 三时段内容（早安/午间/睡前）、30 秒视频明信片、睡前 Live2D、亲密周报 | **未实现** |

结论：**推送 + 签到 + 积分**已具备；文档中的「三时段仪式」内容与形态未实现。

---

### 4. 功能 4：Yesterday Once More 记忆挚爱馆

| 文档能力 | 当前实现情况 |
| --- | --- |
| 主题专区 / 策展角色集 | **部分实现**： [CharacterTheme](../android_app/library/inty_sdk/inty-kotlin-core/src/main/kotlin/com/inty/api/models/api/v1/characterthemes/CharacterTheme.kt)、 [AgentService.CharacterThemeItem](../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/services/AgentService.kt)、 [AgentCacheManager](../android_app/app/src/main/kotlin/com/ai/intellimate/utils/AgentCacheManager.kt) 缓存主题、Explore 主题专区展示（含圣诞等） |
| 回忆编辑器、记忆卡片上传、记忆档案卡 | **未实现** |

结论：**主题专区与角色策展**已部分实现；Remix、记忆卡片、档案卡未做。

---

### 5. 功能 6：Frontier Models 先锋优享

文档称权益已加入订阅文案；**客户端未发现**「Frontier 模式」开关、徽章或模型版本展示，可能仅在订阅文案/后端配置层面。

---

### 6. 功能 7：Premium 数据全量下载

**未实现**：未发现 `data-exports`、一键导出、导出任务状态、下载链接等接口或 UI。

---

### 7. 功能 10：自创礼物给角色

**未实现**：无送礼物入口、创建礼物、credits 扣费送礼、礼物柜等相关代码。

---

### 8. 更新提醒页面（开屏第一次，提醒用户有新功能）

| 文档能力 | 当前实现情况 |
| --- | --- |
| 版本检查与 changelog | **已实现**： [VersionService.checkAppUpgrade](../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/services/VersionService.kt)、 [MainViewModel.checkAppVersion](../android_app/app/src/main/kotlin/com/ai/intellimate/MainViewModel.kt)，含 changelog、reminder_action（强制更新/弹窗/设置角标） |
| 开屏第一次「新功能」提醒页（类似 c.ai） | **未实现**：当前逻辑是「版本更新」提醒，非首次启动的「新功能」引导页 |

结论：**版本更新与 changelog** 已实现；**首次启动新功能提醒页** 未实现。

---

### 9. 发送语音消息（而非文字转语音）

| 文档能力 | 当前实现情况 |
| --- | --- |
| 实时语音通话中发送语音 | **已实现**： [AICallRepository.sendVoice](../android_app/app/src/main/kotlin/com/ai/intellimate/call/data/AICallRepository.kt)、VoiceCallViewModel.sendVoice |
| 聊天内「语音消息」类型与播放 | **已实现**： [ChatBeans.isVoiceMessage](../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model/ChatBeans.kt)、VoiceMessageGroup、TtsManager/fetchMsgVoice、自动播放设置 |
| 聊天内录一段语音当消息发送（类似 Soul） | **未确认**：代码中有语音消息的**展示与播放**，未看到聊天输入区「录语音发一条消息」的明确入口，需产品确认是否已按「语音消息」形态上线 |

结论：**语音通话 + 语音消息播放** 已实现；**聊天内发送语音消息** 的完整流程需再确认。

---

### 10. Floating IntelliMate Assistant（聊天页悬浮小助手）

| 文档能力 | 当前实现情况 |
| --- | --- |
| 聊天页悬浮按钮 | **部分实现**： [KeepTalkingButton](../android_app/app/src/main/kotlin/com/ai/intellimate/chat/ui/KeepTalkingButton.kt)、 [UiConfigs.ChatPage.FloatingScrollButton](../android_app/app/src/main/kotlin/com/ai/intellimate/ui/UiConfigs.kt)，用于滚动/「继续聊」 |
| 迷你头像、对话小提示、与角色同步、新消息高亮（Clippy 式） | **未实现** |

结论：**悬浮按钮** 有，但形态与文档中的「迷你助手 + 提示 + 角色形象」不一致。

---

### 11. 用户指南 / 轻量提示

文档未单独列，但与体验相关： [intellimate_tips.json](../android_app/app/src/main/assets/intellimate_tips.json) + IntelliMateTips 相关逻辑，用于展示使用技巧（如括号描述动作、Chat Style、Hype an iMate、语音通话、反馈等），可视为轻量「引导/提示」的部分实现。

---

## 三、未在 Android 端发现对应实现的功能

- **功能 2**：幻想导演模式（分镜、文生视频、Live2D 演绎）
- **功能 5**：AI 密友局（群聊、私语、房间状态机）
- **功能 8**：AI 密友主持局（主题群聊、情欲社交）
- **功能 9（Creator Muse）**：付费专属角色、Influence Portal、定期生活片段
- **我们的歌（Memory Song）**：记忆瞬间生成歌曲
- **Regular Review**：按周期生成使用回顾与总结

---

## 四、对照小结（仅「部分实现」）

| FEATURE_IDEAS 功能/点子 | 部分实现内容 |
| --- | --- |
| 功能 1 实时恋爱电话 | 实时语音通话、TTS/语音消息播放、消息生图、角色 AI 图画廊 |
| 功能 9 Leaderboard | 角色能量榜、排名趋势、从后端 sort=energy_points 拉取 |
| 功能 3 每日亲密仪式 | FCM 推送、签到、每日/月度积分奖励 |
| 功能 4 记忆挚爱馆 | 主题专区（CharacterTheme）、Explore 主题展示 |
| 功能 6 Frontier | 仅文档/订阅文案层面，客户端无开关或徽章 |
| 更新提醒（开屏新功能） | 版本检查 + changelog + 强制/弹窗/角标，无首次「新功能」页 |
| 发送语音消息 | 语音通话发送 + 语音消息播放；聊天内发语音消息需确认 |
| Floating 小助手 | 聊天页悬浮按钮（KeepTalking/滚动），非迷你 Clippy 式助手 |

以上均基于当前 android_app 代码与 [FEATURE_IDEAS.md](FEATURE_IDEAS.md) 的对照。
