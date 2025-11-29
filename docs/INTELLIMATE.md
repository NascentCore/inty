# IntelliMate 使用资源指南

> CREATED_BY_AGENT

本指南为不知道如何开始或遇到问题的 IntelliMate 用户，提供一份一目了然的资源索引。内容参考了 Android 客户端的全部内部文档，并按照终端用户能理解的语言重新组织。

## 快速概览（TL;DR）

- **下载安装**：优先通过 [Google Play 内测通道](https://play.google.com/store/apps/details?id=com.ai.intellimate&hl=en-US&ah=EmlT1IB-9hWsv_1I4B8Go9FEIFc) 安装；如需测试新功能，可从 [每日测试版本发布页](https://github.com/NascentCore/inty-app/releases) 获取最新 APK。
- **账号登录**：支持游客身份快速体验，推荐绑定 Google 账号保证聊天记录与 VIP 权益同步（需手机已安装 Google 服务）。
- **主流程**：在 Explore 推荐页发现/关注智能体 → 进入 Chat 聊天 → 使用语音/图片/Keep Talking 等增强能力 → 在 Profile/Settings 管理个人资料与偏好。
- **求助方式**：
  - 应用内：Settings → Help & Feedback（计划补充入口，可先通过内测群反馈）。
  - 测试/运维：参考本指南末尾的“联络渠道与升级流程”。

## 应用主入口图（待补充）

![主界面截图占位](<ADD_HOME_SCREENSHOT_URL_HERE>)

> 请提供一张展示底部导航（Explore / Chats / Profile）的最新截图替换占位符。

## 我想做某件事，该去哪？

| 想要完成的任务 | App 内路径 | 可参考的资源/提示 |
| --- | --- | --- |
| 初次体验/切换环境 | Settings → Debug Backend Endpoint（仅调试构建可见） | 支持在不重新安装的情况下切换到本地/测试服务器（见 `android_app/APP_DYNAMIC_TEST.md` 描述）。 |
| 发现/关注智能体 | 底部导航 Explore | 顶部栏支持双击返回推荐列表第一页；推荐列表支持预加载头像与背景，滑动体验更顺畅。 |
| 与智能体聊天 | 单击任何智能体卡片 → Chat | 支持文本、语音播放（开场白预加载）、即时图片生成。 |
| 创建/编辑智能体 | Explore → “Create”/“+”按钮（或在 Profile → My Agents） | 参考创建流程向导，支持上传头像或使用文本生成背景（涉及 `POST /api/v1/ai/agents/text-to-image`）。 |
| 订阅或恢复购买 | Profile → VIP / Subscription | 集成 Google Play Billing，若遇到扣费问题可查看“故障排查”章节。 |
| 管理通知与隐私 | Settings → Notifications / Privacy | Firebase Cloud Messaging 负责推送，支持随时关闭。 |
| 检查版本/更新 | Settings → About | 版本号基于 Git commit count，若 Play 版本落后可通过测试渠道手动安装最新包。 |
| 提交反馈或举报 | Chat → ⋮ → Report / Profile → Feedback | 举报会通过 Report Service 上报，必要时附截图。 |

## 功能区详解

### 1. Explore（探索）
- 顶部双击即可回到推荐列表第一页，并触发分页刷新。
- 列表提前预加载头像/背景，弱网环境下仍可快速浏览。
- 可切换“推荐”“我的收藏”“自建角色”等标签。
- *截图占位：*
  
  ![Explore 页面截图占位](<ADD_EXPLORE_SCREENSHOT_URL_HERE>)

### 2. Chats（聊天）
- 支持逐条消息的语音播放，音频自动缓存至本地（`AudioCacheManager`）。
- Keep Talking / Message to Image 等按钮会触发相应的 Firebase 事件，便于支持团队定位问题。
- 若遇到“网络错误”提示，可先确认设备是否连接网络，再重试或切换到本地/调试后端。
- *截图占位：*
  
  ![聊天页面截图占位](<ADD_CHAT_SCREENSHOT_URL_HERE>)

### 3. Agents（角色管理）
- 可以从 Explore 卡片直接关注或取消关注。
- 创建或编辑角色时，可上传图片或使用文本生成；生成失败时会提供错误提示（参考 `AvatarManager`）。
- 角色详情页会展示最近生成的 AI 图片，并标注 “AI-Generated”。

### 4. VIP / Subscription
- 订阅选项通过 Google Play Billing 提供；购买后会自动刷新权益。
- 若订单长时间在“处理中”，请打开 Play Store → 账户 → 订阅，检查付款状态。
- 恢复购买（Restore）会重新校验 Google 收据；如仍失败，请截图错误信息反馈给支持团队。

### 5. Settings（设置）
- **Debug Backend Endpoint**：仅调试构建可见，可在不重装的情况下切换 API Base URL；修改后会自动清除网络客户端缓存。
- **Help & Feedback**：建议添加产品帮助文档链接或问卷，方便终端用户提交问题。
- **Remote Config**：多数功能开关（如是否自动启用 Keep Talking）通过 Firebase Remote Config 控制；若看到界面突然变动，可能是远程配置更新导致。

## 故障排查指南

### 网络 / 登录问题
- **无法登录 Google**：确认设备已安装 Google Play 服务；国内设备需手动安装 GMS 套件才能弹出 Google 登录框。
- **页面空白或加载失败**：尝试从系统设置中清除 IntelliMate 的存储，再次启动；或在调试构建下切换回默认后端。

### 聊天与媒体
- **语音无法播放**：检查系统音量；若多次失败，可在 Settings 中清除缓存或重启 App，音频缓存会自动重新生成。
- **图片生成失败**：提示 “IMAGE_GENERATION_LIMIT_REACHED” 表示达到上限，可稍后再试。

### 订阅
- **扣款成功但未解锁**：
  1. 打开 Profile → VIP 页面的“恢复购买”。
  2. 仍无效时，截图订单号（GPA. 开头）发送至支持邮箱。
- **多设备使用**：同一 Google 账号可在多台设备使用，但 Keep Talking/图片生成额度会在服务器侧共享。

### 应用崩溃或性能
- App 内所有崩溃会自动上报 Firebase Crashlytics；若想更快定位问题，请附带：设备型号、系统版本、崩溃发生时的操作步骤。

## 资源清单

- **发布与升级**：
  - Google Play 发布流程文档（`android_app/GOOGLE_PLAY_RELEASE.md`）。
  - 发布说明模板（`android_app/devops/GOOGLE_PLAY_RELEASE_NOTES.md`）。
- **网络 / SDK**：
  - API 架构概览（`android_app/API_ARCH.md`）。
  - 双网络栈说明（`android_app/core/data/NETWORK_MANAGERS_EXPLAINED.md`）。
- **质量保障**：
  - Hermetic 测试建议（`android_app/HERMETIC_TESTS.md`）。
  - 关键 TODO / 架构问题（`android_app/TODOS.md`、`android_app/ARCH_CRITIQUES.md`）。
- **UGC 与合规**：
  - 敏感词清单（`android_app/doc/ugc/README.md`）。
  - AI 内容标识规范（参见 `android_app/AGENTS.md`）。

> 若需对外分享上述内部文档，请评估是否包含敏感信息，再对用户可见版本进行适当裁剪。

## 联络渠道与升级流程

- **应用内反馈**：Settings → Feedback（待上线）或通过应用商店评论。
- **测试人员**：
  - 在 GitHub Issues 或团队协作文档中提交问题，附带日志/截图。
  - 如果需要切换后端或验证新特性，请使用 Debug 构建并通过“Debug Backend Endpoint”面板切换。
- **最终用户**：
  - 建议在欢迎邮件或社区公告中附带本指南链接。
  - 对常见问题（无法登录/订阅问题/媒体加载）可直接回复本指南中的对应段落。

## 需要你补充的内容

1. **最新界面截图**：替换文中的三个截图占位符（主界面、Explore、Chat）。
2. **客服或支持邮箱**：在“联络渠道”中填写正式的客服邮箱或表单链接。
3. **帮助中心链接**：如有 FAQ 或教程视频，请在“资源清单”增加外部链接，方便终端用户一键打开。

完成以上补充后，这份文档即可直接面向非技术用户发布，帮助他们在遇到任何使用疑问时快速定位到对应的资源与解决路径。