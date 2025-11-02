# Android App UI 组件列表

本文档详细列出了 Android app 中用户可见的各类 UI 组件的名称及其内涵。

## 一、主页面结构组件

### 1. HomeScreen（主页面）
- **位置**: `HomeScreen.kt`
- **功能**: 应用的主入口页面，包含五个 Tab 页面的容器
- **组成**: 
  - 底部导航栏（AppBottomNavigationBar）
  - 五个 Tab 内容区（Chat、Conversation、Create、Explore、Profile）

### 2. AppBottomNavigationBar（底部导航栏）
- **位置**: `HomeScreen.kt`
- **功能**: 应用底部的主导航栏，包含五个 Tab 按钮
- **Tab 项**:
  - 首页（Home/Chat）
  - 消息（Messages）
  - 创建（Create）
  - 探索（Explore）
  - 我的（Profile）
- **交互**: 点击切换不同的 Tab 页面

### 3. BottomNavigationBarItem（底部导航栏项目）
- **位置**: `HomeScreen.kt`
- **功能**: 单个 Tab 项的 UI 组件
- **显示**: 图标 + 文字标签
- **状态**: 选中/未选中（选中时图标和文字颜色变化）

## 二、聊天相关组件

### 4. ChatPage（聊天页面）
- **位置**: `ChatPage.kt`
- **功能**: 显示与 AI 角色的对话界面
- **组成**:
  - ChatTopBar（顶部栏）
  - PremiumModelTag（高级模型标签）
  - 消息列表（LazyColumn）
  - ChatInput（输入框）
  - ChatMorePanel（更多面板）
  - ChatSettingsDrawer（设置抽屉）

### 5. ChatTopBar（聊天顶部栏）
- **位置**: `ChatTopBar.kt`
- **功能**: 显示当前聊天角色的信息
- **组成**:
  - 返回按钮（可选）
  - 角色头像和名称卡片
  - 更多按钮（打开设置抽屉）
- **交互**: 点击角色卡片跳转到角色详情页

### 6. PremiumModelTag（高级模型标签）
- **位置**: `PremiumModelTag.kt`
- **功能**: 标识当前角色使用高级模型
- **显示条件**: 非 VIP 用户显示，VIP 用户隐藏
- **交互**: 点击跳转到 VIP 中心或登录页
- **样式**: 渐变背景（激活状态：蓝-紫-粉渐变；置灰状态：灰色渐变），包含 VIP 图标和"Premium model"文字

### 7. ChatItem（聊天消息项）
- **位置**: `ChatItem.kt`
- **功能**: 显示单条聊天消息
- **类型**:
  - ChatItemAI（AI 消息）
  - ChatItemUser（用户消息）
- **组成**:
  - 消息气泡（带圆角背景）
  - 语音播放按钮（仅 AI 消息）
  - 文本内容（支持样式化显示）

### 8. ChatItemAI（AI 消息）
- **位置**: `ChatItem.kt`
- **功能**: 显示 AI 角色的回复消息
- **特征**:
  - 左侧对齐
  - 深色半透明背景
  - 支持语音播放按钮
  - 支持开场白自动播放
  - 支持动作文本样式化（斜体显示）

### 9. ChatItemUser（用户消息）
- **位置**: `ChatItem.kt`
- **功能**: 显示用户发送的消息
- **特征**:
  - 右侧对齐
  - 白色半透明背景
  - 支持长按复制

### 10. LoadingAnimation（加载动画）
- **位置**: `ChatItem.kt`
- **功能**: 显示消息生成中的加载状态
- **样式**: 三个跳动的圆点动画

### 11. AgentInfoChatCard（角色介绍卡片）
- **位置**: `ChatItem.kt`
- **功能**: 在聊天页面顶部显示角色介绍信息
- **特征**:
  - 可展开/折叠文本
  - 显示"Intro:"标签
  - 支持多行文本显示

### 12. ExpandableTextWithButton（可展开文本）
- **位置**: `ChatItem.kt`
- **功能**: 支持展开/折叠的长文本组件
- **交互**: 点击箭头按钮展开或折叠

### 13. ChatInput（聊天输入框）
- **位置**: `ChatInput.kt`
- **功能**: 用户输入消息的组件
- **组成**:
  - 多行文本输入框（IntySmallTextField）
  - 旁白输入按钮（括号按钮）
  - 发送/更多按钮（MultiUseAccessButton）
- **限制**: 
  - 最多 4 行
  - 最多 500 字符
  - 游客用户需要年龄验证

### 14. NarrationInputButton（旁白输入按钮）
- **位置**: `ChatInput.kt`
- **功能**: 快速插入括号用于旁白输入
- **显示**: 仅在输入框获得焦点时显示
- **交互**: 点击插入"()"括号

### 15. MultiUseAccessButton（多功能按钮）
- **位置**: `ChatInput.kt`
- **功能**: 根据输入状态切换发送/更多按钮
- **状态**:
  - 有输入内容：显示发送按钮
  - 无输入内容：显示更多/收起按钮

### 16. KeepTalkingButton（继续对话按钮）
- **位置**: `KeepTalkingButton.kt`
- **功能**: 触发 AI 继续对话的功能按钮
- **显示**: 根据用户设置和角色专用设置显示/隐藏
- **交互**: 点击发送"continue"消息
- **样式**: 黑色半透明背景，显示两个播放符号（>>）

### 17. ChatMorePanel（聊天更多面板）
- **位置**: `ChatMorePanel.kt`
- **功能**: 从底部弹出的更多功能面板
- **功能项**:
  - 回复风格（Reply Style）- VIP 功能
  - 举报（Report）
- **交互**: 点击项执行相应操作

### 18. MorePanelItem（更多面板项）
- **位置**: `ChatMorePanel.kt`
- **功能**: 更多面板中的单个功能项
- **组成**: 图标 + 文字 + VIP 标识（可选）

### 19. ChatSettingsDrawer（聊天设置抽屉）
- **位置**: `ChatSettingsDrawer.kt`
- **功能**: 从右侧滑出的设置抽屉
- **内容**:
  - 我的角色（My Persona）:
    - 名称（Name）
    - 代词（Pronouns）
    - 人设（Persona）
  - 设置（Settings）:
    - 举报（Report）
- **交互**: 点击项可编辑或跳转

### 20. ChatPageContainer（聊天页面容器）
- **位置**: `ChatPageContainer.kt`
- **功能**: 管理多个聊天页面的容器（支持左右滑动切换）

## 三、探索页面组件

### 21. ExplorePage（探索页面）
- **位置**: `ExplorePage.kt`
- **功能**: 显示推荐角色列表的页面
- **组成**:
  - TopAppBar（顶部栏）
  - PullToRefreshBox（下拉刷新）
  - ExploreContent（内容区）

### 22. ExploreContent（探索内容）
- **位置**: `ExploreContent.kt`
- **功能**: 显示角色列表的内容区域
- **组成**: LazyColumn 列表，每个项目为 ExploreCharacterCard

### 23. ExploreCharacterCard（探索角色卡片）
- **位置**: `ExploreCharacterCard.kt`
- **功能**: 展示单个推荐角色的卡片
- **组成**:
  - 背景图片（角色头像或背景）
  - 渐变遮罩层
  - 角色名称
  - 角色介绍（最多 3 行）
  - 智能标签（SmartTagsLayout）
- **交互**: 点击跳转到聊天页面

### 24. SmartTagsLayout（智能标签布局）
- **位置**: `SmartTagsLayout.kt`
- **功能**: 自适应布局的标签组件
- **特征**: 
  - 自动换行，智能计算可显示的标签
  - 支持最大行数限制
  - 支持两种样式：TagItem（标准样式）和 LiteTagItem（卡片样式）
  - 确保不会显示被截断的标签
- **样式**:
  - TagItem: 深色背景，白色边框渐变，较大字体
  - LiteTagItem: 深色背景，紫色边框渐变，较小字体

## 四、消息/会话页面组件

### 25. MessagesPage（消息页面）
- **位置**: `MessagesPage.kt`
- **功能**: 显示会话列表的页面
- **组成**:
  - TopAppBar（顶部栏）
  - 会话列表（LazyColumn）
  - 下拉刷新指示器
  - 加载更多指示器

### 26. ChatHistoryItem（会话历史项）
- **位置**: `MessagesPage.kt`
- **功能**: 显示单个会话的列表项
- **组成**:
  - 角色头像（圆形）
  - 角色名称
  - 最后一条消息预览
  - 时间戳
  - 未读标识（红点）
- **状态**: 支持已删除角色显示"(deleted)"标识

### 27. EmptyDataState（空数据状态）
- **位置**: `EmptyStateComponent.kt`
- **功能**: 显示列表为空时的占位组件
- **组成**: 图标 + 提示文字

## 五、个人资料页面组件

### 28. ProfilePage（个人资料页面）
- **位置**: `ProfilePage.kt`
- **功能**: 显示用户个人资料和创建的角色列表
- **组成**:
  - 用户头像和昵称
  - 用户 ID
  - 用户描述
  - 编辑按钮
  - PremiumBanner（VIP 横幅）
  - 创建的角色网格列表

### 29. PremiumBanner（VIP 横幅）
- **位置**: `ProfilePage.kt`
- **功能**: 显示 VIP 订阅状态和操作入口
- **状态显示**:
  - 无有效订阅：显示"Activate now"
  - 有效订阅：显示"Since [购买日期]"
  - 即将过期：显示"Expires on [过期日期]"
- **交互**: 点击跳转到 VIP 中心

### 30. MyAgentCard（我的角色卡片）
- **位置**: `ProfilePage.kt`
- **功能**: 显示用户创建的角色卡片
- **组成**:
  - 角色头像（支持 Shimmer 加载占位）
  - 底部渐变遮罩
  - 角色名称
  - 角色介绍
  - 菜单按钮（编辑/删除）
- **交互**: 
  - 点击卡片：跳转到聊天
  - 点击菜单：显示编辑/删除选项

### 31. ShimmerPlaceholder（闪烁占位符）
- **位置**: `ShimmerPlaceholder.kt`
- **功能**: 图片加载时的占位动画效果
- **样式**: 闪烁动画效果

## 六、登录/注册组件

### 32. LoginScreen（登录屏幕）
- **位置**: `LoginScreen.kt`
- **功能**: 用户登录界面
- **组成**:
  - LoginCloseButton（关闭按钮）
  - LogoImage（Logo 图片）
  - WelcomeTitle（欢迎标题）
  - WelcomeSubtitle（欢迎副标题）
  - GoogleLoginButton（Google 登录按钮）
  - PolicyText（隐私政策文本）

### 33. LoginCloseButton（登录关闭按钮）
- **位置**: `LoginUI.kt`
- **功能**: 关闭登录页面的按钮

### 34. LogoImage（Logo 图片）
- **位置**: `LoginUI.kt`
- **功能**: 显示应用 Logo

### 35. WelcomeTitle（欢迎标题）
- **位置**: `LoginUI.kt`
- **功能**: 显示欢迎文字标题

### 36. WelcomeSubtitle（欢迎副标题）
- **位置**: `LoginUI.kt`
- **功能**: 显示欢迎文字副标题

### 37. GoogleLoginButton（Google 登录按钮）
- **位置**: `LoginUI.kt`
- **功能**: Google 账号登录按钮
- **状态**: 支持加载状态显示

### 38. PolicyText（隐私政策文本）
- **位置**: `PolicyRowUI.kt`
- **功能**: 显示隐私政策和使用条款链接

### 39. RegInfoScreen（注册信息屏幕）
- **位置**: `RegInfoScreen.kt`
- **功能**: 收集用户注册信息（年龄等）

## 七、角色详情组件

### 40. AgentInfoScreen（角色信息屏幕）
- **位置**: `AgentInfoScreen.kt`
- **功能**: 显示角色的详细信息页面
- **组成**:
  - 角色背景图片（AgentBackground）
  - 顶部返回和更多按钮
  - 角色名称和 ID
  - 介绍区域（Intro）
  - 开场白区域（Opening）
  - 底部菜单（举报）

### 41. AgentBackground（角色背景）
- **位置**: `AgentBackground.kt`
- **功能**: 显示角色的背景图片
- **特征**: 支持渐变遮罩（可选）

### 42. AgentSpacerLine（角色分隔线）
- **位置**: `AgentInfoScreen.kt`
- **功能**: 信息区域之间的分隔线
- **样式**: 渐变水平线

### 43. BottomSheetContent（底部菜单内容）
- **位置**: `AgentInfoScreen.kt`
- **功能**: 角色详情页的底部菜单
- **选项**: 举报、取消

## 八、对话框组件

### 44. ForceUpgradeDialog（强制更新对话框）
- **位置**: `DialogUI.kt`
- **功能**: 提示用户必须更新应用
- **特征**: 无法关闭，必须点击更新按钮

### 45. DeleteAccountDialog（删除账号对话框）
- **位置**: `DialogUI.kt`
- **功能**: 确认删除账号的对话框
- **交互**: 确认删除或取消

### 46. UnlimitChatDialog（无限聊天对话框）
- **位置**: `UnlimitChatDialog.kt`
- **功能**: 提示用户聊天次数限制的对话框
- **交互**: 跳转到 VIP 中心或登录页

### 47. ExpiredVipDialog（VIP 过期对话框）
- **位置**: `ExpiredVipDialog.kt`
- **功能**: 提示 VIP 订阅已过期的对话框
- **交互**: 跳转到订阅或登录页

### 48. EditDialog（编辑对话框）
- **位置**: `EditDialog.kt`
- **功能**: 编辑用户信息的对话框
- **支持字段**: 名称、代词、人设等

### 49. ReplyStyleSheet（回复风格底部表单）
- **位置**: `ReplyStyleSheet.kt`
- **功能**: 编辑 AI 回复风格的底部表单
- **权限**: VIP 专享功能

### 50. VipDialog（VIP 对话框）
- **位置**: `VipDialog.kt`
- **功能**: VIP 相关的提示对话框

## 九、通用 UI 组件

### 51. GradientButton（渐变按钮）
- **位置**: `CommonUI.kt`
- **功能**: 通用渐变背景按钮
- **样式**: 紫色到橙色的渐变

### 52. SubmitButton（提交按钮）
- **位置**: `CommonUI.kt`
- **功能**: 提交表单的按钮

### 53. EnterButton（进入按钮）
- **位置**: `CommonUI.kt`
- **功能**: 进入页面的按钮

### 54. MySettingItem（设置项）
- **位置**: `MySettingUI.kt`
- **功能**: 设置列表中的单个设置项
- **组成**: 键值对显示，右侧箭头

### 55. HeartRedDot（红点标识）
- **位置**: `core/design/ui/...`
- **功能**: 未读消息或通知的红点标识

### 56. EmptyStateComponent（空状态组件）
- **位置**: `EmptyStateComponent.kt`
- **功能**: 通用的空状态显示组件

### 57. Shimmer（闪烁效果）
- **位置**: `core/design/ui/Shimmer.kt`
- **功能**: 通用的加载闪烁动画

## 十、输入组件

### 58. IntySmallTextField（小文本输入框）
- **位置**: `TextField.kt`
- **功能**: 自定义的文本输入框
- **特征**: 支持多行、字符限制、焦点管理

### 59. SingleLineTextInputField（单行文本输入框）
- **位置**: `SingleLineTextInputField.kt`
- **功能**: 单行文本输入组件

## 十一、其他组件

### 60. VoicePlayer（语音播放器）
- **位置**: `VoicePlayer.kt`
- **功能**: 播放 AI 语音消息的组件
- **特征**: 支持播放/暂停、自动播放、TTS 生成

### 61. MyModalNavigationDrawer（模态导航抽屉）
- **位置**: `MyModalNavigationDrawer.kt`
- **功能**: 自定义的侧边抽屉组件

### 62. TopAppBar（顶部应用栏）
- **位置**: Material3 组件
- **功能**: 页面顶部的标题栏
- **使用场景**: ExplorePage、MessagesPage 等

### 63. PullToRefreshBox（下拉刷新）
- **位置**: Material3 组件
- **功能**: 下拉刷新功能容器
- **使用场景**: ExplorePage

### 64. CircularProgressIndicator（圆形进度指示器）
- **位置**: Material3 组件
- **功能**: 加载状态指示器
- **使用场景**: 列表加载、刷新等

### 65. LazyColumn（懒加载列）
- **位置**: Compose 组件
- **功能**: 垂直滚动的列表容器
- **使用场景**: 消息列表、会话列表等

### 66. LazyVerticalGrid（懒加载网格）
- **位置**: Compose 组件
- **功能**: 网格布局的列表容器
- **使用场景**: 角色卡片网格

## 十二、设置页面组件

### 69. SettingContent（设置内容）
- **位置**: `SettingContent.kt`
- **功能**: 设置页面的主内容容器
- **组成**:
  - SettingTopBar（顶部栏）
  - SupportAndHelpSection（支持与帮助区域）
  - LogoutButton（退出登录按钮）
  - SettingDialogs（对话框）

### 70. SettingTopBar（设置顶部栏）
- **位置**: `SettingContent.kt`
- **功能**: 设置页面的顶部标题栏
- **组成**: 标题文字 + 返回按钮

### 71. SettingSection（设置项容器）
- **位置**: `SettingUI.kt`
- **功能**: 设置项的分组容器
- **样式**: 带边框和背景的圆角容器

### 72. SettingSwitchItem（设置开关项）
- **位置**: `SettingUI.kt`
- **功能**: 带开关的设置项
- **组成**: 标题文字 + 开关图标（打开/关闭状态）
- **交互**: 点击切换开关状态

### 73. SettingNavigationItem（设置导航项）
- **位置**: `SettingUI.kt`
- **功能**: 可点击跳转的设置项
- **组成**: 标题 + 副标题（可选）+ 红点标识（可选）+ 箭头图标
- **交互**: 点击跳转到对应页面

### 74. SettingInfoItem（设置信息项）
- **位置**: `SettingUI.kt`
- **功能**: 只显示信息的设置项（不可点击）
- **组成**: 标题 + 值 + 红点标识（可选）

### 75. SettingDivider（设置分隔线）
- **位置**: `SettingUI.kt`
- **功能**: 设置项之间的分隔线
- **样式**: 渐变水平线

### 76. LogoutButton（退出登录按钮）
- **位置**: `SettingUI.kt`
- **功能**: 退出登录的按钮
- **样式**: 居中显示文字，带边框容器

### 77. SubscriptionManagementContainer（订阅管理容器）
- **位置**: `SubscriptionUI.kt`
- **功能**: 订阅管理功能的容器组件
- **样式**: 带边框和背景的圆角容器

## 十三、状态指示组件

### 78. Loading States（加载状态）
- **位置**: `ExploreLoadingStates.kt`
- **功能**: 探索页面的加载状态组件
- **类型**: 初始加载、刷新、加载更多、错误状态

### 79. StyledMessageText（样式化消息文本）
- **位置**: `ChatItem.kt`
- **功能**: 支持样式化的消息文本显示
- **特征**: 动作文本斜体显示、特殊格式解析

## 十四、其他功能组件

### 80. TagItem（标准标签项）
- **位置**: `SmartTagsLayout.kt`
- **功能**: 标准样式的标签项
- **样式**: 深色背景，白色边框渐变，较大字体

### 81. LiteTagItem（精简标签项）
- **位置**: `SmartTagsLayout.kt`
- **功能**: 精简样式的标签项（用于卡片）
- **样式**: 深色背景，紫色边框渐变，较小字体

### 82. SettingDialogs（设置对话框）
- **位置**: `SettingContent.kt`
- **功能**: 设置页面相关的对话框集合
- **类型**: 删除账号确认对话框等

### 83. SupportAndHelpSection（支持与帮助区域）
- **位置**: `SettingContent.kt`
- **功能**: 设置页面中的支持与帮助功能区域
- **包含**: 邮件支持、订阅管理、删除账号等功能项

## 总结

以上共列出了 83 个主要的 UI 组件，涵盖了 Android app 的所有用户可见界面元素。这些组件按照功能分为：
- 主页面结构（3 个）
- 聊天相关（17 个）
- 探索页面（4 个）
- 消息/会话（3 个）
- 个人资料（4 个）
- 登录/注册（8 个）
- 角色详情（4 个）
- 对话框（6 个）
- 通用 UI（7 个）
- 输入组件（2 个）
- 设置页面（9 个）
- 状态指示（2 个）
- 其他功能（4 个）

每个组件都经过精心设计，符合 Material Design 3 规范，并提供良好的用户体验。
