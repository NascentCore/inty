# 实时语音通话功能测试场景

## 后期添加功能

- [ ] 【待定，先不做开发】通话结束显示通话记录，将语音通话的内容折叠显示，并标记为语音通话，同时以 chat page 的消息气泡的形式显示
  包含播放按钮，可以播放原始音频（不清楚多复杂）
  - 【待定】无通话内容时，仍然显示某种语音消息气泡，来说明某个时间用户使用了语音通话功能高
  - 【待定】连接过程中取消，显示 Canceled（与微信类似）

- [ ] 扬声器被其他应用占用时可以暂停其他应用使用扬声器、然后通话结束、重新开启其他应用播放（talkie 作为参考）
- [ ] 【待定】麦克风的类似情况（比较罕见，目前无需处理）

## 功能架构概览

- [ ] 所有测试项目都需要提供录屏证据

实时语音通话功能基于 WebSocket 实现，主要组件包括：

- **VoiceCallScreen**: UI 层，处理权限和界面展示
- **VoiceCallViewModel**: 业务逻辑层，管理状态和协调组件
- **AICallRepository**: 数据层，WebSocket 连接管理（带重连机制）
- **AICallDataSource**: WebSocket 数据源实现
- **AudioRecordManager**: 音频录制（16kHz PCM，单声道，16位）
- **AudioStreamPlayer**: 音频播放（24kHz PCM，单声道，16位）

## 测试场景清单

### 1. 连接和网络场景

#### 1.1 正常连接流程

- [x] 启动语音通话，成功建立 WebSocket 连接，并开始语音通话；用户必须首先开口，然后后端探测结束，然后 AI 回复。
- [ ] 播放流畅性
- [x] 连接状态文本正确显示（connecting connected ...）
- [x] 角色名字和头像正确加载和显示
- [x] 手动关闭连接后退出

#### 1.2 失败及其他异常、订阅场景

- [ ] 连接超时处理（界面上显示 error 文本在 App UI）
- [x] 服务器不可达时的错误处理（界面上显示 error 文本在 App UI）
- [x] 网络错误状态正确显示（界面上显示 error 文本在 App UI）
- [ ] 后端非订阅拦截的错误（界面上显示 Toast、直接显示后端提供的可读的简洁错误字符码）
- [ ] 后端订阅拦截（界面上 Dialog）

#### 1.3 网络中断和重连

- [x] 通话过程中网络断开（WiFi/移动数据）然后重新连接，通话会继续

### 2. 权限相关场景

#### 2.1 权限请求流程【@yaxiong 测试】

- [ ] 首次进入时自动请求录音权限
- [ ] 权限被拒绝后的提示和引导
- [x] 权限被永久拒绝后引导到设置页面【@yaxiong 测试过，有录屏】
- [ ] 从设置返回后权限状态正确更新

### 3. 音频录制和播放场景

#### 3.3 静音功能

- [x] 点击静音按钮后停止录制
- [x] 静音状态下仍能接收和播放音频
- [x] 取消静音后恢复录制
- [x] 静音状态正确显示在 UI

### 4. 错误处理场景

#### 4.1 业务错误【@yaxiong】

- [ ] **SUBSCRIPTION_REQUIRED**: 显示订阅引导对话框
- [ ] **LIVE_CHAT_DURATION_LIMIT_REACHED**: 显示时长限制提示
- [ ] **LIVE_CHAT_AGENT_LIMIT_REACHED**: 显示 Agent 数量限制提示
- [ ] 其他错误码显示 Toast 提示

### 5. 生命周期场景

#### 5.2 应用生命周期

- [x] 应用切换到后台时保持连接（或正确处理），应用回到前台时恢复通话

### 8. UI 交互场景

#### 8.1 界面显示

- [x] Agent 头像和名称正确显示
- [x] 连接状态文字正确显示
- [x] 静音按钮状态正确显示
- [x] 结束按钮功能正常

#### 8.2 用户操作

- [x] 点击返回按钮正确退出
- [x] 点击结束按钮正确结束通话
- [x] 点击静音按钮正确切换状态
- [ ] 对话框按钮（订阅、更多信息）功能正常

### 9. 集成测试场景

#### 9.2 与其他功能集成

- [x] 从聊天页面进入语音通话
- [x] 通话结束后返回聊天页面
- [ ] 订阅状态变化对通话的影响

## 关键测试点

### 音频参数

- **录制**: 16kHz, CHANNEL_IN_MONO, ENCODING_PCM_16BIT
- **播放**: 24kHz, CHANNEL_OUT_MONO, ENCODING_PCM_16BIT
- **传输**: Base64 编码

### 队列配置

- **发送队列**: 最大 30 个数据包
- **播放队列**: 最大 250 个数据包
- **警告阈值**: 80% 使用率

### 重连机制

- **最大重连次数**: 5 次
- **重连延迟**: 递增（attempt * 2000ms）
- **重连条件**: 连接失败或异常断开

### 错误码

- `SUBSCRIPTION_REQUIRED` (10001001)
- `LIVE_CHAT_AGENT_LIMIT_REACHED` (10001007)
- `LIVE_CHAT_DURATION_LIMIT_REACHED` (10001008)

## 测试建议

1. **自动化测试**: 重点覆盖连接、权限、音频流程的核心路径
2. **手动测试**: 重点测试网络中断、权限变化、长时间通话等场景
3. **性能测试**: 使用工具监控 CPU、内存、网络使用情况
4. **兼容性测试**: 在不同 Android 版本和设备上测试音频功能
5. **压力测试**: 测试队列满载、快速操作等边界情况

## 相关文件

- UI 层: `android_app/app/src/main/kotlin/com/ai/intellimate/call/VoiceCallScreen.kt`
- ViewModel: `android_app/app/src/main/kotlin/com/ai/intellimate/call/VoiceCallViewModel.kt`
- Repository: `android_app/app/src/main/kotlin/com/ai/intellimate/call/data/AICallRepository.kt`
- DataSource: `android_app/app/src/main/kotlin/com/ai/intellimate/call/data/AICallDataSource.kt`
- 音频录制: `android_app/app/src/main/kotlin/com/ai/intellimate/audio/AudioRecordManager.kt`
- 音频播放: `android_app/app/src/main/kotlin/com/ai/intellimate/audio/AudioStreamPlayer.kt`
